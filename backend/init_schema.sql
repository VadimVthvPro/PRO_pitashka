--
-- PostgreSQL database dump
--


-- Dumped from database version 17.2
-- Dumped by pg_dump version 17.9 (Homebrew)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: -
--

-- *not* creating schema, since initdb creates it


--
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON SCHEMA public IS '';


--
-- Name: activate_referral(bigint); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.activate_referral(p_referred_id bigint) RETURNS void
    LANGUAGE plpgsql
    AS $$
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
$$;


--
-- Name: calculate_training_calories(integer, bigint, integer); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.calculate_training_calories(p_training_type_id integer, p_user_id bigint, p_duration_minutes integer) RETURNS numeric
    LANGUAGE plpgsql
    AS $$
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
            SELECT base_coefficient INTO v_base_coef
            FROM training_types WHERE id = p_training_type_id;

            SELECT uh.weight, uh.height,
                   EXTRACT(YEAR FROM AGE(um.date_of_birth))::INTEGER,
                   um.user_sex
            INTO v_weight, v_height, v_age, v_gender
            FROM user_health uh
            JOIN user_main um ON um.user_id = uh.user_id
            WHERE uh.user_id = p_user_id
            ORDER BY uh.date DESC LIMIT 1;

            v_gender_mod := get_gender_modifier(v_gender, p_training_type_id);
            v_age_mod := get_age_group_modifier(v_age, p_training_type_id);
            v_weight_mod := get_weight_category_modifier(v_weight, p_training_type_id);
            v_height_mod := get_height_category_modifier(v_height, p_training_type_id);

            v_calories := (v_base_coef * v_weight * (p_duration_minutes / 60.0))
                          * v_gender_mod * v_age_mod * v_weight_mod * v_height_mod;
            RETURN ROUND(v_calories, 3);
        END;
        $$;


--
-- Name: FUNCTION calculate_training_calories(p_training_type_id integer, p_user_id bigint, p_duration_minutes integer); Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON FUNCTION public.calculate_training_calories(p_training_type_id integer, p_user_id bigint, p_duration_minutes integer) IS 'Расчет сожженных калорий с учетом всех параметров пользователя';


