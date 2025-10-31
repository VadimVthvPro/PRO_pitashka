# ⚡ Быстрый старт PROpitashka

## 🎯 За 5 минут до запуска

### Шаг 1: Инициализация PostgreSQL

```bash
# 1. Создайте базу данных
createdb propitashka

# 2. Примените полную схему
psql -U postgres -d propitashka -f setup_database.sql
```

**Важно**: В `setup_database.sql` измените пароли:
- `propitashka_bot` - пользователь для бота
- `propitashka_admin` - пользователь для админки
- Администратор по умолчанию: `admin/admin` (измените после первого входа!)

---

### Шаг 2: Настройте `.env`

```bash
# Скопируйте шаблон
cp .env.example .env
```

Заполните минимальные поля:
```env
# Telegram Bot (получите у @BotFather)
TOKEN=your_telegram_bot_token

# AI Keys
GEMINI_API_KEY=your_gemini_key
DEEPSEEK_API_KEY=your_deepseek_key

# Database
DB_PASSWORD=your_postgres_password

# Redis (если используете)
REDIS_PASSWORD=your_redis_password
```

---

### Шаг 3: Запуск

#### Вариант A: С Docker (рекомендуется)

```bash
# Запустите все сервисы
docker-compose up --build

# В новом терминале примените миграции
docker-compose exec db psql -U postgres -d propitashka -f /app/setup_database.sql
```

#### Вариант B: Локально

```bash
# 1. Активируйте виртуальное окружение
source bin/activate  # или venv/bin/activate

# 2. Установите зависимости (если еще не установлены)
pip install -r requirements.txt

# 3. Запустите Redis (в отдельном терминале)
redis-server

# 4. Запустите бота
python main.py
```

---

### Шаг 4: Тестирование

1. Откройте Telegram
2. Найдите вашего бота
3. Отправьте `/start`
4. Следуйте инструкциям онбординга

---

## 🔧 Первые шаги после запуска

### Проверьте подключение к БД

```bash
psql -U postgres -d propitashka -c "SELECT COUNT(*) FROM user_main;"
```

### Просмотрите логи

```bash
# Docker
docker-compose logs -f bot

# Локально
tail -f bot_output.log
```

### Запустите админ-панель (только macOS)

```bash
open "PROpitashka Admin.app"
```

Войдите с учетными данными: `admin/admin`

---

## 📊 Первая аналитика

Выполните простой запрос:

```bash
psql -U postgres -d propitashka -c "
SELECT 
    COUNT(DISTINCT user_id) AS total_users,
    COUNT(*) AS total_records
FROM user_main;
"
```

---

## ❓ Проблемы?

### Бот не отвечает

1. Проверьте токен в `.env`
2. Убедитесь, что PostgreSQL запущен
3. Проверьте логи: `python main.py` (локально) или `docker-compose logs bot`

### Ошибка подключения к БД

```bash
# Проверьте, что БД существует
psql -U postgres -l | grep propitashka

# Проверьте подключение
psql -U postgres -d propitashka -c "SELECT 1;"
```

### Redis не работает

```bash
# Проверьте, что Redis запущен
redis-cli ping
# Должно вернуть: PONG
```

---

## 📚 Дополнительная документация

- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Деплой на облако
- [ANALYTICS_GUIDE.md](ANALYTICS_GUIDE.md) - Работа с аналитикой
- [ADMIN_APP_README.md](ADMIN_APP_README.md) - Админ-панель

---

**Готово! Ваш бот запущен!** 🎉








