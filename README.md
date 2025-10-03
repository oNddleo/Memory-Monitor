# Memory Monitor

A Python-based Linux system service that automatically monitors and terminates processes exceeding configurable memory thresholds. Designed to prevent Out-of-Memory (OOM) conditions by proactively managing memory-hungry processes.

## Features

- **Dual Threshold System**: Kill processes based on percentage of total RAM or absolute GB usage
- **Process Whitelisting**: Protect critical system processes by PID, name, or username
- **Graceful Termination**: Attempts SIGTERM first, then SIGKILL if necessary
- **Dry-Run Mode**: Test configuration without actually killing processes
- **Systemd Integration**: Run as a background service with automatic restart
- **Comprehensive Logging**: File and journal logging with automatic log rotation

## Requirements

- Linux system with systemd
- Python 3.6+
- Root privileges (recommended for killing all processes)

## Quick Start

### Installation

```bash
# Clone or download the repository
cd Memory-Monitor

# Run the installer script
sudo bash installer.sh
```

The installer will:
- Install Python dependencies
- Create `/opt/memory-monitor/` directory
- Copy files and create default configuration
- Set up systemd service
- Configure log rotation
- Start the service automatically

### Manual Installation

#### Using uv (Recommended)

```bash
# Install dependencies with uv
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt

# Copy files
sudo mkdir -p /opt/memory-monitor
sudo cp memory_monitor.py config.toml /opt/memory-monitor/
sudo cp memory_monitor.service /etc/systemd/system/

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable memory-monitor
sudo systemctl start memory-monitor
```

#### Using pip

```bash
# Install dependencies
pip3 install -r requirements.txt

# Copy files
sudo mkdir -p /opt/memory-monitor
sudo cp memory_monitor.py config.toml /opt/memory-monitor/
sudo cp memory_monitor.service /etc/systemd/system/

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable memory-monitor
sudo systemctl start memory-monitor
```

## Configuration

### Default Settings

The service uses these default settings from `config.toml`:

```toml
[thresholds]
ram_percent_threshold = 10.0  # Kill if process uses >10% of total RAM
ram_gb_threshold = 2.0        # Kill if process uses >2GB RAM
check_interval = 30           # Check every 30 seconds

[whitelist]
pids = [1]                    # Never kill these PIDs
names = [                     # Never kill processes with these names
    "systemd",
    "kernel",
    "init",
    "sshd",
    "docker",
]
users = ["root"]              # Processes owned by these users

[settings]
dry_run = false               # Set true to test without killing
log_file = "/var/log/memory_monitor.log"
enable_syslog = true
```

### Customizing Configuration

Edit the `config.toml` file to customize thresholds and behavior:

```bash
sudo nano /opt/memory-monitor/config.toml
sudo systemctl restart memory-monitor
```

### Whitelisting Processes

Add processes to protect in `config.toml`:

```toml
[whitelist]
pids = [1, 1234]              # Protect specific PIDs
names = [
    "systemd",
    "sshd",
    "docker",
    "postgres",               # Add your critical processes
    "nginx",
]
users = ["root"]              # Protect processes by username
```

**Note**: By default, root user processes are NOT protected. To change this behavior, modify the `is_whitelisted()` method in memory_monitor.py.

## Usage

### Service Management

```bash
# Check service status
systemctl status memory-monitor

# View live logs
journalctl -u memory-monitor -f

# View recent logs
journalctl -u memory-monitor -n 50

# Stop/start/restart service
sudo systemctl stop memory-monitor
sudo systemctl start memory-monitor
sudo systemctl restart memory-monitor

# Disable service
sudo systemctl disable memory-monitor
```

### Testing in Dry-Run Mode

Before using in production, test with dry-run mode:

```bash
# Edit config to enable dry-run
sudo nano /opt/memory-monitor/config.toml
# Set: dry_run = true

# Restart and watch logs
sudo systemctl restart memory-monitor
journalctl -u memory-monitor -f
```

This will log which processes *would* be killed without actually terminating them.

### Manual Testing

#### Using uv

```bash
# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt

# Run the script
sudo .venv/bin/python3 memory_monitor.py
```

#### Using standard venv

```bash
# Create virtual environment and install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run the script
sudo ./venv/bin/python3 memory_monitor.py
```

#### Direct execution

```bash
# Run directly (as root, requires system-wide psutil)
sudo python3 memory_monitor.py
```

## How It Works

