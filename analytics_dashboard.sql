-- ============================================
-- Analytics Dashboard Queries
-- PROpitashka - Key Metrics
-- ============================================

-- ============================================
-- 1. DAU (Daily Active Users) - Last 7 Days
-- ============================================
-- Показывает количество уникальных активных пользователей за последние 7 дней
SELECT 
    date::date AS day,
    COUNT(DISTINCT user_id) AS daily_active_users
FROM (
    SELECT user_id, date FROM food
    UNION ALL
    SELECT user_id, date FROM user_training
    UNION ALL
    SELECT user_id, data AS date FROM water
) AS user_activity
WHERE date >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY date::date
ORDER BY day DESC;

-- ============================================
-- 2. MAU (Monthly Active Users) - Current Month
-- ============================================
-- Количество уникальных активных пользователей в текущем месяце
SELECT 
    COUNT(DISTINCT user_id) AS monthly_active_users
FROM (
    SELECT user_id, date FROM food
    WHERE date >= DATE_TRUNC('month', CURRENT_DATE)
    UNION ALL
    SELECT user_id, date FROM user_training
    WHERE date >= DATE_TRUNC('month', CURRENT_DATE)
    UNION ALL
    SELECT user_id, data AS date FROM water
    WHERE data >= DATE_TRUNC('month', CURRENT_DATE)
) AS user_activity;

-- ============================================
-- 3. New Users Registration - Last 30 Days
-- ============================================
-- Динамика регистрации новых пользователей за последние 30 дней
SELECT 
    created_at::date AS registration_date,
    COUNT(*) AS new_users
FROM user_main
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY created_at::date
ORDER BY registration_date DESC;

-- ============================================
-- 4. User Activation Rate
-- ============================================
-- Процент пользователей, которые выполнили первое ключевое действие (добавили еду)
SELECT 
    COUNT(DISTINCT um.user_id) AS total_users,
    COUNT(DISTINCT f.user_id) AS activated_users,
    ROUND(
        (COUNT(DISTINCT f.user_id)::numeric / NULLIF(COUNT(DISTINCT um.user_id), 0)) * 100, 
        2
    ) AS activation_rate_percent
FROM user_main um
LEFT JOIN food f ON um.user_id = f.user_id
WHERE um.created_at >= CURRENT_DATE - INTERVAL '30 days';

-- ============================================
-- 5. 1-Day Retention Rate
-- ============================================
-- Процент пользователей, вернувшихся на следующий день после регистрации
WITH user_first_action AS (
    SELECT 
        um.user_id,
        um.created_at::date AS registration_date,
        MIN(f.date) AS first_food_date
    FROM user_main um
    LEFT JOIN food f ON um.user_id = f.user_id
    WHERE um.created_at >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY um.user_id, um.created_at::date
)
SELECT 
    COUNT(*) AS total_new_users,
    COUNT(CASE WHEN first_food_date = registration_date + 1 THEN 1 END) AS returned_next_day,
    ROUND(
        (COUNT(CASE WHEN first_food_date = registration_date + 1 THEN 1 END)::numeric / NULLIF(COUNT(*), 0)) * 100,
        2
    ) AS one_day_retention_percent
FROM user_first_action;

-- ============================================
-- 6. 7-Day Retention Rate
-- ============================================
-- Процент пользователей, активных на 7-й день после регистрации
WITH user_cohort AS (
    SELECT 
        um.user_id,
        um.created_at::date AS registration_date
    FROM user_main um
    WHERE um.created_at >= CURRENT_DATE - INTERVAL '14 days'
        AND um.created_at < CURRENT_DATE - INTERVAL '7 days'
),
user_activity_day7 AS (
    SELECT DISTINCT 
        uc.user_id,
        uc.registration_date
    FROM user_cohort uc
    INNER JOIN (
        SELECT user_id, date FROM food
        UNION ALL
        SELECT user_id, date FROM user_training
        UNION ALL
        SELECT user_id, data AS date FROM water
    ) AS activity 
        ON uc.user_id = activity.user_id 
        AND activity.date = uc.registration_date + 7
)
SELECT 
    COUNT(DISTINCT uc.user_id) AS total_cohort_users,
    COUNT(DISTINCT ua7.user_id) AS active_on_day7,
    ROUND(
        (COUNT(DISTINCT ua7.user_id)::numeric / NULLIF(COUNT(DISTINCT uc.user_id), 0)) * 100,
        2
    ) AS seven_day_retention_percent
FROM user_cohort uc
LEFT JOIN user_activity_day7 ua7 ON uc.user_id = ua7.user_id;

-- ============================================
-- 7. Average Actions Per User (Last 30 Days)
-- ============================================
-- Среднее количество действий на одного пользователя
WITH user_actions AS (
    SELECT 
        user_id,
        COUNT(*) AS action_count
    FROM (
        SELECT user_id, date FROM food WHERE date >= CURRENT_DATE - INTERVAL '30 days'
        UNION ALL
        SELECT user_id, date FROM user_training WHERE date >= CURRENT_DATE - INTERVAL '30 days'
        UNION ALL
        SELECT user_id, data AS date FROM water WHERE data >= CURRENT_DATE - INTERVAL '30 days'
    ) AS all_actions
    GROUP BY user_id
)
SELECT 
    COUNT(DISTINCT user_id) AS active_users,
    SUM(action_count) AS total_actions,
    ROUND(AVG(action_count), 2) AS avg_actions_per_user
