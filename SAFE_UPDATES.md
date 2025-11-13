# Safe Updates Guide

## How to Update Your Service Without Losing Data

Your CSAT service is now protected against data loss during updates. Here's how it works and how to safely update the service.

## Protected Files

The following files are **never** tracked by Git and will **never** be overwritten by `git pull`:

```
surveys.json              # Live survey data
surveys.json.backup*      # Backup copies
app.log*                  # Application logs
.env                      # Sensitive configuration
__pycache__/             # Python cache
venv/                    # Virtual environment
```

## Safe Update Process

### Step 1: SSH into your server

```bash
ssh root@your-server-ip
cd /opt/csat
```

### Step 2: Backup current state (optional but recommended)

```bash
# Create a backup before updating
sudo -u csat cp /var/lib/csat/surveys.json /var/lib/csat/surveys.json.backup.$(date +%Y%m%d_%H%M%S)

# Verify backup exists
ls -la /var/lib/csat/surveys.json*
```

### Step 3: Pull latest code

```bash
# Pull latest code from GitLab
sudo git pull origin master

# Or if you have specific branch
sudo git pull origin branch-name
```

### Step 4: Check what changed

```bash
# See the last few commits
git log --oneline -5

# Check what files were modified
git diff HEAD~1 --name-only
```

### Step 5: Install any new dependencies

```bash
# If requirements.txt changed, reinstall
cd /opt/csat
sudo -u csat /opt/csat/venv/bin/pip install -r requirements.txt
```

### Step 6: Restart the service

```bash
# Restart to load the new code
sudo systemctl restart csat

# Verify it's running
sudo systemctl status csat

# Check logs for any errors
sudo journalctl -u csat -f
```

### Step 7: Verify surveys.json is intact

```bash
# Check surveys.json still exists and has data
ls -lh /var/lib/csat/surveys.json

# Check file size (should be > 0 bytes if you have surveys)
wc -l /var/lib/csat/surveys.json
```

## What's Protected

### surveys.json (Live Survey Data)
- Contains all pending and completed surveys
- **Never** committed to Git
- **Never** overwritten by `git pull`
- Persists across service restarts
- Manually backed up with `.gitignore`

### .env (Configuration)
- Contains sensitive settings like `JIRA_WEBHOOK_URL`
- **Never** tracked by Git
- Safe to edit on server without affecting repository
- Won't be overwritten during updates

### Logs
- `app.log` and rotated backups (`app.log.1.gz`, etc.)
- Never tracked or overwritten
- Safe for monitoring and debugging

## If Something Goes Wrong

### Restore from backup

```bash
# If you need to restore surveys.json
sudo cp /var/lib/csat/surveys.json.backup.YYYYMMDD_HHMMSS /var/lib/csat/surveys.json

# Fix permissions if needed
sudo chown csat:csat /var/lib/csat/surveys.json
sudo chmod 640 /var/lib/csat/surveys.json

# Restart service
sudo systemctl restart csat
```

### Rollback to previous commit

```bash
# See recent commits
git log --oneline -10

# Reset to previous commit (be careful!)
sudo git reset --hard COMMIT_HASH

# Restart service
sudo systemctl restart csat
```

## Automated Updates (Optional)

You can create a cron job for automatic updates:

```bash
# Edit crontab
sudo crontab -e

# Add this line to update daily at 2 AM
0 2 * * * cd /opt/csat && git pull origin master && systemctl restart csat >> /var/log/csat-update.log 2>&1
```

Then monitor the update log:

```bash
tail -f /var/log/csat-update.log
```

## Best Practices

✅ **Do:**
- Backup `surveys.json` before major updates
- Check commit history before updating
- Verify service is running after update
- Monitor logs for any errors
- Keep `.gitignore` updated with new sensitive files

❌ **Don't:**
- Remove `.gitignore` rules
- Manually add `surveys.json` to Git
- Skip the restart step
- Ignore error messages in logs
- Force-push to master

## Files You CAN Safely Modify on Server

These files can be edited on the server and won't be overwritten:

- `/opt/csat/.env` - Configuration
- `/var/lib/csat/surveys.json` - Survey data
- `/var/log/csat/app.log*` - Logs
- `/etc/logrotate.d/csat` - Log rotation
- `/etc/nginx/sites-available/csat` - Nginx config

## Files That WILL Be Overwritten

These files will be updated when you `git pull`:

- `main.py` - Application code
- `requirements.txt` - Python dependencies
- `static/*` - Frontend files
- `templates/*` - HTML templates
- Documentation (*.md files)

---

**Summary:** Your surveys and configuration are safe! They're protected by `.gitignore` and will never be overwritten by Git operations.
