#!/bin/bash
# Простой скрипт запуска

cd "$(dirname "$0")"

# Активация виртуального окружения
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Проверка зависимостей
pip install -r requirements.txt

# Запуск
python run.py
