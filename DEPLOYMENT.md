# CSAT Service Deployment Guide

## Production Deployment on Ubuntu

This guide covers deploying the CSAT survey service to an Ubuntu server for public internet access.

### Prerequisites

- Ubuntu 20.04 or later
- Root or sudo access
- Domain names: `csat.service.ru` and `csat.anotherservice.eng`
- SSL certificates (Let's Encrypt recommended)

### Step 1: System Setup

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3.10 python3.10-venv python3-pip \
  nginx certbot python3-certbot-nginx curl git supervisor

# Create csat user
sudo useradd -m -s /bin/bash csat

# Create application directories
sudo mkdir -p /opt/csat /var/lib/csat /var/log/csat
sudo chown -R csat:csat /opt/csat /var/lib/csat /var/log/csat
sudo chmod 750 /var/lib/csat /var/log/csat
```

### Step 2: Application Setup

```bash
# Clone or copy your application
sudo -u csat git clone <your-repo> /opt/csat
# OR
sudo cp -r /path/to/csat /opt/csat
sudo chown -R csat:csat /opt/csat

# Navigate to app directory
cd /opt/csat

# Create Python virtual environment
sudo -u csat python3.10 -m venv venv

# Activate venv and install dependencies
sudo -u csat bash -c 'source venv/bin/activate && pip install -r requirements.txt'
```

### Step 3: Create requirements.txt

```bash
cat > /opt/csat/requirements.txt << 'EOF'
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6
requests==2.31.0
jinja2==3.1.2
python-dotenv==1.0.0
EOF
```

### Step 4: Environment Configuration

Create `/opt/csat/.env`:

```bash
sudo cat > /opt/csat/.env << 'EOF'
# Server Configuration
CSAT_HOST=127.0.0.1
CSAT_PORT=8000
CSAT_WORKERS=4
CSAT_RELOAD=false

# Data and Logging
CSAT_DATA_DIR=/var/lib/csat
CSAT_LOG_DIR=/var/log/csat

# Survey Configuration
CSAT_SURVEY_EXPIRY_HOURS=24

# CORS Configuration (comma-separated)
CSAT_ALLOWED_ORIGINS=https://csat.service.ru,https://csat.anotherservice.eng

# Jira Integration (set your webhook URL)
JIRA_WEBHOOK_URL=https://your-jira-instance.com/rest/api/3/webhooks
EOF

sudo chown csat:csat /opt/csat/.env
sudo chmod 600 /opt/csat/.env
```

### Step 5: Systemd Service

Create `/etc/systemd/system/csat.service`:

```bash
sudo cat > /etc/systemd/system/csat.service << 'EOF'
[Unit]
Description=CSAT Survey Service
After=network.target

[Service]
Type=notify
User=csat
WorkingDirectory=/opt/csat
Environment="PATH=/opt/csat/venv/bin"
EnvironmentFile=/opt/csat/.env

# Run the application
ExecStart=/opt/csat/venv/bin/python -m uvicorn main:app \
  --host ${CSAT_HOST} \
  --port ${CSAT_PORT} \
  --workers ${CSAT_WORKERS} \
  --access-log

# Restart policy
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=csat

# Security
PrivateTmp=yes
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/var/lib/csat /var/log/csat

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable csat
sudo systemctl start csat

# Check status
sudo systemctl status csat
```

### Step 6: Nginx Reverse Proxy

Create `/etc/nginx/sites-available/csat`:

```bash
sudo cat > /etc/nginx/sites-available/csat << 'EOF'
upstream csat_backend {
    server 127.0.0.1:8000;
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name csat.service.ru csat.anotherservice.eng;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS Server - Russian
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name csat.service.ru;

    ssl_certificate /etc/letsencrypt/live/csat.service.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/csat.service.ru/privkey.pem;

    # SSL Configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Logging
    access_log /var/log/nginx/csat.access.log combined;
    error_log /var/log/nginx/csat.error.log warn;

    # Compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
    gzip_min_length 1000;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=general:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=submit:10m rate=5r/s;

    location / {
        limit_req zone=general burst=20 nodelay;
        proxy_pass http://csat_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "upgrade";
    }

    location /survey/*/submit {
        limit_req zone=submit burst=5 nodelay;
        proxy_pass http://csat_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        expires 30d;
        add_header Cache-Control "public, immutable";
        proxy_pass http://csat_backend;
    }
}

# HTTPS Server - English
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name csat.anotherservice.eng;

    ssl_certificate /etc/letsencrypt/live/csat.anotherservice.eng/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/csat.anotherservice.eng/privkey.pem;

    # SSL Configuration (same as above)
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Logging
    access_log /var/log/nginx/csat-eng.access.log combined;
    error_log /var/log/nginx/csat-eng.error.log warn;

    # Compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
    gzip_min_length 1000;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=general_eng:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=submit_eng:10m rate=5r/s;

    location / {
        limit_req zone=general_eng burst=20 nodelay;
        proxy_pass http://csat_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "upgrade";
    }

    location /survey/*/submit {
        limit_req zone=submit_eng burst=5 nodelay;
        proxy_pass http://csat_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        expires 30d;
        add_header Cache-Control "public, immutable";
        proxy_pass http://csat_backend;
    }
}
EOF

# Enable the site
sudo ln -s /etc/nginx/sites-available/csat /etc/nginx/sites-enabled/
sudo systemctl reload nginx
```

### Step 7: SSL Certificates (Let's Encrypt)

```bash
# Install certificates
sudo certbot certonly --nginx \
  -d csat.service.ru \
  -d csat.anotherservice.eng \
  --email your-email@example.com \
  --agree-tos \
  --non-interactive

# Auto-renewal (runs daily)
sudo certbot renew --quiet

# Verify auto-renewal is set up
sudo systemctl enable certbot.timer
```

### Step 8: Firewall Configuration

```bash
# Enable UFW (if not already enabled)
sudo ufw enable

# Allow SSH, HTTP, HTTPS
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Verify rules
sudo ufw status
```

### Step 9: Monitoring and Logs

```bash
# View service logs
sudo journalctl -u csat -f

# View Nginx access logs
sudo tail -f /var/log/nginx/csat.access.log

# View application logs
sudo tail -f /var/log/csat/app.log

# Monitor service health
sudo systemctl status csat
```

### Step 10: Health Check

```bash
# Test the service is running
curl -I https://csat.service.ru/survey/test 2>/dev/null | head -n 1

# Check service status
sudo systemctl status csat --no-pager

# Check Nginx status
sudo systemctl status nginx --no-pager
```

## Production Checklist

- [ ] Environment variables configured in `.env`
- [ ] SSL certificates obtained and installed
- [ ] Nginx reverse proxy configured
- [ ] Systemd service created and enabled
- [ ] Firewall rules configured
- [ ] Log rotation configured
- [ ] Monitoring/alerting configured
- [ ] Backup strategy for surveys.json
- [ ] JIRA_WEBHOOK_URL configured
- [ ] CORS origins configured correctly

## Important Notes

1. **Data Backup**: Regularly backup `/var/lib/csat/surveys.json`
2. **Log Rotation**: Configure logrotate for `/var/log/csat/app.log`
3. **SSL Renewal**: Let's Encrypt certificates auto-renew (check certbot timer)
4. **Resource Limits**: Monitor memory/CPU usage with `htop`
5. **Rate Limiting**: Adjust Nginx `limit_req` based on your traffic

## Troubleshooting

### Service won't start
```bash
sudo systemctl status csat -l
sudo journalctl -u csat -n 50
```

### Nginx 502 Bad Gateway
- Check if backend is running: `sudo systemctl status csat`
- Check if port 8000 is listening: `sudo ss -tulpn | grep 8000`

### SSL certificate issues
```bash
sudo certbot renew --force-renewal
sudo systemctl reload nginx
```

### Permission denied errors
- Check file ownership: `ls -la /var/lib/csat`
- Fix if needed: `sudo chown -R csat:csat /var/lib/csat /var/log/csat`
