#!/bin/bash
# CSAT Deployment Script
# Run this on the Ubuntu server with sudo

set -e  # Exit on error

echo "🚀 CSAT Service Deployment Script"
echo "=================================="

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "❌ This script must be run as root"
   exit 1
fi

# Step 1: System Setup
echo "📦 Step 1: Installing system dependencies..."
apt update && apt upgrade -y
apt install -y python3.10 python3.10-venv python3-pip \
  nginx certbot python3-certbot-nginx curl git supervisor

# Step 2: Create users and directories
echo "👤 Step 2: Creating csat user and directories..."
if ! id -u csat > /dev/null 2>&1; then
    useradd -m -s /bin/bash csat
fi

mkdir -p /opt/csat /var/lib/csat /var/log/csat
chown -R csat:csat /opt/csat /var/lib/csat /var/log/csat
chmod 750 /var/lib/csat /var/log/csat

# Step 3: Application Setup
echo "📥 Step 3: Setting up application..."
if [ -d "/opt/csat/.git" ]; then
    echo "Repository already exists, pulling latest..."
    cd /opt/csat
    sudo -u csat git pull
else
    echo "Enter repository URL (or skip with Enter):"
    read repo_url
    if [ ! -z "$repo_url" ]; then
        git clone "$repo_url" /opt/csat
    fi
fi

cd /opt/csat

# Python environment
echo "🐍 Step 4: Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    sudo -u csat python3.10 -m venv venv
fi

sudo -u csat bash -c 'source venv/bin/activate && pip install -r requirements.txt'

# Step 5: Environment Configuration
echo "⚙️  Step 5: Creating environment configuration..."
cat > /opt/csat/.env << 'EOF'
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
CSAT_ALLOWED_ORIGINS=https://survey.ostrovok.ru,https://survey.emergingtravel.com

# Jira Integration
JIRA_WEBHOOK_URL=https://help.etg.team/rest/cb-automation/latest/hooks/0757f9384ac13d78353d8f86be65e7bd9877e50a
EOF

chown csat:csat /opt/csat/.env
chmod 600 /opt/csat/.env

echo "⚠️  Edit /opt/csat/.env to configure JIRA_WEBHOOK_URL and CORS origins"

# Step 6: Systemd Service
echo "🔧 Step 6: Creating systemd service..."
cat > /etc/systemd/system/csat.service << 'EOF'
[Unit]
Description=CSAT Survey Service
After=network.target

[Service]
Type=notify
User=csat
WorkingDirectory=/opt/csat
Environment="PATH=/opt/csat/venv/bin"
EnvironmentFile=/opt/csat/.env

ExecStart=/opt/csat/venv/bin/python -m uvicorn main:app \
  --host ${CSAT_HOST} \
  --port ${CSAT_PORT} \
  --workers ${CSAT_WORKERS}

Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=csat

PrivateTmp=yes
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/var/lib/csat /var/log/csat

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable csat

# Step 7: Nginx Configuration
echo "🌐 Step 7: Configuring Nginx..."
cp /opt/csat/DEPLOYMENT.md /opt/csat/nginx-config-example.conf
# Note: User should manually configure nginx based on DEPLOYMENT.md

# Step 8: SSL Setup (optional)
echo "🔐 Step 8: SSL Certificate Setup (optional)"
echo "To set up SSL certificates later, run:"
echo "sudo certbot certonly --nginx -d survey.ostrovok.ru -d survey.emergingtravel.com"

# Step 9: Start Service
echo "▶️  Step 9: Starting CSAT service..."
systemctl start csat

# Check status
if systemctl is-active --quiet csat; then
    echo "✅ CSAT service is running!"
else
    echo "❌ CSAT service failed to start. Check logs:"
    journalctl -u csat -n 20
fi

echo ""
echo "========================================="
echo "✨ Deployment Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Edit /opt/csat/.env to configure settings"
echo "2. Read /opt/csat/DEPLOYMENT.md for Nginx setup"
echo "3. Obtain SSL certificates with certbot"
echo "4. Configure Nginx based on the guide"
echo ""
echo "Check service status:"
echo "  sudo systemctl status csat"
echo ""
echo "View logs:"
echo "  sudo journalctl -u csat -f"
