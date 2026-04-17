# PROpitashka — Полный технический анализ проекта

> Документ подготовлен для миграции Telegram-бота на веб-приложение.  
> Дата анализа: 15.04.2026

---

## Содержание

1. [Общее описание проекта](#1-общее-описание-проекта)
2. [Структура файлов](#2-структура-файлов)
3. [Зависимости](#3-зависимости)
4. [Конфигурация и переменные окружения](#4-конфигурация-и-переменные-окружения)
5. [Схема базы данных (PostgreSQL)](#5-схема-базы-данных-postgresql)
6. [Все SQL-запросы и обращения к БД](#6-все-sql-запросы-и-обращения-к-бд)
7. [Функциональные модули бота](#7-функциональные-модули-бота)
8. [Система локализации (i18n)](#8-система-локализации-i18n)
9. [AI-интеграция (Google Gemini)](#9-ai-интеграция-google-gemini)
10. [Кэширование (Redis)](#10-кэширование-redis)
11. [Админ-панель](#11-админ-панель)
12. [Статические ресурсы](#12-статические-ресурсы)
13. [FSM (конечный автомат состояний)](#13-fsm-конечный-автомат-состояний)
14. [Замечания и рекомендации по улучшению](#14-замечания-и-рекомендации-по-улучшению)

---

## 1. Общее описание проекта

**PROpitashka** — Telegram-бот, персональный помощник по питанию и фитнесу. Он позволяет:

- Регистрировать пользователя (рост, вес, дата рождения, пол, цель)
- Вести дневник питания (ввод еды текстом или распознавание по фото через AI)
- Записывать тренировки (20 типов с расчётом сожжённых калорий по параметрам пользователя)
- Получать сводку за день / месяц / год (КБЖУ, тренировки, вода)
- Генерировать AI-планы питания и тренировок на неделю
- Помогать с рецептами и упражнениями через AI
- Трекать выпитую воду (стаканы по 300 мл)
- Свободно общаться с AI-ассистентом (catch-all чат)
- Поддерживать 5 языков: RU, EN, DE, FR, ES

**Стек:** Python 3.12, aiogram 3.13, PostgreSQL, Redis, Google Gemini API

---

## 2. Структура файлов

```
PROpitashka/
├── main.py                          # Основной файл бота (2901 строка) — ВСЯ логика
├── config.py                        # Централизованная конфигурация (из .env)
├── keyboards.py                     # Reply-клавиатуры бота (зависят от языка)
├── main_mo.py                       # Локализация: printer(), printer_with_given()
├── food_database_fallback.py        # Fallback-база КБЖУ ~40 продуктов
├── logger_setup.py                  # Настройка логирования (файл + консоль)
├── requirements.txt                 # Зависимости Python
├── .env / .env.example              # Переменные окружения
├── .gitignore
│
├── app/
│   ├── domain/
│   │   ├── workouts/
│   │   │   └── workout_service.py   # Бизнес-логика тренировок v2.0
│   │   └── calendar/
│   │       └── calendar_service.py  # Валидация дат, расчёт возраста
│   ├── presentation/
│   │   ├── bot/
│   │   │   ├── routers/
│   │   │   │   └── workout_handlers.py  # Обработчики тренировок (aiogram Router)
│   │   │   └── keyboards/
│   │   │       └── workout_keyboards.py # Inline-клавиатуры тренировок с пагинацией
│   │   └── utils/
│   │       └── calendar_utils.py    # Inline-календарь для выбора даты рождения
│
├── migrations/
│   ├── 001_create_training_system.sql     # Таблицы training_types, training_coefficients
│   ├── 002_add_training_summary_functions.sql  # Функции сводки тренировок
│   └── 003_create_admin_users.sql         # Таблица admin_users
│
├── locales/
│   ├── ru/LC_MESSAGES/messages.po   # Русский (основной, ~590 строк)
│   ├── en/LC_MESSAGES/messages.po   # English
│   ├── de/LC_MESSAGES/messages.po   # Deutsch
│   ├── fr/LC_MESSAGES/messages.po   # Française
│   └── es/LC_MESSAGES/messages.po   # Spanish
│
├── admin_of_bases.py                # Desktop-админка (tkinter, ~990 строк)
├── create_admin.py                  # Скрипт создания админ-пользователя
├── start_bot.sh                     # Скрипт запуска бота
├── restart_bot.sh                   # Скрипт перезапуска бота
├── start_admin.sh / start_admin_v2.sh  # Скрипты запуска админки
│
├── privacy_policy_ru.txt            # Политика конфиденциальности (5 языков)
├── privacy_policy_en.txt
├── privacy_policy_de.txt
├── privacy_policy_fr.txt
├── privacy_policy_es.txt
├── PRIVACY_POLICY.txt               # Полная политика (мультиязычная)
│
├── new_logo.jpg                     # Логотип бота (отправляется при регистрации)
├── new_logo.png                     # Логотип (PNG-версия)
├── admin_icon.icns                  # Иконка для macOS-админки
├── PROpitashka Admin.app/           # macOS bundle для админки
│
├── docs/
│   └── privacy_policy.html          # HTML-версия политики
│
├── bot.log                          # Файл логов бота
└── *.md                             # Документация (README, QUICKSTART и т.д.)
```

---

## 3. Зависимости

| Пакет | Версия | Назначение |
|-------|--------|-----------|
| aiogram | 3.13.0 | Telegram Bot Framework (async) |
| psycopg2-binary | 2.9.9 | Драйвер PostgreSQL |
| google-generativeai | 0.8.5 | Google Gemini AI (текст + фото) |
| aiohttp | 3.9.3 | Async HTTP-клиент (используется aiogram) |
| requests | 2.31.0 | Sync HTTP-клиент (вспомогательный) |
| translate | 3.6.1 | Перевод текстов (для рецептов/тренировок) |
| python-dotenv | 1.0.1 | Загрузка .env файлов |
| redis | 5.0.1 | Redis для кэширования AI-ответов |
| python-dateutil | 2.8.2 | Утилиты работы с датами |
| bcrypt | — | Хэширование паролей админов (в admin_of_bases.py) |
| gettext | stdlib | Локализация (i18n) |

---

## 4. Конфигурация и переменные окружения

Класс `Config` в `config.py` загружает все настройки из `.env`:

| Переменная | Описание | Значение по умолчанию |
|------------|----------|----------------------|
| `TOKEN` | Telegram Bot Token | — (обязательно) |
| `GEMINI_API_KEY` | Google Gemini API ключ | — |
| `DB_NAME` | Имя БД PostgreSQL | `propitashka` |
| `DB_USER` | Пользователь БД | `postgres` |
| `DB_PASSWORD` | Пароль БД | — (обязательно) |
| `DB_HOST` | Хост БД | `localhost` |
| `DB_PORT` | Порт БД | `5432` |
| `DB_SSLMODE` | SSL-режим | `prefer` |
| `DB_SSL_ENABLED` | SSL вкл/выкл | `false` |
| `REDIS_HOST` | Хост Redis | `localhost` |
| `REDIS_PORT` | Порт Redis | `6379` |
| `REDIS_PASSWORD` | Пароль Redis | — |
| `REDIS_DB` | Номер БД Redis | `0` |
| `ADMIN_DB_USER` | Админ-пользователь БД | `admin_user` |
| `ADMIN_DB_PASSWORD` | Пароль админа БД | — |
| `ADMIN_SECRET_KEY` | Секретный ключ | — |
| `ENVIRONMENT` | Окружение | `development` |
| `LOG_LEVEL` | Уровень логирования | `INFO` |
| `CACHE_ENABLED` | Кэш вкл/выкл | `true` |
| `ANALYTICS_ENABLED` | Аналитика вкл/выкл | `false` |
| `REFERRAL_ENABLED` | Рефералы вкл/выкл | `false` |
| `API_TIMEOUT` | Таймаут API | `30` сек |
| `API_RETRY_ATTEMPTS` | Кол-во повторов | `3` |
| `API_RETRY_DELAY` | Задержка повтора | `1.0` сек |
| `CACHE_TTL_FOOD_RECOGNITION` | TTL кэша распознавания еды | `604800` (7 дней) |
| `CACHE_TTL_RECIPES` | TTL кэша рецептов | `86400` (1 день) |
| `CACHE_TTL_AI_RESPONSES` | TTL кэша AI-ответов | `3600` (1 час) |

---

## 5. Схема базы данных (PostgreSQL)

### 5.1. Таблица `user_main` — основная информация пользователя

| Колонка | Тип | Описание |
|---------|-----|----------|
| `user_id` | BIGINT PK | Telegram user ID |
| `user_name` | VARCHAR | Имя пользователя (first_name из Telegram) |
| `user_sex` | VARCHAR | Пол (текст на языке пользователя, например «Мужчина» / «Man») |
| `date_of_birth` | VARCHAR | Дата рождения (формат `ДД-ММ-ГГГГ`) |
| `privacy_consent_given` | BOOLEAN | Согласие на политику конфиденциальности |
| `privacy_consent_at` | TIMESTAMP | Время согласия |
| `utm_source` | VARCHAR | UTM-метка источника |
| `utm_medium` | VARCHAR | UTM-метка канала |
| `utm_campaign` | VARCHAR | UTM-метка кампании |
| `ref_code` | VARCHAR | Реферальный код |

### 5.2. Таблица `user_lang` — языковые настройки

| Колонка | Тип | Описание |
|---------|-----|----------|
| `user_id` | BIGINT PK | Telegram user ID |
| `lang` | VARCHAR | Код языка: `ru`, `en`, `de`, `fr`, `es` |

### 5.3. Таблица `user_health` — данные о здоровье (ежедневные)

| Колонка | Тип | Описание |
|---------|-----|----------|
| `user_id` | BIGINT | Telegram user ID |
| `date` | DATE | Дата записи |
| `imt` | DECIMAL | Индекс массы тела |
| `imt_str` | VARCHAR | ИМТ текстом (например «Норма») |
| `cal` | DECIMAL | Дневная норма калорий (формула Миффлина-Сан-Жеора) |
| `weight` | DECIMAL | Текущий вес (кг) |
| `height` | DECIMAL | Рост (см) |

### 5.4. Таблица `user_aims` — цели пользователя

| Колонка | Тип | Описание |
|---------|-----|----------|
| `user_id` | BIGINT PK | Telegram user ID |
| `user_aim` | VARCHAR | Цель (текст на языке пользователя: «Сброс веса» / «Набор веса» / «Удержание массы») |
| `daily_cal` | DECIMAL | Расчётная дневная норма калорий |

### 5.5. Таблица `food` — дневник питания

| Колонка | Тип | Описание |
|---------|-----|----------|
| `user_id` | BIGINT | Telegram user ID |
| `date` | DATE | Дата записи |
| `name_of_food` | VARCHAR | Название блюда/продукта |
| `b` | DECIMAL | Белки (граммы на фактический вес) |
| `g` | DECIMAL | Жиры (граммы на фактический вес) |
| `u` | DECIMAL | Углеводы (граммы на фактический вес) |
| `cal` | DECIMAL | Калорийность (ккал на фактический вес) |

### 5.6. Таблица `water` — трекер воды

| Колонка | Тип | Описание |
|---------|-----|----------|
| `user_id` | BIGINT | Telegram user ID |
| `data` | DATE | Дата (колонка называется `data`, не `date`) |
| `count` | INTEGER | Кол-во стаканов (1 стакан = 300 мл) |

**UNIQUE constraint:** `(user_id, data)` — при повторном нажатии `count += 1` через `ON CONFLICT DO UPDATE`.

### 5.7. Таблица `user_training` — записи тренировок

| Колонка | Тип | Описание |
|---------|-----|----------|
| `id` | SERIAL PK | Авто-ID |
| `user_id` | BIGINT | Telegram user ID |
| `date` | DATE | Дата тренировки |
| `training_cal` | DECIMAL(10,3) | Сожжённые калории |
| `tren_time` | INTEGER | Длительность (минуты) |
| `training_type_id` | INTEGER FK | Ссылка на `training_types.id` (v2.0) |
| `training_name` | VARCHAR(255) | Название тренировки на языке пользователя |
| `updated_at` | TIMESTAMPTZ | Время обновления |

### 5.8. Таблица `training_types` — справочник тренировок (20 шт.)

| Колонка | Тип | Описание |
|---------|-----|----------|
| `id` | SERIAL PK | ID тренировки |
| `name_ru` | VARCHAR(255) | Название на русском |
| `name_en` | VARCHAR(255) | Название на английском |
| `name_de` | VARCHAR(255) | Название на немецком |
| `name_fr` | VARCHAR(255) | Название на французском |
| `name_es` | VARCHAR(255) | Название на испанском |
| `base_coefficient` | DECIMAL(5,2) | Базовый коэфф. расхода (ккал/кг/час) |
| `emoji` | VARCHAR(10) | Эмодзи тренировки |
| `description_ru` / `_en` / `_de` / `_fr` / `_es` | TEXT | Описания |
| `is_active` | BOOLEAN | Активна ли тренировка |
| `created_at` / `updated_at` | TIMESTAMPTZ | Время создания/обновления |

**20 тренировок:** Бег, Быстрый бег, Ходьба, Быстрая ходьба, Велосипед, Плавание, Тренажёрный зал, Кроссфит, Упражнения с весом тела, Аэробика, Зумба, Йога, Пилатес, Футбол, Баскетбол, Теннис, Танцы, Бокс, Единоборства, Растяжка.

### 5.9. Таблица `training_coefficients` — модификаторы расчёта калорий

Хранит коэффициенты для расчёта калорий в зависимости от:
- **Пол:** `gender_male_modifier`, `gender_female_modifier`
- **Возраст (5 групп):** 18-25, 26-35, 36-45, 46-55, 56+
- **Вес (6 групп):** <60, 60-70, 71-80, 81-90, 91-100, >100
- **Рост (3 группы):** <160, 160-175, >175

### 5.10. Таблица `chat_history` — история AI-чата

| Колонка | Тип | Описание |
|---------|-----|----------|
| `user_id` | BIGINT | Telegram user ID |
| `message_type` | VARCHAR | `'user'` или `'bot'` |
| `message_text` | TEXT | Текст сообщения |
| `created_at` | TIMESTAMPTZ | Время сообщения |

### 5.11. Таблица `admin_users` — администраторы

| Колонка | Тип | Описание |
|---------|-----|----------|
| `id` | SERIAL PK | ID |
| `username` | VARCHAR(100) UNIQUE | Логин |
| `password_hash` | VARCHAR(255) | Хэш пароля (bcrypt) |
| `created_at` | TIMESTAMPTZ | Время создания |
| `last_login_at` | TIMESTAMPTZ | Последний вход |

### 5.12. Хранимые функции PostgreSQL

| Функция | Назначение |
|---------|-----------|
| `calculate_training_calories(type_id, user_id, minutes)` | Расчёт калорий с учётом всех коэффициентов |
| `get_age_group_modifier(age, type_id)` | Возрастной модификатор |
| `get_weight_category_modifier(weight, type_id)` | Весовой модификатор |
| `get_height_category_modifier(height, type_id)` | Ростовой модификатор |
| `get_gender_modifier(gender, type_id)` | Гендерный модификатор |
| `get_training_summary_day(user_id, date)` | Список тренировок за день |
| `get_training_top5_month(user_id, year, month)` | Топ-5 тренировок за месяц |
| `get_training_top5_year(user_id, year)` | Топ-5 тренировок за год |
| `get_training_stats_period(user_id, start, end)` | Статистика за период |

### 5.13. Представление (VIEW)

| Представление | Назначение |
|---------------|-----------|
| `v_training_statistics` | Агрегированная статистика тренировок |

### 5.14. Связи между таблицами

```
user_main (user_id PK)
  ├── user_lang (user_id PK)
  ├── user_health (user_id + date)
  ├── user_aims (user_id PK)
  ├── food (user_id + date)
  ├── water (user_id + data)  ← колонка data вместо date
  ├── user_training (user_id + date)
  │     └── training_types (id) ← FK через training_type_id
  │           └── training_coefficients (training_type_id)
  ├── chat_history (user_id)
  └── (admin_users — отдельная таблица, не связана с user_main)
```

---

## 6. Все SQL-запросы и обращения к БД

### 6.1. Регистрация / Авторизация

| Место | Запрос | Описание |
|-------|--------|----------|
| `/start` | `SELECT privacy_consent_given, ref_code FROM user_main WHERE user_id = %s` | Проверка: пользователь уже есть? |
| `/start` | `INSERT INTO user_main (user_id, user_name, utm_source, ...) ON CONFLICT DO NOTHING` | Создание пользователя |
| `/start` | `UPDATE user_main SET utm_source=..., ref_code=... WHERE user_id = %s` | Обновление UTM/реферала |
| Выбор языка | `INSERT INTO user_lang (user_id, lang) ON CONFLICT DO UPDATE SET lang = ...` | Сохранение/обновление языка |
| Согласие privacy | `UPDATE user_main SET privacy_consent_given = TRUE, privacy_consent_at = NOW()` | Фиксация согласия |
| Вход | `SELECT imt, imt_str, cal, weight, height FROM user_health WHERE user_id = %s ORDER BY date DESC LIMIT 1` | Загрузка данных пользователя |
| Регистрация (вес) | `INSERT INTO user_health (user_id, imt, imt_str, cal, date, weight, height) VALUES (...)` | Сохранение параметров здоровья |
| Регистрация (вес) | `INSERT INTO user_main (...) ON CONFLICT DO UPDATE SET user_sex, date_of_birth` | Обновление пола и даты рождения |
| Регистрация (вес) | `INSERT INTO user_aims (user_id, user_aim, daily_cal) ON CONFLICT DO UPDATE` | Сохранение цели |

### 6.2. Питание

| Место | Запрос | Описание |
|-------|--------|----------|
| Ввод еды (текст/фото) | `INSERT INTO food (user_id, date, name_of_food, b, g, u, cal) VALUES (...)` | Добавление продукта |
| Фото еды | То же + AI-распознавание | JSON от Gemini → INSERT в food |

### 6.3. Тренировки

| Место | Запрос | Описание |
|-------|--------|----------|
| Выбор тренировки | `SELECT id, name_{lang}, emoji, description_{lang}, base_coefficient FROM training_types WHERE is_active = true` | Список тренировок |
| Расчёт калорий | `SELECT calculate_training_calories(%s, %s, %s)` | Вызов хранимой функции |
| Сохранение | `INSERT INTO user_training (user_id, training_type_id, training_name, date, tren_time, training_cal) VALUES (...)` | Сохранение тренировки |
| Итого за день | `SELECT COALESCE(SUM(training_cal), 0) FROM user_training WHERE date = CURRENT_DATE AND user_id = %s` | Суммарные калории за день |
| Старая система | `INSERT INTO user_training (user_id, date, training_cal, tren_time) VALUES (...)` | Старая запись тренировки (без type_id) |

### 6.4. Вода

| Место | Запрос | Описание |
|-------|--------|----------|
| Добавить стакан | `INSERT INTO water (user_id, data, count) VALUES (%s, CURRENT_DATE, 1) ON CONFLICT DO UPDATE SET count = water.count + 1 RETURNING count` | +1 стакан |

### 6.5. Сводка

| Период | Запросы |
|--------|---------|
| **День** | `SUM(training_cal)`, `SUM(cal)`, `SUM(b)`, `SUM(g)`, `SUM(u)` из food, `SUM(count)` из water, `name_of_food` из food, `training_name, tren_time, training_cal` из user_training |
| **Месяц** | Цикл по дням месяца: weight, SUM(b/g/u/cal) из food, SUM(count) из water, SUM(training_cal), SUM(tren_time) из user_training. Топ-5 тренировок за месяц |
| **Год** | Цикл по 12 месяцам: SUM(cal/b/g/u) из food, SUM(count) из water по дням, weight из user_health. Топ-5 тренировок за год. AVG(training_cal) из user_training |

### 6.6. AI-генерация

| Место | Запросы |
|-------|---------|
| Недельный план | `SELECT lang FROM user_lang`, `SELECT user_aim, daily_cal FROM user_aims`, `SELECT user_sex, date_of_birth FROM user_main`, `SELECT imt, weight, height FROM user_health` |
| Рецепт | `SELECT lang FROM user_lang` |
| Тренировка AI | `SELECT lang FROM user_lang`, `SELECT imt FROM user_health WHERE date = today` |

### 6.7. AI-чат

| Место | Запросы |
|-------|---------|
| Сохранение сообщения | `INSERT INTO chat_history (user_id, message_type, message_text)` |
| Получение контекста | `SELECT message_type, message_text, created_at FROM chat_history WHERE user_id = %s ORDER BY created_at DESC LIMIT %s` |
| Информация для AI | `SELECT user_sex, date_of_birth FROM user_main`, `SELECT imt, weight, height FROM user_health ORDER BY date DESC LIMIT 1`, `SELECT user_aim, daily_cal FROM user_aims` |

### 6.8. Прочее

| Место | Запрос | Описание |
|-------|--------|----------|
| Смена языка | `UPDATE user_lang SET lang='{lang}' WHERE user_id = {id}` | Обновление языка |
| Middleware (privacy) | `SELECT privacy_consent_given FROM user_main WHERE user_id = %s` | Проверка согласия |
| Catch-all (AI chat) | `SELECT user_id FROM user_main WHERE user_id = %s` | Проверка регистрации |
| keyboards.py | `SELECT lang FROM user_lang WHERE user_id = {id}` | Получение языка для клавиатуры |
| main_mo.py | `SELECT lang FROM user_lang WHERE user_id = %s` | Получение языка для перевода |

---

## 7. Функциональные модули бота

### 7.1. Регистрация (Registration Flow)

**Шаги:**
1. `/start` → выбор языка (5 языков)
2. Показ политики конфиденциальности → accept/decline
3. Меню: «Регистрация» / «Вход»
4. Регистрация: рост → дата рождения (inline-календарь) → пол → цель → вес
5. Расчёт ИМТ и дневной нормы калорий
6. Сохранение в `user_health`, `user_main`, `user_aims`
7. Показ главного меню

**Формула расчёта калорий (Миффлин-Сан-Жеора):**
- Мужчина: `(10 × вес) + (6.25 × рост) - (5 × возраст) + 5`
- Женщина: `(10 × вес) + (6.25 × рост) - (5 × возраст) - 161`

**Расчёт ИМТ:** `вес / (рост_в_метрах²)`

**Классификация ИМТ:** <15 (сильно меньше нормы), 14-18 (недостаточная масса), 18-25 (норма), 25-30 (предожирение), >30 (ожирение)

### 7.2. Главное меню (9 кнопок)

| Кнопка (RU) | Функция |
|-------------|---------|
| Добавить тренировки | Выбор из 20 типов, ввод длительности, расчёт калорий |
| Ввести еду за день | По фото (AI) или текстом (названия + граммы) |
| Сводка | За день / месяц / год |
| Помочь с рецептом | AI генерирует рецепт для завтрака/обеда/ужина |
| Помочь с тренировкой | AI генерирует план тренировки по типу + ИМТ |
| Смена языка | Выбор нового языка из 5 вариантов |
| Недельный план питания и тренировок | AI генерирует полный план на неделю |
| Добавить выпитый стаканчик воды | +1 стакан (300 мл) |
| Присоединиться к чату | Ссылка на Telegram-группу |

### 7.3. Ввод еды

**Способ 1 — по фото:**
1. Пользователь отправляет фото
2. Фото загружается в Gemini API
3. AI распознаёт блюда, возвращает JSON с КБЖУ
4. Данные сохраняются в таблицу `food`

**Способ 2 — текстом:**
1. Пользователь вводит названия блюд через запятую
2. Затем вводит граммовки через запятую
3. AI генерирует КБЖУ (JSON формат)
4. При ошибке AI → fallback-поиск в локальной базе `food_database_fallback.py`
5. Данные сохраняются в таблицу `food`

### 7.4. Тренировки (v2.0 — новая система)

1. Пользователь нажимает «Добавить тренировки»
2. Показывается inline-клавиатура с 20 тренировками (пагинация по 6 шт.)
3. Выбирает тренировку → вводит длительность (1-300 мин)
4. Если нет веса за сегодня → запрашивает вес
5. Вызывает PG-функцию `calculate_training_calories()` с учётом всех модификаторов
6. Сохраняет в `user_training`
7. Показывает итог дня

### 7.5. Сводка (Day / Month / Year)

**День:** Калории тренировок, список блюд, КБЖУ, вода (мл)  
**Месяц:** Изменение веса, средние значения тренировок/КБЖУ/воды, топ-5 тренировок  
**Год:** 12 месяцев данных, изменение веса, средние значения, топ-5 тренировок  

### 7.6. AI-генерация планов

**Недельный план питания:** Отправляет в Gemini промпт с полом, ростом, возрастом, ИМТ, целью.  
**Недельный план тренировок:** Отправляет промпт + план питания для согласованности.  
**Рецепт:** Пользователь выбирает приём пищи (завтрак/обед/ужин), AI генерирует рецепт.  
**Тренировка AI:** Пользователь выбирает тип (силовая/растяжка/кардио), AI генерирует план с учётом ИМТ.

### 7.7. AI-чат (Catch-All)

Любое текстовое сообщение, не пойманное другими обработчиками, отправляется в AI-чат:
- Собираются данные пользователя (возраст, пол, ИМТ, цель)
- Загружается контекст последних 10 сообщений из `chat_history`
- Формируется системный промпт
- Ответ сохраняется в `chat_history`
- Контекстный разговор

### 7.8. Трекер воды

Нажатие кнопки → `INSERT INTO water ... ON CONFLICT DO UPDATE SET count = count + 1`.  
1 нажатие = 1 стакан = 300 мл.

---

## 8. Система локализации (i18n)

**Движок:** Python `gettext` с `.po`-файлами.

**5 языков:** ru, en, de, fr, es

**Как работает:**
1. `main_mo.py` → `printer(user_id, key)` — получает язык из БД, возвращает перевод
2. `keyboards.py` → `keyboard(user_id, key)` — строит клавиатуру на языке пользователя
3. Некоторые тексты захардкожены в `main.py` (словари для каждого языка)

**Файл `messages.po`** содержит ~90 msgid/msgstr пар, включая:
- Тексты интерфейса (кнопки, сообщения)
- AI-промпты (питание, тренировки, рецепты, чат)
- Сообщения об ошибках
- Мотивационные сообщения

**Ключевые ключи локализации:**
- `start`, `info`, `SuccesfulReg`, `height`, `age`, `sex`, `aim`, `weight`
- `kbmain1`..`kbmain9` — кнопки главного меню
- `svoDAY`, `svoMONTH`, `svoYEAR` — шаблоны сводок
- `pitforweek`, `trenforweek`, `mealai`, `trenai` — AI-промпты
- `ai_chat_system` — системный промпт AI-чата
- `food_recognition_prompt` — промпт распознавания фото еды

---

## 9. AI-интеграция (Google Gemini)

**Модель:** `gemini-2.5-flash`

**Использование:**

| Функция | API | Назначение |
|---------|-----|-----------|
| `generate()` | `genai.GenerativeModel.generate_content()` | Текстовая генерация (планы, рецепты, чат) |
| Фото-распознавание | `genai.upload_file()` + `generate_content([prompt, file])` | Анализ фото еды |

**Кэширование AI-ответов:**
- Redis с настраиваемым TTL
- Ключи: `plan:pit:{user_id}:...`, `plan:tren:{user_id}:...`, `recipe:...`, `training:...`, `ai_chat:...`

**Retry-логика:** Декоратор `@async_retry(max_attempts, delay, exceptions)` для всех AI-вызовов.

---

## 10. Кэширование (Redis)

**Опциональный** — бот работает и без Redis.

- `get_from_cache(key)` — получение из кэша
- `set_to_cache(key, value, ttl)` — запись в кэш с TTL
- TTL: AI-ответы 1 час, рецепты 1 день, распознавание еды 7 дней

---

## 11. Админ-панель

**Файл:** `admin_of_bases.py` (~990 строк, tkinter)

**Функционал:**
- Авторизация (bcrypt)
- Просмотр всех таблиц БД
- Добавление / редактирование / удаление записей
- Экспорт данных
- Просмотр колонок таблиц

**Запуск:** `python admin_of_bases.py` или через `start_admin.sh`

---

## 12. Статические ресурсы

| Файл | Назначение |
|------|-----------|
| `new_logo.jpg` | Логотип (отправляется при регистрации, 34 КБ) |
| `new_logo.png` | PNG-версия логотипа (264 байт — миниатюрная) |
| `admin_icon.icns` | Иконка macOS-админки (542 КБ) |
| `privacy_policy_*.txt` | Политики конфиденциальности (5 языков) |
| `docs/privacy_policy.html` | HTML-версия политики |
| GIF-библиотека | URL-ссылки на Giphy (жим штанги лёжа и fallback) |

---

## 13. FSM (конечный автомат состояний)

### Основной класс `REG(StatesGroup)`

| Состояние | Для чего |
|-----------|---------|
| `height` | Ввод роста |
| `age` | Ввод даты рождения (текстом, устаревший) |
| `age_calendar` | Выбор даты через inline-календарь |
| `sex` | Выбор пола |
| `want` | Выбор цели |
| `weight` | Ввод веса |
| `food` | Выбор способа ввода еды (фото/текст) |
| `food_list` | Ввод названий блюд текстом |
| `food_photo` | Отправка фото еды |
| `grams` / `grams1` | Ввод граммовок |
| `food_meals` | Выбор приёма пищи для рецепта |
| `train` | Выбор типа тренировки (AI) |
| `tren_choiser` | Выбор после AI-тренировки (меню/техника) |
| `length` | Ввод длительности (старая система) |
| `svo` | Выбор периода сводки |
| `leng` / `leng2` | Смена языка |
| `new_weight` / `new_height` | Ввод веса/роста для сводки |
| `tren_ai` | AI-ответ тренировки |
| `ai_ans` | (не используется) |

### Класс `WorkoutStates(StatesGroup)` (новая система)

| Состояние | Для чего |
|-----------|---------|
| `selecting_workout` | Выбор тренировки из inline-списка |
| `entering_duration` | Ввод длительности |
| `entering_weight` | Ввод веса (если нет данных за сегодня) |

### Middleware

| Middleware | Назначение |
|-----------|-----------|
| `PrivacyConsentMiddleware` | Блокирует сообщения без согласия на privacy policy |
| `DatabaseMiddleware` | DI: передаёт `db_connection` и `workout_service` в обработчики |

---

## 14. Замечания и рекомендации по улучшению

### 14.1. SQL-инъекции (КРИТИЧНО)

Несколько мест используют f-строки и `.format()` для SQL-запросов вместо параметризованных запросов:

- `keyboards.py:77` — `"SELECT lang FROM user_lang WHERE user_id = {}".format(int(user_id))`
- `main.py:1087` — `cursor.execute("SELECT lang FROM user_lang WHERE user_id = {}".format(user_id))`
- `main.py:2140-2145` — `UPDATE user_lang SET lang='{languages[data['leng2']]}' WHERE user_id = {message.from_user.id}`
- `main.py:1938-1953` — Множество `.format()` запросов в AI-генерации
- `main.py:2263-2266` — INSERT с f-строками
- `main.py:2297-2323` — Все SELECT-запросы в дневной сводке
- `main.py:2362-2416` — Все запросы в месячной сводке

> **Рекомендация:** При миграции на веб ВСЕ запросы должны использовать параметризацию через `%s`.

### 14.2. Глобальное подключение к БД

Бот использует **одно** глобальное подключение `conn` и один `cursor` для всех пользователей. Это создаёт:
- Потенциальные проблемы при конкурентном доступе
- Невозможность корректно обрабатывать ошибки соединения

> **Рекомендация:** Использовать пул подключений (например, `psycopg2.pool.ThreadedConnectionPool` или async-пул `asyncpg`).

### 14.3. Хранение пола как текста

Пол хранится как текст на языке пользователя («Мужчина», «Man», «Homme» и т.д.). Это усложняет:
- Расчёты (нужно переводить обратно)
- Логику вычисления калорий

> **Рекомендация:** Хранить `gender` как ENUM или code (`M`/`F`), а текстовое отображение формировать при рендеринге.

### 14.4. Дата рождения как строка

`date_of_birth` хранится как `VARCHAR` в формате `ДД-ММ-ГГГГ`, а не как `DATE`.

> **Рекомендация:** Хранить как `DATE` тип в PostgreSQL, конвертировать при записи/чтении.

### 14.5. Дублирование кода

`main.py` — монолит в 2901 строку. Много дублирующихся блоков:
- Получение языка пользователя (повторяется в ~15 местах)
- Расчёт сводки (повторяющиеся SQL-запросы)
- Формирование сообщений на разных языках (словари в 5 местах)

> **Рекомендация:** Вынести общие функции в сервисный слой, использовать DI.

### 14.6. Колонка `data` вместо `date` в таблице `water`

В таблице `water` колонка даты называется `data`, во всех остальных таблицах — `date`.

> **Рекомендация:** При миграции унифицировать название на `date`.

### 14.7. Цель хранится как текст на языке пользователя

`user_aims.user_aim` содержит «Сброс веса» / «Weight loss» / «Gewichtsverlust» и т.д.

> **Рекомендация:** Хранить как code (`weight_loss`, `maintain`, `weight_gain`), рендерить текст на фронте.

### 14.8. Формула перевода (translate)

Используется библиотека `translate` для перевода текстов при генерации рецептов/планов. Качество перевода невысокое.

> **Рекомендация:** На вебе использовать фронтовую локализацию (i18n), а AI-промпты формировать на языке пользователя напрямую.

### 14.9. Старая и новая системы тренировок сосуществуют

В `main.py` есть старая система (состояние `REG.length`, функция `intensiv()`) и новая (`WorkoutStates`, `workout_service`). Они частично пересекаются.

> **Рекомендация:** Оставить только новую систему (v2.0).

### 14.10. Монолитная архитектура

Весь бот — в одном файле `main.py`. Отдельные модули (`app/domain/workouts`, `app/domain/calendar`) уже начали выделять, но бо́льшая часть логики остаётся в монолите.

> **Рекомендация:** При миграции на веб-приложение построить чёткую слоистую архитектуру: routes → services → repositories → models.

### 14.11. Хардкод пути к файлу логотипа

`main.py:612` — `FSInputFile(path='/Users/VadimVthv/Desktop/PROpitashka/new_logo.jpg')` — абсолютный путь.

> **Рекомендация:** Использовать относительные пути или config-переменные.

### 14.12. autocommit + явный commit

`conn.autocommit = True` включён при инициализации, но при этом в коде встречаются `conn.commit()`. Это потенциально противоречиво.

> **Рекомендация:** Выбрать одну стратегию: или autocommit, или explicit transactions.

---

## Итого: что нужно перенести на веб

### Бизнес-логика (переносится полностью):
1. Регистрация пользователя (рост, вес, дата рождения, пол, цель)
2. Расчёт ИМТ и дневной нормы калорий
3. Дневник питания (текстовый ввод + AI-распознавание фото)
4. Система тренировок (20 типов, расчёт калорий через PG-функции)
5. Трекер воды
6. Сводка (день / месяц / год)
7. AI-генерация планов питания и тренировок
8. AI-рецепты и планы тренировок
9. AI-чат (свободный разговор)
10. Локализация (5 языков)

### Специфика веб-версии (новое):
1. **Авторизация через Telegram** — одноразовый код, приходящий в Telegram
2. **Бесшовный вход** — пользователь не замечает повторную авторизацию (session/cookie)
3. **Push-уведомления** — через Telegram (бот шлёт уведомления о напоминаниях, итогах дня)
4. **Веб-интерфейс** — вместо Telegram-клавиатур будет полноценный UI

### БД — переносится как есть (с рекомендованными улучшениями):
- 11 таблиц + 9 функций + 1 представление
- Добавить таблицу `web_sessions` для авторизации на вебе
- Исправить тип `date_of_birth` на `DATE`
- Исправить `user_sex` и `user_aim` на ENUM/коды
- Унифицировать `water.data` → `water.date`
