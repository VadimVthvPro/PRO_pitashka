--
-- PostgreSQL database dump
--

\restrict 7Ym878G8O0LKQwYkx13TqCnYMtlwHCpcDOWfYJByPMLIZR5jdcZo3wWKLTQWqCc

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
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.alembic_version (version_num) FROM stdin;
004_streaks_badges
\.


--
-- Data for Name: badges; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.badges (id, code, title, description, icon, tier, category, sort_order) FROM stdin;
1	streak_3	Три дня подряд	Три активных дня кряду	solar:flame-bold-duotone	bronze	streak	10
2	streak_7	Неделя стали	Семь дней без пропусков	solar:flame-bold-duotone	silver	streak	20
3	streak_30	Месяц характера	Тридцать дней подряд. Это уже привычка	solar:flame-bold-duotone	gold	streak	30
4	streak_100	100 дней	Сто дней активности	solar:crown-star-bold-duotone	legend	streak	40
5	water_first	Первый глоток	Первый стакан воды вообще	solar:cup-bold-duotone	bronze	water	110
6	water_goal	Ровно 8	Выпил дневную норму	solar:cup-bold-duotone	silver	water	120
7	water_7	Гидромаст	Норма воды 7 дней подряд	solar:cup-star-bold-duotone	gold	water	130
8	food_first	Первая тарелка	Первое добавление еды	solar:plate-bold-duotone	bronze	food	210
9	food_balance	Балансист	БЖУ в пределах ±10% от цели за день	solar:plate-bold-duotone	silver	food	220
10	workout_first	Разогрев	Первая тренировка в дневнике	solar:dumbbell-large-bold-duotone	bronze	workout	310
11	workout_5wk	Марафонец	Пять тренировок за календарную неделю	solar:running-bold-duotone	gold	workout	320
12	ai_10	Любопытный	Задал AI десять вопросов	solar:magic-stick-3-bold-duotone	silver	ai	410
\.


--
-- Name: badges_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.badges_id_seq', 12, true);


--
-- PostgreSQL database dump complete
--

\unrestrict 7Ym878G8O0LKQwYkx13TqCnYMtlwHCpcDOWfYJByPMLIZR5jdcZo3wWKLTQWqCc

