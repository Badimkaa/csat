# Log Rotation Setup Guide

## Problem

By default, `app.log` grows indefinitely and will eventually fill your disk. You need to configure log rotation to manage this.

## Solution: Logrotate Configuration

### Step 1: Create Logrotate Config

```bash
sudo cat > /etc/logrotate.d/csat << 'EOF'
/var/log/csat/app.log {
    daily                    # Rotate every day
    rotate 30                # Keep 30 days of backups
    compress                 # Compress old logs with gzip
    delaycompress            # Don't compress most recent backup
    missingok                # Don't error if file doesn't exist
    notifempty               # Don't rotate if file is empty
    create 0640 csat csat    # Create new log file with these permissions
    sharedscripts            # Run script only once (not per log file)
    postrotate
        systemctl reload csat > /dev/null 2>&1 || true
    endscript
}
EOF
```

### Step 2: Verify Configuration

```bash
# Test the configuration
sudo logrotate -d /etc/logrotate.d/csat

# Check for syntax errors
sudo logrotate -v /etc/logrotate.d/csat
```

### Step 3: Force Initial Rotation (Optional Testing)

```bash
# Force rotate all configured logs
sudo logrotate -f /etc/logrotate.d/csat

# Check results
ls -lh /var/log/csat/

# View compressed logs
zcat /var/log/csat/app.log.1.gz | head
```

## How It Works

### Daily Rotation Process

**Day 1:**
- Application writes to: `app.log`
- Logrotate runs (usually at 6:25 AM)
- File renamed: `app.log` → `app.log.1`
- New file created: `app.log` (empty)
- Application resumes writing to `app.log`

**Day 2:**
- Logrotate runs
- `app.log.1` → `app.log.2`
- `app.log` → `app.log.1`
- New `app.log` created
- Optional: `app.log.2` is compressed to `app.log.2.gz`

### After 30 Days

```
/var/log/csat/
├── app.log              (current day's logs, ~5-50 MB)
├── app.log.1.gz         (yesterday, compressed, ~0.5-5 MB)
├── app.log.2.gz         (2 days ago)
├── app.log.3.gz         (3 days ago)
...
└── app.log.30.gz        (30 days ago)
```

Anything older than `app.log.30.gz` is deleted.

## Space Savings

**Without compression:**
- 30 files × 50 MB = **1.5 GB**

**With compression (typical ratio):**
- 30 files × 5 MB = **150 MB**

**Savings: ~90%**

## Configuration Options Explained

| Option | Purpose |
|--------|---------|
| `daily` | Rotate every day (can be: daily, weekly, monthly, yearly) |
| `rotate 30` | Keep 30 rotated files (older ones deleted) |
| `compress` | Gzip compress old log files |
| `delaycompress` | Don't compress the most recent backup yet |
| `missingok` | Don't error if log file missing |
| `notifempty` | Skip rotation if log file is empty |
| `create 0640 csat csat` | Create new file: permissions 640, owner csat:csat |
| `postrotate/endscript` | Script to run after rotation |

## Monitoring

### Check Logrotate Status

```bash
# View logrotate manual
man logrotate

# Check cron job for logrotate
cat /etc/cron.daily/logrotate

# Or use systemd timer
sudo systemctl list-timers | grep logrotate
```

### Estimate Disk Usage

```bash
# Current log size
du -sh /var/log/csat/

# Total size including backups
du -sh /var/log/csat/

# Count rotated files
ls /var/log/csat/app.log* | wc -l

# List all log files with sizes
ls -lh /var/log/csat/
```

### Example Output

```bash
$ ls -lh /var/log/csat/
total 25M
-rw-r----- 1 csat csat  42M Nov 13 15:30 app.log
-rw-r----- 1 csat csat 1.2M Nov 13 00:00 app.log.1.gz
-rw-r----- 1 csat csat 1.5M Nov 12 00:00 app.log.2.gz
-rw-r----- 1 csat csat 1.1M Nov 11 00:00 app.log.3.gz
-rw-r----- 1 csat csat 950K Nov 10 00:00 app.log.4.gz
```

