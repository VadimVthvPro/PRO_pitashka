# 📊 Система Логирования PROpitashka

## Обзор

Бот использует профессиональную систему логирования с записью в файлы и PostgreSQL базу данных. Это позволяет отслеживать работу бота, находить ошибки и анализировать поведение пользователей.

## 🗂️ Структура логов

### Файловые логи

Логи хранятся в директории `PROpitashka/logs/`:

- **`bot_all.log`** - Все логи (DEBUG и выше)
  - Максимальный размер: 10 МБ
  - Хранится 10 ротированных файлов
  - Подробный формат с номерами строк

- **`bot_errors.log`** - Только ошибки (ERROR и выше)
  - Максимальный размер: 5 МБ
  - Хранится 10 ротированных файлов
  - Включает полные трейсбеки ошибок

### База данных

Логи сохраняются в таблицу `bot_logs` в PostgreSQL:

```sql
CREATE TABLE bot_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    level VARCHAR(10),                    -- Уровень лога (INFO, ERROR и т.д.)
    logger_name VARCHAR(100),             -- Имя логгера
    message TEXT,                         -- Текст сообщения
    user_id BIGINT,                       -- ID пользователя Telegram
    username VARCHAR(100),                -- Username пользователя
    function_name VARCHAR(100),           -- Имя функции
    line_number INTEGER,                  -- Номер строки в коде
    error_traceback TEXT                  -- Полный трейсбек ошибки
);
```

## 📝 Уровни логирования

### DEBUG
Подробная отладочная информация. Используется для глубокой диагностики.

**Пример:**
```python
logger.debug("Получены данные от пользователя: {data}")
```

### INFO
Подтверждение нормальной работы. Ключевые события.

**Пример:**
```python
log_user_action(logger, user, "Регистрация завершена", "Вес: 70кг")
```

### WARNING
Предупреждения о потенциальных проблемах.

**Пример:**
```python
logger.warning(f"Пользователь {user_id} - неполные данные")
```

### ERROR
Ошибки, которые не привели к остановке бота.

**Пример:**
```python
log_error(logger, user, exception, "Ошибка при сохранении данных")
```

### CRITICAL
Критические ошибки, требующие немедленного внимания.

**Пример:**
```python
logger.critical("Невозможно подключиться к базе данных")
```

## 🔍 Просмотр логов

### На сервере через SSH

```bash
# Подключаемся к серверу
ssh user@your-server.com

# Переходим в директорию бота
cd /path/to/PROpitashka/PROpitashka

# Просмотр всех логов
tail -f logs/bot_all.log

# Просмотр только ошибок
tail -f logs/bot_errors.log

# Последние 100 строк
tail -n 100 logs/bot_all.log

# Поиск по логам
grep "Ошибка" logs/bot_all.log

# Поиск ошибок конкретного пользователя
grep "user_id: 123456" logs/bot_errors.log
```

### Из базы данных

```sql
-- Последние 50 логов
SELECT * FROM bot_logs 
ORDER BY timestamp DESC 
LIMIT 50;

-- Все ошибки за последний день
SELECT * FROM bot_logs 
WHERE level IN ('ERROR', 'CRITICAL') 
  AND timestamp > NOW() - INTERVAL '1 day'
ORDER BY timestamp DESC;

-- Действия конкретного пользователя
SELECT timestamp, level, message 
FROM bot_logs 
WHERE user_id = 123456
ORDER BY timestamp DESC;

-- Статистика ошибок по функциям
SELECT function_name, COUNT(*) as error_count
FROM bot_logs
WHERE level = 'ERROR'
GROUP BY function_name
ORDER BY error_count DESC;

-- Поиск ошибок с трейсбеком
SELECT timestamp, message, error_traceback
FROM bot_logs
WHERE error_traceback IS NOT NULL
ORDER BY timestamp DESC
LIMIT 10;
```

## 🛠️ Примеры использования

### Логирование действия пользователя

```python
from logger_config import log_user_action

@dp.message(CommandStart())
async def start(message: Message):
    log_user_action(
        logger, 
        message.from_user, 
        "Команда /start", 
        "Дополнительная информация"
    )
```

### Логирование ошибки

```python
from logger_config import log_error

try:
    # Ваш код
    result = some_function()
except Exception as e:
    log_error(
        logger, 
        message.from_user, 
        e, 
        "Контекст ошибки"
    )
```

### Обычное логирование

```python
logger.info("Бот запущен успешно")
logger.warning("Низкая скорость ответа API")
logger.error("Ошибка соединения с БД", exc_info=True)
```

## 📊 Анализ логов

### Типичные сценарии

**1. Пользователь сообщил об ошибке**
```bash
# Находим username пользователя
grep "@username" logs/bot_all.log

# Смотрим его последние действия
tail -n 200 logs/bot_all.log | grep "user_id: 123456"
```

**2. Бот перестал отвечать**
```bash
# Проверяем критические ошибки
grep "CRITICAL" logs/bot_errors.log

# Последние действия перед остановкой
tail -n 50 logs/bot_all.log
```

**3. Анализ производительности**
```sql
-- Сколько запросов обрабатывается в час
SELECT 
    DATE_TRUNC('hour', timestamp) as hour,
    COUNT(*) as requests
FROM bot_logs
WHERE message LIKE '%Команда%'
GROUP BY hour
ORDER BY hour DESC;
```

## 🔐 Безопасность

⚠️ **Важно:**
- Логи содержат user_id и username пользователей
- НЕ логируйте пароли, токены или личные данные
- Регулярно очищайте старые логи
- Ограничьте доступ к серверу и БД

## 🧹 Очистка старых логов

### Файлы
Ротация происходит автоматически (хранится 10 файлов).

Для ручной очистки:
```bash
# Удалить логи старше 30 дней
find logs/ -name "*.log*" -mtime +30 -delete
```

### База данных
```sql
-- Удалить логи старше 90 дней
DELETE FROM bot_logs 
WHERE timestamp < NOW() - INTERVAL '90 days';

-- Или оставить только последние 100 000 записей
DELETE FROM bot_logs 
WHERE id NOT IN (
    SELECT id FROM bot_logs 
    ORDER BY timestamp DESC 
    LIMIT 100000
);
```

## 📈 Мониторинг

Рекомендуется настроить автоматический мониторинг:

```bash
# Создать cron задачу для проверки ошибок
# Каждый час проверяем логи и отправляем уведомление
0 * * * * grep "CRITICAL" /path/to/logs/bot_errors.log && echo "Критическая ошибка!" | mail -s "Alert" admin@example.com
```

## 🔧 Настройка

Конфигурация находится в `logger_config.py`:

- Изменить размер файлов: `maxBytes`
- Количество backup файлов: `backupCount`
- Уровни логирования для разных handlers
- Параметры подключения к БД

## 📚 Дополнительно

- [Документация logging](https://docs.python.org/3/library/logging.html)
- [Статья на Хабре о логировании](https://habr.com/ru/companies/otus/articles/782646/)

---

**Помните**: Хорошие логи - это половина успеха в отладке и поддержке приложения! 🚀

