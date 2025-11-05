# 🚀 Быстрый запуск PROpitashka (обновленная версия)

## ✨ Что нового после модернизации?

✅ Кросс-платформенность (никаких хардкод путей!)  
✅ Безопасная админ-панель (защита от brute-force, принудительная смена пароля)  
✅ Privacy Policy на HTTPS (мультиязычная HTML версия)  
✅ Система аудита безопасности  
✅ Полная документация  

---

## 📋 Предварительные требования

- Python 3.11+
- PostgreSQL 14+
- Redis 7+
- Git
- Telegram Bot Token (от @BotFather)
- Google Gemini API Key (от Google AI Studio)

---

## 🛠️ Установка и настройка

### Шаг 1: Клонирование и установка зависимостей

```bash
# Перейдите в директорию проекта
cd PROpitashka

# Создайте виртуальное окружение (если еще не создано)
python3 -m venv .

# Активируйте виртуальное окружение
source bin/activate  # macOS/Linux
# или
.\Scripts\activate  # Windows

# Установите зависимости
pip install -r requirements.txt
```

### Шаг 2: Настройка базы данных

```bash
# Войдите в PostgreSQL
psql -U postgres

# Создайте базу данных
CREATE DATABASE propitashka;

# Создайте пользователей (замените пароли!)
CREATE USER propitashka_user WITH PASSWORD 'your_secure_password';
CREATE USER propitashka_admin WITH PASSWORD 'your_admin_password';

# Выдайте права
GRANT ALL PRIVILEGES ON DATABASE propitashka TO propitashka_admin;
GRANT CONNECT ON DATABASE propitashka TO propitashka_user;

# Подключитесь к БД
\c propitashka

# Выдайте права на схему
GRANT USAGE ON SCHEMA public TO propitashka_user;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO propitashka_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO propitashka_user;

\q
```

### Шаг 3: Применение миграций

```bash
# Примените все миграции по порядку
psql -U postgres -d propitashka -f setup_database.sql
psql -U postgres -d propitashka -f analytics_dashboard.sql
psql -U postgres -d propitashka -f migrate_birthdate.sql
psql -U postgres -d propitashka -f add_chat_history.sql

# 🆕 ВАЖНО: Примените новую миграцию для безопасности
psql -U postgres -d propitashka -f migrations/005_secure_admin_system.sql
```

### Шаг 4: Конфигурация окружения

```bash
# Скопируйте пример конфигурации
cp .env.example .env

# Отредактируйте .env и заполните ваши значения
nano .env
```

**Минимально необходимые параметры в `.env`:**

```env
# Telegram Bot
TOKEN=your_bot_token_from_botfather

# Google Gemini AI
GEMINI_API_KEY=your_gemini_api_key

# PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_NAME=propitashka
DB_USER=propitashka_user
DB_PASSWORD=your_secure_password

# Admin DB
ADMIN_DB_USER=propitashka_admin
ADMIN_DB_PASSWORD=your_admin_password

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Environment
ENVIRONMENT=development
LOG_LEVEL=INFO

# 🆕 Privacy Policy URL (замените после размещения!)
PRIVACY_POLICY_URL=https://yourusername.github.io/propitashka-privacy/privacy_policy.html
```

### Шаг 5: Проверка безопасности

```bash
# 🆕 Запустите аудит безопасности
python scripts/security_audit.py
```

**Устраните все ❌ критичные проблемы перед запуском!**

### Шаг 6: Смена дефолтного пароля админа

```bash
# 🆕 ОБЯЗАТЕЛЬНО: Смените дефолтный пароль admin/admin
python scripts/change_admin_password.py

# Следуйте инструкциям на экране
# Пароль должен быть 12+ символов с буквами, цифрами и спецсимволами
```

---

## 🚀 Запуск проекта

### Запуск Telegram бота

```bash
# Убедитесь, что виртуальное окружение активировано
source bin/activate

# Запустите бота
python main.py
```

**Вы должны увидеть:**
```
✅ All critical assets validated successfully
Gemini API configured successfully with gemini-2.5-flash model (new API)
Redis cache configured successfully: localhost:6379/0
Bot polling started...
```

### Запуск админ-панели

```bash
# В отдельном терминале
python admin_of_bases.py
```

**При первом входе:**
- Логин: `admin`
- Пароль: `admin`
- ⚠️ Система **немедленно** попросит сменить пароль!

---

## 🔒 Размещение Privacy Policy на HTTPS

### Вариант A: GitHub Pages (бесплатно)

```bash
# 1. Создайте новый репозиторий на GitHub
# Например: propitashka-privacy

# 2. Инициализируйте Git в папке docs
cd docs/
git init
git add privacy_policy.html
git commit -m "Add privacy policy"

# 3. Подключите remote и запушьте
git remote add origin https://github.com/yourusername/propitashka-privacy.git
git branch -M main
git push -u origin main

# 4. Включите GitHub Pages
# Перейдите: Settings → Pages
# Source: main branch, folder: / (root)
```

