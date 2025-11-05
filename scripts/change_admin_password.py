#!/usr/bin/env python3
"""
Скрипт для безопасной смены пароля администратора PROpitashka.
Использует bcrypt для хеширования и проверяет надежность пароля.

Использование:
    python scripts/change_admin_password.py              # Интерактивный режим
    python scripts/change_admin_password.py --generate   # Генерация случайного пароля

Автор: PROpitashka Team
Дата: 2025-10-31
"""
import sys
import os
from pathlib import Path

# Добавляем корневую директорию в путь для импорта config
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import bcrypt
    import psycopg2
    import getpass
    import re
    from datetime import datetime
    from config import config
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("\n💡 Установите необходимые зависимости:")
    print("   pip install bcrypt psycopg2-binary python-dotenv")
    sys.exit(1)


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Проверяет надежность пароля.
    
    Требования:
    - Минимум 12 символов
    - Хотя бы одна заглавная буква
    - Хотя бы одна строчная буква
    - Хотя бы одна цифра
    - Хотя бы один специальный символ
    
    Returns:
        (is_valid, error_message)
    """
    if len(password) < 12:
        return False, "⚠️  Пароль должен содержать минимум 12 символов"
    
    if not re.search(r'[A-Z]', password):
        return False, "⚠️  Пароль должен содержать хотя бы одну заглавную букву (A-Z)"
    
    if not re.search(r'[a-z]', password):
        return False, "⚠️  Пароль должен содержать хотя бы одну строчную букву (a-z)"
    
    if not re.search(r'\d', password):
        return False, "⚠️  Пароль должен содержать хотя бы одну цифру (0-9)"
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "⚠️  Пароль должен содержать хотя бы один специальный символ (!@#$%^&* и т.д.)"
    
    # Проверка на общие слабые пароли
    weak_passwords = [
        'password', 'qwerty', '12345678', 'admin123', 'letmein',
        'welcome', 'monkey', '1234567890', 'password1', 'abc123',
        'password123', 'admin1234', 'password12', '123456789'
    ]
    if password.lower() in weak_passwords:
        return False, "⚠️  Этот пароль слишком распространенный и небезопасный"
    
    return True, ""


def hash_password(password: str) -> str:
    """Хеширует пароль с использованием bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def change_admin_password(username: str, new_password: str) -> bool:
    """
    Меняет пароль администратора в базе данных.
    
    Args:
        username: Имя пользователя администратора
        new_password: Новый пароль (уже валидированный)
        
    Returns:
        True если успешно, False при ошибке
    """
    try:
        conn = psycopg2.connect(**config.get_db_config(admin=True))
        cursor = conn.cursor()
        
        # Проверяем, существует ли пользователь
        cursor.execute("SELECT username FROM admin_users WHERE username = %s", (username,))
        if not cursor.fetchone():
            print(f"❌ Пользователь '{username}' не найден в базе данных!")
            cursor.close()
            conn.close()
            return False
        
        # Хешируем новый пароль
        password_hash = hash_password(new_password)
        
        # Обновляем пароль
        cursor.execute("""
            UPDATE admin_users 
            SET password_hash = %s,
                password_changed_at = NOW(),
                password_reset_required = FALSE,
                failed_login_attempts = 0,
                locked_until = NULL
            WHERE username = %s
        """, (password_hash, username))
        
        conn.commit()
        
        print(f"\n✅ Пароль для пользователя '{username}' успешно изменен!")
        print(f"📅 Дата смены: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        cursor.close()
        conn.close()
        return True
        
    except psycopg2.Error as e:
        print(f"❌ Ошибка базы данных: {e}")
        return False
    except Exception as e:
        print(f"❌ Непредвиденная ошибка: {e}")
        return False


def interactive_password_change():
    """Интерактивный режим смены пароля."""
    print("=" * 70)
    print("     🔒 СМЕНА ПАРОЛЯ АДМИНИСТРАТОРА PROPITASHKA")
    print("=" * 70)
    print()
    
    # Запрашиваем имя пользователя
    username = input("👤 Введите имя пользователя (по умолчанию: admin): ").strip()
    if not username:
        username = "admin"
    
    print()
    print("📋 Требования к паролю:")
    print("  • Минимум 12 символов")
    print("  • Заглавные и строчные буквы (A-Z, a-z)")
    print("  • Цифры (0-9)")
    print("  • Специальные символы (!@#$%^&* и т.д.)")
    print()
    
    max_attempts = 3
    attempt = 0
    
    while attempt < max_attempts:
        attempt += 1
        
        # Запрашиваем новый пароль (скрытый ввод)
        try:
            new_password = getpass.getpass("🔑 Введите новый пароль: ")
        except KeyboardInterrupt:
            print("\n\n❌ Отменено пользователем")
            return
        
        if not new_password:
            print("❌ Пароль не может быть пустым!")
            continue
        
        # Валидируем пароль
        is_valid, error_msg = validate_password_strength(new_password)
        if not is_valid:
            print(f"{error_msg}")
            if attempt < max_attempts:
                print(f"Попробуйте еще раз (попытка {attempt}/{max_attempts})\n")
            continue
        
        # Подтверждение пароля
        try:
            confirm_password = getpass.getpass("🔑 Подтвердите новый пароль: ")
        except KeyboardInterrupt:
            print("\n\n❌ Отменено пользователем")
            return
        
        if new_password != confirm_password:
            print("❌ Пароли не совпадают! Попробуйте еще раз.")
            if attempt < max_attempts:
                print(f"Попытка {attempt}/{max_attempts}\n")
            continue
        
        # Все проверки пройдены
        break
    else:
        print("\n❌ Превышено количество попыток. Попробуйте позже.")
        return
    
    print()
    confirm = input("⚠️  Вы уверены, что хотите сменить пароль? (yes/no): ").strip().lower()
    if confirm not in ['yes', 'y', 'да', 'д']:
        print("❌ Отменено пользователем")
        return
    
    print()
    print("🔄 Обновление пароля...")
    
    if change_admin_password(username, new_password):
        print()
        print("=" * 70)
        print("✅ УСПЕХ!")
        print("=" * 70)
        print()
        print("💡 ВАЖНО: Сохраните новый пароль в безопасном месте!")
        print("   Рекомендуется использовать менеджер паролей:")
        print("   - 1Password (https://1password.com)")
        print("   - Bitwarden (https://bitwarden.com)")
        print("   - LastPass (https://lastpass.com)")
        print()
    else:
        print()
        print("=" * 70)
        print("❌ ОШИБКА!")
        print("=" * 70)
        print()
        print("💡 Проверьте:")
        print("   1. Правильность настроек БД в .env файле")
        print("   2. Наличие прав администратора БД")
        print("   3. Применена ли миграция: migrations/005_secure_admin_system.sql")
        print()


def generate_random_password() -> str:
    """Генерирует случайный безопасный пароль."""
    import secrets
    import string
    
    # Генерируем пароль из 16 символов
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    
    # Пытаемся до 100 раз сгенерировать пароль, который пройдет валидацию
    for _ in range(100):
        password = ''.join(secrets.choice(alphabet) for _ in range(16))
        is_valid, _ = validate_password_strength(password)
        if is_valid:
            return password
    
    # Если не получилось, создаем вручную гарантированно валидный
    return (
        secrets.choice(string.ascii_uppercase) +
        secrets.choice(string.ascii_lowercase) +
        secrets.choice(string.digits) +
        secrets.choice("!@#$%^&*") +
        ''.join(secrets.choice(alphabet) for _ in range(12))
    )


def print_usage():
    """Выводит справку по использованию."""
    print("""
Использование:
    python scripts/change_admin_password.py              # Интерактивный режим
    python scripts/change_admin_password.py --generate   # Генерация случайного пароля
    python scripts/change_admin_password.py --help       # Показать эту справку

Примеры:
    # Интерактивная смена пароля
    python scripts/change_admin_password.py

    # Сгенерировать и показать случайный безопасный пароль
    python scripts/change_admin_password.py --generate

Требования:
    - База данных должна быть запущена
    - Файл .env должен содержать корректные данные для подключения
    - Миграция 005_secure_admin_system.sql должна быть применена
    """)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        
        if arg in ['--generate', '-g']:
            # Режим генерации случайного пароля
            print("=" * 70)
            print("     🎲 ГЕНЕРАТОР БЕЗОПАСНОГО ПАРОЛЯ")
            print("=" * 70)
            print()
            password = generate_random_password()
            print("Сгенерированный безопасный пароль:")
            print()
            print(f"    {password}")
            print()
            print("=" * 70)
            print()
            print("💡 Используйте этот пароль или создайте свой с помощью:")
            print("   python scripts/change_admin_password.py")
            print()
            
        elif arg in ['--help', '-h', 'help']:
            # Показываем справку
            print_usage()
            
        else:
            print(f"❌ Неизвестный аргумент: {arg}")
            print_usage()
            sys.exit(1)
    else:
        # Интерактивный режим (по умолчанию)
        try:
            interactive_password_change()
        except KeyboardInterrupt:
            print("\n\n❌ Прервано пользователем")
            sys.exit(1)
        except Exception as e:
            print(f"\n❌ Критическая ошибка: {e}")
            sys.exit(1)


