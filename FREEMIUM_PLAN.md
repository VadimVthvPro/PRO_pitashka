# Freemium + Telegram Stars — полный план

Документ описывает то, что реально реализуется в ветке `freemium-stars`
и будет развёрнуто параллельно прод-стеку на портах `3201/8102`.
Прод (3200/8101) не трогаем — он продолжает работать с текущей кодовой базой.

---

## 1. Цель

1. Перевести приложение на модель **freemium**: бесплатный тир с жёсткими
   лимитами по тяжёлым AI-фичам + платные тиры **Premium** и **Pro**.
2. Оплата через **Telegram Stars** (`XTR`) — внутренний механизм Telegram, деньги
   попадают на Stars-баланс бота `@PROpitashka_bot`. Владелец бота — аккаунт
   `@vadimvthv`, вывод Stars доступен только владельцу.
3. Мягкая деградация: если юзер уперся в лимит, ему показывается paywall с
   кнопкой «Оплатить звёздами» → прямая отправка инвойса из бота в его
   личку, после оплаты тир повышается моментально.
4. Параллельная версия: старое приложение остаётся на прежних портах, новое
   работает рядом. В любой момент можно откатиться на прежнюю ветку.

---

## 2. Tiers, лимиты и цены

### Тарифы (редактируются через `tier_plans` в БД)

| Ключ            | Name         | Цена (Stars) | USD-эквивалент¹ | Срок   |
|-----------------|--------------|--------------|-----------------|--------|
| `free`          | Free         | 0            | —               | ∞      |
| `premium_month` | Premium      | **249 ⭐**    | ~$3.32          | 30 дн  |
| `premium_year`  | Premium Year | **2490 ⭐**   | ~$33.18 (−17%)  | 365 дн |
| `pro_month`     | Pro          | **499 ⭐**    | ~$6.65          | 30 дн  |
| `pro_year`      | Pro Year     | **4990 ⭐**   | ~$66.49 (−17%)  | 365 дн |

¹ На 2026-04: 1 ⭐ ≈ $0.01333 выплаты; после комиссии Telegram на баланс бота
   приходит ≈70% (≈$0.0093 за Star). Итого: Premium month → ~$2.32 чистыми.

### Лимиты по фичам

Лимиты хранятся в `tier_plans.limits JSONB`, ключи — квотам, значения — лимит
на период (`day` | `month`). `-1` = безлимит.

| Ключ                  | Free       | Premium    | Pro         | Период |
|-----------------------|------------|------------|-------------|--------|
| `ai_chat_msg`         | 10         | 200        | −1          | day    |
| `ai_photo`            | 3          | 30         | −1          | day    |
| `ai_meal_plan`        | 1          | 10         | −1          | month  |
| `ai_workout_plan`     | 1          | 10         | −1          | month  |
| `ai_recipe`           | 3          | 30         | −1          | month  |
| `ai_digest`           | 1          | 8          | −1          | month  |
| `food_manual`         | 30         | 200        | −1          | day    |
| `social_post_photo`   | 0          | 1          | −1          | day    |
| `history_days`        | 14         | 365        | −1          | —      |

Pro отличается от Premium:
- безлимит на все AI-запросы,
- приоритетная модель (`gemini-2.5-pro` вместо `gemini-2.5-flash`),
- расширенная история (все дни),
- без рекламы (баннеры партнёров / upsell в интерфейсе),
- «комбо-пакеты» — план питания + тренировки + рецепты в одном клике,
- экспорт данных в CSV/PDF,
- beta-доступ к новым фичам.

---

## 3. Поток оплаты через Stars (high-level)

```
┌─────────────┐   paywall    ┌──────────────────┐  /api/billing/stars/invoice
│  Frontend   ├─────────────>│   FastAPI (8102) ├───────────────────────────┐
└─────┬───────┘              └─────────┬────────┘                           │
      │  t.me/PROpitashka_bot?start=pay_xxx                                  │
      ▼                                │                                    ▼
┌─────────────┐   start=pay_xxx        │              aiogram Bot createInvoiceLink(XTR)
│  Telegram   │◄───────────────────────┘                   │
│  пользователь│                                           │
│   (client)  │  инвойс от бота в личке                    │
└─────┬───────┘                                            │
      │  Pay ⭐  (native Stars UI)                         │
      ▼                                                    │
┌─────────────┐   pre_checkout_query    ┌─────────────────┐│
│   Telegram  ├─────────────────────────>│  telegram_bot   ├┘
│   Servers   │   successful_payment    │  payments.py    │
└─────────────┘◄────────────────────────┤                 │
                                         │  subscription  │
                                         │  granted (DB)  │
                                         └────────┬───────┘
                                                  │
                                 push в WS/poll в /api/billing/me
                                                  ▼
                                       ┌──────────────────┐
                                       │    Frontend       │  «Оплата прошла»
                                       └──────────────────┘
```