--
-- Name: check_subscription_expiry(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.check_subscription_expiry() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
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
$$;


--
-- Name: generate_referral_code(bigint); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.generate_referral_code(p_user_id bigint) RETURNS character varying
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_code VARCHAR(50);
BEGIN
    -- Генерируем код формата: REF + user_id + случайные 4 символа
    v_code := 'REF' || p_user_id || UPPER(SUBSTRING(MD5(RANDOM()::TEXT) FROM 1 FOR 4));
    RETURN v_code;
END;
$$;


--
-- Name: get_age_group_modifier(integer, integer); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.get_age_group_modifier(p_age integer, p_training_type_id integer) RETURNS numeric
    LANGUAGE plpgsql
    AS $$
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
$$;


--
-- Name: get_gender_modifier(character varying, integer); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.get_gender_modifier(p_gender character varying, p_training_type_id integer) RETURNS numeric
    LANGUAGE plpgsql
    AS $$
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
$$;


--
-- Name: get_height_category_modifier(numeric, integer); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.get_height_category_modifier(p_height numeric, p_training_type_id integer) RETURNS numeric
    LANGUAGE plpgsql
    AS $$
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
$$;


--
-- Name: get_training_stats_period(bigint, date, date); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.get_training_stats_period(p_user_id bigint, p_start_date date, p_end_date date) RETURNS TABLE(total_workouts bigint, total_duration integer, total_calories numeric, avg_duration numeric, avg_calories numeric)
    LANGUAGE plpgsql
    AS $$
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
$$;


--
-- Name: FUNCTION get_training_stats_period(p_user_id bigint, p_start_date date, p_end_date date); Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON FUNCTION public.get_training_stats_period(p_user_id bigint, p_start_date date, p_end_date date) IS 'Получить статистику тренировок за произвольный период';


--
-- Name: get_training_summary_day(bigint, date); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.get_training_summary_day(p_user_id bigint, p_date date) RETURNS TABLE(training_name character varying, duration integer, calories numeric, training_time timestamp without time zone)
    LANGUAGE plpgsql
    AS $$
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
$$;


--
-- Name: FUNCTION get_training_summary_day(p_user_id bigint, p_date date); Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON FUNCTION public.get_training_summary_day(p_user_id bigint, p_date date) IS 'Получить список всех тренировок за конкретный день';


--
-- Name: get_training_top5_month(bigint, integer, integer); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.get_training_top5_month(p_user_id bigint, p_year integer, p_month integer) RETURNS TABLE(training_name character varying, workout_count bigint, avg_duration numeric, total_calories numeric)
    LANGUAGE plpgsql
    AS $$
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
$$;


--
-- Name: FUNCTION get_training_top5_month(p_user_id bigint, p_year integer, p_month integer); Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON FUNCTION public.get_training_top5_month(p_user_id bigint, p_year integer, p_month integer) IS 'Получить топ-5 самых популярных тренировок за месяц';


--
-- Name: get_training_top5_year(bigint, integer); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.get_training_top5_year(p_user_id bigint, p_year integer) RETURNS TABLE(training_name character varying, workout_count bigint, avg_duration numeric, total_calories numeric)
    LANGUAGE plpgsql
    AS $$
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
$$;


--
-- Name: FUNCTION get_training_top5_year(p_user_id bigint, p_year integer); Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON FUNCTION public.get_training_top5_year(p_user_id bigint, p_year integer) IS 'Получить топ-5 самых популярных тренировок за год';


--
-- Name: get_weight_category_modifier(numeric, integer); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.get_weight_category_modifier(p_weight numeric, p_training_type_id integer) RETURNS numeric
    LANGUAGE plpgsql
    AS $$
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
$$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: admin_users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.admin_users (
    id integer NOT NULL,
    username character varying(255) NOT NULL,
    password_hash character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    last_login timestamp with time zone
);


--
-- Name: TABLE admin_users; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.admin_users IS 'Учетные записи администраторов системы';


--
-- Name: COLUMN admin_users.username; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.admin_users.username IS 'Имя пользователя для входа';


--
-- Name: COLUMN admin_users.password_hash; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.admin_users.password_hash IS 'Хеш пароля (bcrypt)';


--
-- Name: admin_users_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.admin_users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: admin_users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.admin_users_id_seq OWNED BY public.admin_users.id;


--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: badges; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.badges (
    id integer NOT NULL,
    code character varying(64) NOT NULL,
    title character varying(128) NOT NULL,
    description text NOT NULL,
    icon character varying(128) NOT NULL,
    tier character varying(16) NOT NULL,
    category character varying(32) NOT NULL,
    sort_order integer DEFAULT 0 NOT NULL
);


--
-- Name: badges_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.badges_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: badges_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.badges_id_seq OWNED BY public.badges.id;


--
-- Name: chat_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.chat_history (
    id integer NOT NULL,
    user_id bigint NOT NULL,
    message_type character varying(10) NOT NULL,
    message_text text NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT chat_history_message_type_check CHECK (((message_type)::text = ANY ((ARRAY['user'::character varying, 'bot'::character varying])::text[])))
);


--
-- Name: TABLE chat_history; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.chat_history IS 'История сообщений пользователя с ботом для контекстного общения с ИИ';


--
-- Name: COLUMN chat_history.message_type; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chat_history.message_type IS 'Тип сообщения: user (от пользователя) или bot (от бота)';


--
-- Name: chat_history_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.chat_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: chat_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.chat_history_id_seq OWNED BY public.chat_history.id;


--
-- Name: food; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.food (
    id integer NOT NULL,
    user_id bigint,
    date date,
    name_of_food character varying(255),
    b numeric(7,3),
    g numeric(7,3),
    u numeric(7,3),
    cal numeric(7,3)
);


--
-- Name: TABLE food; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.food IS 'Записи о потребленной пище';


--
-- Name: food_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.food_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: food_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.food_id_seq OWNED BY public.food.id;


--
-- Name: otp_codes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.otp_codes (
    id bigint NOT NULL,
    telegram_username character varying(255) NOT NULL,
    user_id bigint,
    code character varying(6) NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    used boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: otp_codes_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.otp_codes_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: otp_codes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.otp_codes_id_seq OWNED BY public.otp_codes.id;


--
-- Name: training_coefficients; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.training_coefficients (
    id integer NOT NULL,
    training_type_id integer NOT NULL,
    gender_male_modifier numeric(4,3) DEFAULT 1.0,
    gender_female_modifier numeric(4,3) DEFAULT 0.85,
    age_18_25_modifier numeric(4,3) DEFAULT 1.0,
    age_26_35_modifier numeric(4,3) DEFAULT 0.95,
    age_36_45_modifier numeric(4,3) DEFAULT 0.90,
    age_46_55_modifier numeric(4,3) DEFAULT 0.85,
    age_56_plus_modifier numeric(4,3) DEFAULT 0.80,
    weight_under_60_modifier numeric(4,3) DEFAULT 0.90,
    weight_60_70_modifier numeric(4,3) DEFAULT 1.0,
    weight_71_80_modifier numeric(4,3) DEFAULT 1.05,
    weight_81_90_modifier numeric(4,3) DEFAULT 1.10,
    weight_91_100_modifier numeric(4,3) DEFAULT 1.15,
    weight_over_100_modifier numeric(4,3) DEFAULT 1.20,
    height_under_160_modifier numeric(4,3) DEFAULT 0.95,
    height_160_175_modifier numeric(4,3) DEFAULT 1.0,
    height_over_175_modifier numeric(4,3) DEFAULT 1.05,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: TABLE training_coefficients; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.training_coefficients IS 'Коэффициенты корректировки расхода калорий для разных параметров пользователя';


--
-- Name: training_coefficients_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.training_coefficients_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: training_coefficients_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.training_coefficients_id_seq OWNED BY public.training_coefficients.id;


--
-- Name: training_types; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.training_types (
    id integer NOT NULL,
    name_ru character varying(255) NOT NULL,
    name_en character varying(255) NOT NULL,
    name_de character varying(255) NOT NULL,
    name_fr character varying(255) NOT NULL,
    name_es character varying(255) NOT NULL,
    base_coefficient numeric(5,2) NOT NULL,
    emoji character varying(10),
    description_ru text,
    description_en text,
    description_de text,
    description_fr text,
    description_es text,
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: TABLE training_types; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.training_types IS 'Типы тренировок с мультиязычной поддержкой';


--
-- Name: COLUMN training_types.base_coefficient; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.training_types.base_coefficient IS 'Базовый коэффициент расхода калорий в ккал на кг веса в час';


--
-- Name: training_types_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.training_types_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: training_types_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.training_types_id_seq OWNED BY public.training_types.id;


--
-- Name: user_aims; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_aims (
    user_id bigint NOT NULL,
    daily_cal numeric(7,2),
    user_aim character varying(20)
);


--
-- Name: TABLE user_aims; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.user_aims IS 'Цели пользователей по питанию';


--
-- Name: user_badges; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_badges (
    user_id bigint NOT NULL,
    badge_id integer NOT NULL,
    earned_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: user_health; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_health (
    id integer NOT NULL,
    user_id bigint,
    imt numeric(5,2),
    imt_str character varying(255),
    cal numeric(7,2),
    date date,
    weight numeric(5,2),
    height numeric(5,2)
);


--
-- Name: TABLE user_health; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.user_health IS 'История показателей здоровья (вес, рост, ИМТ)';


--
-- Name: user_health_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.user_health_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: user_health_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.user_health_id_seq OWNED BY public.user_health.id;


--
-- Name: user_lang; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_lang (
    user_id bigint NOT NULL,
    lang character varying(10) DEFAULT 'ru'::character varying
);


--
-- Name: TABLE user_lang; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.user_lang IS 'Языковые настройки пользователей';


--
-- Name: user_main; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_main (
    user_id bigint NOT NULL,
    user_name character varying(255),
    created_at timestamp with time zone DEFAULT now(),
    privacy_consent_given boolean DEFAULT false,
    privacy_consent_at timestamp with time zone,
    utm_source character varying(255),
    utm_medium character varying(255),
    utm_campaign character varying(255),
    ref_code character varying(255),
    is_premium boolean DEFAULT false,
    premium_until timestamp without time zone,
    referral_code character varying(50),
    referred_by bigint,
    total_referrals integer DEFAULT 0,
    last_ad_shown timestamp without time zone,
    date_of_birth date,
    user_sex character varying(1),
    telegram_username character varying(255)
);


--
-- Name: TABLE user_main; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.user_main IS 'Основная информация о пользователях';


--
-- Name: COLUMN user_main.privacy_consent_given; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.user_main.privacy_consent_given IS 'Дал ли пользователь согласие на обработку данных';


--
-- Name: COLUMN user_main.privacy_consent_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.user_main.privacy_consent_at IS 'Дата и время предоставления согласия';


--
-- Name: COLUMN user_main.utm_source; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.user_main.utm_source IS 'Источник трафика (например, blogger_name)';


--
-- Name: COLUMN user_main.utm_medium; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.user_main.utm_medium IS 'Канал (например, telegram, instagram)';


--
-- Name: COLUMN user_main.utm_campaign; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.user_main.utm_campaign IS 'Название кампании';


--
-- Name: COLUMN user_main.ref_code; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.user_main.ref_code IS 'Реферальный код';


--
-- Name: user_settings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_settings (
    user_id bigint NOT NULL,
    theme character varying(10) DEFAULT 'auto'::character varying,
    notifications_enabled boolean DEFAULT true,
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: user_streaks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_streaks (
    user_id bigint NOT NULL,
    current_streak integer DEFAULT 0 NOT NULL,
    longest_streak integer DEFAULT 0 NOT NULL,
    last_active_date date,
    freezes_available integer DEFAULT 1 NOT NULL,
    last_freeze_reset date,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: user_training; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_training (
    id integer NOT NULL,
    user_id bigint,
    date date,
    training_cal numeric(7,3),
    tren_time integer,
    training_type_id integer,
    training_name character varying(255),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: TABLE user_training; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.user_training IS 'Записи о тренировках';


--
-- Name: COLUMN user_training.training_cal; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.user_training.training_cal IS 'Количество сожженных калорий';


--
-- Name: COLUMN user_training.tren_time; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.user_training.tren_time IS 'Длительность тренировки в минутах';


--
-- Name: COLUMN user_training.training_type_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.user_training.training_type_id IS 'ID типа тренировки из справочника';


--
-- Name: COLUMN user_training.training_name; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.user_training.training_name IS 'Название тренировки на языке пользователя (для истории)';


--
-- Name: user_training_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.user_training_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: user_training_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.user_training_id_seq OWNED BY public.user_training.id;


--
-- Name: v_training_statistics; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.v_training_statistics AS
 SELECT tt.id AS training_type_id,
    tt.name_ru AS training_name,
    tt.emoji,
    count(ut.id) AS total_sessions,
    count(DISTINCT ut.user_id) AS unique_users,
    round(avg(ut.tren_time), 2) AS avg_duration_minutes,
    round(avg(ut.training_cal), 2) AS avg_calories,
    round(sum(ut.training_cal), 2) AS total_calories_burned
   FROM (public.training_types tt
     LEFT JOIN public.user_training ut ON ((ut.training_type_id = tt.id)))
  WHERE (tt.is_active = true)
  GROUP BY tt.id, tt.name_ru, tt.emoji
  ORDER BY (count(ut.id)) DESC;


--
-- Name: VIEW v_training_statistics; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON VIEW public.v_training_statistics IS 'Статистика использования тренировок';


--
-- Name: water; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.water (
    user_id bigint NOT NULL,
    date date NOT NULL,
    count integer DEFAULT 1
);


--
-- Name: TABLE water; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.water IS 'Учет потребления воды';


--
-- Name: web_sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.web_sessions (
    id bigint NOT NULL,
    user_id bigint NOT NULL,
    token_hash character varying(128) NOT NULL,
    refresh_token_hash character varying(128) NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    last_used_at timestamp with time zone DEFAULT now(),
    user_agent text,
    ip_address character varying(45)
);


--
-- Name: web_sessions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.web_sessions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: web_sessions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.web_sessions_id_seq OWNED BY public.web_sessions.id;


--
-- Name: admin_users id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admin_users ALTER COLUMN id SET DEFAULT nextval('public.admin_users_id_seq'::regclass);


--
-- Name: badges id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.badges ALTER COLUMN id SET DEFAULT nextval('public.badges_id_seq'::regclass);


--
-- Name: chat_history id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_history ALTER COLUMN id SET DEFAULT nextval('public.chat_history_id_seq'::regclass);


--
-- Name: food id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.food ALTER COLUMN id SET DEFAULT nextval('public.food_id_seq'::regclass);


--
-- Name: otp_codes id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.otp_codes ALTER COLUMN id SET DEFAULT nextval('public.otp_codes_id_seq'::regclass);


--
-- Name: training_coefficients id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.training_coefficients ALTER COLUMN id SET DEFAULT nextval('public.training_coefficients_id_seq'::regclass);


--
-- Name: training_types id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.training_types ALTER COLUMN id SET DEFAULT nextval('public.training_types_id_seq'::regclass);


--
-- Name: user_health id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_health ALTER COLUMN id SET DEFAULT nextval('public.user_health_id_seq'::regclass);


--
-- Name: user_training id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_training ALTER COLUMN id SET DEFAULT nextval('public.user_training_id_seq'::regclass);


--
-- Name: web_sessions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.web_sessions ALTER COLUMN id SET DEFAULT nextval('public.web_sessions_id_seq'::regclass);


--
-- Name: admin_users admin_users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admin_users
    ADD CONSTRAINT admin_users_pkey PRIMARY KEY (id);


--
-- Name: admin_users admin_users_username_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admin_users
    ADD CONSTRAINT admin_users_username_key UNIQUE (username);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: badges badges_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.badges
    ADD CONSTRAINT badges_code_key UNIQUE (code);


--
-- Name: badges badges_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.badges
    ADD CONSTRAINT badges_pkey PRIMARY KEY (id);


--
-- Name: chat_history chat_history_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_history
    ADD CONSTRAINT chat_history_pkey PRIMARY KEY (id);


--
-- Name: food food_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.food
    ADD CONSTRAINT food_pkey PRIMARY KEY (id);


--
-- Name: otp_codes otp_codes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.otp_codes
    ADD CONSTRAINT otp_codes_pkey PRIMARY KEY (id);


--
-- Name: training_coefficients training_coefficients_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.training_coefficients
    ADD CONSTRAINT training_coefficients_pkey PRIMARY KEY (id);


--
-- Name: training_types training_types_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.training_types
    ADD CONSTRAINT training_types_pkey PRIMARY KEY (id);


--
-- Name: training_coefficients unique_training_coefficients; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.training_coefficients
    ADD CONSTRAINT unique_training_coefficients UNIQUE (training_type_id);


--
-- Name: training_types unique_training_name_ru; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.training_types
    ADD CONSTRAINT unique_training_name_ru UNIQUE (name_ru);


--
-- Name: user_aims user_aims_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_aims
    ADD CONSTRAINT user_aims_pkey PRIMARY KEY (user_id);


--
-- Name: user_badges user_badges_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_badges
    ADD CONSTRAINT user_badges_pkey PRIMARY KEY (user_id, badge_id);


--
-- Name: user_health user_health_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_health
    ADD CONSTRAINT user_health_pkey PRIMARY KEY (id);


--
-- Name: user_lang user_lang_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_lang
    ADD CONSTRAINT user_lang_pkey PRIMARY KEY (user_id);


--
-- Name: user_main user_main_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_main
    ADD CONSTRAINT user_main_pkey PRIMARY KEY (user_id);


--
-- Name: user_main user_main_referral_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_main
    ADD CONSTRAINT user_main_referral_code_key UNIQUE (referral_code);


--
-- Name: user_settings user_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_settings
    ADD CONSTRAINT user_settings_pkey PRIMARY KEY (user_id);


--
-- Name: user_streaks user_streaks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_streaks
    ADD CONSTRAINT user_streaks_pkey PRIMARY KEY (user_id);


--
-- Name: user_training user_training_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_training
    ADD CONSTRAINT user_training_pkey PRIMARY KEY (id);


--
-- Name: water water_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.water
    ADD CONSTRAINT water_pkey PRIMARY KEY (user_id, date);


--
-- Name: web_sessions web_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.web_sessions
    ADD CONSTRAINT web_sessions_pkey PRIMARY KEY (id);


--
-- Name: web_sessions web_sessions_refresh_token_hash_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.web_sessions
    ADD CONSTRAINT web_sessions_refresh_token_hash_key UNIQUE (refresh_token_hash);


--
-- Name: web_sessions web_sessions_token_hash_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.web_sessions
    ADD CONSTRAINT web_sessions_token_hash_key UNIQUE (token_hash);


--
-- Name: idx_admin_users_username; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_admin_users_username ON public.admin_users USING btree (username);


--
-- Name: idx_chat_history_user_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_chat_history_user_created ON public.chat_history USING btree (user_id, created_at DESC);


--
-- Name: idx_food_user_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_food_user_date ON public.food USING btree (user_id, date);


--
-- Name: idx_otp_codes_expires; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_otp_codes_expires ON public.otp_codes USING btree (expires_at);


--
-- Name: idx_otp_codes_username; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_otp_codes_username ON public.otp_codes USING btree (telegram_username, used);


--
-- Name: idx_training_types_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_training_types_active ON public.training_types USING btree (is_active);


--
-- Name: idx_training_types_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_training_types_created ON public.training_types USING btree (created_at);


--
-- Name: idx_training_user_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_training_user_date ON public.user_training USING btree (user_id, date);


--
-- Name: idx_user_badges_earned; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_user_badges_earned ON public.user_badges USING btree (user_id, earned_at DESC);


--
-- Name: idx_user_health_user_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_user_health_user_date ON public.user_health USING btree (user_id, date);


--
-- Name: idx_user_main_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_user_main_created ON public.user_main USING btree (created_at);


--
-- Name: idx_user_main_ref_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_user_main_ref_code ON public.user_main USING btree (ref_code);


--
-- Name: idx_user_main_referral_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_user_main_referral_code ON public.user_main USING btree (referral_code);


--
-- Name: idx_user_main_tg_username; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_user_main_tg_username ON public.user_main USING btree (telegram_username);


--
-- Name: idx_user_main_utm_source; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_user_main_utm_source ON public.user_main USING btree (utm_source);


--
-- Name: idx_user_streaks_last_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_user_streaks_last_active ON public.user_streaks USING btree (last_active_date);


--
-- Name: idx_user_training_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_user_training_name ON public.user_training USING btree (training_name);


--
-- Name: idx_user_training_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_user_training_type ON public.user_training USING btree (training_type_id);


--
-- Name: idx_water_user_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_water_user_date ON public.water USING btree (user_id, date);


--
-- Name: idx_web_sessions_expires; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_web_sessions_expires ON public.web_sessions USING btree (expires_at);


--
-- Name: idx_web_sessions_refresh; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_web_sessions_refresh ON public.web_sessions USING btree (refresh_token_hash);


--
-- Name: idx_web_sessions_token; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_web_sessions_token ON public.web_sessions USING btree (token_hash);


--
-- Name: idx_web_sessions_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_web_sessions_user ON public.web_sessions USING btree (user_id);


--
-- Name: chat_history chat_history_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_history
    ADD CONSTRAINT chat_history_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.user_main(user_id) ON DELETE CASCADE;


--
-- Name: food food_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.food
    ADD CONSTRAINT food_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.user_main(user_id) ON DELETE CASCADE;


--
-- Name: training_coefficients training_coefficients_training_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.training_coefficients
    ADD CONSTRAINT training_coefficients_training_type_id_fkey FOREIGN KEY (training_type_id) REFERENCES public.training_types(id) ON DELETE CASCADE;


--
-- Name: user_aims user_aims_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_aims
    ADD CONSTRAINT user_aims_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.user_main(user_id) ON DELETE CASCADE;


--
-- Name: user_badges user_badges_badge_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_badges
    ADD CONSTRAINT user_badges_badge_id_fkey FOREIGN KEY (badge_id) REFERENCES public.badges(id) ON DELETE CASCADE;


--
-- Name: user_badges user_badges_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_badges
    ADD CONSTRAINT user_badges_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.user_main(user_id) ON DELETE CASCADE;


--
-- Name: user_health user_health_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_health
    ADD CONSTRAINT user_health_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.user_main(user_id) ON DELETE CASCADE;


--
-- Name: user_lang user_lang_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_lang
    ADD CONSTRAINT user_lang_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.user_main(user_id) ON DELETE CASCADE;


--
-- Name: user_main user_main_referred_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_main
    ADD CONSTRAINT user_main_referred_by_fkey FOREIGN KEY (referred_by) REFERENCES public.user_main(user_id);


--
-- Name: user_settings user_settings_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_settings
    ADD CONSTRAINT user_settings_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.user_main(user_id) ON DELETE CASCADE;


--
-- Name: user_streaks user_streaks_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_streaks
    ADD CONSTRAINT user_streaks_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.user_main(user_id) ON DELETE CASCADE;


--
-- Name: user_training user_training_training_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_training
    ADD CONSTRAINT user_training_training_type_id_fkey FOREIGN KEY (training_type_id) REFERENCES public.training_types(id) ON DELETE SET NULL;


--
-- Name: user_training user_training_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_training
    ADD CONSTRAINT user_training_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.user_main(user_id) ON DELETE CASCADE;


--
-- Name: water water_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.water
    ADD CONSTRAINT water_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.user_main(user_id) ON DELETE CASCADE;


--
-- Name: web_sessions web_sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.web_sessions
    ADD CONSTRAINT web_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.user_main(user_id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--


