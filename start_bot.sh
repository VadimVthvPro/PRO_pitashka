#!/bin/bash

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                                                               ║"
echo "║   🚀 ЗАПУСК БОТА PROpitashka (Google Gemini)                  ║"
echo "║                                                               ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Проверка .env
if [ ! -f ".env" ]; then
    echo "❌ Файл .env не найден!"
    echo "   Создайте файл .env и добавьте TOKEN и GEMINI_API_KEY"
    exit 1
fi

# Проверка TOKEN
if ! grep -q "^TOKEN=.\\+" .env; then
    echo "❌ TOKEN не указан в .env!"
    echo "   Получите TOKEN у @BotFather и добавьте в .env"
    exit 1
fi

# Проверка GEMINI_API_KEY
if ! grep -q "^GEMINI_API_KEY=.\\+" .env; then
    echo "❌ GEMINI_API_KEY не указан в .env!"
    echo "   Получите на https://makersuite.google.com/app/apikey"
    echo ""
    echo "   Добавьте в .env:"
    echo "   GEMINI_API_KEY=AIzaSy..."
    exit 1
fi

echo "✅ Конфигурация проверена"
echo "✅ Используется Google Gemini Pro"
echo ""
echo "🤖 Запускаю бота..."
echo ""

python3 main.py
