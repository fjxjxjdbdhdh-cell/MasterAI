#!/usr/bin/env python3
import subprocess
import json
from typing import Dict, Optional

class DockerManager:
    def __init__(self):
        self.containers: Dict[str, dict] = {}
        
    def create_container(self, user_id: str, mt5_login: int, mt5_password: str, mt5_server: str) -> Optional[str]:
        """Создаёт контейнер для пользователя с его MT5"""
        container_name = f"user_{user_id}"
        
        cmd = f"""docker run -d \
            --name {container_name} \
            --restart unless-stopped \
            -e MT5_LOGIN={mt5_login} \
            -e MT5_PASSWORD={mt5_password} \
            -e MT5_SERVER={mt5_server} \
            -e USER_ID={user_id} \
            -v user_{user_id}_state:/app/ai_state \
            -v user_{user_id}_db:/app/trading.db \
            master-ai"""
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Контейнер создан: {container_name}")
            return container_name
        print(f"❌ Ошибка: {result.stderr}")
        return None
    
    def remove_container(self, user_id: str) -> bool:
        """Удаляет контейнер пользователя"""
        container_name = f"user_{user_id}"
        subprocess.run(f"docker stop {container_name}", shell=True)
        subprocess.run(f"docker rm {container_name}", shell=True)
        print(f"✅ Удалён: {container_name}")
        return True
    
    def get_container_status(self, user_id: str) -> str:
        """Статус контейнера"""
        container_name = f"user_{user_id}"
        result = subprocess.run(f"docker ps --filter name={container_name} --format '{{{{.Status}}}}'", 
                               shell=True, capture_output=True, text=True)
        return result.stdout.strip() or "not_found"

if __name__ == "__main__":
    manager = DockerManager()
    
    # Пример: когда пользователь подключается через сайт
    # manager.create_container("user123", 12345678, "password", "ICMarkets-Demo")
    
    print("✅ Docker Manager готов")
