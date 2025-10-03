# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Memory-Monitor is a Python-based Linux system service that monitors process memory usage and automatically kills processes exceeding configurable thresholds. It's designed to prevent system OOM (Out of Memory) conditions by proactively managing memory-hungry processes.

## Architecture

The project consists of three main components:

1. **memory_monitor.py**: Core Python script containing the `MemoryMonitor` class that scans processes, checks memory usage against thresholds, and terminates violators
2. **memory_monitor.service**: systemd service unit file for running the monitor as a background daemon
3. **installer.sh**: Automated installation script that sets up the service, creates log rotation, and configures systemd

### Key Design Patterns

- **Configuration-driven**: All thresholds and behavior controlled via `CONFIG` dict in memory_monitor.py (lines 17-39)
- **Whitelist protection**: Multi-level protection using PID, process name, and username whitelists to prevent killing critical processes
- **Graceful degradation**: Attempts SIGTERM first, then SIGKILL if process doesn't respond within 5 seconds
- **Dry-run mode**: `DRY_RUN` flag allows testing without actually killing processes

## Common Commands

### Installation
```bash
sudo bash installer.sh
```

### Service Management
```bash
# Check service status
systemctl status memory-monitor

# View live logs
journalctl -u memory-monitor -f

# View recent logs (last 50 lines)
journalctl -u memory-monitor -n 50

# Start/stop/restart
systemctl start memory-monitor
systemctl stop memory-monitor
systemctl restart memory-monitor
```

### Testing
```bash
# Run in dry-run mode (set DRY_RUN=True in CONFIG first)
sudo python3 memory_monitor.py

# Run with Python dependencies
pip3 install -r requirements.txt
python3 memory_monitor.py
```

## Configuration

Edit thresholds in `memory_monitor.py` CONFIG dict (lines 17-39):
- `RAM_PERCENT_THRESHOLD`: Kill processes using > X% of total RAM (default: 10%)
- `RAM_GB_THRESHOLD`: Kill processes using > X GB RAM (default: 2GB)
- `CHECK_INTERVAL`: Scan frequency in seconds (default: 30s)
- `WHITELIST_PIDS`, `WHITELIST_NAMES`, `WHITELIST_USERS`: Protection lists

After modifying CONFIG, restart the service:
```bash
systemctl restart memory-monitor
```

## Important Implementation Details

- The monitor must run as root to kill processes owned by other users
- Process whitelisting logic in `is_whitelisted()` (lines 66-92) - root processes are NOT protected by default (line 83)
- Memory calculation uses RSS (Resident Set Size) for GB checks, not VMS
- The script protects itself from suicide via PID check (line 86)
- Signal handlers (lines 229-232) ensure graceful shutdown on SIGTERM/SIGINT
