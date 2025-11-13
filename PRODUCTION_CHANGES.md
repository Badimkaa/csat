# Production Changes Summary

## Overview
The CSAT application has been updated for production deployment on Ubuntu servers for public internet access.

## Code Changes Made to main.py

### 1. **Logging System** (Lines 13-26)
- ✅ Replaced `print()` statements with proper logging
- ✅ Logs to both file (`/var/log/csat/app.log`) and console
- ✅ Structured log format with timestamps

### 2. **File Paths** (Lines 29-31)
- ✅ Changed from relative to absolute paths
- ✅ Data directory: `/var/lib/csat` (configurable via `CSAT_DATA_DIR`)
- ✅ Ensures app works regardless of working directory

### 3. **CORS Security** (Lines 45-52)
- ✅ Changed from `allow_origins=["*"]` to specific domains
- ✅ Configurable via `CSAT_ALLOWED_ORIGINS` environment variable
- ✅ Restricted HTTP methods to GET and POST only
- ✅ Restricted headers to Content-Type only

### 4. **Configuration** (Lines 57-58)
- ✅ SURVEY_EXPIRY_HOURS now configurable via env var
- ✅ SURVEYS_FILE uses absolute path from DATA_DIR

### 5. **Error Handling** (Throughout)
- ✅ All `print()` calls replaced with `logger.*()` calls
- ✅ Better error tracking and debugging capabilities

### 6. **Application Entry Point** (Lines 264-273)
- ✅ Removed `reload=True` (development feature, security risk)
- ✅ Added multi-worker support for production
- ✅ All settings configurable via environment variables
- ✅ Hosts on `127.0.0.1` by default (behind Nginx)

## Environment Variables

### Server Configuration
```bash
CSAT_HOST=127.0.0.1        # Listen on localhost (behind Nginx)
CSAT_PORT=8000             # Internal port
CSAT_WORKERS=4             # Number of uvicorn workers
CSAT_RELOAD=false          # Auto-reload (disable in production)
```

### Data & Logging
```bash
CSAT_DATA_DIR=/var/lib/csat         # Data directory
CSAT_LOG_DIR=/var/log/csat          # Log directory
CSAT_SURVEY_EXPIRY_HOURS=24         # Survey validity period
```

### Security & Integration
```bash
CSAT_ALLOWED_ORIGINS=https://csat.service.ru,https://csat.anotherservice.eng
JIRA_WEBHOOK_URL=https://your-jira-instance.com/rest/api/3/webhooks
```

## New Files Created

### 1. **requirements.txt**
- FastAPI 0.104.1
- Uvicorn with standard extras
- All production dependencies

### 2. **DEPLOYMENT.md** (Comprehensive Guide)
- Step-by-step deployment instructions
- Systemd service setup
- Nginx reverse proxy configuration
- SSL/TLS with Let's Encrypt
- Security hardening
- Firewall configuration
- Monitoring and troubleshooting

### 3. **deploy.sh** (Automated Deployment)
- Automated setup script
- Creates users and directories
- Installs dependencies
- Configures systemd service
- Quick reference for next steps

### 4. **PRODUCTION_CHANGES.md** (This file)
- Documents all changes made

## Security Improvements

### 1. **CORS Hardening**
- Before: `allow_origins=["*"]` (accepts requests from any domain)
- After: Only specified domains allowed

### 2. **HTTP Methods**
- Before: All methods allowed
- After: Only GET and POST

### 3. **Headers**
- Before: All headers allowed
- After: Only Content-Type

### 4. **Debug Mode**
- Before: `reload=True` (file watching, auto-reload)
- After: Disabled for production

### 5. **Logging**
- Before: Console only with `print()`
- After: File + console with structured logging and timestamps

### 6. **File Permissions**
- Data directory: `750` (owner: csat user only)
- Sensitive files: `600` (owner read-write only)

### 7. **Process Isolation**
- Runs as non-root `csat` user
- Systemd security settings: PrivateTmp, NoNewPrivileges, ProtectSystem, ProtectHome

## Architecture Changes

### Before (Development)
```
Client → App (port 8000)
       ↓
   surveys.json (current dir)
```

### After (Production)
```
Client → Nginx (443/HTTPS) → App (127.0.0.1:8000)
              ↓
         SSL/TLS, Rate Limiting
         Security Headers
       ↓
   /var/lib/csat/surveys.json
   /var/log/csat/app.log
```

## Deployment Checklist

- [ ] Read DEPLOYMENT.md completely
- [ ] Run `sudo bash deploy.sh` on Ubuntu server
- [ ] Edit `/opt/csat/.env` with your settings
- [ ] Configure Nginx based on DEPLOYMENT.md
- [ ] Obtain SSL certificates with certbot
- [ ] Set JIRA_WEBHOOK_URL in `.env`
- [ ] Test service: `sudo systemctl status csat`
- [ ] Check logs: `sudo journalctl -u csat -f`
- [ ] Test HTTPS endpoints
- [ ] Configure log rotation
- [ ] Set up backup for surveys.json
- [ ] Enable and test firewall

## Important Notes

### Data Persistence
- Surveys stored in: `/var/lib/csat/surveys.json`
- Owned by: `csat:csat` user
- Permissions: `750` directory, `640` file
- **Backup this file regularly!**

### Logging
- Application logs: `/var/log/csat/app.log`
- Nginx access logs: `/var/log/nginx/csat.access.log`
- Nginx error logs: `/var/log/nginx/csat.error.log`
- Systemd logs: `journalctl -u csat`

### SSL/TLS
- Let's Encrypt certificates auto-renew
- Certificates in: `/etc/letsencrypt/live/`
- Certbot timer handles renewal
- Manual check: `sudo certbot certificates`

### Monitoring
- Service auto-restarts on failure
- Check status: `sudo systemctl status csat`
- Monitor logs: `sudo journalctl -u csat -f`
- Check port: `sudo ss -tulpn | grep 8000`

## Rollback Instructions

If you need to revert to development mode:
1. Stop service: `sudo systemctl stop csat`
2. Revert main.py changes from git
3. Edit CSAT_RELOAD=true in `.env`
4. Start service: `sudo systemctl start csat`

## Support & Troubleshooting

See DEPLOYMENT.md for:
- Common issues and solutions
- Log analysis
- Service restart procedures
- SSL certificate troubleshooting

## Next Steps

1. **Copy to server**: `scp -r /path/to/csat user@server:/opt/`
2. **Run deployment**: `ssh user@server 'sudo bash /opt/csat/deploy.sh'`
3. **Configure**: Edit `/opt/csat/.env`
4. **Setup Nginx**: Follow DEPLOYMENT.md sections 6-7
5. **Get SSL**: Run certbot command from DEPLOYMENT.md
6. **Test**: Access https://csat.service.ru/
