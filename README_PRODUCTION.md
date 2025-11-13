# CSAT Survey Service - Production Deployment Guide

## Quick Summary

Your CSAT survey application has been **fully prepared for production deployment** on Ubuntu servers. The service is now:

✅ Secure (CORS hardened, no debug mode)
✅ Scalable (multi-worker support)
✅ Monitored (comprehensive logging)
✅ Maintainable (systemd service management)
✅ Documented (complete deployment guides)

## What's Been Changed?

### Code Changes (main.py)
- ✅ Production logging system (replaces print statements)
- ✅ Absolute file paths (ensures working from any directory)
- ✅ CORS security hardening (restricts to specific domains)
- ✅ Environment-based configuration (12-factor app)
- ✅ Multi-worker support (scales with CPU)
- ✅ Removed debug mode (reload=False)

### New Files Created

| File | Purpose |
|------|---------|
| `requirements.txt` | Python dependencies for production |
| `DEPLOYMENT.md` | Complete step-by-step deployment guide |
| `deploy.sh` | Automated deployment script |
| `OPERATIONS.md` | Daily operations and troubleshooting |
| `PRODUCTION_CHANGES.md` | Detailed list of all changes |
| `README_PRODUCTION.md` | This file |

## Deployment Process

### Option 1: Automated Deployment (Recommended)

```bash
# On your Ubuntu server (as root)
sudo bash /opt/csat/deploy.sh

# Then manually:
# 1. Edit /opt/csat/.env with your settings
# 2. Follow DEPLOYMENT.md sections 6-8 for Nginx and SSL
```

### Option 2: Manual Deployment

Follow the step-by-step guide in `DEPLOYMENT.md`

## Quick Start After Deployment

### 1. Configure Environment
```bash
sudo nano /opt/csat/.env
# Update:
# - CSAT_ALLOWED_ORIGINS
# - JIRA_WEBHOOK_URL
```

### 2. Set Up Nginx
```bash
# Copy nginx config from DEPLOYMENT.md
# Reload Nginx
sudo systemctl reload nginx
```

### 3. Install SSL Certificate
```bash
sudo certbot certonly --nginx \
  -d csat.service.ru \
  -d csat.anotherservice.eng
```

### 4. Start Service
```bash
sudo systemctl start csat
sudo systemctl status csat
```

### 5. Test
```bash
# Check it's running
curl https://csat.service.ru/

# View logs
sudo journalctl -u csat -f
```

## File Structure

```
/opt/csat/                          # Application root
├── main.py                         # Production-ready FastAPI app
├── requirements.txt                # Python dependencies
├── deploy.sh                       # Deployment script
├── .env                           # Environment configuration (after deploy)
├── venv/                          # Python virtual environment
├── static/                        # Frontend files (HTML, CSS, JS)
├── templates/                     # HTML templates
└── surveys.json                   # Survey data (auto-created)

/var/lib/csat/                     # Data directory
├── surveys.json                   # Survey responses (persistent)
└── surveys.json.backup.*          # Backups

/var/log/csat/                     # Log directory
├── app.log                        # Application logs
└── (nginx logs in /var/log/nginx/)

/etc/systemd/system/               # System services
└── csat.service                   # Service definition

/etc/nginx/sites-available/        # Nginx configuration
└── csat                           # Site config (created by you)
```

## Environment Variables Reference

```bash
# Server (usually don't change these)
CSAT_HOST=127.0.0.1           # Listen only internally (Nginx proxies)
CSAT_PORT=8000                # Internal port
CSAT_WORKERS=4                # Number of worker processes
CSAT_RELOAD=false             # Never reload in production

# Data & Logging
CSAT_DATA_DIR=/var/lib/csat   # Where to store surveys.json
CSAT_LOG_DIR=/var/log/csat    # Where to store logs
CSAT_SURVEY_EXPIRY_HOURS=24   # Survey validity duration

# Security - MUST CHANGE FOR PRODUCTION
CSAT_ALLOWED_ORIGINS=https://csat.service.ru,https://csat.anotherservice.eng
JIRA_WEBHOOK_URL=https://your-jira.com/webhook  # Required!
```

## Security Checklist

- [ ] CORS_ALLOWED_ORIGINS is set to your domains (not "*")
- [ ] JIRA_WEBHOOK_URL is configured
- [ ] SSL certificate installed
- [ ] HTTPS enforced (HTTP redirects to HTTPS)
- [ ] Firewall rules applied (22, 80, 443)
- [ ] Service runs as non-root user (csat)
- [ ] Data directory has restricted permissions (750)
- [ ] Backups are set up
- [ ] Logs are monitored

## Common Operations

### View Logs
```bash
sudo journalctl -u csat -f
```

### Restart Service
```bash
sudo systemctl restart csat
```

### Check Status
```bash
sudo systemctl status csat
```