Ключевые детали:

1. **Invoice создаётся внутри бота** — `bot.create_invoice_link(title, ..., currency="XTR", prices=[LabeledPrice(..., amount=stars)])`. Токен провайдера для Stars НЕ нужен.
2. **Payload** — уникальная строка `pay:{user_id}:{plan_key}:{nonce}`, по ней сверяем pre-checkout.
3. **PreCheckoutQuery** — всегда `answer(ok=True)` если payload есть в `star_payments(status='pending')` и сумма совпадает. Иначе `ok=False, error_message=...`.
4. **SuccessfulPayment** — атомарно:
   - обновляем `star_payments.status='paid'`, пишем `telegram_payment_charge_id`,
   - вызываем `subscription_service.grant(user_id, plan_key, source='stars', payment_id=...)`,
   - бот шлёт сообщение «✅ Premium активирован до YYYY-MM-DD, спасибо!»,
   - на фронте `/api/billing/me` вернёт свежий тир.
5. **Возвраты** (Telegram позволяет refund в течение 21 дня): админ-команда `/refund <charge_id>` → `refundStarPayment` → `subscriptions.status='refunded'`, тир → `free`.

---

## 4. Изменения в БД (alembic 011_freemium)

```sql
CREATE TABLE tier_plans (
    plan_key         VARCHAR(32) PRIMARY KEY,
    name             VARCHAR(64) NOT NULL,
    tier             VARCHAR(16) NOT NULL,            -- free|premium|pro
    duration_days    INTEGER,                          -- NULL для free
    price_stars      INTEGER NOT NULL DEFAULT 0,
    price_usd_cents  INTEGER,                          -- для отображения
    limits           JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_active        BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order       INTEGER DEFAULT 0,
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE subscriptions (
    id               BIGSERIAL PRIMARY KEY,
    user_id          BIGINT NOT NULL REFERENCES user_main(user_id) ON DELETE CASCADE,
    plan_key         VARCHAR(32) NOT NULL REFERENCES tier_plans(plan_key),
    tier             VARCHAR(16) NOT NULL,
    status           VARCHAR(16) NOT NULL,              -- active|expired|cancelled|refunded
    source           VARCHAR(16) NOT NULL,              -- stars|card|promo|admin
    start_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    end_at           TIMESTAMPTZ NOT NULL,
    auto_renew       BOOLEAN NOT NULL DEFAULT FALSE,
    payment_id       BIGINT,                             -- FK на star_payments.id
    created_at       TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ON subscriptions(user_id, status);
CREATE INDEX ON subscriptions(end_at) WHERE status='active';

CREATE TABLE star_payments (
    id                           BIGSERIAL PRIMARY KEY,
    user_id                      BIGINT NOT NULL REFERENCES user_main(user_id) ON DELETE CASCADE,
    plan_key                     VARCHAR(32) NOT NULL,
    invoice_payload              VARCHAR(128) NOT NULL UNIQUE,
    stars_amount                 INTEGER NOT NULL,
    status                       VARCHAR(16) NOT NULL DEFAULT 'pending',  -- pending|paid|refunded|failed
    telegram_payment_charge_id   VARCHAR(128),
    provider_payment_charge_id   VARCHAR(128),
    created_at                   TIMESTAMPTZ DEFAULT NOW(),
    paid_at                      TIMESTAMPTZ,
    refunded_at                  TIMESTAMPTZ
);
CREATE INDEX ON star_payments(user_id, status);

CREATE TABLE usage_counters (
    user_id          BIGINT NOT NULL REFERENCES user_main(user_id) ON DELETE CASCADE,
    quota_key        VARCHAR(32) NOT NULL,
    period           CHAR(1) NOT NULL,                   -- 'd' | 'm'
    period_start     DATE NOT NULL,
    count            INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, quota_key, period, period_start)
);
```

Seed `tier_plans` выполнит новая миграция из dict-а, чтобы не трогать
`init_seed.sql`. `is_premium`/`premium_until` в `user_main` оставляем ради
совместимости — их пересчитывает триггер/сервис.

---

## 5. Backend-архитектура

