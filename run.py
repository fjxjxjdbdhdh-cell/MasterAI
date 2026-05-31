#!/usr/bin/env python3
"""
run.py - ПОЛНЫЙ ФАЙЛ ЗАПУСКА MASTER AI
Включает все патчи и исправления
"""

import asyncio
import os
import signal
import sys
import yaml
from dotenv import load_dotenv
from datetime import datetime
import logging

# Импорт основного модуля
from ai_core_complete import (
    MasterAI, 
    get_mt5, 
    AdvancedRiskEngine, 
    OnlineLearningEngine,
    EventBus,
    TradingEvent
)

# ============================================================
# ПАТЧИ (дополнительные функции, которых нет в основном файле)
# ============================================================

async def emit_risk_alerts_patch(self, event_bus, positions, account):
    """Отправка оповещений о рисках"""
    if not event_bus:
        return
    risk_score = self.compute_portfolio_risk_score(positions, account)
    if risk_score > 0.8:
        await event_bus.publish(TradingEvent(
            event_type=EventBus.RISK_ALERT,
            source="AdvancedRiskEngine",
            payload={"risk_score": risk_score, "message": "Critical risk level"},
            priority=2,
        ))

async def check_performance_degradation_patch(self, memory_engine):
    """Проверка деградации производительности"""
    try:
        recent = memory_engine.get_recent_performance(50)
        if recent.get("avg_reward", 0) < -0.5:
            return {
                "degradation_detected": True,
                "avg_reward": recent["avg_reward"],
                "suggested_action": "reduce_risk"
            }
        return None
    except Exception:
        return None

def load_env_config_patch(self):
    """Автозагрузка из .env"""
    load_dotenv()
    
    if os.getenv("RISK_PER_TRADE"):
        self.risk_engine.risk_per_trade = float(os.getenv("RISK_PER_TRADE"))
    if os.getenv("MAX_POSITIONS"):
        self.risk_engine.max_positions = int(os.getenv("MAX_POSITIONS"))
    if os.getenv("MAX_DAILY_LOSS"):
        self.risk_engine.max_daily_loss = float(os.getenv("MAX_DAILY_LOSS"))
    if os.getenv("MAX_DRAWDOWN"):
        self.risk_engine.max_drawdown = float(os.getenv("MAX_DRAWDOWN"))

def apply_patches(ai_instance, risk_engine_instance, learning_engine_instance):
    """Применяет все патчи к объектам AI"""
    applied = []
    
    # Применяем к AdvancedRiskEngine
    if not hasattr(risk_engine_instance, 'emit_risk_alerts'):
        risk_engine_instance.emit_risk_alerts = emit_risk_alerts_patch.__get__(risk_engine_instance)
        applied.append("emit_risk_alerts")
    
    # Применяем к OnlineLearningEngine
    if not hasattr(learning_engine_instance, 'check_performance_degradation'):
        learning_engine_instance.check_performance_degradation = check_performance_degradation_patch.__get__(learning_engine_instance)
        applied.append("check_performance_degradation")
    
    # Применяем к MasterAI
    if not hasattr(ai_instance, '_load_env_config'):
        ai_instance._load_env_config = load_env_config_patch.__get__(ai_instance)
        applied.append("_load_env_config")
    
    if applied:
        logging.info(f"✅ Применены патчи: {', '.join(applied)}")
    else:
        logging.info("ℹ️ Все патчи уже применены")

