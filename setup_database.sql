-- ============================================
-- PROpitashka Database Setup Script
-- Полная инициализация базы данных PostgreSQL
-- ============================================

-- Выполните этот файл один раз при первой настройке:
-- psql -U postgres -d propitashka -f setup_database.sql

\echo '=== Начало инициализации базы данных PROpitashka ==='

-- ============================================
-- 1. Создание основных таблиц
-- ============================================

\echo 'Создание таблицы user_main...'
CREATE TABLE IF NOT EXISTS user_main (
    user_id BIGINT PRIMARY KEY,
    user_name VARCHAR(255),
    user_sex VARCHAR(50),
    date_of_birth VARCHAR(10),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    privacy_consent_given BOOLEAN DEFAULT FALSE,
    privacy_consent_at TIMESTAMPTZ,
    utm_source VARCHAR(255),
    utm_medium VARCHAR(255),
    utm_campaign VARCHAR(255),
    ref_code VARCHAR(255)
);

\echo 'Создание таблицы user_lang...'
CREATE TABLE IF NOT EXISTS user_lang (
    user_id BIGINT PRIMARY KEY,
    lang VARCHAR(10) DEFAULT 'ru',
    FOREIGN KEY (user_id) REFERENCES user_main(user_id) ON DELETE CASCADE
);

\echo 'Создание таблицы user_health...'
CREATE TABLE IF NOT EXISTS user_health (
    id SERIAL PRIMARY KEY,
    user_id BIGINT,
    imt NUMERIC(5, 2),
    imt_str VARCHAR(255),
    cal NUMERIC(7, 2),
    date DATE,
    weight NUMERIC(5, 2),
    height NUMERIC(5, 2),
    FOREIGN KEY (user_id) REFERENCES user_main(user_id) ON DELETE CASCADE
);

\echo 'Создание таблицы user_aims...'
CREATE TABLE IF NOT EXISTS user_aims (
    user_id BIGINT PRIMARY KEY,
    user_aim VARCHAR(255),
    daily_cal NUMERIC(7, 2),
    FOREIGN KEY (user_id) REFERENCES user_main(user_id) ON DELETE CASCADE
);

\echo 'Создание таблицы food...'
CREATE TABLE IF NOT EXISTS food (
    id SERIAL PRIMARY KEY,
    user_id BIGINT,
    date DATE,
    name_of_food VARCHAR(255),
    b NUMERIC(7, 3),
    g NUMERIC(7, 3),
    u NUMERIC(7, 3),
    cal NUMERIC(7, 3),
    FOREIGN KEY (user_id) REFERENCES user_main(user_id) ON DELETE CASCADE
);

\echo 'Создание таблицы user_training...'
CREATE TABLE IF NOT EXISTS user_training (
    id SERIAL PRIMARY KEY,
    user_id BIGINT,
    date DATE,
    training_cal NUMERIC(7, 3),
    tren_time INTEGER,
    FOREIGN KEY (user_id) REFERENCES user_main(user_id) ON DELETE CASCADE
);

\echo 'Создание таблицы water...'
CREATE TABLE IF NOT EXISTS water (
    user_id BIGINT,
    data DATE,
    count INTEGER DEFAULT 1,
    PRIMARY KEY (user_id, data),
    FOREIGN KEY (user_id) REFERENCES user_main(user_id) ON DELETE CASCADE
);

\echo 'Создание таблицы admin_users...'
CREATE TABLE IF NOT EXISTS admin_users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_login TIMESTAMPTZ
);

-- ============================================
-- 2. Создание индексов для производительности
-- ============================================

\echo 'Создание индексов...'
CREATE INDEX IF NOT EXISTS idx_user_health_user_date ON user_health(user_id, date);
CREATE INDEX IF NOT EXISTS idx_food_user_date ON food(user_id, date);
CREATE INDEX IF NOT EXISTS idx_training_user_date ON user_training(user_id, date);
CREATE INDEX IF NOT EXISTS idx_water_user_date ON water(user_id, data);
CREATE INDEX IF NOT EXISTS idx_user_main_created ON user_main(created_at);
CREATE INDEX IF NOT EXISTS idx_user_main_utm_source ON user_main(utm_source);
CREATE INDEX IF NOT EXISTS idx_user_main_ref_code ON user_main(ref_code);

-- ============================================
-- 3. Добавление комментариев к таблицам
-- ============================================

\echo 'Добавление комментариев...'
COMMENT ON TABLE user_main IS 'Основная информация о пользователях';
COMMENT ON TABLE user_lang IS 'Языковые настройки пользователей';
COMMENT ON TABLE user_health IS 'История показателей здоровья (вес, рост, ИМТ)';
COMMENT ON TABLE user_aims IS 'Цели пользователей по питанию';
COMMENT ON TABLE food IS 'Записи о потребленной пище';
COMMENT ON TABLE user_training IS 'Записи о тренировках';
COMMENT ON TABLE water IS 'Учет потребления воды';
COMMENT ON TABLE admin_users IS 'Учетные записи администраторов';

COMMENT ON COLUMN user_main.privacy_consent_given IS 'Дал ли пользователь согласие на обработку данных';
COMMENT ON COLUMN user_main.privacy_consent_at IS 'Дата и время предоставления согласия';
COMMENT ON COLUMN user_main.date_of_birth IS 'Дата рождения в формате ДД-ММ-ГГГГ';
COMMENT ON COLUMN user_main.utm_source IS 'Источник трафика (например, blogger_name)';
COMMENT ON COLUMN user_main.utm_medium IS 'Канал (например, telegram, instagram)';
COMMENT ON COLUMN user_main.utm_campaign IS 'Название кампании';
COMMENT ON COLUMN user_main.ref_code IS 'Реферальный код';

-- ============================================
-- 4. Создание администратора по умолчанию
-- ============================================

\echo 'Создание учетной записи администратора по умолчанию...'
-- Пароль: admin (bcrypt hash)
-- ВАЖНО: Измените пароль сразу после первого входа!
INSERT INTO admin_users (username, password_hash)
VALUES ('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5yvT9qQqU8pom')
ON CONFLICT (username) DO NOTHING;

-- ============================================
-- 5. Настройка ограниченного пользователя БД
-- ============================================

\echo 'Настройка прав доступа...'
-- Создаем роль для бота с ограниченными правами
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'propitashka_bot') THEN
        CREATE ROLE propitashka_bot WITH LOGIN PASSWORD 'your_secure_password_here';
    END IF;
END
$$;

-- Даем права только на нужные таблицы
GRANT CONNECT ON DATABASE propitashka TO propitashka_bot;
GRANT USAGE ON SCHEMA public TO propitashka_bot;
GRANT SELECT, INSERT, UPDATE ON user_main, user_lang, user_health, user_aims, food, user_training, water TO propitashka_bot;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO propitashka_bot;

-- Создаем роль для админки
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'propitashka_admin') THEN
        CREATE ROLE propitashka_admin WITH LOGIN PASSWORD 'your_admin_password_here';
    END IF;
END
$$;

GRANT CONNECT ON DATABASE propitashka TO propitashka_admin;
GRANT USAGE ON SCHEMA public TO propitashka_admin;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO propitashka_admin;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO propitashka_admin;

\echo '=== База данных успешно инициализирована! ==='
\echo ''
\echo 'ВАЖНО: Не забудьте изменить пароли:'
\echo '1. Пароль администратора (по умолчанию: admin/admin)'
\echo '2. Пароль propitashka_bot в скрипте и в .env'
\echo '3. Пароль propitashka_admin в скрипте и в .env'
\echo ''
\echo 'Для просмотра таблиц выполните: \\dt'





