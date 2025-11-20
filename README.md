# CSAT Survey Service

A production-ready FastAPI survey service for collecting customer satisfaction feedback with multi-language support and Jira integration.

**Quick Links:** [Quick Start](#quick-start) | [Deployment](#deployment) | [Configuration](#configuration) | [Operations](#operations) | [Updates](#safe-updates) | [Troubleshooting](#troubleshooting)

---

## Overview

The CSAT (Customer Satisfaction) survey service:
- ✅ Generates unique survey links for Jira tickets
- ✅ Collects 1-5 star ratings with optional comments
- ✅ Supports Russian (survey.ostrovok.ru) and English (survey.emergingtravel.com)
- ✅ Special forms for APIR/APIO projects
- ✅ Automatic webhook delivery to Jira with retries
- ✅ Production-ready with security hardening
- ✅ Data protection - surveys never lost on updates

---

## Quick Start

### For Local Development

```bash
# Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run development server
python main.py

# Access at http://localhost:8000
```

### For Production Deployment

```bash
# On Ubuntu server
cd /opt
sudo git clone https://gitlab.ostrovok.ru/atlassian_team/csat-service.git csat
cd csat
sudo bash deploy.sh

# Then: Configure .env, Setup Nginx, Install SSL (see Deployment below)
```

---

## Deployment

### Prerequisites
- Ubuntu 20.04+ server
- Root or sudo access
- Domains: `survey.ostrovok.ru` and `survey.emergingtravel.com`
- DNS configured to point to your server

### Step 1: Clone Repository

```bash
cd /opt
sudo git clone https://gitlab.ostrovok.ru/atlassian_team/csat-service.git csat
cd csat
```

### Step 2: Run Automated Setup

```bash
sudo bash deploy.sh
```

This script automatically:
- ✅ Installs system dependencies (Python, Nginx, Certbot)
- ✅ Creates `csat` user for service isolation
- ✅ Creates directories (`/var/lib/csat`, `/var/log/csat`)
- ✅ Sets up Python virtual environment
- ✅ Installs Python packages
- ✅ Creates `.env` configuration file
- ✅ Creates systemd service
- ✅ Starts the service

### Step 3: Configure Environment

Edit the configuration:

```bash
sudo nano /opt/csat/.env
```

Verify key settings:

```bash
# CORS - Your production domains
CSAT_ALLOWED_ORIGINS=https://survey.ostrovok.ru,https://survey.emergingtravel.com

# Jira - Your webhook endpoint
JIRA_WEBHOOK_URL=https://help.etg.team/rest/cb-automation/latest/hooks/...

# Server - Usually keep defaults
CSAT_HOST=127.0.0.1
CSAT_PORT=8000
CSAT_WORKERS=4
```

Restart after changes:
```bash
sudo systemctl restart csat
```

### Step 4: Configure Nginx

Create `/etc/nginx/sites-available/csat`:

```bash
sudo nano /etc/nginx/sites-available/csat
```

Paste the Nginx configuration from the "Nginx Configuration" section below.

Enable it:

```bash
sudo ln -s /etc/nginx/sites-available/csat /etc/nginx/sites-enabled/
sudo nginx -t  # Test configuration
sudo systemctl reload nginx
```

### Step 5: Install SSL Certificates

```bash
sudo certbot certonly --nginx \
  -d survey.ostrovok.ru \
  -d survey.emergingtravel.com \
  --email your-email@example.com \
  --agree-tos \
  --non-interactive
```

Verify:
```bash
sudo certbot certificates
```

### Step 6: Test

```bash
# Service running
sudo systemctl status csat

# Port 8000 listening
sudo ss -tulpn | grep 8000

# HTTPS access
curl https://survey.ostrovok.ru/

# Logs
sudo journalctl -u csat -f
```

---

## Configuration

### Environment Variables

All settings in `/opt/csat/.env`:

| Variable | Default | Purpose |
|----------|---------|---------|
| `CSAT_HOST` | `127.0.0.1` | Listen address (internal) |
| `CSAT_PORT` | `8000` | Internal port |
| `CSAT_WORKERS` | `4` | Worker processes |
| `CSAT_RELOAD` | `false` | Never reload in production |
| `CSAT_DATA_DIR` | `/var/lib/csat` | surveys.json location |
| `CSAT_LOG_DIR` | `/var/log/csat` | app.log location |
| `CSAT_SURVEY_EXPIRY_HOURS` | `24` | Link validity (hours) |
| `CSAT_ALLOWED_ORIGINS` | (required) | CORS origins (comma-separated) |
| `JIRA_WEBHOOK_URL` | (required) | Jira webhook endpoint |

### Nginx Configuration

**Note:** If using a centralized Nginx (managed via GitLab), skip the basic config below and use your existing IP-based access control instead.

**For standalone deployments**, use:

```nginx
upstream csat_backend {
    server 127.0.0.1:8000;
}

# HTTP to HTTPS redirect
server {
    listen 80;
    listen [::]:80;
    server_name survey.ostrovok.ru survey.emergingtravel.com;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS - Russian
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name survey.ostrovok.ru;

    ssl_certificate /etc/letsencrypt/live/survey.ostrovok.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/survey.ostrovok.ru/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;

    access_log /var/log/nginx/csat.access.log;
    error_log /var/log/nginx/csat.error.log;

    gzip on;
    gzip_types text/plain text/css application/json application/javascript;

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

# HTTPS - English (same config but for survey.emergingtravel.com)
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name survey.emergingtravel.com;

    ssl_certificate /etc/letsencrypt/live/survey.emergingtravel.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/survey.emergingtravel.com/privkey.pem;

    # (copy SSL and security settings from Russian server block above)
    # (copy location blocks from Russian server block above)
}
```

### API Endpoint Protection

The `/survey/create` endpoint should be protected to prevent unauthorized survey creation.

**Option 1: Nginx IP Allowlist (Recommended for centralized setups)**

```nginx
location = /survey/create {
  allow 10.11.12.13;        # Your Jira server IP
  allow 10.11.12.14;        # Your other Jira server IP
  deny all;
  proxy_pass http://csat_backend;
  include snippets.d/proxy_params;
}
```

This approach:
- ✅ Blocks unauthorized requests at Nginx level (fast)
- ✅ Works with all backend server implementations
- ✅ Easy to audit and manage
- ✅ Requires no code changes

**Option 2: Python IP Validation (Defense in depth)**

Add to `/opt/csat/.env`:
```bash
CSAT_ALLOWED_IPS=10.11.12.13,10.11.12.14
```

Then the application validates IPs at the Python level as well.

### Log Rotation

Logs are automatically rotated daily by the application with no additional configuration needed. The service keeps 7 days of logs in `/var/log/csat/`:

```bash
# View logs
ls -lh /var/log/csat/

# Check current log
sudo tail -f /var/log/csat/app.log

# View rotated logs
sudo ls -la /var/log/csat/app.log.*
```

Logs rotate automatically at midnight and old logs are removed after 7 days.

---

## Operations

### Service Management

```bash
# Check status
sudo systemctl status csat

# Control service
sudo systemctl start csat
sudo systemctl stop csat
sudo systemctl restart csat

# View logs (real-time)
sudo journalctl -u csat -f

# Recent logs (50 lines)
sudo journalctl -u csat -n 50

# Auto-start on boot
sudo systemctl enable csat
```

### Monitoring

```bash
# Is service running?
sudo systemctl is-active csat

# Is port listening?
sudo ss -tulpn | grep 8000

# Resource usage
ps aux | grep uvicorn

# Disk space
du -sh /var/lib/csat /var/log/csat

# Certificate expiry
sudo certbot certificates
```

### Common Tasks

```bash
# Backup survey data
sudo cp /var/lib/csat/surveys.json /var/lib/csat/surveys.json.backup.$(date +%Y%m%d_%H%M%S)

# View survey data
sudo cat /var/lib/csat/surveys.json | jq .

# Check app logs
sudo tail -f /var/log/csat/app.log

# Check Nginx logs
sudo tail -f /var/log/nginx/csat.access.log
```

---

## Safe Updates

**Your survey data is protected and will never be overwritten by Git operations.**

### Protected Files (Never Tracked or Overwritten)
- `surveys.json` - Live survey data
- `.env` - Configuration
- `app.log*` - Application logs

### Update Process

```bash
# On your server
cd /opt/csat

# 1. Backup (optional but recommended)
sudo -u csat cp /var/lib/csat/surveys.json /var/lib/csat/surveys.json.backup.$(date +%Y%m%d_%H%M%S)

# 2. Pull latest code
sudo git pull origin master

# 3. Install new dependencies if needed
sudo -u csat /opt/csat/venv/bin/pip install -r requirements.txt

# 4. Restart service
sudo systemctl restart csat

# 5. Verify
sudo systemctl status csat
```

### Emergency Restore

```bash
# List available backups
ls -la /var/lib/csat/surveys.json.backup*

# Restore from backup
sudo cp /var/lib/csat/surveys.json.backup.YYYYMMDD_HHMMSS /var/lib/csat/surveys.json
sudo chown csat:csat /var/lib/csat/surveys.json

# Restart
sudo systemctl restart csat
```

---

## Troubleshooting

### Service Won't Start

```bash
# What went wrong?
sudo systemctl status csat -l
sudo journalctl -u csat -n 100

# Permission issues?
ls -la /var/lib/csat /var/log/csat

# Fix permissions
sudo chown -R csat:csat /var/lib/csat /var/log/csat
sudo chmod 750 /var/lib/csat /var/log/csat
```

### Nginx 502 Bad Gateway

```bash
# Check backend
sudo ss -tulpn | grep 8000

# Check service
sudo systemctl status csat

# Check error log
sudo tail -f /var/log/nginx/csat.error.log
```

### SSL Certificate Issues

```bash
# Check expiry
sudo certbot certificates

# Certificate details
sudo openssl x509 -in /etc/letsencrypt/live/survey.ostrovok.ru/cert.pem -noout -dates

# Dry run renewal
sudo certbot renew --dry-run

# Manual renewal
sudo certbot renew --force-renewal
```

### High Memory Usage

```bash
# Check workers
ps aux | grep uvicorn

# Reduce workers (edit .env)
sudo nano /opt/csat/.env
# Change: CSAT_WORKERS=2

# Restart
sudo systemctl restart csat
```

### Logs Growing Too Large

Logs are automatically rotated daily at midnight and kept for 7 days. No configuration needed.

Check status:
```bash
ls -lh /var/log/csat/
```

---

## Architecture

```
┌──────────────────────────────────┐
│     Public Internet (HTTPS)      │
└────────────────┬─────────────────┘
                 │
     ┌───────────▼──────────┐
     │ Nginx Reverse Proxy  │
     │  Port 443 (SSL)      │
     │  Rate Limiting       │
     │  Security Headers    │
     └───────────┬──────────┘
                 │
     ┌───────────▼──────────┐
     │   FastAPI App        │
     │ Port 8000 (local)    │
     │ 4 workers            │
     │ Non-root user        │
     └───────────┬──────────┘
                 │
     ┌───────────▼──────────┐
     │  /var/lib/csat/      │
     │ surveys.json (data)  │
     │ app.log (logs)       │
     └──────────────────────┘
```

---

## Security & Reliability

### Implemented
- ✅ CORS restricted to specific domains
- ✅ HTTP methods limited (GET, POST only)
- ✅ Security headers (HSTS, X-Frame-Options, etc)
- ✅ Rate limiting (10 req/s general, 5 req/s submit)
- ✅ SSL/TLS with strong ciphers
- ✅ Service runs as non-root user
- ✅ Data directory permissions (750)
- ✅ No debug mode in production
- ✅ Thread-safe operations with locks (prevents race conditions)
- ✅ Atomic file writes (prevents data corruption)
- ✅ Data consistency guarantees across worker processes
- ✅ `/survey/create` endpoint protected (IP allowlist recommended)

### Best Practices
- Set `CSAT_ALLOWED_ORIGINS` to your domains
- Set `JIRA_WEBHOOK_URL` for Jira integration
- Use strong SSL/TLS settings
- Monitor logs regularly
- Backup surveys.json periodically
- Keep system packages updated

---

## Features

### Multi-Language
- 🇷🇺 Russian: survey.ostrovok.ru
- 🇬🇧 English: survey.emergingtravel.com

### Survey Management
- Unique tokens per survey
- 24-hour expiration (configurable)
- Automatic cleanup
- Protected from overwrite

### Jira Integration
- Webhook delivery
- Automatic retry with exponential backoff
- Error logging

### Form Variations
- **General**: Rating + comment
- **APIR/APIO**: Rating + API name + comment

---

## Project Structure

```
/opt/csat/
├── main.py                 # FastAPI app
├── requirements.txt        # Dependencies
├── deploy.sh              # Setup script
├── .gitignore             # Data protection
├── static/
│   ├── index.html         # Survey form
│   ├── csat.js            # Form logic
│   └── csat.css           # Styling
├── templates/
│   └── 403.html           # Error page
└── README.md              # This file

/var/lib/csat/
└── surveys.json           # Survey data

/var/log/csat/
└── app.log*               # Logs (rotated)
```

---

## API

### Create Survey
```bash
curl -X POST http://localhost:8000/survey/create \
  -F "issue_key=PROJ-123" \
  -F "language=ru"
```

Response: `{"link": "https://survey.ostrovok.ru/survey/ABC123XYZ"}`

**Note:** Language is automatically determined by the domain:
- `survey.ostrovok.ru` → Russian (ru)
- `survey.emergingtravel.com` → English (en)

### Submit Survey
```bash
curl -X POST https://survey.ostrovok.ru/survey/ABC123XYZ/submit \
  -F "score=5" \
  -F "comment=Excellent"
```

Response: `{"status": "ok"}`

**Note:** Language is determined by the domain used in the URL (no lang parameter needed)

---

## Support

- **Logs**: `sudo journalctl -u csat -f`
- **Config**: `/opt/csat/.env`
- **Data**: `/var/lib/csat/surveys.json`
- **Nginx**: `sudo systemctl status nginx`

Check the Troubleshooting section for common issues.