# ============================================================
# НАСТРОЙКА ЛОГИРОВАНИЯ
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("master_ai.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("run")

# ============================================================
# ОСНОВНОЙ КЛАСС ЗАПУСКА
# ============================================================

class AILauncher:
    def __init__(self):
        self.ai = None
        self.running = True
        self.config = None
        
    async def load_config(self):
        """Загрузка конфигурации"""
        try:
            with open("config.yaml", "r") as f:
                self.config = yaml.safe_load(f)
            logger.info("✅ Конфигурация загружена из config.yaml")
        except FileNotFoundError:
            logger.warning("config.yaml не найден, использую стандартные настройки")
            self.config = {
                "trading": {"symbols": ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD"]},
                "safety": {"max_trades_per_hour": 20, "max_trades_per_day": 50}
            }
        
    async def start(self):
        """Запуск AI"""
        await self.load_config()
        
        # Получаем символы
        symbols = os.getenv("SYMBOLS")
        if symbols:
            symbols = symbols.split(",")
        else:
            symbols = self.config["trading"]["symbols"]
        
        logger.info(f"📊 Торгуемые символы: {symbols}")
        
        # Создаём AI
        self.ai = MasterAI(symbols, db_path="trading.db")
        
        # Подключаемся к MT5
        mt5 = get_mt5()
        login = int(os.getenv("MT5_LOGIN", 0))
        
        if login > 0:
            logger.info(f"🔌 Подключение к MT5 (логин: {login})...")
            mt5.connect(
                login=login,
                password=os.getenv("MT5_PASSWORD"),
                server=os.getenv("MT5_SERVER"),
                path=os.getenv("MT5_PATH")
            )
        else:
            logger.warning("⚠️ MT5 логин не указан, работа в симуляционном режиме")
        
        # Применяем патчи
        apply_patches(self.ai, self.ai.advanced_risk_engine, self.ai.online_learning_engine)
        
        # Загружаем настройки из .env
        if hasattr(self.ai, '_load_env_config'):
            self.ai._load_env_config()
        
        # Настройка параметров из конфига
        self.ai.risk_engine.risk_per_trade = float(os.getenv("RISK_PER_TRADE", self.config["trading"].get("risk_per_trade", 0.01)))
        self.ai.risk_engine.max_positions = int(os.getenv("MAX_POSITIONS", self.config["trading"].get("max_positions", 5)))
        
        if hasattr(self.ai, 'execution_safety'):
            self.ai.execution_safety.max_trades_per_hour = self.config["safety"].get("max_trades_per_hour", 20)
            self.ai.execution_safety.max_daily_trades = self.config["safety"].get("max_trades_per_day", 50)
        
        # Запускаем инициализацию
        logger.info("🚀 Инициализация Master AI...")
        await self.ai.initialize()
        
        # Включаем автоторговлю
        if os.getenv("AUTOTRADE_ENABLED", "true").lower() == "true":
            self.ai.autotrade_running = True
            logger.info("✅ АВТОТОРГОВЛЯ ВКЛЮЧЕНА")
        else:
            logger.info("⏸️ Автоторговля выключена (только анализ)")
        
        # Выводим статус
        logger.info(f"🎯 Текущая стратегия: {self.ai.current_strategy}")
        logger.info(f"📈 Режим рынка: {self.ai.current_regime}")
        logger.info(f"⚡ Режим торговли: {self.ai.current_trading_mode}")
        
        # Настройка обработчиков сигналов
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)
        
    def _shutdown(self, *args):
        """Обработка сигналов остановки"""
        logger.info("⏹️ Получен сигнал остановки...")
        self.running = False
        
    async def run(self):
        """Основной цикл работы"""
        await self.start()
        
        last_status_time = 0
        
        while self.running:
            try:
                await asyncio.sleep(10)
                
                # Обновление статуса каждую минуту
                now = datetime.now()
                if now.second < 10:  # Раз в минуту
                    status = self.ai.get_status()
                    total_profit = status.get("analytics", {}).get("total_profit", 0)
                    positions = status.get("open_trades_count", 0)
                    win_rate = status.get("analytics", {}).get("win_rate", 0)
                    
                    logger.info(f"📊 [Статус] Позиций: {positions} | P&L: {total_profit:.2f} | Win Rate: {win_rate:.1%} | Стратегия: {self.ai.current_strategy}")
                
                # Проверка kill switch
                if hasattr(self.ai, 'execution_safety') and self.ai.execution_safety.kill_switch_active:
                    logger.critical(f"💀 KILL SWITCH АКТИВЕН! Причина: {self.ai.execution_safety.kill_switch_reason}")
                    
                    # Автоматический сброс через час
                    if self.ai.execution_safety.kill_switch_triggered_at:
                        elapsed = (datetime.utcnow() - self.ai.execution_safety.kill_switch_triggered_at).total_seconds()
                        if elapsed > 3600:
                            logger.info("🔄 Автоматический сброс kill switch через час")
                            self.ai.execution_safety.deactivate_kill_switch(manual=False)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Ошибка в основном цикле: {e}")
                await asyncio.sleep(30)
        
        # Корректное завершение
        logger.info("🛑 Остановка AI...")
        await self.ai.shutdown()
        logger.info("✅ Master AI остановлен")

# ============================================================
# ЗАПУСК
# ============================================================

async def main():
    """Главная функция"""
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║     ███╗   ███╗ █████╗ ███████╗████████╗███████╗██████╗     ║
    ║     ████╗ ████║██╔══██╗██╔════╝╚══██╔══╝██╔════╝██╔══██╗    ║
    ║     ██╔████╔██║███████║███████╗   ██║   █████╗  ██████╔╝    ║
    ║     ██║╚██╔╝██║██╔══██║╚════██║   ██║   ██╔══╝  ██╔══██╗    ║
    ║     ██║ ╚═╝ ██║██║  ██║███████║   ██║   ███████╗██║  ██║    ║
    ║     ╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝   ╚═╝   ╚══════╝╚═╝  ╚═╝    ║
    ║                                                              ║
    ║                   MASTER AI TRADING SYSTEM                   ║
    ║                           v3.0                               ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    launcher = AILauncher()
    await launcher.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ Прервано пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        sys.exit(1)
