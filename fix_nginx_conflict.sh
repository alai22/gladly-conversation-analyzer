#!/bin/bash

# Quick fix for nginx conflict
# Removes conflicting default server and fixes nginx config

set -e

echo "🔧 Fixing Nginx Configuration Conflict"
echo "======================================"

# Check existing nginx config
echo "Checking existing nginx configuration..."
if [ -f /etc/nginx/nginx.conf ]; then
    echo "Current nginx.conf exists"
fi

# Check for default server blocks
if grep -q "default_server" /etc/nginx/nginx.conf; then
    echo "Found default_server in main config"
fi

# Check what server blocks exist
echo ""
echo "Checking server blocks in conf.d..."
ls -la /etc/nginx/conf.d/

# Remove our config temporarily
echo ""
echo "Removing current gladly.conf to fix it..."
rm -f /etc/nginx/conf.d/gladly.conf

# Create a simpler config without default_server
cat > /etc/nginx/conf.d/gladly.conf <<'EOF'
server {
    listen 80;
    listen [::]:80;
    
    # Redirect HTTP to HTTPS
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;

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
EOF

echo ""
echo "Testing nginx configuration..."
nginx -t

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Configuration is valid!"
    echo "Starting nginx..."
    systemctl start nginx
    systemctl enable nginx
    
    echo ""
    echo "✓ Nginx should now be running!"
    echo ""
    echo "Check status with: sudo systemctl status nginx"
else
    echo "✗ Configuration test failed"
    exit 1
fi
