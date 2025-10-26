# 📊 Руководство по аналитике PROpitashka

## Обзор

Этот документ содержит инструкции по использованию аналитических запросов для отслеживания ключевых метрик вашего Telegram-бота PROpitashka.

## 📁 Файлы

- **`analytics_dashboard.sql`** - SQL-скрипт с готовыми запросами для всех метрик

## 🚀 Как использовать

### Вариант 1: Запуск в PostgreSQL

```bash
# Подключитесь к вашей базе данных
psql -U postgres -d propitashka

# Выполните конкретный запрос
\i analytics_dashboard.sql
```

### Вариант 2: Выполнение отдельных запросов

Откройте файл `analytics_dashboard.sql` и скопируйте нужный запрос в ваш PostgreSQL клиент (pgAdmin, DBeaver и т.д.).

## 📈 Доступные метрики

### 1. **DAU (Daily Active Users)**
- **Что показывает**: Количество уникальных пользователей, активных каждый день за последнюю неделю
- **Как использовать**: Отслеживайте тренд ежедневной активности
- **Запрос #1** в `analytics_dashboard.sql`

### 2. **MAU (Monthly Active Users)**
- **Что показывает**: Общее количество активных пользователей в текущем месяце
- **Как использовать**: Оцените масштаб вашей активной аудитории
- **Запрос #2** в `analytics_dashboard.sql`

### 3. **Новые пользователи**
- **Что показывает**: Динамика регистраций за последние 30 дней
- **Как использовать**: Оцените эффективность маркетинговых кампаний
- **Запрос #3** в `analytics_dashboard.sql`

### 4. **Activation Rate (Активация)**
- **Что показывает**: % пользователей, которые добавили хотя бы одну запись о еде
- **Как использовать**: Понимайте, насколько эффективен ваш onboarding
- **Целевой показатель**: 40%+
- **Запрос #4** в `analytics_dashboard.sql`

### 5. **1-Day Retention (Удержание на 1 день)**
- **Что показывает**: % пользователей, вернувшихся на следующий день после регистрации
- **Как использовать**: Оцените "липкость" продукта
- **Целевой показатель**: 25%+
- **Запрос #5** в `analytics_dashboard.sql`

### 6. **7-Day Retention (Удержание на 7 день)**
- **Что показывает**: % пользователей, активных через неделю после регистрации
- **Как использовать**: Долгосрочная оценка вовлеченности
- **Целевой показатель**: 15%+
- **Запрос #6** в `analytics_dashboard.sql`

### 7. **Average Actions Per User**
- **Что показывает**: Среднее количество действий на одного активного пользователя
- **Как использовать**: Понимайте глубину engagement
- **Запрос #7** в `analytics_dashboard.sql`

### 8. **Referral Source Analysis (UTM-анализ)**
- **Что показывает**: Эффективность различных источников трафика
- **Как использовать**: Оптимизируйте маркетинговые бюджеты
- **Запрос #8** в `analytics_dashboard.sql`

### 9. **Top Referral Codes**
- **Что показывает**: Самые успешные реферальные коды (блогеры)
- **Как использовать**: Определите лучших амбассадоров
- **Запрос #9** в `analytics_dashboard.sql`

### 10. **User Engagement Summary**
- **Что показывает**: Общая сводка по типам активности
- **Как использовать**: Быстрый обзор использования функций
- **Запрос #10** в `analytics_dashboard.sql`

### 11. **Cohort Analysis (Когортный анализ)**
- **Что показывает**: Удержание пользователей по неделям регистрации
- **Как использовать**: Оцените влияние изменений продукта на retention
- **Запрос #11** в `analytics_dashboard.sql`

## 🎯 Рекомендации по использованию

### Ежедневно
- Проверяйте **DAU** (запрос #1)
- Смотрите на **новые регистрации** (запрос #3)

### Еженедельно
- Анализируйте **Activation Rate** (запрос #4)
- Проверяйте **1-Day Retention** (запрос #5)
- Оценивайте **эффективность источников** (запрос #8)

### Ежемесячно
- Полный **Cohort Analysis** (запрос #11)
- Глубокий анализ **реферальных источников** (запросы #8, #9)
- Оценка **среднего engagement** (запрос #7)

## 🔧 Автоматизация

Вы можете настроить автоматическую отправку отчетов с помощью:

### Cron Job (Linux/Mac)

```bash
# Создайте скрипт для ежедневной отправки DAU
cat > /path/to/daily_stats.sh << 'EOF'
#!/bin/bash
psql -U postgres -d propitashka -c "
SELECT 
    CURRENT_DATE as report_date,
    COUNT(DISTINCT user_id) AS daily_active_users
FROM (
    SELECT user_id FROM food WHERE date = CURRENT_DATE
    UNION ALL
    SELECT user_id FROM user_training WHERE date = CURRENT_DATE
    UNION ALL
    SELECT user_id FROM water WHERE data = CURRENT_DATE
) AS user_activity;
" | mail -s "PROpitashka Daily Stats" your@email.com
EOF

chmod +x /path/to/daily_stats.sh

# Добавьте в crontab для ежедневного запуска в 9:00
crontab -e
# 0 9 * * * /path/to/daily_stats.sh
```

### Python Script

Вы можете создать Python-скрипт для отправки отчетов в Telegram:

```python
import psycopg2
from telegram import Bot

def send_daily_report(bot_token, admin_chat_id):
    # Подключаемся к БД
    conn = psycopg2.connect(dbname='propitashka', user='postgres', password='your_password')
    cur = conn.cursor()
    
    # Выполняем запрос
    cur.execute("""
        SELECT COUNT(DISTINCT user_id) AS dau
        FROM (
            SELECT user_id FROM food WHERE date = CURRENT_DATE
            UNION ALL
            SELECT user_id FROM user_training WHERE date = CURRENT_DATE
        ) AS activity
    """)
    
    dau = cur.fetchone()[0]
    
    # Отправляем в Telegram
    bot = Bot(token=bot_token)
    bot.send_message(
        chat_id=admin_chat_id,
        text=f"📊 Ежедневная статистика\n\n👥 DAU: {dau}"
    )
    
    conn.close()
```

## 📝 Примечания

- Все запросы оптимизированы для PostgreSQL
- Используйте индексы на полях `user_id`, `date`, `created_at` для ускорения запросов
- Для больших объемов данных (>100k записей) рассмотрите материализованные представления

## 🆘 Поддержка

Если у вас возникли вопросы по аналитике, обратитесь к документации PostgreSQL или создайте issue в репозитории проекта.





