#!/usr/bin/env python3
"""
Test script to allocate memory for testing the Memory Monitor
Creates a process that uses 100MB of RAM
"""

import time
import sys

def allocate_memory(megabytes=100):
    """Allocate specified amount of memory in MB"""
    print(f"Allocating {megabytes}MB of memory...")

    # Create a list that holds approximately the specified MB
    # Each character is roughly 1 byte, so we need megabytes * 1024 * 1024 bytes
    bytes_needed = megabytes * 1024 * 1024

    # Allocate memory by creating a large byte array
    memory_hog = bytearray(bytes_needed)

    # Fill it with data to ensure it's actually allocated in RAM
    for i in range(0, bytes_needed, 1024):
        memory_hog[i] = i % 256

    print(f"Successfully allocated {megabytes}MB")
    print(f"Process PID: {sys.argv[0] if len(sys.argv) > 0 else 'unknown'}")
    print("Press Ctrl+C to exit...")

    # Keep the process running and hold the memory
    try:
        while True:
            time.sleep(10)
            print(f"Still holding {megabytes}MB of memory... (PID: {id(memory_hog)})")
    except KeyboardInterrupt:
        print("\nExiting...")
        del memory_hog

if __name__ == "__main__":
    # Default to 100MB, but allow custom amount via command line
    mb = 100
    if len(sys.argv) > 1:
        try:
            mb = int(sys.argv[1])
        except ValueError:
            print(f"Invalid argument. Usage: {sys.argv[0]} [megabytes]")
            sys.exit(1)

    allocate_memory(mb)
