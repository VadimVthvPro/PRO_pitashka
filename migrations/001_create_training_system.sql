-- ============================================
-- Migration: Create Training System v2.0
-- Создание новой системы управления тренировками
-- ============================================

-- Выполните этот файл для обновления БД:
-- psql -U postgres -d propitashka -f migrations/001_create_training_system.sql

\echo '=== Начало миграции системы тренировок ==='

-- ============================================
-- 1. Создание таблицы типов тренировок
-- ============================================

\echo 'Создание таблицы training_types...'
CREATE TABLE IF NOT EXISTS training_types (
    id SERIAL PRIMARY KEY,
    -- Названия на разных языках
    name_ru VARCHAR(255) NOT NULL,
    name_en VARCHAR(255) NOT NULL,
    name_de VARCHAR(255) NOT NULL,
    name_fr VARCHAR(255) NOT NULL,
    name_es VARCHAR(255) NOT NULL,
    
    -- Базовый коэффициент расхода калорий (ккал/кг/час)
    base_coefficient NUMERIC(5, 2) NOT NULL,
    
    -- Эмодзи для визуализации
    emoji VARCHAR(10),
    
    -- Описание тренировки
    description_ru TEXT,
    description_en TEXT,
    description_de TEXT,
    description_fr TEXT,
    description_es TEXT,
    
    -- Служебные поля
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Индекс для быстрого поиска
    CONSTRAINT unique_training_name_ru UNIQUE(name_ru)
);

-- Индексы для быстрого поиска по активным тренировкам
CREATE INDEX IF NOT EXISTS idx_training_types_active ON training_types(is_active);
CREATE INDEX IF NOT EXISTS idx_training_types_created ON training_types(created_at);

COMMENT ON TABLE training_types IS 'Типы тренировок с мультиязычной поддержкой';
COMMENT ON COLUMN training_types.base_coefficient IS 'Базовый коэффициент расхода калорий в ккал на кг веса в час';

-- ============================================
-- 2. Создание таблицы коэффициентов
-- ============================================

\echo 'Создание таблицы training_coefficients...'
CREATE TABLE IF NOT EXISTS training_coefficients (
    id SERIAL PRIMARY KEY,
    training_type_id INTEGER NOT NULL REFERENCES training_types(id) ON DELETE CASCADE,
    
    -- Модификаторы по полу (множители)
    gender_male_modifier NUMERIC(4, 3) DEFAULT 1.0,
    gender_female_modifier NUMERIC(4, 3) DEFAULT 0.85,
    
    -- Модификаторы по возрастным группам
    age_18_25_modifier NUMERIC(4, 3) DEFAULT 1.0,
    age_26_35_modifier NUMERIC(4, 3) DEFAULT 0.95,
    age_36_45_modifier NUMERIC(4, 3) DEFAULT 0.90,
    age_46_55_modifier NUMERIC(4, 3) DEFAULT 0.85,
    age_56_plus_modifier NUMERIC(4, 3) DEFAULT 0.80,
    
    -- Модификаторы по весовым категориям (кг)
    weight_under_60_modifier NUMERIC(4, 3) DEFAULT 0.90,
    weight_60_70_modifier NUMERIC(4, 3) DEFAULT 1.0,
    weight_71_80_modifier NUMERIC(4, 3) DEFAULT 1.05,
    weight_81_90_modifier NUMERIC(4, 3) DEFAULT 1.10,
    weight_91_100_modifier NUMERIC(4, 3) DEFAULT 1.15,
    weight_over_100_modifier NUMERIC(4, 3) DEFAULT 1.20,
    
    -- Модификаторы по росту (см)
    height_under_160_modifier NUMERIC(4, 3) DEFAULT 0.95,
    height_160_175_modifier NUMERIC(4, 3) DEFAULT 1.0,
    height_over_175_modifier NUMERIC(4, 3) DEFAULT 1.05,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT unique_training_coefficients UNIQUE(training_type_id)
);

COMMENT ON TABLE training_coefficients IS 'Коэффициенты корректировки расхода калорий для разных параметров пользователя';

-- ============================================
-- 3. Модификация таблицы user_training
-- ============================================

\echo 'Модификация таблицы user_training...'

