-- =====================================================
-- Миграция: Безопасная система администраторов
-- Версия: 005
-- Дата: 2025-10-31
-- Описание: Добавление полей для безопасного управления админами
-- =====================================================

BEGIN;

-- 1. Создание таблицы admin_users (если не существует)
CREATE TABLE IF NOT EXISTS admin_users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- 2. Добавление новых полей для безопасности
ALTER TABLE admin_users 
ADD COLUMN IF NOT EXISTS password_reset_required BOOLEAN DEFAULT TRUE,
ADD COLUMN IF NOT EXISTS password_changed_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS failed_login_attempts INT DEFAULT 0,
ADD COLUMN IF NOT EXISTS locked_until TIMESTAMP,
ADD COLUMN IF NOT EXISTS two_factor_enabled BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS two_factor_secret VARCHAR(32),
ADD COLUMN IF NOT EXISTS session_token VARCHAR(255),
ADD COLUMN IF NOT EXISTS session_expires_at TIMESTAMP;

-- 3. Создание индексов для производительности
CREATE INDEX IF NOT EXISTS idx_admin_users_username 
ON admin_users(username);

CREATE INDEX IF NOT EXISTS idx_admin_users_session_token 
ON admin_users(session_token);

CREATE INDEX IF NOT EXISTS idx_admin_users_locked_until 
ON admin_users(locked_until);

-- 4. Создание таблицы для логирования входов
CREATE TABLE IF NOT EXISTS admin_login_log (
    log_id SERIAL PRIMARY KEY,
    admin_username VARCHAR(50) NOT NULL,
    login_attempt_at TIMESTAMP NOT NULL DEFAULT NOW(),
    success BOOLEAN NOT NULL,
    ip_address INET,
    user_agent TEXT,
    failure_reason VARCHAR(255)
);

CREATE INDEX IF NOT EXISTS idx_admin_login_log_username 
ON admin_login_log(admin_username);

CREATE INDEX IF NOT EXISTS idx_admin_login_log_timestamp 
ON admin_login_log(login_attempt_at DESC);

-- 5. Создание дефолтного администратора с bcrypt-хешем 
-- (пароль: admin, но требует смены при первом входе)
-- Bcrypt hash для "admin": $2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LwP8qYpfTaYNPJKdK

INSERT INTO admin_users (username, password_hash, email, password_reset_required)
VALUES ('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LwP8qYpfTaYNPJKdK', NULL, TRUE)
ON CONFLICT (username) 
DO UPDATE SET 
    password_reset_required = TRUE,
    password_changed_at = NULL;

-- 6. Добавление комментариев к таблицам и колонкам
COMMENT ON TABLE admin_users IS 
'Таблица администраторов с безопасным хранением паролей (bcrypt)';

COMMENT ON COLUMN admin_users.password_reset_required IS 
'Требуется смена пароля при следующем входе';

COMMENT ON COLUMN admin_users.failed_login_attempts IS 
'Количество неудачных попыток входа (сбрасывается при успешном входе)';

COMMENT ON COLUMN admin_users.locked_until IS 
'Временная блокировка аккаунта до указанного времени (после 5 неудачных попыток)';

COMMENT ON TABLE admin_login_log IS 
'Лог всех попыток входа в админ-панель (успешных и неудачных)';

COMMIT;

-- Информация для администратора
DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Миграция 005 успешно применена!';
    RAISE NOTICE '========================================';
    RAISE NOTICE '';
    RAISE NOTICE '⚠️  ВАЖНО: Безопасность';
    RAISE NOTICE '';
    RAISE NOTICE 'Дефолтный пароль "admin" помечен как небезопасный.';
    RAISE NOTICE 'При следующем входе вам будет предложено сменить пароль.';
    RAISE NOTICE '';
    RAISE NOTICE '💡 Для ручной смены пароля используйте:';
    RAISE NOTICE '   python scripts/change_admin_password.py';
    RAISE NOTICE '';
    RAISE NOTICE '🔒 Новые возможности:';
    RAISE NOTICE '   - Защита от brute-force (блокировка после 5 попыток)';
    RAISE NOTICE '   - Логирование всех попыток входа';
    RAISE NOTICE '   - Принудительная смена дефолтного пароля';
    RAISE NOTICE '   - Хеширование паролей через bcrypt';
    RAISE NOTICE '';
    RAISE NOTICE '========================================';
END $$;


