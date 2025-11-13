# CSAT Operations Guide

Quick reference for common server operations.

## Service Management

### Start/Stop/Restart
```bash
# Start service
sudo systemctl start csat

# Stop service
sudo systemctl stop csat

# Restart service
sudo systemctl restart csat

# Check status
sudo systemctl status csat

# Enable auto-start on boot
sudo systemctl enable csat

# Disable auto-start on boot
sudo systemctl disable csat
```

### View Logs

```bash
# Real-time application logs
sudo journalctl -u csat -f

# Last 50 lines of logs
sudo journalctl -u csat -n 50

# Logs from last hour
sudo journalctl -u csat --since "1 hour ago"

# View application log file directly
sudo tail -f /var/log/csat/app.log

# Nginx access logs
sudo tail -f /var/log/nginx/csat.access.log

# Nginx error logs
sudo tail -f /var/log/nginx/csat.error.log
```

## Configuration Changes

### Update Environment Variables
```bash
# Edit configuration
sudo nano /opt/csat/.env

# Reload configuration (requires service restart)
sudo systemctl restart csat
```

### Update Application Code
```bash
# Pull latest from git
cd /opt/csat
sudo -u csat git pull

# Or if you copied files manually
# Copy files and change ownership
sudo cp -r /path/to/new/files /opt/csat/
sudo chown -R csat:csat /opt/csat

# Restart service
sudo systemctl restart csat
```

## Monitoring

### Check Service is Running
```bash
# Check if process is active
sudo systemctl is-active csat

# Check if port 8000 is listening
sudo ss -tulpn | grep 8000

# Check process memory and CPU
ps aux | grep uvicorn

# More detailed monitoring
sudo top -p $(pgrep -f uvicorn | head -1)
```

### Check Nginx is Running
```bash
# Check status
sudo systemctl status nginx

# Reload configuration (no downtime)
sudo systemctl reload nginx

# Test configuration
sudo nginx -t

# View active connections
sudo netstat -n | grep :443 | wc -l
```

## SSL/TLS Management

### Renew Certificates
```bash
# Manual renewal
sudo certbot renew

# Force renewal
sudo certbot renew --force-renewal

# Check certificate expiry
sudo certbot certificates

# Automatic renewal is handled by systemd timer
# Check timer status
sudo systemctl status certbot.timer
```

### Install New Certificate
```bash
# For new domain
sudo certbot certonly --nginx -d yourdomain.com

# Check renewal will work
sudo certbot renew --dry-run
```

## Data Management

### Backup Surveys Data
```bash
# Manual backup
sudo cp /var/lib/csat/surveys.json /var/lib/csat/surveys.json.backup.$(date +%Y%m%d_%H%M%S)

# Automated daily backup (add to crontab)
0 2 * * * sudo cp /var/lib/csat/surveys.json /var/lib/csat/surveys.json.backup.$(date +\%Y\%m\%d)

# View backup size
sudo du -sh /var/lib/csat/
```

### Clear Expired Surveys (on next app restart)
```bash
# Service automatically cleans expired surveys on startup
sudo systemctl restart csat

# Check logs for cleanup
sudo journalctl -u csat | grep "cleanup"
```

### Export Surveys Data
```bash
# Copy to home directory for download
sudo cp /var/lib/csat/surveys.json ~/surveys.json
sudo chown $USER:$USER ~/surveys.json

# Or directly read (if you have permissions)
sudo cat /var/lib/csat/surveys.json | jq .
```

## Firewall Management

### UFW Commands
```bash
# Enable firewall
sudo ufw enable

# Check status
sudo ufw status

# Allow port
sudo ufw allow 443/tcp
sudo ufw allow 80/tcp
sudo ufw allow 22/tcp

# Deny port
sudo ufw deny 8000

# View rules with numbers
sudo ufw status numbered

# Remove rule by number
sudo ufw delete 5
```

## Performance Tuning

### Check System Resources
```bash
# Memory usage
free -h

# Disk usage
df -h

# CPU usage
top -bn1 | head -20

# Network connections to app
ss -n | grep :8000
```