### Update Code
```bash
cd /opt/csat
sudo -u csat git pull
sudo systemctl restart csat
```

### Backup Data
```bash
sudo cp /var/lib/csat/surveys.json /var/lib/csat/surveys.json.backup.$(date +%Y%m%d)
```

See `OPERATIONS.md` for more commands.

## Documentation Files

- **DEPLOYMENT.md** - Complete deployment guide with all steps
- **OPERATIONS.md** - Operations reference, troubleshooting, common commands
- **PRODUCTION_CHANGES.md** - Detailed list of code changes and improvements

## Architecture

```
┌─────────────────────────────────────────────┐
│        Public Internet (HTTPS)              │
└──────────────────┬──────────────────────────┘
                   │
        ┌──────────▼──────────┐
        │  Nginx Reverse Proxy│
        │   Port 443 (SSL)    │
        │  Rate Limiting      │
        │ Security Headers    │
        └──────────┬──────────┘
                   │
        ┌──────────▼──────────┐
        │  FastAPI App        │
        │ Port 8000 (local)   │
        │ 4 workers           │
        │ Non-root user       │
        └──────────┬──────────┘
                   │
        ┌──────────▼──────────┐
        │  /var/lib/csat/     │
        │ surveys.json (data) │
        │ app.log (logs)      │
        └─────────────────────┘
```

## What to Do Next

### Immediate (Before Going Live)
1. Copy files to Ubuntu server
2. Run `deploy.sh` script
3. Configure `.env` file
4. Set up Nginx reverse proxy
5. Obtain SSL certificates
6. Test the service thoroughly

### After Deployment
1. Monitor logs daily: `sudo journalctl -u csat -f`
2. Set up automated backups for surveys.json
3. Configure log rotation
4. Test SSL renewal: `sudo certbot renew --dry-run`
5. Set up monitoring/alerting if needed

### Regular Maintenance
- Weekly: Backup surveys.json
- Monthly: Check certificate expiry
- Quarterly: System updates

## Troubleshooting

### Service won't start
```bash
sudo systemctl status csat -l
sudo journalctl -u csat -n 50
```

### Nginx 502 Bad Gateway
```bash
# Check if backend is running
sudo ss -tulpn | grep 8000
sudo systemctl status csat
```

### Permission denied errors
```bash
sudo chown -R csat:csat /var/lib/csat /var/log/csat
sudo chmod 750 /var/lib/csat /var/log/csat
```

### SSL certificate issues
```bash
sudo certbot certificates
sudo certbot renew --dry-run
```

See `OPERATIONS.md` for more troubleshooting.

## Support

### Emergency Contact Points
- Application logs: `/var/log/csat/app.log`
- Nginx logs: `/var/log/nginx/csat*.log`
- Systemd logs: `sudo journalctl -u csat`

### When Asking for Help, Provide
```bash
# System info
uname -a

# Service status
sudo systemctl status csat

# Recent logs
sudo journalctl -u csat -n 50

# Resource usage
ps aux | grep uvicorn
```

## Performance Notes

- Each worker process uses ~50-100MB RAM
- 4 workers handle 100+ concurrent requests
- Nginx caches static files (30-day cache)
- Rate limiting: 10 req/s per IP
- Submit endpoint: 5 req/s per IP

## Key Improvements Over Development Version

| Aspect | Development | Production |
|--------|-------------|-----------|
| Debug Mode | ✓ reload=True | ✗ reload=False |
| CORS | ✓ Allow all | ✓ Specific domains |
| Logging | print() | Structured logging + file |
| Workers | 1 (single-threaded) | 4 (multi-worker) |
| Paths | Relative | Absolute |
| Config | Hardcoded | Environment variables |
| User | Running process user | Dedicated `csat` user |
| Permissions | Unrestricted | 750/640 restricted |
| SSL | None | Let's Encrypt |
| Proxy | None | Nginx reverse proxy |
| Rate Limiting | None | Enabled |
| Security Headers | None | HSTS, X-Frame-Options, etc |

## Success Indicators

✅ You know deployment is successful when:

- [ ] `sudo systemctl status csat` shows "active (running)"
- [ ] `curl https://csat.service.ru/` returns HTML (no error)
- [ ] `sudo journalctl -u csat -f` shows no errors
- [ ] SSL certificate is valid: `sudo certbot certificates`
- [ ] Nginx is serving with HTTPS: `curl -I https://csat.service.ru/`
- [ ] Data persists across restarts
- [ ] Logs are being written to `/var/log/csat/app.log`

## Questions?

1. Check `DEPLOYMENT.md` for detailed instructions
2. Check `OPERATIONS.md` for common operations
3. Check application logs: `sudo journalctl -u csat -f`
4. Check Nginx logs: `sudo tail -f /var/log/nginx/csat.error.log`

---

**You're now ready for production! Good luck! 🚀**
