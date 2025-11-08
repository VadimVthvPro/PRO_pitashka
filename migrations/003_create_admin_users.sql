-- ============================================
-- Migration: Create admin_users table
-- Создание таблицы администраторов
-- ============================================

-- Выполните этот файл для создания админов:
-- psql -U postgres -d propitashka -f migrations/003_create_admin_users.sql

\echo '=== Начало миграции admin_users ==='

-- ============================================
-- 1. Создание таблицы admin_users
-- ============================================

\echo 'Создание таблицы admin_users...'

CREATE TABLE IF NOT EXISTS admin_users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_login_at TIMESTAMPTZ,
    
    CONSTRAINT unique_admin_username UNIQUE(username)
);

CREATE INDEX IF NOT EXISTS idx_admin_users_username ON admin_users(username);
CREATE INDEX IF NOT EXISTS idx_admin_users_last_login ON admin_users(last_login_at);

COMMENT ON TABLE admin_users IS 'Учетные записи администраторов системы';
COMMENT ON COLUMN admin_users.username IS 'Имя пользователя для входа';
COMMENT ON COLUMN admin_users.password_hash IS 'Хеш пароля (bcrypt)';
COMMENT ON COLUMN admin_users.last_login_at IS 'Дата и время последнего входа';

-- ============================================
-- 2. Создание администратора по умолчанию
-- ============================================

\echo 'Создание администратора по умолчанию...'

-- Пароль: admin
-- Хеш создан с помощью bcrypt: bcrypt.hashpw(b'admin', bcrypt.gensalt()).decode('utf-8')
INSERT INTO admin_users (username, password_hash)
VALUES ('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqYGZ0NJWK')
ON CONFLICT (username) DO NOTHING;

\echo 'Администратор по умолчанию создан:';
\echo '  Логин: admin';
\echo '  Пароль: admin';
\echo '';
\echo '⚠️  ВАЖНО: Смените пароль после первого входа!';

-- ============================================
-- 3. Завершение миграции
-- ============================================

\echo '';
\echo '=== Миграция admin_users завершена успешно! ==='
\echo '';
\echo 'Для входа используйте:';
\echo '  Логин: admin';
\echo '  Пароль: admin';
\echo '';