FROM user_actions;

-- ============================================
-- 8. Referral Source Analysis
-- ============================================
-- Эффективность различных источников привлечения
SELECT 
    COALESCE(utm_source, 'direct') AS traffic_source,
    COUNT(DISTINCT user_id) AS total_users,
    COUNT(DISTINCT CASE 
        WHEN user_id IN (SELECT DISTINCT user_id FROM food) 
        THEN user_id 
    END) AS activated_users,
    ROUND(
        (COUNT(DISTINCT CASE WHEN user_id IN (SELECT DISTINCT user_id FROM food) THEN user_id END)::numeric 
        / NULLIF(COUNT(DISTINCT user_id), 0)) * 100,
        2
    ) AS activation_rate_percent
FROM user_main
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY utm_source
ORDER BY total_users DESC;

-- ============================================
-- 9. Top Referral Codes
-- ============================================
-- Самые успешные реферальные коды
SELECT 
    ref_code,
    COUNT(DISTINCT user_id) AS referred_users,
    COUNT(DISTINCT CASE 
        WHEN user_id IN (SELECT DISTINCT user_id FROM food) 
        THEN user_id 
    END) AS activated_users
FROM user_main
WHERE ref_code IS NOT NULL
    AND created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY ref_code
ORDER BY referred_users DESC
LIMIT 10;

-- ============================================
-- 10. User Engagement Summary
-- ============================================
-- Общая сводка активности пользователей за последний месяц
SELECT 
    'Food Logs' AS metric,
    COUNT(*) AS total,
    COUNT(DISTINCT user_id) AS unique_users,
    ROUND(AVG(cal), 2) AS avg_calories
FROM food
WHERE date >= CURRENT_DATE - INTERVAL '30 days'

UNION ALL

SELECT 
    'Training Sessions' AS metric,
    COUNT(*) AS total,
    COUNT(DISTINCT user_id) AS unique_users,
    ROUND(AVG(training_cal), 2) AS avg_value
FROM user_training
WHERE date >= CURRENT_DATE - INTERVAL '30 days'

UNION ALL

SELECT 
    'Water Logs' AS metric,
    SUM(count) AS total,
    COUNT(DISTINCT user_id) AS unique_users,
    ROUND(AVG(count), 2) AS avg_glasses
FROM water
WHERE data >= CURRENT_DATE - INTERVAL '30 days';

-- ============================================
-- 11. Cohort Analysis - Weekly Retention
-- ============================================
-- Когортный анализ по неделям регистрации
WITH weekly_cohorts AS (
    SELECT 
        user_id,
        DATE_TRUNC('week', created_at)::date AS cohort_week
    FROM user_main
    WHERE created_at >= CURRENT_DATE - INTERVAL '8 weeks'
),
cohort_activity AS (
    SELECT 
        wc.cohort_week,
        COUNT(DISTINCT wc.user_id) AS cohort_size,
        COUNT(DISTINCT CASE 
            WHEN activity.date >= wc.cohort_week + INTERVAL '1 week' 
            AND activity.date < wc.cohort_week + INTERVAL '2 weeks'
            THEN wc.user_id 
        END) AS week_1_retention,
        COUNT(DISTINCT CASE 
            WHEN activity.date >= wc.cohort_week + INTERVAL '2 weeks'
            AND activity.date < wc.cohort_week + INTERVAL '3 weeks'
            THEN wc.user_id 
        END) AS week_2_retention,
        COUNT(DISTINCT CASE 
            WHEN activity.date >= wc.cohort_week + INTERVAL '3 weeks'
            AND activity.date < wc.cohort_week + INTERVAL '4 weeks'
            THEN wc.user_id 
        END) AS week_3_retention
    FROM weekly_cohorts wc
    LEFT JOIN (
        SELECT user_id, date FROM food
        UNION ALL
        SELECT user_id, date FROM user_training
        UNION ALL
        SELECT user_id, data AS date FROM water
    ) AS activity ON wc.user_id = activity.user_id
    GROUP BY wc.cohort_week
)
SELECT 
    cohort_week,
    cohort_size,
    week_1_retention,
    ROUND((week_1_retention::numeric / NULLIF(cohort_size, 0)) * 100, 2) AS week_1_percent,
    week_2_retention,
    ROUND((week_2_retention::numeric / NULLIF(cohort_size, 0)) * 100, 2) AS week_2_percent,
    week_3_retention,
    ROUND((week_3_retention::numeric / NULLIF(cohort_size, 0)) * 100, 2) AS week_3_percent
FROM cohort_activity
ORDER BY cohort_week DESC;

-- ============================================
-- End of Analytics Dashboard
-- ============================================









