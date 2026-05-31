# patches.py — ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ AI

import os
from dotenv import load_dotenv
from typing import Optional

# ============================================================
# ДЛЯ AdvancedRiskEngine
# ============================================================
async def emit_risk_alerts(self, event_bus, positions, account):
    """Отправка оповещений о рисках"""
    if not event_bus:
        return
    risk_score = self.compute_portfolio_risk_score(positions, account)
    if risk_score > 0.8:
        from ai_core_complete import TradingEvent, EventBus
        await event_bus.publish(TradingEvent(
            event_type=EventBus.RISK_ALERT,
            source="AdvancedRiskEngine",
            payload={"risk_score": risk_score, "message": "Critical risk level"},
            priority=2,
        ))

# ============================================================
# ДЛЯ OnlineLearningEngine
# ============================================================
async def check_performance_degradation(self, memory_engine) -> Optional[dict]:
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

# ============================================================
# ДЛЯ MasterAI
# ============================================================
def load_env_config(self):
    """Автозагрузка из .env"""
    load_dotenv()
    
    if os.getenv("RISK_PER_TRADE"):
        self.risk_engine.risk_per_trade = float(os.getenv("RISK_PER_TRADE"))
    if os.getenv("MAX_POSITIONS"):
        self.risk_engine.max_positions = int(os.getenv("MAX_POSITIONS"))

# ============================================================
# ФУНКЦИЯ ПРИМЕНЕНИЯ ПАТЧЕЙ
# ============================================================
def apply_patches(ai_instance, risk_engine_instance, learning_engine_instance):
    """Применяет все патчи к объектам AI"""
    
    # Применяем к AdvancedRiskEngine
    if not hasattr(risk_engine_instance, 'emit_risk_alerts'):
        risk_engine_instance.emit_risk_alerts = emit_risk_alerts.__get__(risk_engine_instance)
    
    # Применяем к OnlineLearningEngine
    if not hasattr(learning_engine_instance, 'check_performance_degradation'):
        learning_engine_instance.check_performance_degradation = check_performance_degradation.__get__(learning_engine_instance)
    
    # Применяем к MasterAI
    if not hasattr(ai_instance, '_load_env_config'):
        ai_instance._load_env_config = load_env_config.__get__(ai_instance)
    
    print("✅ Патчи применены")
