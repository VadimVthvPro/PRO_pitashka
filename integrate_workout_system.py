#!/usr/bin/env python3
"""
Скрипт автоматической интеграции новой системы тренировок в main.py
Автоматически вносит необходимые изменения в код
"""

import os
import sys
import re
from pathlib import Path


def backup_file(filepath):
    """Создать резервную копию файла"""
    backup_path = f"{filepath}.backup"
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ Создана резервная копия: {backup_path}")
    return backup_path


def read_file(filepath):
    """Прочитать файл"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()


def write_file(filepath, content):
    """Записать файл"""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)


def add_imports(content):
    """Добавить необходимые импорты"""
    print("📦 Добавление импортов...")
    
    # Найти место после существующих импортов
    import_pattern = r'(from aiogram\.fsm\.state import State, StatesGroup.*?\n)'
    
    new_imports = """
# Импорты для новой системы тренировок
from app.domain.workouts.workout_service import get_workout_service
from app.presentation.bot.routers.workout_handlers import get_workout_router, WorkoutStates
"""
    
    # Проверяем, не добавлены ли уже импорты
    if 'from app.domain.workouts.workout_service' in content:
        print("⚠️  Импорты уже добавлены, пропускаем")
        return content
    
    # Добавляем импорты после определения FSM
    content = re.sub(import_pattern, r'\1' + new_imports, content, count=1)
    print("✅ Импорты добавлены")
    return content


def create_workout_service(content):
    """Создать экземпляр сервиса тренировок"""
    print("🔧 Создание экземпляра workout_service...")
    
    # Найти место после создания подключения к БД
    db_pattern = r'(conn = psycopg2\.connect\(\*\*config\.get_db_config\(\)\).*?\n.*?cursor = conn\.cursor\(\).*?\n)'
    
    workout_service_code = """
# Создание сервиса тренировок
workout_service = get_workout_service(conn)
"""
    
    # Проверяем, не создан ли уже сервис
    if 'workout_service = get_workout_service' in content:
        print("⚠️  workout_service уже создан, пропускаем")
        return content
    
    content = re.sub(db_pattern, r'\1' + workout_service_code, content, count=1, flags=re.DOTALL)
    print("✅ workout_service создан")
    return content


def register_router(content):
    """Зарегистрировать роутер тренировок"""
    print("🎯 Регистрация роутера тренировок...")
    
    # Найти место после создания диспетчера
    dp_pattern = r'(dp = Dispatcher\(storage=storage\).*?\n)'
    
    router_code = """
# Регистрация роутера тренировок
workout_router = get_workout_router()
dp.include_router(workout_router)
"""
    
    # Проверяем, не зарегистрирован ли уже роутер
    if 'workout_router = get_workout_router' in content:
        print("⚠️  Роутер уже зарегистрирован, пропускаем")
        return content
    
    content = re.sub(dp_pattern, r'\1' + router_code, content, count=1)
    print("✅ Роутер зарегистрирован")
    return content


def create_middleware(content):
    """Создать middleware для dependency injection"""
    print("🔌 Создание middleware...")
    
    middleware_code = """

# ============================================
# Middleware для Dependency Injection
# ============================================

class DatabaseMiddleware(BaseMiddleware):
    \"\"\"Middleware для передачи db_connection и workout_service в обработчики\"\"\"
    
    def __init__(self, db_connection, workout_service):
        super().__init__()
        self.db_connection = db_connection
        self.workout_service = workout_service
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        data["db_connection"] = self.db_connection
        data["workout_service"] = self.workout_service
        return await handler(event, data)

