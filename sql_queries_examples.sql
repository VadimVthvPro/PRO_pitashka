-- ================================================
-- SQL Запросы для анализа логов бота PROpitashka
-- ================================================

-- 1. ПРОСМОТР ПОСЛЕДНИХ ЛОГОВ
-- ================================================

-- Последние 50 событий
SELECT 
    timestamp,
    level,
    username,
    message
FROM bot_logs 
ORDER BY timestamp DESC 
LIMIT 50;


-- 2. ПОИСК ОШИБОК
-- ================================================

-- Все ошибки за последние 24 часа
SELECT 
    timestamp,
    username,
    message,
    error_traceback
FROM bot_logs 
WHERE level IN ('ERROR', 'CRITICAL') 
    AND timestamp > NOW() - INTERVAL '1 day'
ORDER BY timestamp DESC;

-- Критические ошибки
SELECT * FROM bot_logs 
WHERE level = 'CRITICAL'
ORDER BY timestamp DESC;

-- Ошибки с полным трейсбеком
SELECT 
    timestamp,
    message,
    function_name,
    line_number,
    error_traceback
FROM bot_logs
WHERE error_traceback IS NOT NULL
ORDER BY timestamp DESC
LIMIT 20;


-- 3. АНАЛИЗ ДЕЙСТВИЙ ПОЛЬЗОВАТЕЛЕЙ
-- ================================================

-- Действия конкретного пользователя
SELECT 
    timestamp,
    level,
    message
FROM bot_logs 
WHERE user_id = 123456  -- Замените на нужный ID
ORDER BY timestamp DESC;

-- Пользователи с наибольшим количеством ошибок
SELECT 
    username,
    user_id,
    COUNT(*) as error_count
FROM bot_logs
WHERE level = 'ERROR'
    AND timestamp > NOW() - INTERVAL '7 days'
GROUP BY username, user_id
ORDER BY error_count DESC
LIMIT 10;

-- Активность пользователей за день
SELECT 
    username,
    COUNT(*) as actions
FROM bot_logs
WHERE timestamp > CURRENT_DATE
GROUP BY username
ORDER BY actions DESC;


-- 4. СТАТИСТИКА
-- ================================================

-- Количество событий по уровням
SELECT 
    level,
    COUNT(*) as count
FROM bot_logs
WHERE timestamp > NOW() - INTERVAL '7 days'
GROUP BY level
ORDER BY count DESC;

-- Самые частые ошибки
SELECT 
    function_name,
    COUNT(*) as error_count,
    MAX(timestamp) as last_occurrence
FROM bot_logs
WHERE level = 'ERROR'
GROUP BY function_name
ORDER BY error_count DESC
LIMIT 20;

-- Активность по часам (за последний день)
SELECT 
    DATE_TRUNC('hour', timestamp) as hour,
    COUNT(*) as events
FROM bot_logs
WHERE timestamp > NOW() - INTERVAL '1 day'
GROUP BY hour
ORDER BY hour DESC;

-- Статистика действий по функциям
SELECT 
    function_name,
    level,
    COUNT(*) as count
FROM bot_logs
WHERE timestamp > NOW() - INTERVAL '1 day'
GROUP BY function_name, level
ORDER BY count DESC;


-- 5. ПОИСК КОНКРЕТНЫХ СОБЫТИЙ
-- ================================================

-- Поиск по тексту сообщения
SELECT * FROM bot_logs
WHERE message LIKE '%Регистрация%'
ORDER BY timestamp DESC
LIMIT 50;

-- Успешные входы пользователей
SELECT 
    timestamp,
    username,
    message
FROM bot_logs
WHERE message LIKE '%Успешный вход%'
ORDER BY timestamp DESC;

-- Добавление еды
SELECT 
    timestamp,
    username,
    message
FROM bot_logs
WHERE message LIKE '%Добавлена еда%'
    AND timestamp > CURRENT_DATE
ORDER BY timestamp DESC;

-- Использование AI функций
SELECT 
    timestamp,
    username,
    message
FROM bot_logs
WHERE message LIKE '%AI%' OR message LIKE '%Gemini%'
ORDER BY timestamp DESC;


-- 6. ОЧИСТКА СТАРЫХ ЛОГОВ
-- ================================================

-- ОСТОРОЖНО! Удаляет старые логи
-- Удалить логи старше 90 дней
DELETE FROM bot_logs 
WHERE timestamp < NOW() - INTERVAL '90 days';

-- Оставить только последние 100,000 записей
DELETE FROM bot_logs 
WHERE id NOT IN (
    SELECT id FROM bot_logs 
    ORDER BY timestamp DESC 
    LIMIT 100000
);


-- 7. МОНИТОРИНГ ПРОИЗВОДИТЕЛЬНОСТИ
-- ================================================

-- Размер таблицы логов
SELECT 
    pg_size_pretty(pg_total_relation_size('bot_logs')) as table_size,
    COUNT(*) as total_records
FROM bot_logs;

-- Запросов к AI за день
SELECT COUNT(*) as ai_requests
FROM bot_logs
WHERE (message LIKE '%Gemini%' OR message LIKE '%запрос%')
    AND timestamp > CURRENT_DATE;


-- 8. ОТЛАДКА КОНКРЕТНЫХ ПРОБЛЕМ
-- ================================================

-- Последовательность действий пользователя перед ошибкой
WITH user_errors AS (
    SELECT user_id, timestamp
    FROM bot_logs
    WHERE level = 'ERROR'
        AND user_id IS NOT NULL
    ORDER BY timestamp DESC
    LIMIT 1
)
SELECT 
    bl.timestamp,
    bl.level,
    bl.message,
    bl.function_name
FROM bot_logs bl
JOIN user_errors ue ON bl.user_id = ue.user_id
WHERE bl.timestamp BETWEEN ue.timestamp - INTERVAL '5 minutes' AND ue.timestamp
ORDER BY bl.timestamp;

-- Частота определенного типа ошибок
SELECT 
    DATE(timestamp) as date,
    COUNT(*) as error_count
FROM bot_logs
WHERE message LIKE '%Ошибка при входе%'
GROUP BY date
ORDER BY date DESC;


-- 9. ЭКСПОРТ ДАННЫХ
-- ================================================

-- Экспорт ошибок в CSV (выполнить в psql)
-- \copy (SELECT timestamp, username, message, error_traceback FROM bot_logs WHERE level='ERROR' ORDER BY timestamp DESC LIMIT 1000) TO '/tmp/errors.csv' CSV HEADER;


-- 10. ПОЛЕЗНЫЕ ИНДЕКСЫ (уже созданы в logger_config.py)
-- ================================================

-- Если нужно пересоздать индексы:
-- CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON bot_logs(timestamp);
-- CREATE INDEX IF NOT EXISTS idx_logs_level ON bot_logs(level);
-- CREATE INDEX IF NOT EXISTS idx_logs_user_id ON bot_logs(user_id);
-- CREATE INDEX IF NOT EXISTS idx_logs_function ON bot_logs(function_name);

