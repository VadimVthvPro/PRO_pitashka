# 🚀 Руководство по развертыванию PROpitashka

## Обзор

Это руководство поможет вам развернуть PROpitashka бота на продакшн-среде с использованием облачных сервисов.

---

## 📋 Что будем развертывать

1. **PostgreSQL** (база данных) - на управляемом сервисе
2. **Redis** (кэш) - на управляемом сервисе или в Docker
3. **Telegram Bot** (Python приложение) - на облачной платформе
4. **Privacy Policy** (статическая страница) - на домене

---

## 🎯 Рекомендуемый стек

### Вариант 1: Бюджетный (бесплатный уровень)
- **База данных**: Supabase (500 MB бесплатно) или Neon (512 MB бесплатно)
- **Redis**: Upstash (10,000 команд/день бесплатно)
- **Бот**: Fly.io (бесплатный уровень) или Render (бесплатный уровень)
- **Домен**: Freenom (бесплатные домены .tk, .ml) или ваш собственный

### Вариант 2: Продакшн (платный)
- **База данных**: DigitalOcean Managed PostgreSQL ($15/мес) или AWS RDS
- **Redis**: DigitalOcean Managed Redis ($15/мес) или AWS ElastiCache
- **Бот**: DigitalOcean App Platform ($5/мес) или AWS ECS
- **Домен**: Namecheap, GoDaddy (~$10/год)

---

## 📝 Пошаговая инструкция

### Шаг 1: Подготовка базы данных (PostgreSQL)

#### Вариант A: Supabase (рекомендуется для старта)