"""
    
    # Проверяем, не создан ли уже middleware
    if 'class DatabaseMiddleware' in content:
        print("⚠️  DatabaseMiddleware уже создан, пропускаем")
        return content
    
    # Вставляем middleware перед созданием бота
    bot_pattern = r'(bot = Bot\(TOKEN.*?\))'
    content = re.sub(bot_pattern, middleware_code + r'\n\1', content, count=1)
    
    # Регистрируем middleware
    privacy_middleware_pattern = r'(dp\.update\.middleware\(PrivacyConsentMiddleware\(\)\))'
    middleware_registration = r'\1\ndp.update.middleware(DatabaseMiddleware(conn, workout_service))'
    
    if 'dp.update.middleware(DatabaseMiddleware' not in content:
        content = re.sub(privacy_middleware_pattern, middleware_registration, content, count=1)
        print("✅ Middleware создан и зарегистрирован")
    else:
        print("⚠️  Middleware уже зарегистрирован")
    
    return content


def remove_old_handlers(content):
    """Удалить старые обработчики тренировок"""
    print("🗑️  Удаление старых обработчиков...")
    
    # Удаляем старый обработчик tren()
    tren_pattern = r'@dp\.message\(F\.text\.in_\(\{[^}]*Добавить тренировки[^}]*\}\)\)\nasync def tren\(.*?\n(?=(?:@dp\.|def |class |# =))'
    content = re.sub(tren_pattern, '', content, flags=re.DOTALL)
    
    # Удаляем старый обработчик tren_type()
    tren_type_pattern = r'@dp\.message\(REG\.types\)\nasync def tren_type\(.*?\n(?=(?:@dp\.|def |class |# =))'
    content = re.sub(tren_type_pattern, '', content, flags=re.DOTALL)
    
    # Удаляем функцию intensiv()
    intensiv_pattern = r'def intensiv\(intensiv, id\):.*?\n(?=(?:@dp\.|def |class |# =))'
    content = re.sub(intensiv_pattern, '', content, flags=re.DOTALL)
    
    print("✅ Старые обработчики удалены")
    return content


def remove_old_state(content):
    """Удалить старое состояние REG.types"""
    print("🗑️  Удаление старого состояния FSM...")
    
    # Удаляем строку types = State()
    types_pattern = r'\s*types = State\(\)\s*\n'
    content = re.sub(types_pattern, '\n', content)
    
    print("✅ Старое состояние удалено")
    return content


def update_keyboards_py():
    """Обновить keyboards.py - удалить старую клавиатуру tren"""
    print("\n🎹 Обновление keyboards.py...")
    
    keyboards_path = 'keyboards.py'
    if not os.path.exists(keyboards_path):
        print("⚠️  keyboards.py не найден")
        return
    
    # Создаем резервную копию
    backup_file(keyboards_path)
    
    content = read_file(keyboards_path)
    
    # Удаляем определение клавиатуры tren
    tren_keyboard_pattern = r'\s*tren = ReplyKeyboardMarkup\(.*?\),\s*\n'
    content = re.sub(tren_keyboard_pattern, '', content, flags=re.DOTALL)
    
    # Удаляем 'tren' из словаря kb
    kb_pattern = r"'tren':\s*tren,\s*"
    content = re.sub(kb_pattern, '', content)
    
    write_file(keyboards_path, content)
    print("✅ keyboards.py обновлен")


def main():
    """Главная функция"""
    print("=" * 60)
    print("🚀 АВТОМАТИЧЕСКАЯ ИНТЕГРАЦИЯ СИСТЕМЫ ТРЕНИРОВОК V2.0")
    print("=" * 60)
    print()
    
    # Проверяем наличие main.py
    main_py_path = 'main.py'
    if not os.path.exists(main_py_path):
        print("❌ Ошибка: main.py не найден в текущей директории")
        print(f"   Текущая директория: {os.getcwd()}")
        return 1
    
    print(f"📁 Рабочая директория: {os.getcwd()}")
    print()
    
    # Создаем резервную копию
    print("💾 Создание резервных копий...")
    backup_file(main_py_path)
    print()
    
    # Читаем содержимое main.py
    print("📖 Чтение main.py...")
    content = read_file(main_py_path)
    print(f"✅ Прочитано {len(content)} символов")
    print()
    
    # Применяем изменения
    content = add_imports(content)
    content = create_workout_service(content)
    content = register_router(content)
    content = create_middleware(content)
    content = remove_old_state(content)
    content = remove_old_handlers(content)
    
    # Записываем обновленный файл
    print()
    print("💾 Сохранение изменений в main.py...")
    write_file(main_py_path, content)
    print("✅ main.py обновлен")
    print()
    
    # Обновляем keyboards.py
    update_keyboards_py()
    
    print()
    print("=" * 60)
    print("✅ ИНТЕГРАЦИЯ ЗАВЕРШЕНА УСПЕШНО!")
    print("=" * 60)
    print()
    print("📋 Следующие шаги:")
    print("1. Проверьте файлы *.backup - это резервные копии")
    print("2. Запустите миграцию БД:")
    print("   psql -U postgres -d propitashka -f migrations/001_create_training_system.sql")
    print("3. Протестируйте бота: python main.py")
    print()
    print("📚 Документация: TRAINING_SYSTEM_V2_INTEGRATION.md")
    print()
    
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