```
backend/app/
  models/billing.py           # pydantic: PlanOut, MeOut, InvoiceOut, UsageOut
  repositories/billing_repo.py
  services/subscription_service.py
  services/quota_service.py
  routers/billing.py
  dependencies_billing.py     # RequireTier, QuotaGuard
telegram_bot/handlers/payments.py
telegram_bot/stars.py         # helpers: create_invoice_link, refund
```

Ключевые функции:

- `subscription_service.get_tier(user_id) → {tier, plan_key, end_at, limits}` —
  resolves активную подписку; если истекла → `free`. Кешируется в Redis на 60 с.
- `quota_service.check(user_id, key)` → `(ok: bool, used: int, limit: int, reset_at)`;
  raises `HTTPException(402, code='quota_exceeded', upgrade_url='/billing?...')`.
- `quota_service.consume(user_id, key, n=1)` — атомарный INSERT..ON CONFLICT DO UPDATE.
- `subscription_service.grant(user_id, plan_key, source, payment_id)` — создаёт
  запись в `subscriptions`, закрывает предыдущие `active`, синхронизирует
  `user_main.is_premium/premium_until`, чистит Redis-кеш.

### Как применяем к эндпоинтам

```python
# routers/ai.py
@router.post("/chat")
async def ai_chat(..., _quota: QuotaGuard = Depends(quota("ai_chat_msg"))):
    ...
```

`QuotaGuard` повышает исключение `QuotaExceeded`, которое ловится глобальным
handler'ом и превращается в `402 Payment Required` с телом:

```json
{
  "code": "quota_exceeded",
  "message": "Дневной лимит AI-сообщений исчерпан",
  "quota_key": "ai_chat_msg",
  "limit": 10,
  "used": 10,
  "reset_at": "2026-04-16T00:00:00Z",
  "upgrade": {
    "plan_key": "premium_month",
    "invoice_url": "https://t.me/PROpitashka_bot?start=pay_abc"
  }
}
```

### RequireTier

Для чисто-платных фич (например `social_post_photo`, экспорт CSV):

```python
@router.get("/export")
async def export_csv(..., _: None = Depends(require_tier("premium"))):
    ...
```

Если тир ниже — `402` с аналогичным телом.

---

## 6. Telegram Stars: детали для Беларуси / `@vadimvthv`

1. **Куда приходят деньги.** Stars зачисляются на баланс бота
   `@PROpitashka_bot`. Владелец бота в BotFather — личный Telegram-аккаунт
   `@vadimvthv`. Смена владельца бота НЕ нужна — баланс уже принадлежит
   вашему аккаунту.
2. **Вывод Stars.** В приложении Telegram:
   `My Stars` → `Withdraw earnings`. Требуется:
   - Подтверждённый TON-кошелёк (встроенный `Wallet` в Telegram или внешний).
   - Обычно 1000+ Stars для вывода (минимум меняется, смотри Telegram).
   - Комиссия Telegram ~30% на stars→TON.
3. **TON → BYN/USDT в Беларуси.**
   - `Wallet` в Telegram → свап TON в USDT/USDC.
   - Далее P2P на Bybit/OKX/Kucoin → продажа за BYN на белорусский банк
     (Belarusbank/MTБ/Альфа), карту Visa/Mastercard или наличный пункт.
   - Налоги: физлицо — декларация на подоходный 13% если суммы
     существенные. По рекомендациям — оформить ИП (УСН 6%) при регулярных
     поступлениях > 1000 BYN/мес.
4. **Что НЕ требуется для Stars:**
   - Provider token (как у Stripe/ЮKassa) — нет.
   - Счёт в банке, эквайринг, KYC-валидация со стороны пользователя.
   - Дополнительных сертификатов/виджетов.

---

## 7. Frontend-дизайн

Все изменения следуют `DESIGN_GUIDE.md`, mobile-first, `--radius` / `--card` /
`--accent`, 44-px тап-таргеты, safe-area-insets.

### Новые экраны / компоненты

1. **`/billing`** — «Подписка». Hero-плашка с текущим тиром + до когда,
   три карточки тарифов (Free/Premium/Pro), переключатель Месяц/Год,
   таблица «что включено», блок Usage (прогресс-бары по квотам), история
   платежей (последние 10). CTA «Оплатить ⭐ 249» открывает Telegram bot.
2. **`UpgradeModal`** — bottom-sheet, всплывает при `402 quota_exceeded`
   или по явному клику. Внутри 2 карточки (Premium/Pro) + Telegram CTA.