### Adjust Worker Processes
```bash
# Edit environment file
sudo nano /opt/csat/.env

# Change CSAT_WORKERS (usually 2-4x CPU cores)
# CPU cores: nproc

# Restart service
sudo systemctl restart csat
```

## Troubleshooting

### Service Won't Start
```bash
# Check detailed error
sudo systemctl status csat -l

# Check journalctl
sudo journalctl -u csat -n 100

# Check if port is in use
sudo ss -tulpn | grep 8000

# Check file permissions
ls -la /var/lib/csat
ls -la /var/log/csat

# Fix permissions if needed
sudo chown -R csat:csat /var/lib/csat /var/log/csat
sudo chmod 750 /var/lib/csat /var/log/csat
```

### Nginx 502 Bad Gateway
```bash
# Check if backend is running
sudo systemctl status csat

# Check if port 8000 is listening
sudo ss -tulpn | grep 8000

# Check Nginx error log
sudo tail -f /var/log/nginx/csat.error.log

# Reload Nginx
sudo systemctl reload nginx
```

### High Memory Usage
```bash
# Check memory per worker
ps aux | grep uvicorn

# Reduce workers in .env
sudo nano /opt/csat/.env
# Set CSAT_WORKERS to lower value

# Restart
sudo systemctl restart csat
```

### SSL Certificate Issues
```bash
# Check certificate expiry
sudo certbot certificates

# Check expiry date
sudo openssl x509 -in /etc/letsencrypt/live/csat.service.ru/cert.pem -noout -dates

# Dry run renewal
sudo certbot renew --dry-run

# Force renewal
sudo certbot renew --force-renewal

# Check Nginx SSL configuration
sudo openssl s_client -connect csat.service.ru:443 -servername csat.service.ru
```

## Maintenance Schedule

### Daily
- [ ] Monitor logs for errors
- [ ] Check disk space: `df -h`

### Weekly
- [ ] Backup surveys.json
- [ ] Check certificate expiry: `sudo certbot certificates`

### Monthly
- [ ] Review system resource usage
- [ ] Test SSL renewal: `sudo certbot renew --dry-run`
- [ ] Check Nginx access logs for unusual patterns

### Quarterly
- [ ] Full system update: `sudo apt upgrade`
- [ ] Review CORS origins in configuration
- [ ] Rotate old log files

## Emergency Procedures

### Service Recovery
```bash
# If service crashes repeatedly
sudo systemctl stop csat

# Check what went wrong
sudo journalctl -u csat -n 100

# Fix configuration if needed
sudo nano /opt/csat/.env

# Restore from backup if surveys.json corrupted
sudo cp /var/lib/csat/surveys.json.backup /var/lib/csat/surveys.json
sudo chown csat:csat /var/lib/csat/surveys.json

# Restart
sudo systemctl start csat
```

### Disk Space Emergency
```bash
# Check disk usage
df -h

# Find large files
du -sh /var/lib/csat
du -sh /var/log/csat

# Compress old logs
gzip /var/log/csat/app.log.*

# Remove old backups (keep only recent ones)
ls -lt /var/lib/csat/surveys.json.backup* | tail -n +5 | xargs rm
```

## Useful Commands Reference

```bash
# Quick status check
sudo systemctl status csat && echo "✓ CSAT OK" || echo "✗ CSAT DOWN"

# Full health check
echo "=== Service ===" && \
sudo systemctl is-active csat && \
echo "=== Port ===" && \
sudo ss -tulpn | grep 8000 && \
echo "=== Disk ===" && \
df -h /var/lib/csat && \
echo "=== Latest Errors ===" && \
sudo journalctl -u csat -n 5

# Watch logs in real-time
sudo journalctl -u csat -f

# Find old backups
find /var/lib/csat -name "*.backup.*" -mtime +30

# Calculate survey storage size
du -sh /var/lib/csat/surveys.json
```

## Support Commands for Troubleshooting

When asking for support, provide:
```bash
# System info
uname -a

# Service status
sudo systemctl status csat

# Recent logs (50 lines)
sudo journalctl -u csat -n 50

# Resource usage
ps aux | grep uvicorn

# Disk space
df -h /var/lib/csat

# Nginx status
sudo systemctl status nginx
```
