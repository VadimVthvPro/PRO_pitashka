# 🥗 PROpitashka - AI-Powered Nutrition & Fitness Telegram Bot

<div align="center">

![Version](https://img.shields.io/badge/version-2.0--dev-blue)
![Python](https://img.shields.io/badge/python-3.12-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-in%20development-yellow)

**Умный Telegram-бот для отслеживания питания, тренировок и здоровья с поддержкой AI**

[Возможности](#-возможности) • [Установка](#-установка) • [Конфигурация](#-конфигурация) • [Разработка](#-разработка) • [Roadmap](#-roadmap)

</div>

---

## 📋 О проекте

PROpitashka - это многофункциональный Telegram-бот, который помогает пользователям:
- 📸 Распознавать еду по фото с помощью AI (Google Gemini)
- 📊 Отслеживать калории, белки, жиры и углеводы
- 💪 Вести дневник тренировок
- 💧 Контролировать потребление воды
- ⚖️ Рассчитывать ИМТ и отслеживать вес
- 🎯 Устанавливать и достигать целей по питанию
- 🌍 Работать на 5 языках (RU, EN, DE, FR, ES)

## ✨ Возможности

### Для пользователей
- 🤖 **AI-распознавание еды** - загрузите фото, получите БЖУ и калории
- 📈 **Трекинг прогресса** - отслеживайте свои показатели
- 🏋️ **Дневник тренировок** - записывайте активность и сожженные калории
- 💬 **Многоязычность** - поддержка 5 языков
- 📱 **Удобный интерфейс** - интуитивные кнопки и команды
- 🎯 **Персонализация** - индивидуальные цели и рекомендации

### Для администраторов
- 🖥️ **Desktop-приложение** - удобное управление данными
- 📊 **Аналитика** - метрики использования и engagement
- 👥 **Управление пользователями** - просмотр и редактирование данных
- 🔍 **Поиск и фильтрация** - быстрый доступ к информации

## 🚀 Быстрый старт

### Требования
- Python 3.12+
- PostgreSQL 14+
- Telegram Bot Token (от @BotFather)
- Google Gemini API Key

### Установка

```bash
# Клонировать репозиторий
git clone https://github.com/yourusername/PROpitashka.git
cd PROpitashka

# Создать виртуальное окружение
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# Установить зависимости
pip install -r requirements.txt

# Настроить переменные окружения
cp .env.example .env
# Отредактируйте .env и добавьте свои ключи

# Инициализировать базу данных
psql -U postgres -f database_init.sql

# Запустить бота
cd PROpitashka
python main.py
```

## ⚙️ Конфигурация

Создайте файл `.env` на основе `.env.example`:

```env
# Telegram
TOKEN=your_bot_token

# AI Services
GEMINI_API_KEY=your_gemini_key

# Database
DB_NAME=propitashka
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
```

Полный список переменных см. в [.env.example](.env.example)

## 📊 Архитектура

```
PROpitashka/
├── PROpitashka/          # Основной код бота
│   ├── main.py           # Точка входа
│   ├── db_config.py      # Конфигурация БД
│   ├── logger_config.py  # Настройка логирования
│   └── keyboards.py      # Клавиатуры Telegram
├── admin_of_bases.py     # GUI админка (Tkinter)
├── database_init.sql     # SQL схема
├── locales/              # Переводы (gettext)
└── requirements.txt      # Зависимости Python
```

## 🛠 Технологии

- **Bot Framework**: aiogram 3.x
- **AI**: Google Gemini, GigaChat, Yandex GPT
- **Database**: PostgreSQL
- **Admin UI**: Tkinter
- **Localization**: gettext
- **Logging**: Python logging + PostgreSQL

## 📈 Roadmap

Текущая версия: **v1.0** (Production)  
В разработке: **v2.0** (Production Ready)

### v2.0 - Production Ready
- [x] Создан план разработки
- [ ] Безопасность: секреты в .env, SSL к БД
- [ ] Авторизация в админке
- [ ] Retry механизмы и кэширование
- [ ] Docker и деплой в облако
- [ ] Аналитика и метрики
- [ ] Улучшенная валидация данных
- [ ] Проверенные переводы и онбординг

Полный roadmap: [DEVELOPMENT_ROADMAP.md](DEVELOPMENT_ROADMAP.md)

## 🤝 Вклад в проект

Мы приветствуем вклад в развитие проекта! 

1. Fork репозитория
2. Создайте feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit изменения (`git commit -m 'Add some AmazingFeature'`)
4. Push в branch (`git push origin feature/AmazingFeature`)
5. Откройте Pull Request

## 📝 Лицензия

Этот проект лицензирован под MIT License - см. файл [LICENSE](LICENSE)

## 👥 Авторы

- **PROpitashka Team** - *Initial work*

## 📞 Контакты

- Telegram: [@PROpitashka_bot](https://t.me/PROpitashka_bot)
- Issues: [GitHub Issues](https://github.com/yourusername/PROpitashka/issues)

## 🙏 Благодарности

- Google Gemini за AI-распознавание
- aiogram за отличный фреймворк
- Всем контрибьюторам проекта

---

<div align="center">

**Сделано с ❤️ командой PROpitashka**

⭐ Поставьте звезду, если проект вам понравился!

</div>