1. Зарегистрируйтесь на [Supabase](https://supabase.com)
2. Создайте новый проект
3. Получите строку подключения:
   - Перейдите в Settings → Database
   - Скопируйте Connection String (URI mode)
4. Обновите `.env`:
   ```env
   DB_HOST=db.xxx.supabase.co
   DB_PORT=5432
   DB_NAME=postgres
   DB_USER=postgres
   DB_PASSWORD=your_password_from_supabase
   DB_SSLMODE=require
   DB_SSL_ENABLED=true
   ```

5. Примените миграции:
   ```bash
   # Подключитесь к базе
   psql "postgresql://postgres:password@db.xxx.supabase.co:5432/postgres"
   
   # Выполните инициализацию
   \i database_init.sql
   
   # Выполните миграции
   \i migrations/002_add_admin_users.sql
   \i migrations/003_add_privacy_consent.sql
   \i migrations/004_add_utm_and_referrals.sql
   ```

#### Вариант B: Neon

1. Зарегистрируйтесь на [Neon](https://neon.tech)
2. Создайте проект и скопируйте строку подключения
3. Следуйте шагам 4-5 из варианта A

---

### Шаг 2: Подготовка Redis (кэш)

#### Вариант A: Upstash (рекомендуется для старта)

1. Зарегистрируйтесь на [Upstash](https://upstash.com)
2. Создайте Redis базу (выберите регион ближе к вашим пользователям)
3. Скопируйте Redis URL
4. Обновите `.env`:
   ```env
   REDIS_HOST=your-redis.upstash.io
   REDIS_PORT=6379
   REDIS_PASSWORD=your_redis_password
   ```

#### Вариант B: Redis в Docker (если деплоите на VPS)

Если вы используете собственный сервер, Redis уже включен в `docker-compose.yml`.

---

### Шаг 3: Развертывание бота

#### Вариант A: Fly.io (рекомендуется)

1. **Установите Fly CLI**:
   ```bash
   curl -L https://fly.io/install.sh | sh
   ```

2. **Войдите в аккаунт**:
   ```bash
   fly auth login
   ```

3. **Создайте конфигурацию `fly.toml`** (в корне проекта):
   ```toml
   app = "propitashka-bot"

   [env]
     ENVIRONMENT = "production"
     LOG_LEVEL = "INFO"

   [[services]]
     internal_port = 8080
     protocol = "tcp"

     [[services.ports]]
       handlers = ["http"]
       port = 80

     [[services.ports]]
       handlers = ["tls", "http"]
       port = 443
   ```

4. **Установите секреты**:
   ```bash
   fly secrets set TOKEN="your_telegram_token"
   fly secrets set GEMINI_API_KEY="your_gemini_key"
   fly secrets set DEEPSEEK_API_KEY="your_deepseek_key"
   fly secrets set DB_PASSWORD="your_db_password"
   fly secrets set REDIS_PASSWORD="your_redis_password"
   # ... все остальные переменные из .env
   ```

5. **Разверните приложение**:
   ```bash
   fly deploy
   ```

6. **Проверьте логи**:
   ```bash
   fly logs
   ```

#### Вариант B: Render

1. Зарегистрируйтесь на [Render](https://render.com)
2. Создайте новый Web Service
3. Подключите ваш GitHub репозиторий
4. Настройте:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py`
5. Добавьте Environment Variables (все из `.env`)
6. Нажмите Create Web Service

#### Вариант C: DigitalOcean App Platform

1. Зарегистрируйтесь на [DigitalOcean](https://digitalocean.com)
2. Перейдите в Apps → Create App
3. Подключите GitHub репозиторий
4. Настройте:
   - **Type**: Worker (не Web Service, так как бот не принимает HTTP)
   - **Build Command**: `pip install -r requirements.txt`
   - **Run Command**: `python main.py`
5. Добавьте Environment Variables
6. Нажмите Create App

---

### Шаг 4: Настройка домена для Privacy Policy

#### 4.1. Покупка/регистрация домена

**Бесплатные опции**:
- Freenom (.tk, .ml, .ga домены)
- GitHub Pages (yourusername.github.io)

**Платные (рекомендуется)**:
- Namecheap (~$10/год)
- GoDaddy
- Google Domains

#### 4.2. Хостинг HTML-страницы

**Вариант A: GitHub Pages (бесплатно)**

1. Создайте репозиторий `propitashka-privacy`
2. Добавьте файл `docs/privacy_policy.html`
3. Включите GitHub Pages в настройках репозитория
4. Ваша страница будет доступна по адресу: `https://yourusername.github.io/propitashka-privacy/privacy_policy.html`

**Вариант B: Netlify/Vercel (бесплатно + собственный домен)**

1. Зарегистрируйтесь на [Netlify](https://netlify.com) или [Vercel](https://vercel.com)
2. Создайте новый сайт, загрузите папку `docs/`
3. Подключите свой домен в настройках
4. Настройте DNS записи:
   ```
   Type: CNAME
   Name: www
   Value: your-site.netlify.app
   ```

#### 4.3. Обновите ссылку в боте

После развертывания обновите URL в коде:

```python
# main.py, строка ~237
await message.answer(
    "Добро пожаловать! Прежде чем мы начнем, пожалуйста, ознакомьтесь с нашей "
    "<a href='https://yourdomain.com/privacy'>политикой конфиденциальности</a> "
    # ...
)
```

---

## 🔒 Безопасность (обязательно!)

### 1. Никогда не коммитьте `.env` файл

Убедитесь, что `.env` в `.gitignore`:
```bash
echo ".env" >> .gitignore
```

### 2. Используйте SSL для базы данных

В `.env`:
```env
DB_SSLMODE=require
DB_SSL_ENABLED=true
```

### 3. Ограничьте права пользователя БД

Выполните SQL из файла `database_users_setup.sql`.

### 4. Установите сложные пароли

Используйте генератор паролей для:
- `DB_PASSWORD`
- `ADMIN_DB_PASSWORD`
- `ADMIN_SECRET_KEY`
- `REDIS_PASSWORD`

---

## 📊 Мониторинг

### Логи

**Fly.io**:
```bash
fly logs
```

**Render**:
- Dashboard → Logs

**DigitalOcean**:
- App → Runtime Logs

### Метрики

Используйте SQL-запросы из `analytics_dashboard.sql` для мониторинга:
- DAU/MAU
- Активация пользователей
- Retention
- UTM-источники

Рекомендуется настроить автоматическую отправку отчетов себе в Telegram (см. `ANALYTICS_GUIDE.md`).

---

## 🐛 Отладка проблем

### Проблема: Бот не отвечает

1. Проверьте логи:
   ```bash
   fly logs  # или через дашборд платформы
   ```

2. Проверьте переменные окружения:
   ```bash
   fly secrets list
   ```

3. Убедитесь, что бот запущен:
   ```bash
   fly status
   ```

### Проблема: Ошибки подключения к БД

1. Проверьте, что PostgreSQL доступен:
   ```bash
   psql "your_connection_string"
   ```

2. Проверьте SSL настройки в `.env`

3. Проверьте whitelist IP на стороне хостинга БД

### Проблема: Redis не работает

1. Проверьте подключение:
   ```bash
   redis-cli -h your-host -p 6379 -a your_password ping
   ```

2. Проверьте лимиты на Upstash dashboard

---

## ✅ Чеклист перед запуском

- [ ] PostgreSQL база создана и миграции применены
- [ ] Redis настроен и доступен
- [ ] Все переменные окружения установлены
- [ ] SSL включен для базы данных
- [ ] Бот успешно задеплоен и запущен
- [ ] Privacy policy доступна по HTTPS
- [ ] Ссылка на privacy policy обновлена в коде
- [ ] Логи проверены на ошибки
- [ ] Тестовое сообщение боту отправлено и получен ответ
- [ ] Админ-панель работает (если используете)

---

## 📞 Поддержка

Если у вас возникли проблемы:
1. Проверьте логи приложения
2. Проверьте документацию вашей платформы
3. Создайте issue в GitHub репозитории

---

**Готово! Ваш бот готов к работе в продакшне!** 🎉