-- Добавляем новые колонки
ALTER TABLE user_training 
ADD COLUMN IF NOT EXISTS training_type_id INTEGER REFERENCES training_types(id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS training_name VARCHAR(255),
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- Создаем индексы
CREATE INDEX IF NOT EXISTS idx_user_training_type ON user_training(training_type_id);
CREATE INDEX IF NOT EXISTS idx_user_training_name ON user_training(training_name);

COMMENT ON COLUMN user_training.training_type_id IS 'ID типа тренировки из справочника';
COMMENT ON COLUMN user_training.training_name IS 'Название тренировки на языке пользователя (для истории)';
COMMENT ON COLUMN user_training.tren_time IS 'Длительность тренировки в минутах';
COMMENT ON COLUMN user_training.training_cal IS 'Количество сожженных калорий';

-- ============================================
-- 4. Заполнение таблицы training_types
-- ============================================

\echo 'Заполнение справочника тренировок...'

INSERT INTO training_types (
    name_ru, name_en, name_de, name_fr, name_es,
    base_coefficient, emoji, description_ru, description_en
) VALUES 
-- Кардио тренировки
('Бег', 'Running', 'Laufen', 'Course', 'Correr', 
 8.5, '🏃', 'Бег на средней скорости', 'Running at moderate pace'),

('Быстрый бег', 'Fast Running', 'Schnelles Laufen', 'Course rapide', 'Carrera rápida', 
 12.0, '🏃‍♂️', 'Интенсивный бег', 'High-intensity running'),

('Ходьба', 'Walking', 'Gehen', 'Marche', 'Caminar', 
 3.5, '🚶', 'Ходьба в умеренном темпе', 'Walking at moderate pace'),

('Быстрая ходьба', 'Brisk Walking', 'Schnelles Gehen', 'Marche rapide', 'Caminar rápido', 
 5.0, '🚶‍♂️', 'Быстрая спортивная ходьба', 'Brisk power walking'),

('Велосипед', 'Cycling', 'Radfahren', 'Cyclisme', 'Ciclismo', 
 7.0, '🚴', 'Езда на велосипеде средней интенсивности', 'Moderate cycling'),

('Плавание', 'Swimming', 'Schwimmen', 'Natation', 'Natación', 
 9.0, '🏊', 'Плавание различными стилями', 'Swimming various strokes'),

-- Силовые тренировки
('Тренажерный зал', 'Gym Workout', 'Fitnessstudio', 'Salle de sport', 'Gimnasio', 
 6.5, '💪', 'Силовые упражнения в зале', 'Strength training in gym'),

('Кроссфит', 'CrossFit', 'CrossFit', 'CrossFit', 'CrossFit', 
 10.0, '🏋️', 'Высокоинтенсивные функциональные тренировки', 'High-intensity functional training'),

('Упражнения с весом тела', 'Bodyweight Exercises', 'Körpergewichtsübungen', 'Exercices au poids du corps', 'Ejercicios con peso corporal', 
 5.5, '🤸', 'Отжимания, подтягивания, приседания', 'Push-ups, pull-ups, squats'),

-- Групповые занятия
('Аэробика', 'Aerobics', 'Aerobic', 'Aérobie', 'Aeróbicos', 
 7.5, '🤾', 'Ритмичные аэробные упражнения', 'Rhythmic aerobic exercises'),

('Зумба', 'Zumba', 'Zumba', 'Zumba', 'Zumba', 
 7.0, '💃', 'Танцевальная фитнес-программа', 'Dance fitness program'),

('Йога', 'Yoga', 'Yoga', 'Yoga', 'Yoga', 
 3.0, '🧘', 'Практика йоги для гибкости и баланса', 'Yoga practice for flexibility'),

('Пилатес', 'Pilates', 'Pilates', 'Pilates', 'Pilates', 
 4.0, '🧘‍♀️', 'Упражнения для укрепления мышц кора', 'Core strengthening exercises'),

-- Активный отдых
('Футбол', 'Football/Soccer', 'Fußball', 'Football', 'Fútbol', 
 9.0, '⚽', 'Игра в футбол', 'Playing soccer'),

('Баскетбол', 'Basketball', 'Basketball', 'Basket-ball', 'Baloncesto', 
 8.5, '🏀', 'Игра в баскетбол', 'Playing basketball'),

('Теннис', 'Tennis', 'Tennis', 'Tennis', 'Tenis', 
 7.5, '🎾', 'Игра в теннис', 'Playing tennis'),

('Танцы', 'Dancing', 'Tanzen', 'Danse', 'Bailar', 
 6.0, '💃', 'Различные виды танцев', 'Various types of dancing'),

-- Боевые искусства
('Бокс', 'Boxing', 'Boxen', 'Boxe', 'Boxeo', 
 10.5, '🥊', 'Тренировка по боксу', 'Boxing training'),

('Единоборства', 'Martial Arts', 'Kampfsport', 'Arts martiaux', 'Artes marciales', 
 9.5, '🥋', 'Различные виды единоборств', 'Various martial arts'),

-- Другое
('Растяжка', 'Stretching', 'Dehnung', 'Étirements', 'Estiramientos', 
 2.5, '🤸‍♀️', 'Упражнения на растяжку и гибкость', 'Flexibility and stretching exercises')

ON CONFLICT (name_ru) DO NOTHING;

\echo 'Добавлено 20 типов тренировок';

-- ============================================
-- 5. Заполнение таблицы коэффициентов
-- ============================================

\echo 'Заполнение коэффициентов для тренировок...'

-- Создаем коэффициенты для каждой тренировки
INSERT INTO training_coefficients (
    training_type_id,
    gender_male_modifier, gender_female_modifier,
    age_18_25_modifier, age_26_35_modifier, age_36_45_modifier, age_46_55_modifier, age_56_plus_modifier,
    weight_under_60_modifier, weight_60_70_modifier, weight_71_80_modifier, weight_81_90_modifier, weight_91_100_modifier, weight_over_100_modifier,
    height_under_160_modifier, height_160_175_modifier, height_over_175_modifier
)
SELECT 
    id,
    -- Базовые коэффициенты для всех тренировок (можно настроить индивидуально)
    CASE 
        WHEN base_coefficient >= 9.0 THEN 1.10  -- Для интенсивных тренировок мужчины сжигают больше
        ELSE 1.0
    END as gender_male_modifier,
    
    CASE 
        WHEN base_coefficient >= 9.0 THEN 0.85
        ELSE 0.88
    END as gender_female_modifier,
    
    -- Возрастные коэффициенты
    1.05, 1.0, 0.95, 0.90, 0.85,
    
    -- Весовые коэффициенты
    0.92, 1.0, 1.05, 1.08, 1.12, 1.18,
    
    -- Ростовые коэффициенты
    0.96, 1.0, 1.03
FROM training_types
ON CONFLICT (training_type_id) DO NOTHING;

\echo 'Коэффициенты заполнены для всех тренировок';

-- ============================================
-- 6. Создание функции для расчета калорий
-- ============================================

\echo 'Создание вспомогательных функций...';

-- Функция определения возрастной группы
CREATE OR REPLACE FUNCTION get_age_group_modifier(p_age INTEGER, p_training_type_id INTEGER)
RETURNS NUMERIC AS $$
DECLARE
    v_modifier NUMERIC(4, 3);
BEGIN
    SELECT CASE 
        WHEN p_age BETWEEN 18 AND 25 THEN age_18_25_modifier
        WHEN p_age BETWEEN 26 AND 35 THEN age_26_35_modifier
        WHEN p_age BETWEEN 36 AND 45 THEN age_36_45_modifier
        WHEN p_age BETWEEN 46 AND 55 THEN age_46_55_modifier
        ELSE age_56_plus_modifier
    END INTO v_modifier
    FROM training_coefficients
    WHERE training_type_id = p_training_type_id;
    
    RETURN COALESCE(v_modifier, 1.0);
END;
$$ LANGUAGE plpgsql;

-- Функция определения весовой категории
CREATE OR REPLACE FUNCTION get_weight_category_modifier(p_weight NUMERIC, p_training_type_id INTEGER)
RETURNS NUMERIC AS $$
DECLARE
    v_modifier NUMERIC(4, 3);
BEGIN
    SELECT CASE 
        WHEN p_weight < 60 THEN weight_under_60_modifier
        WHEN p_weight BETWEEN 60 AND 70 THEN weight_60_70_modifier
        WHEN p_weight BETWEEN 71 AND 80 THEN weight_71_80_modifier
        WHEN p_weight BETWEEN 81 AND 90 THEN weight_81_90_modifier
        WHEN p_weight BETWEEN 91 AND 100 THEN weight_91_100_modifier
        ELSE weight_over_100_modifier
    END INTO v_modifier
    FROM training_coefficients
    WHERE training_type_id = p_training_type_id;
    
    RETURN COALESCE(v_modifier, 1.0);
END;
$$ LANGUAGE plpgsql;

-- Функция определения категории роста
CREATE OR REPLACE FUNCTION get_height_category_modifier(p_height NUMERIC, p_training_type_id INTEGER)
RETURNS NUMERIC AS $$
DECLARE
    v_modifier NUMERIC(4, 3);
BEGIN
    SELECT CASE 
        WHEN p_height < 160 THEN height_under_160_modifier
        WHEN p_height BETWEEN 160 AND 175 THEN height_160_175_modifier
        ELSE height_over_175_modifier
    END INTO v_modifier
    FROM training_coefficients
    WHERE training_type_id = p_training_type_id;
    
    RETURN COALESCE(v_modifier, 1.0);
END;
$$ LANGUAGE plpgsql;

-- Функция получения гендерного модификатора
CREATE OR REPLACE FUNCTION get_gender_modifier(p_gender VARCHAR, p_training_type_id INTEGER)
RETURNS NUMERIC AS $$
DECLARE
    v_modifier NUMERIC(4, 3);
BEGIN
    SELECT CASE 
        WHEN LOWER(p_gender) IN ('мужской', 'male', 'männlich', 'homme', 'masculino', 'м', 'm') 
            THEN gender_male_modifier
        ELSE gender_female_modifier
    END INTO v_modifier
    FROM training_coefficients
    WHERE training_type_id = p_training_type_id;
    
    RETURN COALESCE(v_modifier, 1.0);
END;
$$ LANGUAGE plpgsql;

-- Главная функция расчета калорий
CREATE OR REPLACE FUNCTION calculate_training_calories(
    p_training_type_id INTEGER,
    p_user_id BIGINT,
    p_duration_minutes INTEGER
)
RETURNS NUMERIC AS $$
DECLARE
    v_base_coef NUMERIC(5, 2);
    v_weight NUMERIC(5, 2);
    v_height NUMERIC(5, 2);
    v_age INTEGER;
    v_gender VARCHAR(50);
    
    v_gender_mod NUMERIC(4, 3);
    v_age_mod NUMERIC(4, 3);
    v_weight_mod NUMERIC(4, 3);
    v_height_mod NUMERIC(4, 3);
    
    v_calories NUMERIC(7, 3);
BEGIN
    -- Получаем базовый коэффициент тренировки
    SELECT base_coefficient INTO v_base_coef
    FROM training_types
    WHERE id = p_training_type_id;
    
    -- Получаем параметры пользователя
    SELECT 
        uh.weight,
        uh.height,
        EXTRACT(YEAR FROM AGE(TO_DATE(um.date_of_birth, 'DD-MM-YYYY')))::INTEGER,
        um.user_sex
    INTO v_weight, v_height, v_age, v_gender
    FROM user_health uh
    JOIN user_main um ON um.user_id = uh.user_id
    WHERE uh.user_id = p_user_id
    ORDER BY uh.date DESC
    LIMIT 1;
    
    -- Получаем модификаторы
    v_gender_mod := get_gender_modifier(v_gender, p_training_type_id);
    v_age_mod := get_age_group_modifier(v_age, p_training_type_id);
    v_weight_mod := get_weight_category_modifier(v_weight, p_training_type_id);
    v_height_mod := get_height_category_modifier(v_height, p_training_type_id);
    
    -- Расчет: (базовый_коэф * вес * (длительность/60)) * все_модификаторы
    v_calories := (v_base_coef * v_weight * (p_duration_minutes / 60.0)) 
                  * v_gender_mod * v_age_mod * v_weight_mod * v_height_mod;
    
    RETURN ROUND(v_calories, 3);
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION calculate_training_calories IS 'Расчет сожженных калорий с учетом всех параметров пользователя';

-- ============================================
-- 7. Создание представлений для админки
-- ============================================

\echo 'Создание представлений...';

CREATE OR REPLACE VIEW v_training_statistics AS
SELECT 
    tt.id as training_type_id,
    tt.name_ru as training_name,
    tt.emoji,
    COUNT(ut.id) as total_sessions,
    COUNT(DISTINCT ut.user_id) as unique_users,
    ROUND(AVG(ut.tren_time), 2) as avg_duration_minutes,
    ROUND(AVG(ut.training_cal), 2) as avg_calories,
    ROUND(SUM(ut.training_cal), 2) as total_calories_burned
FROM training_types tt
LEFT JOIN user_training ut ON ut.training_type_id = tt.id
WHERE tt.is_active = TRUE
GROUP BY tt.id, tt.name_ru, tt.emoji
ORDER BY total_sessions DESC;

COMMENT ON VIEW v_training_statistics IS 'Статистика использования тренировок';

-- ============================================
-- 8. Завершение миграции
-- ============================================

\echo '=== Миграция завершена успешно! ==='
\echo '';
\echo 'Создано:';
\echo '  - Таблица training_types с 20 тренировками';
\echo '  - Таблица training_coefficients с коэффициентами';
\echo '  - Обновлена таблица user_training';
\echo '  - Созданы функции расчета калорий';
\echo '  - Созданы представления для статистики';
\echo '';
\echo 'Для просмотра тренировок: SELECT * FROM training_types;';
\echo 'Для просмотра статистики: SELECT * FROM v_training_statistics;';