**Ваш URL:** `https://yourusername.github.io/propitashka-privacy/privacy_policy.html`

### Вариант B: Netlify (рекомендуется)

```bash
# 1. Установите Netlify CLI
npm install -g netlify-cli

# 2. Залогиньтесь
netlify login

# 3. Деплой
cd docs/
netlify init
netlify deploy --prod
```

**Ваш URL:** `https://propitashka-privacy.netlify.app`

### После размещения:

```bash
# Обновите .env
echo "PRIVACY_POLICY_URL=https://ваш-реальный-url.com/privacy_policy.html" >> .env

# Перезапустите бота
```

---

## 🧪 Тестирование

### Проверка бота

1. Найдите вашего бота в Telegram: `@your_bot_username`
2. Отправьте `/start`
3. Пройдите регистрацию
4. Проверьте команду `/privacy` - должна открыться ссылка

### Проверка админки

1. Запустите `python admin_of_bases.py`
2. Войдите с новым паролем
3. Проверьте все вкладки
4. Проверьте логи входов:
   ```sql
   SELECT * FROM admin_login_log ORDER BY login_attempt_at DESC LIMIT 10;
   ```

### Проверка безопасности

```bash
# Запустите аудит
python scripts/security_audit.py

# Все проверки должны быть ✅ или ⚠️ (без ❌)
```

---

## 📊 Полезные команды

### База данных

```bash
# Подключение к БД
psql -U postgres -d propitashka

# Бэкап
pg_dump -U postgres propitashka > backup_$(date +%Y%m%d).sql

# Восстановление
psql -U postgres -d propitashka < backup_20251031.sql
```

### Логи

```bash
# Просмотр логов бота
tail -f bot.log

# Поиск ошибок
grep ERROR bot.log

# Последние 100 строк
tail -n 100 bot.log
```

### Мониторинг

```bash
# Проверка процессов
ps aux | grep python

# Redis
redis-cli ping
redis-cli INFO

# PostgreSQL
psql -U postgres -c "SELECT version();"
```

---

## 🆘 Решение проблем

### Ошибка: "Asset validation failed"

```bash
# Убедитесь, что логотип на месте
ls -la assets/images/logo.jpg

# Если нет - скопируйте
cp new_logo.jpg assets/images/logo.jpg
```

### Ошибка: "Connection to database failed"

```bash
# Проверьте PostgreSQL
sudo systemctl status postgresql  # Linux
brew services list | grep postgresql  # macOS

# Проверьте креденшелы в .env
grep DB_ .env
```

### Ошибка: "GEMINI_API_KEY not found"

```bash
# Убедитесь, что ключ в .env
grep GEMINI_API_KEY .env

# Проверьте, что .env загружается
python -c "from config import config; print(config.GEMINI_API_KEY)"
```

### Ошибка: "Admin login failed"

```bash
# Сбросьте пароль админа
python scripts/change_admin_password.py

# Проверьте таблицу
psql -U postgres -d propitashka -c "SELECT username, password_reset_required FROM admin_users;"
```

---

## 📚 Дополнительная документация

- **SECURITY.md** - Руководство по безопасности
- **MODERNIZATION_SUMMARY.md** - Отчет о модернизации
- **DEPLOYMENT_GUIDE.md** - Развертывание на продакшен
- **ANALYTICS_GUIDE.md** - Работа с аналитикой
- **ADMIN_APP_README.md** - Инструкции по админ-панели

---

## 🎯 Контрольный список перед продакшном

- [ ] Применены все миграции
- [ ] Сменен дефолтный пароль админа
- [ ] Privacy Policy размещена на HTTPS
- [ ] Запущен аудит безопасности (без ❌)
- [ ] Настроены бэкапы БД
- [ ] SSL включен для БД (`DB_SSL_ENABLED=true`)
- [ ] Логи настроены (`LOG_LEVEL=INFO`)
- [ ] Redis работает
- [ ] Протестированы основные команды бота
- [ ] Проверена админ-панель

---

## 💡 Рекомендации

1. **Используйте systemd/supervisor** для автозапуска бота на продакшене
2. **Настройте Nginx** как reverse proxy
3. **Включите SSL** для БД
4. **Добавьте Sentry** для мониторинга ошибок
5. **Настройте автоматические бэкапы** через cron

---

## 🆘 Поддержка

При возникновении проблем:
1. Проверьте `bot.log` на ошибки
2. Запустите `python scripts/security_audit.py`
3. Проверьте документацию в `SECURITY.md`
4. Проверьте GitHub Issues проекта

---

## 🎉 Готово!

Ваш бот PROpitashka готов к работе!

**Следующие шаги:**
1. Разместите Privacy Policy на HTTPS
2. Настройте мониторинг (Sentry/UptimeRobot)
3. Добавьте монетизацию (Premium-подписка)
4. Запустите рекламу/реферальную программу

**Удачи! 🚀💰**


