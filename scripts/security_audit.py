#!/usr/bin/env python3
"""
Скрипт для аудита безопасности проекта PROpitashka.
Проверяет наличие распространенных уязвимостей.

Использование:
    python scripts/security_audit.py

Автор: PROpitashka Team
Дата: 2025-10-31
"""
import sys
import os
from pathlib import Path
import re

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import psycopg2
    from config import config
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("\n💡 Установите необходимые зависимости:")
    print("   pip install psycopg2-binary python-dotenv")
    sys.exit(1)


class SecurityAuditor:
    """Класс для проведения аудита безопасности проекта."""
    
    def __init__(self):
        self.issues = []
        self.warnings = []
        self.passed = []
        self.base_dir = Path(__file__).parent.parent
    
    def check_default_admin_password(self):
        """Проверяет, изменен ли дефолтный пароль админа."""
        print("1. Проверка дефолтного пароля администратора... ", end="", flush=True)
        
        try:
            conn = psycopg2.connect(**config.get_db_config(admin=True))
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT username, password_reset_required, password_changed_at
                FROM admin_users
                WHERE username = 'admin'
            """)
            
            result = cursor.fetchone()
            if result:
                username, reset_required, changed_at = result
                
                if reset_required or changed_at is None:
                    self.issues.append(
                        "❌ КРИТИЧНО: Дефолтный пароль администратора не изменен!\n"
                        "   Запустите: python scripts/change_admin_password.py"
                    )
                    print("❌")
                else:
                    self.passed.append("✅ Пароль администратора изменен")
                    print("✅")
            else:
                self.warnings.append("⚠️  Пользователь admin не найден в базе данных")
                print("⚠️")
            
            cursor.close()
            conn.close()
        except Exception as e:
            self.warnings.append(f"⚠️  Не удалось проверить пароль админа: {e}")
            print("⚠️")
    
    def check_env_file_in_gitignore(self):
        """Проверяет, что .env файл в .gitignore."""
        print("2. Проверка .gitignore... ", end="", flush=True)
        
        gitignore_path = self.base_dir / ".gitignore"
        
        if gitignore_path.exists():
            with open(gitignore_path, 'r') as f:
                content = f.read()
                
            if ".env" in content:
                self.passed.append("✅ .env файл в .gitignore")
                print("✅")
            else:
                self.issues.append(
                    "❌ КРИТИЧНО: .env файл не добавлен в .gitignore!\n"
                    "   Добавьте строку '.env' в .gitignore"
                )
                print("❌")
        else:
            self.warnings.append("⚠️  .gitignore файл не найден")
            print("⚠️")
    
    def check_hardcoded_paths(self):
        """Проверяет наличие хардкод путей в коде."""
        print("3. Проверка хардкод путей... ", end="", flush=True)
        
        main_py_path = self.base_dir / "main.py"
        
        if main_py_path.exists():
            with open(main_py_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Поиск абсолютных путей
            patterns = [
                r'/Users/\w+/',  # macOS paths
                r'C:\\Users\\',  # Windows paths
                r'/home/\w+/',   # Linux paths
            ]
            
            found_paths = []
            for pattern in patterns:
                matches = re.findall(pattern, content)
                found_paths.extend(matches)
            
            if found_paths:
                self.issues.append(
                    f"❌ Найдены хардкод пути в main.py: {set(found_paths)}"
                )
                print("❌")
            else:
                self.passed.append("✅ Хардкод пути не обнаружены")
                print("✅")
        else:
            self.warnings.append("⚠️  main.py не найден")
            print("⚠️")
    
    def check_ssl_enabled(self):
        """Проверяет, включен ли SSL для БД."""
        print("4. Проверка SSL для базы данных... ", end="", flush=True)
        
        if hasattr(config, 'DB_SSL_ENABLED') and config.DB_SSL_ENABLED:
            self.passed.append("✅ SSL для БД включен")
            print("✅")
        else:
            if config.ENVIRONMENT == 'production':
                self.warnings.append(
                    "⚠️  SSL для БД не включен на продакшене!\n"
                    "   Добавьте в .env:\n"
                    "   DB_SSLMODE=require\n"
                    "   DB_SSL_ENABLED=true"
                )
                print("⚠️")
            else:
                self.passed.append("✅ SSL не требуется (development)")
                print("✅")
    
    def check_api_keys_in_env(self):
        """Проверяет, что API ключи загружаются из .env."""
        print("5. Проверка API ключей... ", end="", flush=True)
        
        main_py_path = self.base_dir / "main.py"
        
        if main_py_path.exists():
            with open(main_py_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Поиск хардкод API ключей (простая проверка)
            api_key_pattern = r'(GEMINI_API_KEY|TOKEN)\s*=\s*["\'][A-Za-z0-9_-]{20,}["\']'
            matches = re.findall(api_key_pattern, content)
            
            if matches:
                self.issues.append(
                    "❌ КРИТИЧНО: Возможно захардкожены API ключи в коде!\n"
                    "   Используйте config.GEMINI_API_KEY из .env"
                )
                print("❌")
            else:
                self.passed.append("✅ API ключи загружаются из переменных окружения")
                print("✅")
        else:
            print("⚠️")
    
    def check_privacy_policy_exists(self):
        """Проверяет наличие файлов политики конфиденциальности."""
        print("6. Проверка Privacy Policy... ", end="", flush=True)
        
        languages = ['ru', 'en', 'de', 'fr', 'es']
        missing = []
        
        for lang in languages:
            filepath = self.base_dir / f"privacy_policy_{lang}.txt"
            if not filepath.exists():
                missing.append(lang)
        
        if missing:
            self.warnings.append(
                f"⚠️  Отсутствуют файлы политики конфиденциальности для: {', '.join(missing)}"
            )
            print("⚠️")
        else:
            self.passed.append("✅ Все файлы политики конфиденциальности на месте")
            print("✅")
    
    def check_admin_login_logging(self):
        """Проверяет, что таблица логирования входов существует."""
        print("7. Проверка логирования входов... ", end="", flush=True)
        
        try:
            conn = psycopg2.connect(**config.get_db_config(admin=True))
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'admin_login_log'
                )
            """)
            
            exists = cursor.fetchone()[0]
            
            if exists:
                # Проверяем количество записей
                cursor.execute("SELECT COUNT(*) FROM admin_login_log")
                count = cursor.fetchone()[0]
                
                self.passed.append(f"✅ Логирование входов работает ({count} записей)")
                print("✅")
            else:
                self.warnings.append(
                    "⚠️  Таблица admin_login_log не найдена.\n"
                    "   Примените миграцию: psql -U postgres -d propitashka -f migrations/005_secure_admin_system.sql"
                )
                print("⚠️")
            
            cursor.close()
            conn.close()
        except Exception as e:
            self.warnings.append(f"⚠️  Не удалось проверить логирование: {e}")
            print("⚠️")
    
    def check_sentry_configured(self):
        """Проверяет настройку Sentry для мониторинга ошибок."""
        print("8. Проверка Sentry... ", end="", flush=True)
        
        if hasattr(config, 'SENTRY_DSN') and config.SENTRY_DSN:
            self.passed.append("✅ Sentry настроен")
            print("✅")
        else:
            if config.ENVIRONMENT == 'production':
                self.warnings.append(
                    "⚠️  Sentry не настроен на продакшене!\n"
                    "   Зарегистрируйтесь на sentry.io и добавьте SENTRY_DSN в .env"
                )
                print("⚠️")
            else:
                self.passed.append("✅ Sentry не требуется (development)")
                print("✅")
    
    def check_assets_structure(self):
        """Проверяет наличие структуры assets."""
        print("9. Проверка структуры assets... ", end="", flush=True)
        
        assets_dir = self.base_dir / "assets"
        required_dirs = ["images", "gifs", "documents"]
        
        if assets_dir.exists():
            missing_dirs = [d for d in required_dirs if not (assets_dir / d).exists()]
            
            if missing_dirs:
                self.warnings.append(
                    f"⚠️  Отсутствуют директории: {', '.join(missing_dirs)}"
                )
                print("⚠️")
            else:
                # Проверяем наличие логотипа
                logo_path = assets_dir / "images" / "logo.jpg"
                if logo_path.exists():
                    self.passed.append("✅ Структура assets корректна, логотип найден")
                    print("✅")
                else:
                    self.warnings.append("⚠️  Логотип не найден в assets/images/logo.jpg")
                    print("⚠️")
        else:
            self.issues.append(
                "❌ Директория assets не найдена!\n"
                "   Создайте: mkdir -p assets/images assets/gifs assets/documents"
            )
            print("❌")
    
    def check_migrations_applied(self):
        """Проверяет применение миграций."""
        print("10. Проверка миграций... ", end="", flush=True)
        
        try:
            conn = psycopg2.connect(**config.get_db_config(admin=True))
            cursor = conn.cursor()
            
            # Проверяем наличие всех необходимых таблиц
            required_tables = [
                'user_main', 'food', 'user_aims', 'user_health',
                'user_lang', 'user_training', 'water', 'admin_users', 'admin_login_log'
            ]
            
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            
            existing_tables = [row[0] for row in cursor.fetchall()]
            missing_tables = [t for t in required_tables if t not in existing_tables]
            
            if missing_tables:
                self.warnings.append(
                    f"⚠️  Отсутствуют таблицы: {', '.join(missing_tables)}\n"
                    "   Примените все миграции из директории migrations/"
                )
                print("⚠️")
            else:
                self.passed.append("✅ Все необходимые таблицы созданы")
                print("✅")
            
            cursor.close()
            conn.close()
        except Exception as e:
            self.warnings.append(f"⚠️  Не удалось проверить миграции: {e}")
            print("⚠️")
    
    def run_audit(self):
        """Запускает все проверки."""
        print("=" * 70)
        print("  🔒 АУДИТ БЕЗОПАСНОСТИ PROPITASHKA")
        print("=" * 70)
        print(f"\n📅 Дата: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🌍 Окружение: {config.ENVIRONMENT}")
        print()
        
        # Запускаем все проверки
        checks = [
            self.check_default_admin_password,
            self.check_env_file_in_gitignore,
            self.check_hardcoded_paths,
            self.check_ssl_enabled,
            self.check_api_keys_in_env,
            self.check_privacy_policy_exists,
            self.check_admin_login_logging,
            self.check_sentry_configured,
            self.check_assets_structure,
            self.check_migrations_applied,
        ]
        
        for check in checks:
            try:
                check()
            except Exception as e:
                print(f"❌ ({e})")
                self.warnings.append(f"⚠️  Ошибка при выполнении проверки: {e}")
        
        # Выводим результаты
        print()
        print("=" * 70)
        print("  📊 РЕЗУЛЬТАТЫ АУДИТА")
        print("=" * 70)
        print()
        
        if self.passed:
            print("✅ ПРОЙДЕНО:")
            for item in self.passed:
                print(f"  {item}")
            print()
        
        if self.warnings:
            print("⚠️  ПРЕДУПРЕЖДЕНИЯ:")
            for item in self.warnings:
                lines = item.split('\n')
                for line in lines:
                    print(f"  {line}")
            print()
        
        if self.issues:
            print("❌ КРИТИЧНЫЕ ПРОБЛЕМЫ:")
            for item in self.issues:
                lines = item.split('\n')
                for line in lines:
                    print(f"  {line}")
            print()
            print("⚠️  ВНИМАНИЕ: Обнаружены критичные проблемы безопасности!")
            print("Необходимо исправить их перед развертыванием на продакшн.")
            print()
            return False
        else:
            print("✅ Критичных проблем не обнаружено!")
            if not self.warnings:
                print("🎉 Проект готов к развертыванию с точки зрения безопасности.")
            else:
                print("💡 Рекомендуется устранить предупреждения перед продакшном.")
            print()
            return True
    
    def print_recommendations(self):
        """Выводит рекомендации по улучшению безопасности."""
        print("=" * 70)
        print("  💡 РЕКОМЕНДАЦИИ ПО БЕЗОПАСНОСТИ")
        print("=" * 70)
        print()
        print("1. 🔐 Регулярно меняйте пароли админов (раз в 90 дней)")
        print("2. 📊 Проверяйте логи входов: SELECT * FROM admin_login_log")
        print("3. 💾 Настройте автоматические бэкапы БД")
        print("4. 🔔 Настройте алерты в Sentry на критичные ошибки")
        print("5. 🔒 Включите SSL для БД на продакшене")
        print("6. 🌐 Разместите Privacy Policy на HTTPS")
        print("7. 📝 Ведите журнал изменений конфигурации")
        print("8. 🚨 Настройте мониторинг доступности бота")
        print()


if __name__ == "__main__":
    try:
        auditor = SecurityAuditor()
        success = auditor.run_audit()
        auditor.print_recommendations()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n❌ Прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


