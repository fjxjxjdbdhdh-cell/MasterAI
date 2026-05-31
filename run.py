#!/usr/bin/env python3
"""
run.py - ПОЛНЫЙ ФАЙЛ ЗАПУСКА MASTER AI
"""

import asyncio
import os
import signal
import sys
import json
from dotenv import load_dotenv
from datetime import datetime
import logging

# Загрузка .env
load_dotenv()

from ai_core_complete import MasterAI, get_mt5

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("master_ai.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("run")

# Глобальная переменная для экземпляра AI
_ai_instance = None

class AILauncher:
    def __init__(self):
        self.ai = None
        self.running = True
        
    async def start(self):
        global _ai_instance
        
        # Получаем символы из .env или стандартные
        symbols = os.getenv("SYMBOLS", "EURUSD,GBPUSD,USDJPY,XAUUSD").split(",")
        
        logger.info(f"📊 Торгуемые символы: {symbols}")
        
        # Создаём AI
        self.ai = MasterAI(symbols, db_path="trading.db")
        _ai_instance = self.ai
        
        # Подключаемся к MT5 (если указан логин)
        login = int(os.getenv("MT5_LOGIN", 0))
        
        if login > 0:
            logger.info(f"🔌 Подключение к MT5 (логин: {login})...")
            mt5 = get_mt5()
            mt5.connect(
                login=login,
                password=os.getenv("MT5_PASSWORD"),
                server=os.getenv("MT5_SERVER"),
                path=os.getenv("MT5_PATH")
            )
        else:
            logger.warning("⚠️ MT5 логин не указан, работа в симуляционном режиме")
        
        # Настройка параметров из .env
        if os.getenv("RISK_PER_TRADE"):
            self.ai.risk_engine.risk_per_trade = float(os.getenv("RISK_PER_TRADE"))
        if os.getenv("MAX_POSITIONS"):
            self.ai.risk_engine.max_positions = int(os.getenv("MAX_POSITIONS"))
        
        # Запускаем инициализацию
        logger.info("🚀 Инициализация Master AI...")
        await self.ai.initialize()
        
        # Включаем автоторговлю
        if os.getenv("AUTOTRADE_ENABLED", "true").lower() == "true":
            self.ai.autotrade_running = True
            logger.info("✅ АВТОТОРГОВЛЯ ВКЛЮЧЕНА")
        else:
            logger.info("⏸️ Автоторговля выключена")
        
        logger.info(f"🎯 Стратегия: {self.ai.current_strategy}")
        logger.info(f"📈 Режим: {self.ai.current_regime}")
        
        # Обработка сигналов
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)
        
    def _shutdown(self, *args):
        logger.info("⏹️ Остановка...")
        self.running = False
        
    async def run(self):
        await self.start()
        
        while self.running:
            try:
                await asyncio.sleep(30)
                
                status = self.ai.get_status()
                total_profit = status.get("analytics", {}).get("total_profit", 0)
                positions = status.get("open_trades_count", 0)
                
                logger.info(f"📈 Позиций: {positions} | P&L: {total_profit:.2f} | {self.ai.current_strategy}")
                
                # Проверка kill switch
                if hasattr(self.ai, 'execution_safety') and self.ai.execution_safety.kill_switch_active:
                    logger.critical(f"💀 KILL SWITCH АКТИВЕН!")
                    break
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Ошибка: {e}")
                await asyncio.sleep(10)
        
        await self.ai.shutdown()
        logger.info("✅ AI остановлен")

# ============================================================
# ФУНКЦИИ ДЛЯ API (вызов из Docker контейнера)
# ============================================================

async def send_message(message: str) -> str:
    """Для приёма команд из API"""
    global _ai_instance
    if _ai_instance:
        result = await _ai_instance.chat(message, {})
        return result.get("reply", "Нет ответа")
    return "AI не инициализирован"

def get_status_json() -> str:
    """Получить статус в JSON"""
    global _ai_instance
    if _ai_instance:
        return json.dumps(_ai_instance.get_status())
    return json.dumps({"error": "AI not initialized"})

def start_trading():
    """Запустить торговлю"""
    global _ai_instance
    if _ai_instance:
        _ai_instance.autotrade_running = True
        logger.info("✅ Торговля запущена через API")

def stop_trading():
    """Остановить торговлю"""
    global _ai_instance
    if _ai_instance:
        _ai_instance.autotrade_running = False
        logger.info("⏸️ Торговля остановлена через API")

# ============================================================
# ЗАПУСК
# ============================================================

async def main():
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║              MASTER AI TRADING SYSTEM v3.0                   ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    launcher = AILauncher()
    await launcher.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ Прервано")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        sys.exit(1)