3. **`QuotaBar`** — тонкая полоска `used/limit` с иконкой, встраивается в
   `ai-chat` header, на dashboard в hero, на food и plans.
4. **`PaywallBanner`** — карточка «У тебя Free. Открой Premium…» на
   dashboard для free-юзеров (скрывается, если already premium+).

### Интеграция в существующие экраны

- **Dashboard**: QuotaBar для `ai_chat_msg` и `ai_photo`.
- **AI-chat**: QuotaBar сверху + обработка 402 → UpgradeModal с
  предзаполненным планом.
- **Food**: QuotaBar на тап «Добавить по фото», при превышении — модалка.
- **Plans**: plan generators показывают «осталось X из Y в этом месяце».
- **Digest**: кнопка regen блокируется, если квота исчерпана.
- **Settings**: новая секция «Подписка» → кнопка «Открыть /billing».
- **BottomNav / MobileMenu**: пункт «Premium» с бейджем-звёздочкой при Free.

### Обработка ошибок

`lib/api.ts` расширяется: на `402 quota_exceeded` / `402 require_tier` —
диспатчим глобальное событие `billing:paywall` с payload, на которое
слушает `UpgradeModalProvider` (в `app/(app)/layout.tsx`).

---

## 8. Деплой (параллельно)

Создаём новые файлы:

- `docker-compose.freemium.yml` — такие же сервисы, но:
  - `project_name: propitashka-freemium` (COMPOSE_PROJECT_NAME),
  - имена контейнеров `propitashka-*-freemium`,
  - volumes `postgres_data_freemium` / `redis_data_freemium` / `uploads_data_freemium`,
  - порты `FRONTEND_PUBLIC_PORT=3201`, `BACKEND_LOCAL_PORT=8102`.
- `.env.freemium.example` — те же переменные, другой `FRONTEND_URL`,
  свежий JWT secret, опционально отдельный `TELEGRAM_TOKEN` (можно оставить
  тот же — и тогда будет один бот для обеих версий; при параллельном
  polling возникнет Conflict. Рекомендуется создать **второго бота** в
  BotFather (`@PROpitashka_freemium_bot`) — в `.env.freemium.example`
  указать его токен).

### Стратегия бота

Сейчас на прод-версии уже работает `@PROpitashka_bot` (polling). Два
инстанса polling одного и того же бота несовместимы (TelegramConflictError).
Решения:
1. **Рекомендуется:** создать в BotFather второго бота
   (`@PROpitashkaStars_bot` или `@PROpitashka_dev_bot`) и писать его токен
   в `.env.freemium`. Free-юзеры тестовой версии получают OTP/инвойсы от
   второго бота.
2. Либо на freemium-ветке временно отключить polling (`TELEGRAM_TOKEN=""`)
   и тестировать оплату вручную через REST-моки.

По умолчанию в шаблоне `.env.freemium.example` оставлю `TELEGRAM_TOKEN=`
пустым и добавлю комментарий с инструкцией.

### Миграция БД

Freemium-стек имеет собственную Postgres-базу (другой volume), значит
миграции применяются с чистого листа:

```
alembic upgrade head
# → применит 001…010 (прод-миграции) + 011_freemium
```

---

## 9. Порядок работ (чек-лист)

1. ✅ Планирование (этот файл)
2. ⏳ `git checkout -b freemium-stars`
3. ⏳ Скелет параллельного деплоя (`docker-compose.freemium.yml`, `.env.freemium.example`)
4. ⏳ Миграция БД + модели/репозитории
5. ⏳ `subscription_service` + `quota_service`
6. ⏳ Router `/api/billing/*`
7. ⏳ Telegram-обработчики Stars
8. ⏳ Применение квот к `/api/ai/*`, `/api/food/photo`, `/api/digest/*`
9. ⏳ Frontend: lib + components + /billing + интеграция в экраны
10. ⏳ Глобальный UpgradeModal по событию `billing:paywall`
11. ⏳ `npm run build` + backend smoke-test
12. ⏳ Запуск freemium-стека на сервере (3201/8102)
13. ⏳ Sanity-check: оплата → тир повышен → квота сбросилась
14. ⏳ Документация в `FREEMIUM_DEPLOY.md`

---

## 10. Откат

Ветка `main` (или `master`) не трогается. Чтобы откатиться:

```
docker compose -p propitashka-freemium -f docker-compose.freemium.yml down
git checkout main
```

Прод-стек на 3200/8101 продолжает работать всё это время и является
«эталонной» версией.
