#!/bin/bash

echo "🛑 Останавливаю все процессы бота..."
pkill -9 -f "python.*main.py" 2>/dev/null
killall -9 python3 python 2>/dev/null

echo "⏳ Жду 3 секунды для освобождения Telegram API..."
sleep 3

echo "🚀 Запускаю бота..."
cd /Users/VadimVthv/Desktop/PROpitashka
python3 main.py






