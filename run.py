#!/usr/bin/env python3
import asyncio
import os
import signal
import sys
import yaml
from dotenv import load_dotenv
from ai_core_complete import MasterAI, get_mt5
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("run")

class AILauncher:
    def __init__(self):
        self.ai = None
        self.running = True
        
    async def start(self):
        # Загрузка конфига
        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)
        
        symbols = os.getenv("SYMBOLS", ",".join(config["trading"]["symbols"])).split(",")
        
        # Создание AI
        self.ai = MasterAI(symbols, db_path="trading.db")
        
        # Подключение к MT5
        mt5 = get_mt5()
        login = int(os.getenv("MT5_LOGIN", 0))
        if login > 0:
            mt5.connect(
                login=login,
                password=os.getenv("MT5_PASSWORD"),
                server=os.getenv("MT5_SERVER"),
                path=os.getenv("MT5_PATH")
            )
        
        # Настройка параметров
        self.ai.risk_engine.risk_per_trade = float(os.getenv("RISK_PER_TRADE", config["trading"]["risk_per_trade"]))
        self.ai.risk_engine.max_positions = int(os.getenv("MAX_POSITIONS", config["trading"]["max_positions"]))
        self.ai.execution_safety.max_trades_per_hour = config["safety"]["max_trades_per_hour"]
        self.ai.execution_safety.max_daily_trades = config["safety"]["max_trades_per_day"]
        
        # Запуск
        await self.ai.initialize()
        
        if os.getenv("AUTOTRADE_ENABLED", "true").lower() == "true":
            self.ai.autotrade_running = True
            logger.info("✅ Автоторговля ВКЛЮЧЕНА")
        
        logger.info(f"🎯 Стратегия: {self.ai.current_strategy}")
        logger.info(f"📊 Режим: {self.ai.current_regime}")
        
        # Обработка сигналов
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)
        
    def _shutdown(self, *args):
        logger.info("⏹️ Получен сигнал остановки...")
        self.running = False
        
    async def run(self):
        await self.start()
        
        while self.running:
            try:
                await asyncio.sleep(30)
                
                # Обновление статуса
                status = self.ai.get_status()
                total_profit = status.get("analytics", {}).get("total_profit", 0)
                positions = status.get("open_trades_count", 0)
                
                logger.info(f"📈 Позиций: {positions} | P&L: {total_profit:.2f} | Стратегия: {self.ai.current_strategy}")
                
                # Проверка kill switch
                if self.ai.execution_safety.kill_switch_active:
                    logger.critical(f"💀 KILL SWITCH АКТИВЕН: {self.ai.execution_safety.kill_switch_reason}")
                    break
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Ошибка: {e}")
                await asyncio.sleep(10)
        
        await self.ai.shutdown()
        logger.info("🛑 AI остановлен")

async def main():
    launcher = AILauncher()
    await launcher.run()

if __name__ == "__main__":
    asyncio.run(main())
