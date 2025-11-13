# Production Deployment Files Checklist

## Essential Files to Deploy

### Application Code
- [x] `main.py` - Production-ready FastAPI application
- [x] `static/` directory - Frontend HTML, CSS, JS
- [x] `templates/` directory - HTML templates (403.html, etc)

### Configuration & Dependencies
- [x] `requirements.txt` - Python dependencies
- [x] `.env.example` (you'll create) - Environment variables template

### Deployment Automation
- [x] `deploy.sh` - Automated deployment script
- [x] `DEPLOYMENT.md` - Complete step-by-step guide

### Documentation
- [x] `README_PRODUCTION.md` - Quick start guide
- [x] `OPERATIONS.md` - Operations and troubleshooting
- [x] `PRODUCTION_CHANGES.md` - Detailed change log
- [x] `DEPLOYMENT_SUMMARY.txt` - Summary of deployment

---

## Step-by-Step Deployment Checklist

### Phase 1: Preparation (On your local machine)
- [ ] Read README_PRODUCTION.md
- [ ] Have Ubuntu 20.04+ server ready with root access
- [ ] Have domain names configured (DNS pointing to server)
- [ ] Have Jira webhook URL ready

### Phase 2: File Transfer
- [ ] Copy entire `/Users/vadzim/csat` directory to server:
  ```bash
  scp -r /Users/vadzim/csat user@server:/tmp/
  sudo cp -r /tmp/csat /opt/csat
  sudo chown -R root:root /opt/csat
  ```

### Phase 3: Automated Setup (On server)
- [ ] Run deployment script:
  ```bash
  sudo bash /opt/csat/deploy.sh
  ```

### Phase 4: Configuration (On server)
- [ ] Edit environment file:
  ```bash
  sudo nano /opt/csat/.env
  ```
  - [ ] Set `CSAT_ALLOWED_ORIGINS`
  - [ ] Set `JIRA_WEBHOOK_URL`
  - [ ] Verify other settings

### Phase 5: Nginx & SSL Setup (On server)
- [ ] Follow DEPLOYMENT.md Section 6 (Nginx config)
- [ ] Follow DEPLOYMENT.md Section 7 (SSL certificates)
  ```bash
  sudo certbot certonly --nginx \
    -d csat.service.ru \
    -d csat.anotherservice.eng
  ```
- [ ] Reload Nginx: `sudo systemctl reload nginx`

### Phase 6: Service Startup & Testing (On server)
- [ ] Start service: `sudo systemctl start csat`
- [ ] Check status: `sudo systemctl status csat`
- [ ] Test HTTPS: `curl https://csat.service.ru/`
- [ ] Check logs: `sudo journalctl -u csat -f`

### Phase 7: Post-Deployment (On server)
- [ ] Verify surveys.json exists: `ls -la /var/lib/csat/surveys.json`
- [ ] Verify logs exist: `ls -la /var/log/csat/app.log`
- [ ] Set up log rotation
- [ ] Create backup script
- [ ] Configure monitoring

---

## Files by Purpose

### For Initial Setup
1. `deploy.sh` - Run this first
2. `requirements.txt` - Installed by deploy.sh
3. `.env` - Edit after deploy.sh

### For Operations
1. `OPERATIONS.md` - Reference daily
2. `DEPLOYMENT.md` - For troubleshooting
3. Service logs - Monitor regularly

### For Reference
1. `README_PRODUCTION.md` - Overview
2. `PRODUCTION_CHANGES.md` - What changed
3. `DEPLOYMENT_SUMMARY.txt` - Quick reference

---

## What NOT to Change

❌ Don't modify these after deployment (unless you know what you're doing):
- `/etc/systemd/system/csat.service` - Systemd service
- `/etc/nginx/sites-available/csat` - Nginx config
- `/opt/csat/main.py` - Unless fixing a bug

✅ Safe to modify:
- `/opt/csat/.env` - Configuration (restart service after)
- `/var/lib/csat/surveys.json` - Data (backup first!)
- Nginx config (test before reload)

---

## Quick Commands Reference

### Check Service
```bash
sudo systemctl status csat
sudo journalctl -u csat -f
```

### Restart Service
```bash
sudo systemctl restart csat
```

### View Config
```bash
sudo cat /opt/csat/.env
```

### Backup Data
```bash
sudo cp /var/lib/csat/surveys.json /var/lib/csat/surveys.json.backup.$(date +%Y%m%d)
```

### Check Disk Usage
```bash
du -sh /var/lib/csat
du -sh /var/log/csat
```

---

## Troubleshooting Guide

### Service won't start
```bash
sudo systemctl status csat -l
sudo journalctl -u csat -n 100
```

### Permission denied
```bash
sudo chown -R csat:csat /var/lib/csat /var/log/csat
sudo chmod 750 /var/lib/csat /var/log/csat
```

### Nginx 502 Bad Gateway
```bash
sudo ss -tulpn | grep 8000
sudo systemctl status csat
```

### SSL certificate issues
```bash
sudo certbot certificates
sudo certbot renew --dry-run
```

See `OPERATIONS.md` for more troubleshooting.

---

## Success Checklist

✅ You've succeeded when:
- [ ] `sudo systemctl status csat` shows "active (running)"
- [ ] `curl https://csat.service.ru/` returns HTML (no error)
- [ ] `/var/log/csat/app.log` has recent log entries
- [ ] `/var/lib/csat/surveys.json` exists and has permissions 640
- [ ] SSL certificate is valid: `sudo certbot certificates`
- [ ] You can view logs: `sudo journalctl -u csat -f`

---

## Support Resources

1. **DEPLOYMENT.md** - Complete deployment guide (follow step-by-step)
2. **OPERATIONS.md** - Daily operations and troubleshooting
3. **README_PRODUCTION.md** - Overview and quick start
4. **Application logs** - Check `/var/log/csat/app.log`
5. **Systemd logs** - Check `sudo journalctl -u csat`
6. **Nginx logs** - Check `/var/log/nginx/csat*.log`

---

**Version**: Production Ready
**Last Updated**: 2024
**Status**: ✅ Ready for Deployment
