#!/usr/bin/env python3
"""
Скрипт для проверки подключения к базе данных
"""
import sys
from config import config

print("=" * 60)
print("Проверка конфигурации базы данных")
print("=" * 60)
print()

# Проверка обычных credentials
print("📋 Обычные credentials (для бота):")
db_config = config.get_db_config(admin=False)
print(f"  DB_NAME: {db_config.get('dbname')}")
print(f"  DB_USER: {db_config.get('user')}")
print(f"  DB_PASSWORD: {'*' * len(db_config.get('password', '')) if db_config.get('password') else '(НЕ ЗАДАН!)'}")
print(f"  DB_HOST: {db_config.get('host')}")
print(f"  DB_PORT: {db_config.get('port')}")
print()

# Проверка admin credentials
print("👨‍💼 Admin credentials (для администратора):")
admin_config = config.get_db_config(admin=True)
print(f"  ADMIN_DB_USER: {admin_config.get('user')}")
print(f"  ADMIN_DB_PASSWORD: {'*' * len(admin_config.get('password', '')) if admin_config.get('password') else '(НЕ ЗАДАН!)'}")
print()

# Попытка подключения
print("🔌 Проверка подключения к базе данных...")
print()

try:
    import psycopg2
    
    # Пробуем admin credentials
    print("1️⃣ Пробуем подключиться с admin credentials...")
    if admin_config.get('password'):
        conn = psycopg2.connect(**admin_config)
        print("   ✅ Успешно подключились с ADMIN_DB_USER!")
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"   PostgreSQL версия: {version.split(',')[0]}")
        cursor.close()
        conn.close()
    else:
        print("   ⚠️  ADMIN_DB_PASSWORD не задан, пробуем обычные credentials...")
        
        # Пробуем обычные credentials
        print()
        print("2️⃣ Пробуем подключиться с обычными credentials...")
        conn = psycopg2.connect(**db_config)
        print("   ✅ Успешно подключились с DB_USER!")
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"   PostgreSQL версия: {version.split(',')[0]}")
        cursor.close()
        conn.close()
    
    print()
    print("=" * 60)
    print("✅ Подключение к базе данных работает!")
    print("=" * 60)
    print()
    print("Теперь можете запустить: python admin_of_bases.py")
    
except Exception as e:
    print()
    print("=" * 60)
    print("❌ ОШИБКА подключения!")
    print("=" * 60)
    print(f"Причина: {e}")
    print()
    print("🔧 Что делать:")
    print("1. Проверьте, что PostgreSQL запущен: pg_isready")
    print("2. Проверьте данные в файле .env:")
    print("   - DB_PASSWORD или ADMIN_DB_PASSWORD должен быть указан")
    print("   - DB_USER / ADMIN_DB_USER (обычно 'postgres')")
    print("   - DB_NAME (обычно 'propitashka')")
    print("3. Проверьте, что база данных существует:")
    print("   psql -U postgres -l | grep propitashka")
    sys.exit(1)

