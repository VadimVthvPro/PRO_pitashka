# План будущих фич (социальные + расширения)

> Фичи ниже требуют серьёзной инфраструктуры (модерация, приватность,
> анти-спам). Пока в продакшен не катятся — поэтому собрали
> детальный план, чтобы реализовывать поэтапно, после фидбека
> от первой волны пользователей.

## 1. Соревнования и лидерборды

### Цель
Здоровая конкуренция: кто больше дней подряд ведёт дневник, у кого
дольше streak, кто провёл больше тренировок за неделю.

### Что нужно
- **DB миграция**: таблица `user_privacy` (`user_id`, `show_in_leaderboard BOOL`,
  `display_handle TEXT`). По умолчанию `show_in_leaderboard = FALSE` (GDPR-дружественно).
- **Onboarding шаг**: чекбокс "Участвовать в лидерборде" + ник (3-20 символов).
- **Репозиторий** `leaderboard_repo.py`: материализованное view `leaderboard_weekly`
  с агрегатами (streak_current, food_days, workout_sessions). Обновление раз в час
  через APScheduler.
- **Эндпоинты**:
  - `GET /api/leaderboard/streaks?period=week|month` → top 50
  - `GET /api/leaderboard/me` → позиция пользователя
- **Frontend** `/leaderboard`: таблица с анимированными позициями, sticker
  «твоё место», подсветка текущего пользователя.
- **Анти-читинг**: запись не засчитывается, если `entries < 3` за день
  (иначе легко гиперзасорить пустыми).

### Этапы
1. Privacy consent + DB schema (1 день)
2. Scheduled materialization (0.5 дня)
3. Endpoint + frontend таблица (1 день)
4. Анти-читинг фильтры (0.5 дня)

---

## 2. Публикация рецептов + лайки

### Цель
Пользователи делятся своими рецептами, ставят друг другу лайки,
находят идеи что приготовить.

### Что нужно
- **DB**: `recipes` (`id`, `user_id`, `title`, `body`, `photo_url NULLABLE`,
  `kbju JSONB`, `status` enum: `pending|approved|rejected`, `created_at`).
  `recipe_likes` (`user_id`, `recipe_id`, `created_at`).
- **Модерация** (ОБЯЗАТЕЛЬНО, иначе спам):
  - Авто-фильтр: blacklist слов, ссылки запрещены.
  - Очередь ручной модерации в админке (кнопки approve/reject).
  - AI-pre-check: `ai_service.moderate_text()` → safe/unsafe/needs_review.
- **Storage фото**: S3-compatible (MinIO локально, Cloudflare R2 в проде).
  Лимит 1 фото, до 2 МБ, ресайз до 1200 px.
- **Эндпоинты**:
  - `POST /api/recipes` (создание → status=pending)
  - `GET /api/recipes?sort=popular|new` (только approved)
  - `POST /api/recipes/{id}/like` / `DELETE` (toggle)
  - `GET /api/recipes/me`
  - `POST /api/admin/recipes/{id}/approve|reject`
- **Frontend**:
  - `/recipes` — лента с карточками, infinite scroll.
  - `/recipes/new` — форма с drag-n-drop фото.
  - `/recipes/[id]` — детальная.
  - В `/admin` — секция «На модерации».
- **Rate-limit**: не более 2 рецептов в сутки на пользователя.

### Этапы
1. Storage setup (MinIO + minio-client) (1 день)
2. DB + эндпоинты (1.5 дня)
3. Модерация (AI + admin UI) (1.5 дня)
4. Frontend лента + форма (2 дня)

---

## 3. Лента фото своей еды

### Цель
Instagram-style лента блюд. Пользователи выкладывают фото приёма пищи
(часто — уже сфотографированные для AI-распознавания), друзья
ставят «аппетитно».

### Что нужно
- **Интеграция с food-entries**: опциональный флаг `share_photo BOOL`
  при добавлении еды. Уже есть `photo_url` в `food`.
- **DB**: `food_shares` (`food_id`, `shared_at`, `caption TEXT`).
  `food_reactions` (`user_id`, `food_id`, `emoji` enum: `fire|heart|appetite|wow`).
- **Privacy**: лента только для подписчиков (см. фичу «друзья»)
  ИЛИ глобальная с возможностью repost'ов. Начать с глобальной но с
  чекбоксом "Показывать только мне" (default TRUE).
- **Эндпоинты**:
  - `POST /api/food/{id}/share` (с caption)
  - `GET /api/feed?since=<cursor>` (пагинация курсором)
  - `POST /api/feed/{food_id}/react` (emoji)
- **Frontend**:
  - `/feed` — Pinterest-like masonry grid.
  - Modal при клике на карточку: фото + КБЖУ + реакции.
- **Модерация**: AI-фильтр на NSFW (`ai_service.moderate_image()`).

### Этапы
1. Миграция + privacy toggle (0.5 дня)
2. Share endpoint + feed endpoint (1 день)
3. Реакции (0.5 дня)
4. Frontend masonry + modal (2 дня)
5. NSFW-фильтр (0.5 дня)

---

## 4. Общая база еды (Phase 2)

> Phase 1 уже есть: `/api/food/search` по встроенному словарю (~80 продуктов).

### Phase 2 — пользовательские записи
Когда юзер через AI добавляет новый продукт, предложить «сохранить в
общую базу» (на модерации). Админ одобряет → попадает в search.

### Что нужно
- **DB**: `community_foods` (`id`, `name UNIQUE`, `cal`, `b`, `g`, `u`,
  `suggested_by`, `status`, `approved_at`).
- **UI**: после успешного AI-распознавания — кнопка
  «Поделиться с сообществом» (default off).
- **Админка**: таблица на модерации.
- **Search**: дополнить `search_foods()` выборкой из `community_foods WHERE status='approved'`.

### Этапы
1. Миграция (0.2 дня)
2. Suggest endpoint + admin approval (0.5 дня)
3. Интеграция в search (0.3 дня)
4. UI после AI (0.5 дня)

---

## Общие предпосылки перед соцфичами

1. **Privacy Policy**: обновить, явно указать про соц-функции, лидерборды.
2. **Consent wizard**: отдельный экран после регистрации (уже есть
   `privacy_consent_given`) — добавить `social_consent`.
3. **Модерационный фреймворк**: `backend/app/services/moderation_service.py`:
   - `moderate_text(text) → {safe, severity, reasons}`
   - `moderate_image(bytes) → {safe, severity}`
4. **Rate-limiting**: Redis-based, декоратор `@rate_limit(per="minute", max=10)`.
5. **Reporting**: `POST /api/reports` с причиной — необходим до любого UGC.

## Что готово уже сейчас (локальный тест)

- Streaks + Badges (`/achievements`)
- Weight + AI forecast (`/weight`)
- Weekly AI digest + fallback (`/digest`)
- Quick repeat + favorites (`/food?tab=repeat`)
- Food search API (`/api/food/search?q=...`)
