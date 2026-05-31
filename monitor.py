#!/usr/bin/env python3
import subprocess
import time
import psutil
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("monitor")

class ProcessMonitor:
    def __init__(self, process_name="run.py"):
        self.process_name = process_name
        self.restart_count = 0
        self.last_restart = None
        
    def is_running(self):
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if self.process_name in ' '.join(proc.info['cmdline'] or []):
                    return True
            except:
                pass
        return False
    
    def restart(self):
        logger.warning("🔄 Перезапуск AI...")
        subprocess.Popen(["python", "run.py"])
        self.restart_count += 1
        self.last_restart = datetime.now()
        
    def run(self):
        while True:
            if not self.is_running():
                logger.error("❌ AI не работает!")
                self.restart()
            else:
                logger.debug("✅ AI работает")
            time.sleep(60)

if __name__ == "__main__":
    monitor = ProcessMonitor()
    monitor.run()
