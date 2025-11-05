-- ============================================
-- МИГРАЦИЯ 006: РЕФЕРАЛЬНАЯ СИСТЕМА И МОНЕТИЗАЦИЯ
-- ============================================
-- Автор: AI Assistant
-- Дата: 2025-10-31
-- Описание: Добавляет реферальную систему, платные подписки и систему рекламы

-- 1. ТАБЛИЦА ПОДПИСОК (платные подписки пользователей)
CREATE TABLE IF NOT EXISTS subscriptions (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES user_main(user_id) ON DELETE CASCADE,
    subscription_type VARCHAR(50) NOT NULL, -- 'free', 'premium_monthly', 'premium_yearly'
    start_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    end_date TIMESTAMP, -- NULL для бесплатной подписки
    is_active BOOLEAN DEFAULT TRUE,
    auto_renewal BOOLEAN DEFAULT FALSE,
    price DECIMAL(10, 2),
    currency VARCHAR(10) DEFAULT 'RUB',
    payment_method VARCHAR(50), -- 'card', 'yoomoney', 'cryptobot'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_active ON subscriptions(is_active);
CREATE INDEX IF NOT EXISTS idx_subscriptions_end_date ON subscriptions(end_date);

-- 2. ТАБЛИЦА РЕФЕРАЛОВ (реферальные связи)
CREATE TABLE IF NOT EXISTS referrals (
    id SERIAL PRIMARY KEY,
    referrer_id BIGINT NOT NULL REFERENCES user_main(user_id) ON DELETE CASCADE, -- кто пригласил
    referred_id BIGINT NOT NULL REFERENCES user_main(user_id) ON DELETE CASCADE, -- кого пригласили
    referral_code VARCHAR(50) UNIQUE NOT NULL,
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'activated', 'rewarded'
    reward_given BOOLEAN DEFAULT FALSE,
    reward_type VARCHAR(50), -- 'premium_days', 'discount', 'bonus_features'
    reward_value INTEGER, -- количество дней премиума или % скидки
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    activated_at TIMESTAMP
);

-- Индексы
CREATE INDEX IF NOT EXISTS idx_referrals_referrer ON referrals(referrer_id);
CREATE INDEX IF NOT EXISTS idx_referrals_referred ON referrals(referred_id);
CREATE INDEX IF NOT EXISTS idx_referrals_code ON referrals(referral_code);

-- 3. ТАБЛИЦА РЕКЛАМНЫХ МАТЕРИАЛОВ
CREATE TABLE IF NOT EXISTS advertisements (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255),
    content TEXT NOT NULL,
    media_type VARCHAR(20), -- 'text', 'photo', 'video', 'document'
    media_file_id VARCHAR(255), -- Telegram file_id для медиа
    target_audience VARCHAR(50) DEFAULT 'free_users', -- 'free_users', 'all_users'
    priority INTEGER DEFAULT 1, -- приоритет показа (1-10)
    is_active BOOLEAN DEFAULT TRUE,
    impressions_count INTEGER DEFAULT 0, -- сколько раз показано
    clicks_count INTEGER DEFAULT 0, -- сколько раз кликнули
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP -- дата истечения рекламы
);

-- Индекс для активных реклам
CREATE INDEX IF NOT EXISTS idx_ads_active ON advertisements(is_active);

-- 4. ТАБЛИЦА ПРОСМОТРОВ РЕКЛАМЫ (для контроля частоты показа)
CREATE TABLE IF NOT EXISTS ad_views (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES user_main(user_id) ON DELETE CASCADE,
    ad_id INTEGER NOT NULL REFERENCES advertisements(id) ON DELETE CASCADE,
    viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    clicked BOOLEAN DEFAULT FALSE
);

-- Индексы для аналитики
CREATE INDEX IF NOT EXISTS idx_ad_views_user ON ad_views(user_id);
CREATE INDEX IF NOT EXISTS idx_ad_views_ad ON ad_views(ad_id);
CREATE INDEX IF NOT EXISTS idx_ad_views_date ON ad_views(viewed_at);

-- 5. ДОБАВЛЯЕМ ПОЛЯ В ТАБЛИЦУ user_main
ALTER TABLE user_main 
ADD COLUMN IF NOT EXISTS is_premium BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS premium_until TIMESTAMP,
ADD COLUMN IF NOT EXISTS referral_code VARCHAR(50) UNIQUE,
ADD COLUMN IF NOT EXISTS referred_by BIGINT REFERENCES user_main(user_id),
ADD COLUMN IF NOT EXISTS total_referrals INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS last_ad_shown TIMESTAMP;

-- Индекс для реферального кода
CREATE INDEX IF NOT EXISTS idx_user_main_referral_code ON user_main(referral_code);

-- 6. ФУНКЦИЯ АВТОМАТИЧЕСКОЙ ГЕНЕРАЦИИ РЕФЕРАЛЬНОГО КОДА
CREATE OR REPLACE FUNCTION generate_referral_code(p_user_id BIGINT)
RETURNS VARCHAR AS $$
DECLARE
    v_code VARCHAR(50);
BEGIN
    -- Генерируем код формата: REF + user_id + случайные 4 символа
    v_code := 'REF' || p_user_id || UPPER(SUBSTRING(MD5(RANDOM()::TEXT) FROM 1 FOR 4));
    RETURN v_code;
END;
$$ LANGUAGE plpgsql;

