#!/bin/bash

# ====================================
# ФИНАЛЬНАЯ ПРОВЕРКА СИСТЕМЫ ТРЕНИРОВОК
# ====================================

echo "🔍 Проверка установки системы тренировок..."
echo ""

# Цвета для вывода
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Счетчики
PASSED=0
FAILED=0

# Функция проверки
check() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ $1${NC}"
        ((PASSED++))
    else
        echo -e "${RED}❌ $1${NC}"
        ((FAILED++))
    fi
}

# 1. Проверка файлов
echo "📁 Проверка файлов..."
[ -f "migrations/001_create_training_system.sql" ] && check "SQL миграция найдена" || check "SQL миграция НЕ найдена"
[ -f "app/domain/workouts/workout_service.py" ] && check "Сервис тренировок найден" || check "Сервис тренировок НЕ найден"
[ -f "app/presentation/bot/keyboards/workout_keyboards.py" ] && check "Клавиатуры найдены" || check "Клавиатуры НЕ найдены"
[ -f "app/presentation/bot/routers/workout_handlers.py" ] && check "Обработчики найдены" || check "Обработчики НЕ найдены"
[ -f "integrate_workout_system.py" ] && check "Скрипт интеграции найден" || check "Скрипт интеграции НЕ найден"
echo ""

# 2. Проверка __init__.py файлов
echo "🐍 Проверка Python пакетов..."
[ -f "app/__init__.py" ] && check "app/__init__.py" || check "app/__init__.py ОТСУТСТВУЕТ"
[ -f "app/domain/__init__.py" ] && check "app/domain/__init__.py" || check "app/domain/__init__.py ОТСУТСТВУЕТ"
[ -f "app/domain/workouts/__init__.py" ] && check "app/domain/workouts/__init__.py" || check "app/domain/workouts/__init__.py ОТСУТСТВУЕТ"
[ -f "app/presentation/__init__.py" ] && check "app/presentation/__init__.py" || check "app/presentation/__init__.py ОТСУТСТВУЕТ"
[ -f "app/presentation/bot/__init__.py" ] && check "app/presentation/bot/__init__.py" || check "app/presentation/bot/__init__.py ОТСУТСТВУЕТ"
[ -f "app/presentation/bot/keyboards/__init__.py" ] && check "app/presentation/bot/keyboards/__init__.py" || check "app/presentation/bot/keyboards/__init__.py ОТСУТСТВУЕТ"
[ -f "app/presentation/bot/routers/__init__.py" ] && check "app/presentation/bot/routers/__init__.py" || check "app/presentation/bot/routers/__init__.py ОТСУТСТВУЕТ"
echo ""

# 3. Проверка документации
echo "📚 Проверка документации..."
[ -f "TRAINING_SYSTEM_V2_INTEGRATION.md" ] && check "Полная документация найдена" || check "Полная документация НЕ найдена"
[ -f "QUICKSTART_TRAINING_V2.md" ] && check "Быстрый старт найден" || check "Быстрый старт НЕ найден"
[ -f "TRAINING_V2_UPDATE.md" ] && check "Обзор изменений найден" || check "Обзор изменений НЕ найден"
echo ""

# 4. Проверка структуры SQL файла
echo "💾 Проверка SQL миграции..."
if [ -f "migrations/001_create_training_system.sql" ]; then
    grep -q "CREATE TABLE.*training_types" migrations/001_create_training_system.sql && check "Таблица training_types" || check "Таблица training_types ОТСУТСТВУЕТ"
    grep -q "CREATE TABLE.*training_coefficients" migrations/001_create_training_system.sql && check "Таблица training_coefficients" || check "Таблица training_coefficients ОТСУТСТВУЕТ"
    grep -q "CREATE.*FUNCTION.*calculate_training_calories" migrations/001_create_training_system.sql && check "Функция calculate_training_calories" || check "Функция calculate_training_calories ОТСУТСТВУЕТ"
    grep -q "INSERT INTO training_types" migrations/001_create_training_system.sql && check "Данные тренировок" || check "Данные тренировок ОТСУТСТВУЮТ"
fi
echo ""

# 5. Проверка Python кода
echo "🐍 Проверка Python кода..."
if [ -f "app/domain/workouts/workout_service.py" ]; then
    grep -q "class WorkoutService" app/domain/workouts/workout_service.py && check "Класс WorkoutService" || check "Класс WorkoutService ОТСУТСТВУЕТ"
    grep -q "def get_training_types" app/domain/workouts/workout_service.py && check "Метод get_training_types" || check "Метод get_training_types ОТСУТСТВУЕТ"
    grep -q "def calculate_training_calories" app/domain/workouts/workout_service.py && check "Метод calculate_training_calories" || check "Метод calculate_training_calories ОТСУТСТВУЕТ"
fi
echo ""

# 6. Проверка клавиатур
echo "⌨️  Проверка клавиатур..."
if [ -f "app/presentation/bot/keyboards/workout_keyboards.py" ]; then
    grep -q "class WorkoutKeyboards" app/presentation/bot/keyboards/workout_keyboards.py && check "Класс WorkoutKeyboards" || check "Класс WorkoutKeyboards ОТСУТСТВУЕТ"
    grep -q "create_training_keyboard" app/presentation/bot/keyboards/workout_keyboards.py && check "Функция create_training_keyboard" || check "Функция create_training_keyboard ОТСУТСТВУЕТ"
    grep -q "ITEMS_PER_PAGE" app/presentation/bot/keyboards/workout_keyboards.py && check "Пагинация настроена" || check "Пагинация НЕ настроена"
fi
echo ""

# 7. Проверка обработчиков
echo "🎯 Проверка обработчиков..."
if [ -f "app/presentation/bot/routers/workout_handlers.py" ]; then
    grep -q "class WorkoutStates" app/presentation/bot/routers/workout_handlers.py && check "FSM состояния WorkoutStates" || check "FSM состояния ОТСУТСТВУЮТ"
    grep -q "workout_router" app/presentation/bot/routers/workout_handlers.py && check "Роутер workout_router" || check "Роутер workout_router ОТСУТСТВУЕТ"
    grep -q "@workout_router.message" app/presentation/bot/routers/workout_handlers.py && check "Обработчики сообщений" || check "Обработчики сообщений ОТСУТСТВУЮТ"
    grep -q "@workout_router.callback_query" app/presentation/bot/routers/workout_handlers.py && check "Обработчики callback" || check "Обработчики callback ОТСУТСТВУЮТ"
fi
echo ""

# Итоги
echo "════════════════════════════════════════"
echo "РЕЗУЛЬТАТЫ ПРОВЕРКИ:"
echo -e "${GREEN}✅ Пройдено: $PASSED${NC}"
echo -e "${RED}❌ Провалено: $FAILED${NC}"
echo "════════════════════════════════════════"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ!${NC}"
    echo ""
    echo "📋 СЛЕДУЮЩИЕ ШАГИ:"
    echo "1. Запустите миграцию БД:"
    echo "   psql -U postgres -d propitashka -f migrations/001_create_training_system.sql"
    echo ""
    echo "2. Запустите скрипт интеграции:"
    echo "   python3 integrate_workout_system.py"
    echo ""
    echo "3. Запустите бота:"
    echo "   python3 main.py"
    echo ""
    echo "📚 Документация: QUICKSTART_TRAINING_V2.md"
    exit 0
else
    echo -e "${RED}⚠️  ОБНАРУЖЕНЫ ПРОБЛЕМЫ!${NC}"
    echo "Проверьте отсутствующие файлы и попробуйте снова."
    exit 1
fi

