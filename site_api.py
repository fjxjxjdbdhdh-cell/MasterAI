#!/usr/bin/env python3
"""
ЕДИНЫЙ API ДЛЯ САЙТА
- Регистрация/вход пользователей
- Подключение MT5 через Docker
- Чат с AI
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import subprocess
import uuid
from datetime import datetime

app = FastAPI(title="Master AI API", version="1.0")

# Разрешаем запросы с твоего сайта
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Укажи свой домен
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# МОДЕЛИ ДАННЫХ
# ============================================================

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class ConnectMT5Request(BaseModel):
    mt5_login: int
    mt5_password: str
    mt5_server: str

class ChatRequest(BaseModel):
    message: str

# ============================================================
# ВРЕМЕННЫЕ ХРАНИЛИЩА (замени на БД)
# ============================================================

users_db = {}        # email -> {id, username, password}
sessions_db = {}     # session_token -> user_id
containers_db = {}   # user_id -> container_name

# ============================================================
# API ЭНДПОИНТЫ
# ============================================================

@app.post("/api/register")
async def register(data: RegisterRequest):
    """Регистрация"""
    if data.email in users_db:
        raise HTTPException(status_code=400, detail="Email уже существует")
    
    user_id = str(uuid.uuid4())[:8]
    users_db[data.email] = {
        "id": user_id,
        "username": data.username,
        "email": data.email,
        "password": data.password,
        "created_at": datetime.now().isoformat()
    }
    
    return {"status": "success", "user_id": user_id, "message": "Регистрация успешна"}

@app.post("/api/login")
async def login(data: LoginRequest):
    """Вход"""
    if data.email not in users_db:
        raise HTTPException(status_code=401, detail="Неверный email или пароль")
    
    user = users_db[data.email]
    if user["password"] != data.password:
        raise HTTPException(status_code=401, detail="Неверный email или пароль")
    
    session_token = str(uuid.uuid4())
    sessions_db[session_token] = user["id"]
    
    return {
        "status": "success",
        "session_token": session_token,
        "user_id": user["id"],
        "username": user["username"]
    }

@app.post("/api/logout")
async def logout(session_token: str):
    """Выход"""
    if session_token in sessions_db:
        del sessions_db[session_token]
    return {"status": "success"}

@app.post("/api/connect_mt5")
async def connect_mt5(data: ConnectMT5Request, session_token: str):
    """Подключение MT5 (создаёт Docker контейнер)"""
    
    if session_token not in sessions_db:
        raise HTTPException(status_code=401, detail="Не авторизован")
    
    user_id = sessions_db[session_token]
    container_name = f"user_{user_id}"
    
    # Создаём Docker контейнер с данными MT5
    cmd = f"""docker run -d \
        --name {container_name} \
        --restart unless-stopped \
        -e MT5_LOGIN={data.mt5_login} \
        -e MT5_PASSWORD={data.mt5_password} \
        -e MT5_SERVER={data.mt5_server} \
        -e USER_ID={user_id} \
        -v user_{user_id}_state:/app/ai_state \
        -v user_{user_id}_db:/app/trading.db \
        master-ai"""
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        containers_db[user_id] = container_name
        return {
            "status": "connected",
            "message": f"MT5 аккаунт {data.mt5_login} подключен",
            "container": container_name
        }
    else:
        raise HTTPException(status_code=500, detail=result.stderr)

@app.post("/api/chat")
async def chat(data: ChatRequest, session_token: str):
    """Чат с AI"""
    
    if session_token not in sessions_db:
        raise HTTPException(status_code=401, detail="Не авторизован")
    
    user_id = sessions_db[session_token]
    container_name = containers_db.get(user_id)
    
    if not container_name:
        raise HTTPException(status_code=404, detail="MT5 не подключен")
    
    # Отправляем команду в контейнер
    safe_message = data.message.replace('"', '\\"')
    cmd = f'docker exec {container_name} python -c "from run import send_message; print(send_message(\'{safe_message}\'))"'
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    return {
        "message": data.message,
        "response": result.stdout.strip() or "AI ответил",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/status")
async def get_status(session_token: str):
    """Статус пользователя"""
    
    if session_token not in sessions_db:
        raise HTTPException(status_code=401, detail="Не авторизован")
    
    user_id = sessions_db[session_token]
    container_name = containers_db.get(user_id)
    
    if not container_name:
        return {"status": "mt5_not_connected"}
    
    # Проверяем работает ли контейнер
    result = subprocess.run(f"docker ps --filter name={container_name} --format '{{{{.Status}}}}'", 
                           shell=True, capture_output=True, text=True)
    
    return {
        "status": "running" if result.stdout else "stopped",
        "container": container_name,
        "user_id": user_id
    }

@app.delete("/api/disconnect_mt5")
async def disconnect_mt5(session_token: str):
    """Отключить MT5 (удалить контейнер)"""
    
    if session_token not in sessions_db:
        raise HTTPException(status_code=401, detail="Не авторизован")
    
    user_id = sessions_db[session_token]
    container_name = containers_db.get(user_id)
    
    if container_name:
        subprocess.run(f"docker stop {container_name}", shell=True)
        subprocess.run(f"docker rm {container_name}", shell=True)
        del containers_db[user_id]
    
    return {"status": "disconnected"}

@app.get("/api/health")
async def health():
    """Проверка работы API"""
    return {
        "status": "healthy",
        "users": len(users_db),
        "active_containers": len(containers_db),
        "active_sessions": len(sessions_db)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