## Viewing Compressed Logs

```bash
# View compressed log file
zcat /var/log/csat/app.log.1.gz | less

# Search in compressed logs
zcat /var/log/csat/app.log.1.gz | grep "error"

# Count errors in compressed log
zcat /var/log/csat/app.log.1.gz | grep -c "ERROR"

# View last 50 lines of compressed log
zcat /var/log/csat/app.log.1.gz | tail -50

# View all compressed logs in reverse date order
for f in $(ls -tr /var/log/csat/app.log*.gz); do echo "=== $f ==="; zcat "$f" | head -3; done
```

## Alternative: Time-Based Rotation

If you want hourly rotation instead of daily:

```bash
/var/log/csat/app.log {
    hourly                   # Rotate every hour
    rotate 168               # Keep 7 days (168 hours)
    compress
    delaycompress
    missingok
    notifempty
    create 0640 csat csat
}
```

## Alternative: Size-Based Rotation

If you want rotation based on file size:

```bash
/var/log/csat/app.log {
    size 100M                # Rotate when file reaches 100 MB
    rotate 10                # Keep 10 files
    compress
    delaycompress
    missingok
    notifempty
    create 0640 csat csat
}
```

## Testing After Setup

### 1. Check that logrotate is working

```bash
# View logrotate status for csat
sudo logrotate -v /etc/logrotate.d/csat 2>&1 | grep csat

# Check systemd journal for logrotate
sudo journalctl -u logrotate -n 20
```

### 2. Monitor disk usage over time

```bash
# Create a monitoring script
cat > ~/check_logs.sh << 'EOF'
#!/bin/bash
echo "=== Log Directory Usage ==="
du -sh /var/log/csat/
echo ""
echo "=== Files ==="
ls -lh /var/log/csat/
echo ""
echo "=== File Count ==="
ls /var/log/csat/app.log* | wc -l
EOF

chmod +x ~/check_logs.sh

# Run daily
/home/myname/check_logs.sh
```

## Troubleshooting

### Logrotate not running

```bash
# Check if logrotate daemon is running
sudo systemctl status logrotate

# Or check cron
sudo systemctl status cron

# Manually run logrotate
sudo logrotate -f /etc/logrotate.d/csat

# Check status
ls -lh /var/log/csat/
```

### Logs not being rotated

```bash
# Verify configuration syntax
sudo logrotate -d /etc/logrotate.d/csat

# Check permissions
ls -la /etc/logrotate.d/csat

# Check if postrotate script is failing
sudo logrotate -v /etc/logrotate.d/csat

# Check service status
sudo systemctl status csat
```

### Permission denied errors

```bash
# Fix permissions
sudo chown csat:csat /var/log/csat
sudo chmod 750 /var/log/csat
sudo chmod 640 /var/log/csat/app.log*
```

## Storage Planning

### Calculate disk space needed

```
Assuming:
- Average log file: 50 MB/day
- Rotation: 30 days
- Compression ratio: 10% of original

Total space: 50 MB × 30 × 0.1 = 150 MB
```

### Examples by traffic level

| Traffic | Daily Size | 30-day (compressed) |
|---------|-----------|-------------------|
| Light (100 req/day) | 5 MB | 15 MB |
| Medium (1000 req/day) | 50 MB | 150 MB |
| Heavy (10000 req/day) | 500 MB | 1.5 GB |

## Post-Deployment Checklist

- [ ] Logrotate config created: `/etc/logrotate.d/csat`
- [ ] Configuration verified: `sudo logrotate -d /etc/logrotate.d/csat`
- [ ] App can write logs: Check `/var/log/csat/app.log`
- [ ] Permissions correct: `ls -l /var/log/csat/`
- [ ] Tested rotation: `sudo logrotate -f /etc/logrotate.d/csat`
- [ ] Compressed files created: `ls /var/log/csat/app.log*.gz`

---

**That's it!** Your logs will now be automatically managed and won't fill your disk.
