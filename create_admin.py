#!/usr/bin/env python3
"""
Скрипт для создания администратора базы данных
Использование: python create_admin.py [username] [password]
"""
import sys
import bcrypt
import psycopg2
from config import config

def create_admin(username, password):
    """Создать нового администратора"""
    
    # Хеширование пароля
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    try:
        # Подключение к БД
        db_config = config.get_db_config(admin=True)
        
        # Если ADMIN_DB_PASSWORD пустой, используем обычные credentials
        if not db_config.get('password'):
            db_config = config.get_db_config(admin=False)
        
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        # Проверка существования таблицы
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'admin_users'
            );
        """)
        
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            print("❌ Таблица admin_users не существует!")
            print("📝 Выполните миграцию: psql -U postgres -d propitashka -f migrations/003_create_admin_users.sql")
            return False
        
        # Создание администратора
        cursor.execute("""
            INSERT INTO admin_users (username, password_hash)
            VALUES (%s, %s)
            ON CONFLICT (username) 
            DO UPDATE SET password_hash = EXCLUDED.password_hash
            RETURNING id;
        """, (username, password_hash))
        
        admin_id = cursor.fetchone()[0]
        conn.commit()
        
        print(f"✅ Администратор '{username}' успешно создан/обновлен (ID: {admin_id})")
        print(f"🔑 Логин: {username}")
        print(f"🔑 Пароль: {password}")
        print()
        print("⚠️  ВАЖНО: Сохраните эти данные в безопасном месте!")
        
        cursor.close()
        conn.close()
        return True
        
    except psycopg2.Error as e:
        print(f"❌ Ошибка базы данных: {e}")
        return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def main():
    """Главная функция"""
    print("=" * 60)
    print("PROпиташка - Создание администратора")
    print("=" * 60)
    print()
    
    # Получение параметров
    if len(sys.argv) >= 3:
        username = sys.argv[1]
        password = sys.argv[2]
    else:
        username = input("Введите логин администратора [admin]: ").strip() or "admin"
        password = input("Введите пароль [admin]: ").strip() or "admin"
    
    # Валидация
    if len(username) < 3:
        print("❌ Логин должен содержать минимум 3 символа")
        return
    
    if len(password) < 4:
        print("❌ Пароль должен содержать минимум 4 символа")
        return
    
    # Создание
    create_admin(username, password)

if __name__ == "__main__":
    main()