-- 7. ФУНКЦИЯ ПРОВЕРКИ ИСТЕЧЕНИЯ ПОДПИСКИ
CREATE OR REPLACE FUNCTION check_subscription_expiry()
RETURNS TRIGGER AS $$
BEGIN
    -- Если подписка истекла, деактивируем её
    IF NEW.end_date IS NOT NULL AND NEW.end_date < CURRENT_TIMESTAMP THEN
        NEW.is_active := FALSE;
        
        -- Обновляем статус премиум в user_main
        UPDATE user_main 
        SET is_premium = FALSE, premium_until = NULL
        WHERE user_id = NEW.user_id;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Триггер проверки истечения при UPDATE
CREATE TRIGGER trigger_check_subscription_expiry
BEFORE UPDATE ON subscriptions
FOR EACH ROW
EXECUTE FUNCTION check_subscription_expiry();

-- 8. ФУНКЦИЯ АКТИВАЦИИ РЕФЕРАЛА
CREATE OR REPLACE FUNCTION activate_referral(p_referred_id BIGINT)
RETURNS VOID AS $$
DECLARE
    v_referrer_id BIGINT;
    v_reward_days INTEGER := 7; -- 7 дней премиума за реферала
BEGIN
    -- Находим реферера
    SELECT referrer_id INTO v_referrer_id
    FROM referrals
    WHERE referred_id = p_referred_id AND status = 'pending'
    LIMIT 1;
    
    IF v_referrer_id IS NOT NULL THEN
        -- Обновляем статус реферала
        UPDATE referrals
        SET status = 'activated',
            activated_at = CURRENT_TIMESTAMP,
            reward_given = TRUE,
            reward_type = 'premium_days',
            reward_value = v_reward_days
        WHERE referred_id = p_referred_id;
        
        -- Добавляем премиум реферерру
        UPDATE user_main
        SET premium_until = COALESCE(premium_until, CURRENT_TIMESTAMP) + INTERVAL '7 days',
            is_premium = TRUE,
            total_referrals = total_referrals + 1
        WHERE user_id = v_referrer_id;
        
        -- Создаем запись о подписке
        INSERT INTO subscriptions (user_id, subscription_type, start_date, end_date, is_active, price)
        VALUES (v_referrer_id, 'referral_bonus', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + INTERVAL '7 days', TRUE, 0);
    END IF;
END;
$$ LANGUAGE plpgsql;

-- 9. ВСТАВЛЯЕМ НАЧАЛЬНЫЕ ДАННЫЕ (для существующих пользователей)
-- Даем всем существующим пользователям бесплатную подписку
INSERT INTO subscriptions (user_id, subscription_type, is_active)
SELECT user_id, 'free', TRUE
FROM user_main
ON CONFLICT DO NOTHING;

-- Генерируем реферальные коды для всех существующих пользователей
UPDATE user_main
SET referral_code = generate_referral_code(user_id)
WHERE referral_code IS NULL;

-- 10. КОММЕНТАРИИ К ТАБЛИЦАМ
COMMENT ON TABLE subscriptions IS 'Таблица подписок пользователей (бесплатные и платные)';
COMMENT ON TABLE referrals IS 'Таблица реферальных связей между пользователями';
COMMENT ON TABLE advertisements IS 'Таблица рекламных материалов для показа бесплатным пользователям';
COMMENT ON TABLE ad_views IS 'Таблица просмотров рекламы для контроля частоты показа';

-- ============================================
-- СТАТИСТИКА И ОТЧЕТЫ
-- ============================================

-- Представление: Активные премиум пользователи
CREATE OR REPLACE VIEW v_premium_users AS
SELECT 
    um.user_id,
    um.user_name,
    um.is_premium,
    um.premium_until,
    s.subscription_type,
    s.start_date,
    s.end_date
FROM user_main um
LEFT JOIN subscriptions s ON um.user_id = s.user_id AND s.is_active = TRUE
WHERE um.is_premium = TRUE;

-- Представление: Статистика рефералов
CREATE OR REPLACE VIEW v_referral_stats AS
SELECT 
    r.referrer_id,
    um.user_name AS referrer_name,
    COUNT(r.id) AS total_referred,
    COUNT(CASE WHEN r.status = 'activated' THEN 1 END) AS activated_count,
    COUNT(CASE WHEN r.reward_given THEN 1 END) AS rewarded_count
FROM referrals r
LEFT JOIN user_main um ON r.referrer_id = um.user_id
GROUP BY r.referrer_id, um.user_name;

-- Представление: Статистика рекламы
CREATE OR REPLACE VIEW v_ad_performance AS
SELECT 
    a.id,
    a.title,
    a.impressions_count,
    a.clicks_count,
    CASE 
        WHEN a.impressions_count > 0 
        THEN ROUND((a.clicks_count::DECIMAL / a.impressions_count) * 100, 2)
        ELSE 0 
    END AS ctr_percentage,
    COUNT(av.id) AS total_views,
    a.created_at
FROM advertisements a
LEFT JOIN ad_views av ON a.id = av.ad_id
GROUP BY a.id, a.title, a.impressions_count, a.clicks_count, a.created_at;

-- ============================================
-- ЗАВЕРШЕНИЕ МИГРАЦИИ
-- ============================================

COMMIT;

SELECT 'Миграция 006 успешно применена! Реферальная система и монетизация настроены.' AS status;


