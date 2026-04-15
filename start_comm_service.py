"""
Start Agent Communication Background Service
==========================================
Launches the notification server that monitors for messages
and wakes sleeping agents.

Usage:
    python E:\AI-Setup\start_comm_service.py

This should be run at Windows startup or when starting OpenCode.
It runs in background and monitors for inter-agent messages.
"""

import sys
import os
import time
import threading
import subprocess
import socket

sys.path.insert(0, r'E:\AI-Setup')

def start_notification_server():
    """Start the notification server in background"""
    from agent_comm_service import NotificationServer
    
    server = NotificationServer(port=5555)
    server.start()
    
    print("[CommService] Notification server running on port 5555")
    print("[CommService] Press Ctrl+C to stop")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[CommService] Stopping...")
        server.stop()
        print("[CommService] Stopped")


def check_and_start_server():
    """Check if server already running, if not start it"""
    import socket
    
    # Check if server already running
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(("127.0.0.1", 5555))
    sock.close()
    
    if result == 0:
        print("[CommService] Server already running on port 5555")
        return False
    
    print("[CommService] Starting notification server...")
    start_notification_server()
    return True


def register_with_windows_startup():
    """Register to run at Windows startup (optional)"""
    import winreg
    
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_WRITE)
        winreg.SetValueEx(key, "OpenCodeCommService", 0, winreg.REG_SZ, 
                         f'"{sys.executable}" "{os.path.abspath(__file__)}"')
        winreg.CloseKey(key)
        print("[CommService] Registered with Windows startup")
        return True
    except:
        return False


def unregister_from_windows_startup():
    """Remove from Windows startup"""
    import winreg
    
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_WRITE)
        winreg.DeleteValue(key, "OpenCodeCommService")
        winreg.CloseKey(key)
        print("[CommService] Removed from Windows startup")
        return True
    except:
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Agent Communication Service")
    parser.add_argument("--register", action="store_true", help="Register with Windows startup")
    parser.add_argument("--unregister", action="store_true", help="Remove from Windows startup")
    parser.add_argument("--check", action="store_true", help="Check if server is running")
    
    args = parser.parse_args()
    
    if args.register:
        register_with_windows_startup()
    elif args.unregister:
        unregister_from_windows_startup()
    elif args.check:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(("127.0.0.1", 5555))
        sock.close()
        if result == 0:
            print("[CommService] Server is RUNNING on port 5555")
        else:
            print("[CommService] Server is NOT running")
    else:
        check_and_start_server()
