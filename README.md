# 🥗 PROpitashka - AI-Powered Nutrition & Fitness Telegram Bot

<div align="center">

![Version](https://img.shields.io/badge/version-2.0--production-green)
![Python](https://img.shields.io/badge/python-3.12-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-production--ready-brightgreen)

**Умный Telegram-бот для отслеживания питания, тренировок и здоровья с поддержкой AI**

</div>

---

## 📋 О проекте

PROpitashka - это production-ready Telegram-бот, который помогает пользователям:
- 📸 **Распознавать еду по фото** с помощью AI (DeepSeek, Gemini)
- 📊 **Отслеживать калории** и БЖУ с fallback-базой продуктов
- 💪 **Вести дневник тренировок** с расчетом сожженных калорий
- 💧 **Контролировать потребление воды**
- ⚖️ **Рассчитывать ИМТ** и отслеживать прогресс по весу
- 🎯 **Достигать целей** по питанию
- 🌍 **Работать на 5 языках** (RU, EN, DE, FR, ES)

## ✨ Ключевые возможности

### 🔒 Безопасность
- ✅ Все секреты в `.env` файлах
- ✅ SSL/TLS для базы данных
- ✅ Раздельная аутентификация для админки и бота
- ✅ Согласие на обработку персональных данных
- ✅ Ограниченные права доступа к БД

### 💪 Надежность
- ✅ Автоматические retry при сбоях API
- ✅ Настраиваемые таймауты
- ✅ Redis кэширование для AI-ответов
- ✅ Fallback база из 50+ продуктов
- ✅ Middleware для проверки согласия пользователя

### 📊 Аналитика
- ✅ UTM-метки и реферальные коды
- ✅ 11 готовых SQL-запросов для метрик
- ✅ DAU, MAU, Retention, Cohort Analysis
- ✅ Отслеживание источников трафика

### 🌍 Локализация
- ✅ 5 языков с дружелюбным тоном
- ✅ Онбординг с объяснением возможностей
- ✅ Gettext (.po/.mo) для переводов

### 🐳 Деплой
- ✅ Docker + Docker Compose
- ✅ Готов для Fly.io, Render, DigitalOcean
- ✅ Полная документация по развертыванию

## 🚀 Быстрый старт с Docker

### 1. Клонируйте репозиторий
```bash
git clone https://github.com/yourusername/PROpitashka.git
cd PROpitashka
```

### 2. Настройте `.env`
```bash
cp .env.example .env
# Отредактируйте .env и добавьте ваши API-ключи
```

**Важные переменные для Docker:**
```env
DB_HOST=db
REDIS_HOST=redis
```

### 3. Запустите всё одной командой
```bash
docker-compose up --build
```

Это запустит:
- 🤖 Telegram бота
- 🗄️ PostgreSQL базу данных
- ⚡ Redis для кэширования

### 4. Примените миграции БД
```bash
docker-compose exec db psql -U postgres -d propitashka -f /app/setup_database.sql
```

### 5. Готово! 🎉
Отправьте `/start` вашему боту в Telegram.

---

## 🛠️ Локальная установка (без Docker)

### Требования
- Python 3.12+
- PostgreSQL 14+
- Redis 7+

### Установка

1. **Установите зависимости:**
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

2. **Настройте PostgreSQL:**
```bash
# Создайте базу данных
createdb propitashka

# Примените схему
psql -U postgres -d propitashka -f setup_database.sql
```

3. **Настройте `.env`:**
```bash
cp .env.example .env
# Отредактируйте .env
```

4. **Запустите Redis:**
```bash
redis-server
```

5. **Запустите бота:**
```bash
python main.py
```

---

## 📁 Структура проекта

```
PROpitashka/
├── main.py                      # Главный файл бота
├── config.py                    # Централизованная конфигурация
├── keyboards.py                 # Клавиатуры Telegram
├── main_mo.py                   # Модуль локализации
├── food_database_fallback.py    # База продуктов (fallback)
├── admin_of_bases.py            # Админ-панель (Tkinter)
│
├── setup_database.sql           # Полная инициализация БД
├── analytics_dashboard.sql      # SQL-запросы для аналитики
│
├── locales/                     # Переводы (gettext)
│   ├── ru/LC_MESSAGES/
│   ├── en/LC_MESSAGES/
│   ├── de/LC_MESSAGES/
│   ├── fr/LC_MESSAGES/
│   └── es/LC_MESSAGES/
│
├── docs/
│   └── privacy_policy.html      # Политика конфиденциальности
│
├── Dockerfile                   # Docker-образ
├── docker-compose.yml           # Оркестрация сервисов
├── requirements.txt             # Python зависимости
├── .gitignore                   # Git игнорирование
│
└── Документация/
    ├── DEPLOYMENT_GUIDE.md      # Руководство по деплою
    ├── ANALYTICS_GUIDE.md       # Руководство по аналитике
    ├── LOCALIZATION_CHECKLIST.md # Чеклист локализации
    └── ADMIN_APP_README.md      # Руководство по админке
```

---

## 🎯 Основные функции

### Для пользователей

- **📸 Распознавание еды по фото** - AI определяет КБЖУ
- **📝 Ввод текстом** - укажите продукты и граммы
- **💪 Дневник тренировок** - 3 уровня интенсивности
- **💧 Учет воды** - отслеживание потребления
- **📊 Сводки** - день/месяц/год
- **🎯 Персональные цели** - похудение/набор/поддержание
- **🤖 AI-планировщик** - недельные планы питания и тренировок
- **🍳 Помощь с рецептами** - идеи для завтрака/обеда/ужина

### Для администраторов

- **🖥️ Desktop-приложение** (macOS) - управление данными
- **📊 Аналитика** - 11 готовых SQL-запросов
- **👥 Управление пользователями**
- **📈 Отслеживание метрик** (DAU, Retention, UTM-источники)

---

## 📊 Аналитика

Используйте готовые SQL-запросы из `analytics_dashboard.sql`:

```bash
psql -U postgres -d propitashka -f analytics_dashboard.sql
```

**Доступные метрики:**
1. DAU/MAU (Daily/Monthly Active Users)
2. Новые регистрации
3. Activation Rate
4. 1-Day & 7-Day Retention
5. Среднее количество действий
6. Анализ UTM-источников
7. Топ реферальных кодов
8. Когортный анализ
9. Engagement по типам активности

Подробнее: [ANALYTICS_GUIDE.md](ANALYTICS_GUIDE.md)

---

## 🌍 Локализация

Бот поддерживает 5 языков с использованием gettext:

```bash
# Редактирование переводов
poedit locales/en/LC_MESSAGES/messages.po

# Компиляция
msgfmt locales/en/LC_MESSAGES/messages.po -o locales/en/LC_MESSAGES/messages.mo
```

Подробный чеклист: [LOCALIZATION_CHECKLIST.md](LOCALIZATION_CHECKLIST.md)

---

## 🚀 Деплой

### Рекомендуемые платформы

**Бесплатный уровень:**
- База: Supabase (500 MB) или Neon (512 MB)
- Redis: Upstash (10K команд/день)
- Бот: Fly.io или Render

**Продакшн:**
- База: DigitalOcean Managed PostgreSQL
- Redis: DigitalOcean Managed Redis
- Бот: DigitalOcean App Platform или AWS ECS

Полное руководство: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)

---

## 🔧 Технологии

- **Backend**: Python 3.12, aiogram 3.x
- **AI**: DeepSeek, Google Gemini, GigaChat
- **Database**: PostgreSQL 14+
- **Cache**: Redis 7+
- **Admin UI**: Tkinter
- **Localization**: gettext
- **Deployment**: Docker, Docker Compose

---

## 📝 Конфигурация

Все настройки в `.env`:

```env
# Telegram
TOKEN=your_bot_token

# AI
GEMINI_API_KEY=your_key
DEEPSEEK_API_KEY=your_key

# Database
DB_NAME=propitashka
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost  # или 'db' для Docker

# Redis
REDIS_HOST=localhost  # или 'redis' для Docker
REDIS_PASSWORD=your_password

# Security
DB_SSL_ENABLED=true
DB_SSLMODE=require
```

Полный список переменных см. в `.env.example`

---

## 🤝 Вклад в проект

Мы приветствуем вклад в развитие проекта!

1. Fork репозитория
2. Создайте feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit изменения (`git commit -m 'Add some AmazingFeature'`)
4. Push в branch (`git push origin feature/AmazingFeature`)
5. Откройте Pull Request

---

## 📝 Лицензия

Этот проект лицензирован под MIT License.

---

## 👥 Авторы

- **PROpitashka Team**

---

## 📞 Поддержка

- 🐛 **Bug reports**: [GitHub Issues](https://github.com/yourusername/PROpitashka/issues)
- 📧 **Email**: support@propitashka.com
- 💬 **Telegram**: [@PROpitashka_support](https://t.me/PROpitashka_support)

---

## 🙏 Благодарности

- Google Gemini & DeepSeek за AI
- aiogram за отличный фреймворк
- Всем контрибьюторам проекта

---

<div align="center">

**Сделано с ❤️ командой PROpitashka**

⭐ **Поставьте звезду, если проект вам понравился!**

[![GitHub stars](https://img.shields.io/github/stars/yourusername/PROpitashka?style=social)](https://github.com/yourusername/PROpitashka)

</div>
