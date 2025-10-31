# Simple HTTPS Setup Guide - Nginx + Let's Encrypt

This is the **simplest way** to add HTTPS to your existing EC2 instance running Docker.

## 🚀 Quick Setup (5-15 minutes)

### Option 1: With Domain Name (Recommended)

If you have a domain name:

```bash
# On your EC2 instance
git pull origin main
chmod +x setup_https_nginx.sh
sudo ./setup_https_nginx.sh
```

The script will:
- Install Nginx
- Install Certbot (Let's Encrypt)
- Get a free SSL certificate
- Configure HTTPS → HTTP proxy to your Docker container
- Set up auto-renewal

**Result:** Your app will be at `https://your-domain.com` with a valid SSL certificate!

### Option 2: Without Domain (Self-Signed Certificate)

If you don't have a domain:

```bash
# On your EC2 instance
git pull origin main
chmod +x setup_https_nginx.sh
sudo ./setup_https_nginx.sh
```

When asked "Do you have a domain?", say **No**.

**Result:** Your app will be at `https://your-ip-address`, but browsers will show a security warning (you can click "Advanced" → "Proceed anyway").

## 📋 What This Does

1. **Installs Nginx** - Reverse proxy server
2. **Sets up SSL** - Let's Encrypt (free) or self-signed
3. **Configures HTTPS** - Listens on port 443
4. **Proxies to Docker** - Forwards requests to `localhost:5000` (your Docker container)
5. **HTTP Redirect** - Automatically redirects HTTP to HTTPS

## 🔧 How It Works

```
Internet → HTTPS (443) → Nginx → HTTP (5000) → Docker Container
         → HTTP (80) → Redirects to HTTPS
```

Your Docker container stays exactly the same - it still runs on port 5000. Nginx just adds HTTPS in front of it.

## ✅ Benefits

- ✅ **No new infrastructure** - Uses your existing EC2 instance
- ✅ **No IAM permissions needed** - Just installs software
- ✅ **Free SSL certificate** - Let's Encrypt (if you have a domain)
- ✅ **Auto-renewal** - Certificate renews automatically
- ✅ **Works with your Git workflow** - No changes to deploy.sh
- ✅ **Fast setup** - 5-15 minutes vs hours with Terraform

## 🔄 After Setup

Your deployment workflow stays the same:

```bash
# Regular deployments
git pull origin main
./deploy.sh production
```

Nginx will continue proxying HTTPS to your Docker container.

## 🌐 Domain Setup (Optional)

If you want to use Let's Encrypt but don't have a domain:

1. **Get a free domain** from:
   - Freenom (.tk, .ml, .ga)
   - Namecheap (if you want a paid one)
   - Or use any domain you own

2. **Point domain to your IP**:
   - Create an A record: `your-domain.com` → `your-ec2-ip`

3. **Run the setup script** and enter your domain name

## 🛠️ Troubleshooting

### Check Nginx Status
```bash
sudo systemctl status nginx
```

### View Nginx Logs
```bash
sudo tail -f /var/log/nginx/error.log
```

### Test Configuration
```bash
sudo nginx -t
```

### Reload Nginx After Changes
```bash
sudo systemctl reload nginx
```

### Check Docker Container
```bash
docker ps
docker logs gladly-prod
```

## 📝 Configuration Files

- **Nginx config:** `/etc/nginx/conf.d/gladly.conf`
- **SSL certificates (Let's Encrypt):** `/etc/letsencrypt/live/your-domain/`
- **SSL certificates (self-signed):** `/etc/nginx/ssl/`

## 🔒 Security

- ✅ Automatic HTTP → HTTPS redirect
- ✅ Modern SSL/TLS protocols (TLS 1.2, 1.3)
- ✅ Security headers (HSTS)
- ✅ Let's Encrypt auto-renewal (if using domain)

## 🎯 Next Steps

1. **Run the setup script** on your EC2 instance
2. **Access your app** via HTTPS
3. **Continue using your normal Git workflow** for deployments

That's it! Much simpler than Terraform! 🎉
