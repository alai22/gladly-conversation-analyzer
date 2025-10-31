#!/bin/bash

# Simple HTTPS Setup with Nginx and Let's Encrypt
# For single EC2 instance deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

echo "🔒 HTTPS Setup with Nginx and Let's Encrypt"
echo "==========================================="
echo ""

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then 
    print_error "Please run as root or with sudo"
    exit 1
fi

# Get public IP address
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
print_info "Detected public IP: $PUBLIC_IP"

# Ask for domain name (optional)
echo ""
print_info "For Let's Encrypt SSL certificate, you need a domain name."
print_info "If you don't have a domain, we can set up a self-signed certificate."
echo ""
read -p "Do you have a domain name pointing to this server? (y/N): " HAS_DOMAIN

if [[ "$HAS_DOMAIN" =~ ^[Yy]$ ]]; then
    read -p "Enter your domain name (e.g., example.com): " DOMAIN_NAME
    
    if [ -z "$DOMAIN_NAME" ]; then
        print_error "Domain name cannot be empty"
        exit 1
    fi
    
    USE_LETSENCRYPT=true
    print_status "Will use Let's Encrypt certificate for $DOMAIN_NAME"
else
    USE_LETSENCRYPT=false
    DOMAIN_NAME=$PUBLIC_IP
    print_warning "Will use self-signed certificate (browsers will show security warning)"
fi

# Install Nginx
print_status "Installing Nginx..."
yum update -y
yum install -y nginx

# Install Certbot if using Let's Encrypt
if [ "$USE_LETSENCRYPT" = true ]; then
    print_status "Installing Certbot..."
    yum install -y certbot python3-certbot-nginx
fi

# Create Nginx configuration
print_status "Creating Nginx configuration..."

if [ "$USE_LETSENCRYPT" = true ]; then
    # HTTP configuration (for Let's Encrypt validation)
    cat > /etc/nginx/conf.d/gladly.conf <<EOF
server {
    listen 80;
    server_name $DOMAIN_NAME;

    # Let's Encrypt validation
    location /.well-known/acme-challenge/ {
        root /usr/share/nginx/html;
    }

    # Redirect HTTP to HTTPS
    location / {
        return 301 https://\$host\$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name $DOMAIN_NAME;

    # SSL certificate paths (will be filled by certbot)
    ssl_certificate /etc/letsencrypt/live/$DOMAIN_NAME/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN_NAME/privkey.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Proxy to Docker container
    location / {
        proxy_pass http://localhost:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
EOF
else
    # Self-signed certificate setup
    print_status "Generating self-signed certificate..."
    mkdir -p /etc/nginx/ssl
    
    # Always use a simple CN for self-signed certificates
    CERT_CN="gladly-ec2-instance"
    
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /etc/nginx/ssl/gladly.key \
        -out /etc/nginx/ssl/gladly.crt \
        -subj "/C=US/ST=State/L=City/O=Organization/CN=${CERT_CN}"
    
    # Create nginx config with proper escaping
    # Remove default_server to avoid conflicts with existing nginx config
    cat > /etc/nginx/conf.d/gladly.conf <<'NGINXEOF'
server {
    listen 80;
    listen [::]:80;
    
    # Redirect HTTP to HTTPS
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
NGINXEOF
    
    # Add SSL and proxy config (using single quotes to prevent variable expansion)
    cat >> /etc/nginx/conf.d/gladly.conf <<'NGINXEOF'

    # SSL certificate
    ssl_certificate /etc/nginx/ssl/gladly.crt;
    ssl_certificate_key /etc/nginx/ssl/gladly.key;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Proxy to Docker container
    location / {
        proxy_pass http://localhost:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
NGINXEOF
fi

# Test Nginx configuration
print_status "Testing Nginx configuration..."
nginx -t

if [ $? -ne 0 ]; then
    print_error "Nginx configuration test failed"
    exit 1
fi

# Start and enable Nginx
print_status "Starting Nginx..."
systemctl start nginx
systemctl enable nginx

# Configure firewall
print_status "Configuring firewall..."
if command -v firewall-cmd &> /dev/null; then
    firewall-cmd --permanent --add-service=http
    firewall-cmd --permanent --add-service=https
    firewall-cmd --reload
elif command -v ufw &> /dev/null; then
    ufw allow 80/tcp
    ufw allow 443/tcp
fi

# Get Let's Encrypt certificate if using domain
if [ "$USE_LETSENCRYPT" = true ]; then
    print_status "Obtaining Let's Encrypt certificate..."
    certbot --nginx -d $DOMAIN_NAME --non-interactive --agree-tos --email admin@$DOMAIN_NAME --redirect
    
    if [ $? -eq 0 ]; then
        print_status "SSL certificate installed successfully!"
        
        # Set up auto-renewal
        print_status "Setting up certificate auto-renewal..."
        systemctl enable certbot.timer
        systemctl start certbot.timer
    else
        print_error "Failed to obtain SSL certificate"
        print_info "Make sure your domain points to this server's IP: $PUBLIC_IP"
        exit 1
    fi
fi

# Reload Nginx
print_status "Reloading Nginx..."
systemctl reload nginx

# Display results
echo ""
echo "🎉 HTTPS Setup Complete!"
echo "======================"
echo ""

if [ "$USE_LETSENCRYPT" = true ]; then
    print_status "Your application is now available at:"
    echo "  HTTPS: https://$DOMAIN_NAME"
    echo "  HTTP:  http://$DOMAIN_NAME (redirects to HTTPS)"
else
    print_status "Your application is now available at:"
    echo "  HTTPS: https://$PUBLIC_IP"
    echo "  HTTP:  http://$PUBLIC_IP (redirects to HTTPS)"
    print_warning "Note: Browsers will show a security warning for self-signed certificate"
    print_info "To avoid warnings, consider getting a domain name and using Let's Encrypt"
fi

echo ""
print_info "Nginx is proxying HTTPS traffic to your Docker container on port 5000"
print_info "Your Docker container continues running as before"
echo ""
print_status "Setup completed successfully!"
