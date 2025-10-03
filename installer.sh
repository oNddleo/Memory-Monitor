#!/bin/bash
#
# Installation script for Memory Monitor Service
# Run as root: sudo bash install.sh
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="/opt/memory-monitor"
SERVICE_NAME="memory-monitor.service"
SYSTEMD_DIR="/etc/systemd/system"
LOG_DIR="/var/log"

echo -e "${GREEN}Memory Monitor Service Installer${NC}"
echo "================================="

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}This script must be run as root${NC}"
   exit 1
fi

# Check Python3 and pip
echo -e "${YELLOW}Checking dependencies...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python3 is not installed. Installing...${NC}"
    apt-get update && apt-get install -y python3 python3-pip || \
    yum install -y python3 python3-pip
fi

# Install Python packages
echo -e "${YELLOW}Installing Python packages...${NC}"
pip3 install psutil tomli

# Create installation directory
echo -e "${YELLOW}Creating installation directory...${NC}"
mkdir -p ${INSTALL_DIR}

# Copy script file
echo -e "${YELLOW}Installing monitor script...${NC}"
if [ -f "memory_monitor.py" ]; then
    cp memory_monitor.py ${INSTALL_DIR}/
    chmod +x ${INSTALL_DIR}/memory_monitor.py
else
    echo -e "${RED}memory_monitor.py not found in current directory${NC}"
    exit 1
fi

# Copy config file
echo -e "${YELLOW}Installing configuration file...${NC}"
if [ -f "config.toml" ]; then
    cp config.toml ${INSTALL_DIR}/
else
    echo -e "${RED}config.toml not found in current directory${NC}"
    exit 1
fi

# Install systemd service
echo -e "${YELLOW}Installing systemd service...${NC}"
if [ -f "memory_monitor.service" ]; then
    cp memory_monitor.service ${SYSTEMD_DIR}/${SERVICE_NAME}
elif [ -f "memory-monitor.service" ]; then
    cp memory-monitor.service ${SYSTEMD_DIR}/${SERVICE_NAME}
else
    # Create service file if not exists
    cat > ${SYSTEMD_DIR}/${SERVICE_NAME} <<'EOF'
[Unit]
Description=Memory Monitor Service
After=multi-user.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/memory-monitor
ExecStart=/usr/bin/python3 /opt/memory-monitor/memory_monitor.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
fi

# Create log rotation config
echo -e "${YELLOW}Setting up log rotation...${NC}"
cat > /etc/logrotate.d/memory-monitor <<EOF
/var/log/memory_monitor.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 root root
    postrotate
        systemctl reload memory-monitor.service > /dev/null 2>&1 || true
    endscript
}
EOF

# Reload systemd
echo -e "${YELLOW}Reloading systemd daemon...${NC}"
systemctl daemon-reload

# Enable and start service
echo -e "${YELLOW}Enabling and starting service...${NC}"
systemctl enable ${SERVICE_NAME}
systemctl start ${SERVICE_NAME}

# Check status
sleep 2
if systemctl is-active --quiet ${SERVICE_NAME}; then
    echo -e "${GREEN}✓ Service installed and running successfully!${NC}"
    echo ""
    echo "Useful commands:"
    echo "  Check status:  systemctl status memory-monitor"
    echo "  View logs:     journalctl -u memory-monitor -f"
    echo "  Stop service:  systemctl stop memory-monitor"
    echo "  Start service: systemctl start memory-monitor"
    echo "  Edit config:   nano ${INSTALL_DIR}/config.toml"
    echo "  Restart after config change: systemctl restart memory-monitor"
else
    echo -e "${RED}✗ Service failed to start. Check logs:${NC}"
    echo "  journalctl -u memory-monitor -n 50"
    exit 1
fi

echo ""
echo -e "${GREEN}Installation complete!${NC}"