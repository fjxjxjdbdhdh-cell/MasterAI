#!/usr/bin/env python3
import shutil
import os
import gzip
import schedule
import time
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backup")

BACKUP_PATH = os.getenv("BACKUP_PATH", "/backups")
KEEP_LAST = int(os.getenv("BACKUP_KEEP_LAST", 10))

def backup():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"{BACKUP_PATH}/ai_state_{timestamp}.tar.gz"
    
    # Сжатие
    with gzip.open(backup_file, "wb") as f:
        shutil.make_archive(backup_file.replace(".gz", ""), 'gztar', "ai_state")
    
    logger.info(f"✅ Бэкап создан: {backup_file}")
    
    # Очистка старых
    backups = sorted([f for f in os.listdir(BACKUP_PATH) if f.endswith(".tar.gz")])
    for old in backups[:-KEEP_LAST]:
        os.remove(os.path.join(BACKUP_PATH, old))
        logger.info(f"🗑️ Удалён старый бэкап: {old}")

def run_backup_scheduler():
    schedule.every(6).hours.do(backup)
    logger.info("🕒 Планировщик бэкапов запущен (каждые 6 часов)")
    
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    run_backup_scheduler()