1. **Scanning**: Every `CHECK_INTERVAL` seconds, scans all running processes
2. **Evaluation**: Checks each process against both thresholds (percentage and GB)
3. **Whitelist Check**: Skips protected processes (system critical, whitelisted)
4. **Termination**:
   - Sends SIGTERM (graceful shutdown)
   - Waits 5 seconds
   - Sends SIGKILL if process still running
5. **Logging**: Records all actions to log file and systemd journal

### Memory Calculation

- **Percentage**: Based on process's share of total system RAM
- **Absolute**: Uses RSS (Resident Set Size) - actual physical memory used
- A process is killed if it exceeds **either** threshold

## Log Files

### Log Locations

- **File**: `/var/log/memory_monitor.log`
- **Systemd Journal**: `journalctl -u memory-monitor`

### Log Rotation

Automatic log rotation configured via `/etc/logrotate.d/memory-monitor`:
- Rotates daily
- Keeps 7 days of logs
- Compresses old logs

### Log Format

```
2025-10-03 10:15:30 - INFO - System Memory: 45.2% used (7.24GB / 16.00GB)
2025-10-03 10:15:31 - WARNING - Killing process: PID=12345, Name=chrome, User=john, RAM=3.50GB (21.88%)
2025-10-03 10:15:31 - INFO - Scan complete. Scanned: 245, Killed: 1
```

## Troubleshooting

### Service Won't Start

```bash
# Check service status
systemctl status memory-monitor

# View error logs
journalctl -u memory-monitor -n 50

# Common issues:
# - Python not installed: sudo apt install python3 python3-pip
# - Missing psutil: pip3 install psutil
# - Permission errors: Service must run as root
```

### Processes Not Being Killed

1. **Check if whitelisted**: Process may match whitelist criteria
2. **Check thresholds**: Process memory usage may be below thresholds
3. **Check permissions**: Service needs root to kill processes from other users
4. **Enable dry-run**: Test to see what would be killed

```bash
# View what's being scanned
journalctl -u memory-monitor -f
```

### False Positives

If legitimate processes are being killed:

1. Add to whitelist in `memory_monitor.py`
2. Increase thresholds in config
3. Check for memory leaks in your applications

## Uninstallation

```bash
# Stop and disable service
sudo systemctl stop memory-monitor
sudo systemctl disable memory-monitor

# Remove files
sudo rm /etc/systemd/system/memory-monitor.service
sudo rm -rf /opt/memory-monitor
sudo rm /var/log/memory_monitor.log
sudo rm /etc/logrotate.d/memory-monitor

# Reload systemd
sudo systemctl daemon-reload
```

## Security Considerations

- **Root Access**: Service runs as root to terminate processes from any user
- **Whitelist Carefully**: Killing critical processes can crash your system
- **Test First**: Always test with `DRY_RUN: true` in new environments
- **Monitor Logs**: Regularly review what's being killed
- **Resource Limits**: Service itself limited to 10% CPU and 100MB RAM

## Advanced Usage

### Custom Check Intervals by Time of Day

Edit `memory_monitor.py` to implement dynamic intervals:

```python
def get_check_interval(self):
    """Example: Check more frequently during business hours"""
    import datetime
    hour = datetime.datetime.now().hour
    if 9 <= hour < 17:  # Business hours
        return 15  # Every 15 seconds
    return 60  # Every minute off-hours
```

### Email Notifications

Add email alerts when processes are killed:

```python
import smtplib
from email.message import EmailMessage

def send_alert(process_info):
    msg = EmailMessage()
    msg.set_content(f"Killed process: {process_info}")
    msg['Subject'] = 'Memory Monitor Alert'
    msg['From'] = 'monitor@example.com'
    msg['To'] = 'admin@example.com'

    with smtplib.SMTP('localhost') as s:
        s.send_message(msg)
```

### Integration with Monitoring Tools

Export metrics to Prometheus, Grafana, or other tools by logging in structured format (JSON).

## Contributing

Contributions are welcome! Please:

1. Test changes thoroughly in dry-run mode
2. Document configuration options
3. Update CLAUDE.md and README.md as needed

## License

This project is provided as-is for system administration purposes. Use at your own risk.

## Author

System Administrator

## Changelog

### v1.0 (2025-10-03)
- Initial release
- Dual threshold system (percentage and GB)
- Process whitelisting
- Graceful termination with fallback
- Dry-run mode for testing
- Systemd service integration
- Automatic log rotation
- TOML configuration file support
