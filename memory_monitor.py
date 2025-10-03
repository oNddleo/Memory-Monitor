#!/usr/bin/env python3
"""
RAM Monitor Script - Kill processes exceeding memory threshold
Author: System Administrator
Purpose: Monitor and kill processes using excessive RAM
"""

import psutil
import time
import logging
import sys
import os
from datetime import datetime
import signal
from pathlib import Path
try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    import tomli as tomllib  # Fallback for older Python versions

# Setup logging (will be configured properly in main)
logger = logging.getLogger(__name__)


def setup_logging(log_file):
    """Setup logging configuration"""
    # Ensure log directory exists and is writable
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir, exist_ok=True)
        except Exception:
            pass

    handlers = [logging.StreamHandler(sys.stdout)]

    # Try to add file handler
    try:
        handlers.append(logging.FileHandler(log_file))
    except PermissionError:
        logger.warning(f"Cannot write to {log_file}, logging to stdout only")

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=handlers,
        force=True
    )


class MemoryMonitor:
    def __init__(self, config):
        self.config = config
        self.total_ram = psutil.virtual_memory().total
        self.ram_percent_threshold = config['RAM_PERCENT_THRESHOLD']
        self.ram_gb_threshold = config['RAM_GB_THRESHOLD'] * (1024 ** 3)  # Convert to bytes

        logger.info(f"Memory Monitor initialized")
        logger.info(f"Total RAM: {self.total_ram / (1024**3):.2f} GB")
        logger.info(f"Thresholds: {self.ram_percent_threshold}% or {config['RAM_GB_THRESHOLD']} GB")
        logger.info(f"Dry Run Mode: {config['DRY_RUN']}")

    def is_whitelisted(self, process):
        """Check if process should be protected from killing"""
        try:
            # Check PID whitelist
            if process.pid in self.config['WHITELIST_PIDS']:
                return True

            # Check process name whitelist
            process_name = process.name().lower()
            for protected_name in self.config['WHITELIST_NAMES']:
                if protected_name.lower() in process_name:
                    return True

            # Check user whitelist (optional)
            if self.config.get('WHITELIST_USERS'):
                username = process.username()
                if username in self.config['WHITELIST_USERS']:
                    return False  # Change to True if you want to protect root processes

            # Don't kill this script itself
            if process.pid == os.getpid():
                return True

            return False

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return True  # If we can't check, don't kill

    def get_memory_usage(self, process):
        """Get memory usage of a process"""
        try:
            memory_info = process.memory_info()
            memory_percent = process.memory_percent()
            return {
                'rss': memory_info.rss,  # Resident Set Size
                'vms': memory_info.vms,  # Virtual Memory Size
                'percent': memory_percent,
                'rss_gb': memory_info.rss / (1024 ** 3)
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None

    def should_kill_process(self, process):
        """Determine if process should be killed based on memory usage"""
        memory_usage = self.get_memory_usage(process)

        if not memory_usage:
            return False, None

        # Check percentage threshold
        if memory_usage['percent'] > self.ram_percent_threshold:
            return True, f"RAM usage {memory_usage['percent']:.2f}% exceeds {self.ram_percent_threshold}%"

        # Check absolute GB threshold
        if memory_usage['rss'] > self.ram_gb_threshold:
            return True, f"RAM usage {memory_usage['rss_gb']:.2f}GB exceeds {self.config['RAM_GB_THRESHOLD']}GB"

        return False, None

    def kill_process(self, process):
        """Kill a process gracefully, then forcefully if needed"""
        try:
            process_info = {
                'pid': process.pid,
                'name': process.name(),
                'cmdline': ' '.join(process.cmdline()[:50]) if process.cmdline() else 'N/A',
                'username': process.username(),
                'memory': self.get_memory_usage(process)
            }

            if self.config['DRY_RUN']:
                logger.warning(f"[DRY RUN] Would kill process: PID={process_info['pid']}, "
                               f"Name={process_info['name']}, "
                               f"User={process_info['username']}, "
                               f"RAM={process_info['memory']['rss_gb']:.2f}GB "
                               f"({process_info['memory']['percent']:.2f}%)")
                return True

            # Log before killing
            logger.warning(f"Killing process: PID={process_info['pid']}, "
                           f"Name={process_info['name']}, "
                           f"User={process_info['username']}, "
                           f"RAM={process_info['memory']['rss_gb']:.2f}GB "
                           f"({process_info['memory']['percent']:.2f}%), "
                           f"CMD={process_info['cmdline']}")

            # Try graceful termination first
            process.terminate()
            time.sleep(5)  # Wait 5 seconds for graceful shutdown

            # Force kill if still alive
            if process.is_running():
                process.kill()
                logger.warning(f"Force killed PID {process.pid} (did not respond to SIGTERM)")

            return True

        except psutil.NoSuchProcess:
            logger.info(f"Process {process.pid} already terminated")
            return True
        except psutil.AccessDenied:
            logger.error(f"Access denied to kill PID {process.pid}")
            return False
        except Exception as e:
            logger.error(f"Error killing process {process.pid}: {e}")
            return False

    def scan_processes(self):
        """Scan all processes and kill those exceeding thresholds"""
        killed_count = 0
        scanned_count = 0

        logger.info("Starting process scan...")

        for process in psutil.process_iter(['pid', 'name', 'username']):
            try:
                scanned_count += 1

                # Skip whitelisted processes
                if self.is_whitelisted(process):
                    continue

                # Check if should kill
                should_kill, reason = self.should_kill_process(process)

                if should_kill:
                    logger.info(f"Process {process.pid} ({process.name()}) marked for termination: {reason}")
                    if self.kill_process(process):
                        killed_count += 1

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            except Exception as e:
                logger.error(f"Error processing PID {process.pid}: {e}")

        logger.info(f"Scan complete. Scanned: {scanned_count}, Killed: {killed_count}")
        return killed_count

    def run(self):
        """Main monitoring loop"""
        logger.info("Memory Monitor started")

        while True:
            try:
                # Log current system memory
                mem = psutil.virtual_memory()
                logger.info(f"System Memory: {mem.percent}% used "
                            f"({mem.used / (1024**3):.2f}GB / {mem.total / (1024**3):.2f}GB)")

                # Scan and kill processes
                self.scan_processes()

                # Wait for next check
                time.sleep(self.config['CHECK_INTERVAL'])

            except KeyboardInterrupt:
                logger.info("Received interrupt signal, shutting down...")
                break
            except Exception as e:
                logger.error(f"Unexpected error in main loop: {e}")
                time.sleep(self.config['CHECK_INTERVAL'])


def handle_signal(signum, frame):
    """Handle system signals"""
    logger.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)


