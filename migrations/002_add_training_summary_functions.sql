-- Функции для сводки тренировок

-- ============================================
-- Функция: Получить список тренировок за день
-- ============================================
CREATE OR REPLACE FUNCTION get_training_summary_day(p_user_id BIGINT, p_date DATE)
RETURNS TABLE (
    training_name VARCHAR,
    duration INTEGER,
    calories DECIMAL(10,3),
    training_time TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ut.training_name,
        ut.duration,
        ut.calories_burned,
        ut.training_date
    FROM user_training ut
    WHERE ut.user_id = p_user_id 
        AND DATE(ut.training_date) = p_date
    ORDER BY ut.training_date;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- Функция: Получить топ-5 тренировок за месяц
-- ============================================
CREATE OR REPLACE FUNCTION get_training_top5_month(p_user_id BIGINT, p_year INTEGER, p_month INTEGER)
RETURNS TABLE (
    training_name VARCHAR,
    workout_count BIGINT,
    avg_duration DECIMAL(10,1),
    total_calories DECIMAL(10,1)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ut.training_name,
        COUNT(*)::BIGINT as workout_count,
        ROUND(AVG(ut.duration), 1) as avg_duration,
        ROUND(SUM(ut.calories_burned), 1) as total_calories
    FROM user_training ut
    WHERE ut.user_id = p_user_id 
        AND EXTRACT(YEAR FROM ut.training_date) = p_year
        AND EXTRACT(MONTH FROM ut.training_date) = p_month
    GROUP BY ut.training_name
    ORDER BY workout_count DESC, total_calories DESC
    LIMIT 5;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- Функция: Получить топ-5 тренировок за год
-- ============================================
CREATE OR REPLACE FUNCTION get_training_top5_year(p_user_id BIGINT, p_year INTEGER)
RETURNS TABLE (
    training_name VARCHAR,
    workout_count BIGINT,
    avg_duration DECIMAL(10,1),
    total_calories DECIMAL(10,1)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ut.training_name,
        COUNT(*)::BIGINT as workout_count,
        ROUND(AVG(ut.duration), 1) as avg_duration,
        ROUND(SUM(ut.calories_burned), 1) as total_calories
    FROM user_training ut
    WHERE ut.user_id = p_user_id 
        AND EXTRACT(YEAR FROM ut.training_date) = p_year
    GROUP BY ut.training_name
    ORDER BY workout_count DESC, total_calories DESC
    LIMIT 5;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- Функция: Получить статистику тренировок за период
-- ============================================
CREATE OR REPLACE FUNCTION get_training_stats_period(
    p_user_id BIGINT, 
    p_start_date DATE, 
    p_end_date DATE
)
RETURNS TABLE (
    total_workouts BIGINT,
    total_duration INTEGER,
    total_calories DECIMAL(10,1),
    avg_duration DECIMAL(10,1),
    avg_calories DECIMAL(10,1)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::BIGINT as total_workouts,
        SUM(ut.duration)::INTEGER as total_duration,
        ROUND(SUM(ut.calories_burned), 1) as total_calories,
        ROUND(AVG(ut.duration), 1) as avg_duration,
        ROUND(AVG(ut.calories_burned), 1) as avg_calories
    FROM user_training ut
    WHERE ut.user_id = p_user_id 
        AND DATE(ut.training_date) BETWEEN p_start_date AND p_end_date;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- Комментарии к функциям
-- ============================================
COMMENT ON FUNCTION get_training_summary_day IS 'Получить список всех тренировок за конкретный день';
COMMENT ON FUNCTION get_training_top5_month IS 'Получить топ-5 самых популярных тренировок за месяц';
COMMENT ON FUNCTION get_training_top5_year IS 'Получить топ-5 самых популярных тренировок за год';
COMMENT ON FUNCTION get_training_stats_period IS 'Получить статистику тренировок за произвольный период';

