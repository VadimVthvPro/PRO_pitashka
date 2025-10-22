-- ================================================
-- Database Initialization Script for PROpitashka Bot
-- ================================================
-- This script creates all necessary tables and indexes
-- Run this script once before starting the bot
-- ================================================

-- Create database (if running as superuser)
-- CREATE DATABASE propitashka;
-- \c propitashka

-- ================================================
-- 1. USER LANGUAGE PREFERENCES
-- ================================================

CREATE TABLE IF NOT EXISTS user_lang (
    user_id BIGINT PRIMARY KEY,
    lang VARCHAR(5) NOT NULL DEFAULT 'ru',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_lang_user_id ON user_lang(user_id);

COMMENT ON TABLE user_lang IS 'Stores user language preferences';
COMMENT ON COLUMN user_lang.lang IS 'Language code: ru, en, de, fr, es';


-- ================================================
-- 2. USER MAIN DATA
-- ================================================

CREATE TABLE IF NOT EXISTS user_main (
    user_id BIGINT PRIMARY KEY,
    user_name VARCHAR(255),
    user_sex VARCHAR(50),
    date_of_birth INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_main_user_id ON user_main(user_id);

COMMENT ON TABLE user_main IS 'Main user profile data';


-- ================================================
-- 3. USER HEALTH DATA
-- ================================================

CREATE TABLE IF NOT EXISTS user_health (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    imt DECIMAL(5,2),
    imt_str VARCHAR(100),
    cal DECIMAL(7,2),
    date DATE NOT NULL,
    weight DECIMAL(6,2),
    height DECIMAL(6,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, date)
);

CREATE INDEX IF NOT EXISTS idx_user_health_user_id ON user_health(user_id);
CREATE INDEX IF NOT EXISTS idx_user_health_date ON user_health(date);
CREATE INDEX IF NOT EXISTS idx_user_health_user_date ON user_health(user_id, date);

COMMENT ON TABLE user_health IS 'Daily health metrics for users';
COMMENT ON COLUMN user_health.imt IS 'Body Mass Index';
COMMENT ON COLUMN user_health.cal IS 'Daily calorie target';


-- ================================================
-- 4. USER GOALS AND AIMS
-- ================================================

CREATE TABLE IF NOT EXISTS user_aims (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    user_aim TEXT,
    daily_cal DECIMAL(7,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id)
);

CREATE INDEX IF NOT EXISTS idx_user_aims_user_id ON user_aims(user_id);

COMMENT ON TABLE user_aims IS 'User fitness and nutrition goals';


-- ================================================
-- 5. FOOD INTAKE LOG
-- ================================================

CREATE TABLE IF NOT EXISTS food (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    date DATE NOT NULL,
    name_of_food VARCHAR(255) NOT NULL,
    b DECIMAL(8,3),
    g DECIMAL(8,3),
    u DECIMAL(8,3),
    cal DECIMAL(8,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_food_user_id ON food(user_id);
CREATE INDEX IF NOT EXISTS idx_food_date ON food(date);
CREATE INDEX IF NOT EXISTS idx_food_user_date ON food(user_id, date);

COMMENT ON TABLE food IS 'User food intake log';
COMMENT ON COLUMN food.b IS 'Protein (grams)';
COMMENT ON COLUMN food.g IS 'Fat (grams)';
COMMENT ON COLUMN food.u IS 'Carbohydrates (grams)';
COMMENT ON COLUMN food.cal IS 'Calories';


-- ================================================
-- 6. TRAINING LOG
-- ================================================

CREATE TABLE IF NOT EXISTS user_training (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    date DATE NOT NULL,
    training_cal DECIMAL(8,2),
    tren_time INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_training_user_id ON user_training(user_id);
CREATE INDEX IF NOT EXISTS idx_training_date ON user_training(date);
CREATE INDEX IF NOT EXISTS idx_training_user_date ON user_training(user_id, date);

COMMENT ON TABLE user_training IS 'User training sessions log';
COMMENT ON COLUMN user_training.training_cal IS 'Calories burned';
COMMENT ON COLUMN user_training.tren_time IS 'Training duration in minutes';


-- ================================================
-- 7. WATER INTAKE LOG
-- ================================================

CREATE TABLE IF NOT EXISTS water (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    data DATE NOT NULL,
    count INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, data)
);

CREATE INDEX IF NOT EXISTS idx_water_user_id ON water(user_id);
CREATE INDEX IF NOT EXISTS idx_water_date ON water(data);
CREATE INDEX IF NOT EXISTS idx_water_user_date ON water(user_id, data);

COMMENT ON TABLE water IS 'Daily water intake tracking';
COMMENT ON COLUMN water.count IS 'Number of glasses (250ml each)';


-- ================================================
-- 8. BOT LOGS (for monitoring and debugging)
-- ================================================

CREATE TABLE IF NOT EXISTS bot_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    level VARCHAR(10) NOT NULL,
    logger_name VARCHAR(100),
    message TEXT NOT NULL,
    user_id BIGINT,
    username VARCHAR(100),
    function_name VARCHAR(100),
    line_number INTEGER,
    error_traceback TEXT
);

CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON bot_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_logs_level ON bot_logs(level);
CREATE INDEX IF NOT EXISTS idx_logs_user_id ON bot_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_logs_function ON bot_logs(function_name);

COMMENT ON TABLE bot_logs IS 'Bot activity and error logs';
COMMENT ON COLUMN bot_logs.level IS 'Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL';


-- ================================================
-- 9. CREATE TRIGGERS FOR updated_at
-- ================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for tables with updated_at
CREATE TRIGGER update_user_lang_updated_at 
    BEFORE UPDATE ON user_lang 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_main_updated_at 
    BEFORE UPDATE ON user_main 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_aims_updated_at 
    BEFORE UPDATE ON user_aims 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();


-- ================================================
-- 10. GRANT PERMISSIONS (adjust username as needed)
-- ================================================

-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO postgres;


-- ================================================
-- 11. VERIFY INSTALLATION
-- ================================================

-- Check all tables
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Count records in each table
SELECT 'user_lang' as table_name, COUNT(*) as records FROM user_lang
UNION ALL
SELECT 'user_main', COUNT(*) FROM user_main
UNION ALL
SELECT 'user_health', COUNT(*) FROM user_health
UNION ALL
SELECT 'user_aims', COUNT(*) FROM user_aims
UNION ALL
SELECT 'food', COUNT(*) FROM food
UNION ALL
SELECT 'user_training', COUNT(*) FROM user_training
UNION ALL
SELECT 'water', COUNT(*) FROM water
UNION ALL
SELECT 'bot_logs', COUNT(*) FROM bot_logs;


-- ================================================
-- SUCCESS MESSAGE
-- ================================================

DO $$
BEGIN
    RAISE NOTICE '============================================';
    RAISE NOTICE 'Database initialization completed successfully!';
    RAISE NOTICE 'All tables and indexes have been created.';
    RAISE NOTICE '============================================';
END $$;