def load_config():
    """Load configuration from config.toml"""
    config_path = Path(__file__).parent / 'config.toml'

    if not config_path.exists():
        logger.error(f"Configuration file not found: {config_path}")
        sys.exit(1)

    try:
        with open(config_path, 'rb') as f:
            toml_config = tomllib.load(f)

        # Convert TOML structure to the expected CONFIG format
        config = {
            'RAM_PERCENT_THRESHOLD': toml_config['thresholds']['ram_percent_threshold'],
            'RAM_GB_THRESHOLD': toml_config['thresholds']['ram_gb_threshold'],
            'CHECK_INTERVAL': toml_config['thresholds']['check_interval'],
            'WHITELIST_PIDS': toml_config['whitelist']['pids'],
            'WHITELIST_NAMES': toml_config['whitelist']['names'],
            'WHITELIST_USERS': toml_config['whitelist']['users'],
            'DRY_RUN': toml_config['settings']['dry_run'],
            'LOG_FILE': toml_config['settings']['log_file'],
            'ENABLE_SYSLOG': toml_config['settings']['enable_syslog'],
        }

        logger.info(f"Loaded configuration from {config_path}")
        return config

    except Exception as e:
        logger.error(f"Failed to load configuration from {config_path}: {e}")
        sys.exit(1)


def main():
    """Main entry point"""
    # Load configuration first
    config = load_config()

    # Setup logging with config
    setup_logging(config['LOG_FILE'])

    # Check if running as root (recommended)
    if os.geteuid() != 0:
        logger.warning("Not running as root. May not be able to kill all processes.")

    # Setup signal handlers
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    # Create and run monitor
    monitor = MemoryMonitor(config)
    monitor.run()


if __name__ == "__main__":
    main()
