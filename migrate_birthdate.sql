-- ============================================
-- Миграция колонки date_of_birth
-- Изменение типа с INTEGER на VARCHAR(10)
-- ============================================

\echo 'Начало миграции date_of_birth...'

-- Шаг 1: Изменяем тип колонки с INTEGER на VARCHAR(10)
ALTER TABLE user_main 
ALTER COLUMN date_of_birth TYPE VARCHAR(10) 
USING date_of_birth::VARCHAR;

-- Шаг 2: Добавляем комментарий к колонке
COMMENT ON COLUMN user_main.date_of_birth IS 'Дата рождения в формате ДД-ММ-ГГГГ';

\echo 'Миграция завершена успешно!'
\echo 'Колонка date_of_birth теперь имеет тип VARCHAR(10)'

