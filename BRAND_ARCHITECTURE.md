# Brand Architecture: PROpitashka ↔ PROfit

> **Status:** draft. Waits for user's final decision on:
> 1. Стилизация имени: `PROfit` vs `Profit`.
> 2. Архитектурный вариант: A (two branches) vs B (one codebase + brand-switch).
>
> Этот документ описывает **Вариант B** как рекомендованный (см. §1). Если выбран A — см. §8.

---

## 1. Why Вариант B

Пользователь описал поведение: «одна команда на сервере — и бренд сменился, обе версии работают по одному функционалу».

Это ровно то, что даёт **одна кодовая база + brand-config через env**. Реальные две ветки — это избыточная механика: дублирующий код, конфликты merge, x2 CI, риск рассинхрона.

Parity обеих версий гарантируется самим фактом одной кодовой базы: любой фикс автоматически работает в обоих брендах.

## 2. Brand data model

### 2.1 Frontend: `frontend/src/lib/brand.config.ts`

```ts
// Read-only словарь всех брендов. Не импортировать напрямую из компонентов —
// только через `brand` из `brand.ts`.
export const BRANDS = {
  propitashka: {
    name: "propitashka",
    displayName: "PROpitashka",
    shortName: "ПРОпиташка",
    tagline: "Тёплый дневник питания и тренировок",
    logoDir: "/brand/propitashka",
    wordmarkBody: "pitashka",      // рендерится в Sidebar/MobileMenu/TopBar
    askForm: { ru: "Пропитошку", en: "Propitoshka", ... },
  },
  profit: {
    name: "profit",
    displayName: "PROfit",
    shortName: "PROfit",
    tagline: "AI-наставник по питанию и тренировкам",
    logoDir: "/brand/profit",
    wordmarkBody: "fit",
    askForm: { ru: "PROfit", en: "PROfit", ... },
  },
} as const;

export type BrandId = keyof typeof BRANDS;
export type BrandData = (typeof BRANDS)[BrandId];
```

### 2.2 Frontend: `frontend/src/lib/brand.ts`

```ts
import { BRANDS, type BrandData, type BrandId } from "./brand.config";

const raw = (process.env.NEXT_PUBLIC_BRAND || "propitashka") as BrandId;
const id: BrandId = raw in BRANDS ? raw : "propitashka";

export const brand: BrandData = BRANDS[id];
```

### 2.3 Backend: `backend/app/brand.py`

```python
from functools import lru_cache
from app.config import settings

BRANDS = {
    "propitashka": {
        "name": "propitashka",
        "display_name": "PROpitashka",
        "short_name": "ПРОпиташка",
        "tagline": "Тёплый дневник питания и тренировок",
    },
    "profit": {
        "name": "profit",
        "display_name": "PROfit",  # зависит от Вопроса 1
        "short_name": "PROfit",
        "tagline": "AI-наставник по питанию и тренировкам",
    },
}

@lru_cache(maxsize=1)
def current() -> dict:
    b = (settings.BRAND or "propitashka").lower()
    return BRANDS.get(b, BRANDS["propitashka"])
```

## 3. Env-контракт

```bash
# .env.freemium
BRAND=profit                              # profit | propitashka
NEXT_PUBLIC_BRAND=profit

# Bot usernames per brand (опционально — если разные боты)
NEXT_PUBLIC_BOT_USERNAME_PROPITASHKA=PROpitashka_bot
NEXT_PUBLIC_BOT_USERNAME_PROFIT=PROpitashka_test_bot

# Backend сам выбирает какой токен использовать
TELEGRAM_BOT_TOKEN_PROPITASHKA=...
TELEGRAM_BOT_TOKEN_PROFIT=...
```

Все остальные ключи (БД, Gemini, Stars) брендонезависимы.

## 4. Runtime vs build-time: важный нюанс Next.js

`NEXT_PUBLIC_*` фиксируются в момент **сборки** Next.js. Это означает:

**Проблема:** чтобы переключить бренд, надо пересобирать фронт — это 2-3 минуты, не 30 секунд.

**Решения (в порядке предпочтения):**

### Вариант 4.1. Runtime-config через API (рекомендовано)

Фронт читает бренд не из `process.env`, а из эндпоинта `/api/brand`:

```ts
// frontend/src/lib/brand.ts — server-first
"use server";
export async function getBrand(): Promise<BrandData> {
  const res = await fetch(`${process.env.BACKEND_INTERNAL_URL}/api/brand`, {
    next: { revalidate: 60 },
  });
  const { brand } = await res.json();
  return BRANDS[brand as BrandId] ?? BRANDS.propitashka;
}
```

Бэкенд отдаёт `{"brand": "profit"}` из `settings.BRAND`. Переключение — перезапуск **только backend**, фронт не пересобирается.

### Вариант 4.2. Two builds, quick switch

Две предсобранные папки: `.next-propitashka/` и `.next-profit/`, docker-compose монтирует нужную через симлинк. Переключение — `ln -snf .next-profit .next && docker restart frontend_freemium` (≤ 5 сек), но на диске x2 места.

### Вариант 4.3. Build on switch

Просто `docker compose build --build-arg NEXT_PUBLIC_BRAND=profit frontend_freemium && docker compose up -d frontend_freemium`. 2-3 минуты на переключение.

**По умолчанию делаем 4.1.** Если нужно абсолютное runtime-переключение логотипа без задержки — делаем 4.2 как опцию.

## 5. Где меняется код (map of changes)

| Место | Было | Станет |
|---|---|---|
| `backend/app/services/prompts.py` | `"PROpitashka"` в 9 строках | `f"{brand_name}"` + аргумент во все `system_*` и `prompt_*` |
| `backend/app/services/ai_service.py` | импортирует prompts без brand | добавляет `brand = current()["display_name"]` и передаёт в каждый prompt-fn |
| `backend/app/config.py` | нет `BRAND` | добавить `BRAND: str = "propitashka"` |
| `backend/telegram_bot/handlers/*.py` | любые хардкоды имени | читать `brand.current()` |
| `frontend/src/app/layout.tsx` | `<title>PROpitashka</title>` | `<title>{brand.displayName}</title>` |
| `frontend/src/app/(auth)/login/page.tsx` | hero-текст | через `brand.displayName` |
| `frontend/src/app/globals.css` | ничего | добавить CSS-переменные для бренда (если нужно) |
| `frontend/src/locales/*.json` | `"welcome": "... PROpitashka ..."` | `"welcome": "... {brand} ..."` + `t("welcome", {brand: brand.displayName})` |
| `frontend/Dockerfile` | `ARG NEXT_PUBLIC_BOT_USERNAME` | добавить `ARG NEXT_PUBLIC_BRAND` |
| `docker-compose.freemium.yml` | `NEXT_PUBLIC_BOT_USERNAME` хардкод | параметризовать `BRAND`, `NEXT_PUBLIC_BRAND` |
| `frontend/public/brand/propitashka/logo.svg` | — | перенести существующий логотип-пташку |
| `frontend/public/brand/profit/logo.svg` | — | новый wordmark (см. §6 дизайн-концепцию) |
| `frontend/public/brand/{profit\|propitashka}/favicon.ico` | — | per-brand favicon |
| `frontend/public/brand/{profit\|propitashka}/og-image.png` | — | per-brand OG |

## 6. Logo и brand assets

### 6.1 PROpitashka (существующий)
- Пташка + `PROpitashka` wordmark — остаётся как есть
- Переносится из `frontend/public/` в `frontend/public/brand/propitashka/`

### 6.2 PROfit (новый — только текст, без иконки)

**Полный дизайн-бриф + готовые AI-промпты** лежат в **[`frontend/public/brand/profit/LOGO_BRIEF.md`](frontend/public/brand/profit/LOGO_BRIEF.md)**. Там: концепция, палитра, don'ts, DALL·E/Midjourney промпты, validation-чеклист.

Краткая выжимка:
- Wordmark на базе Pobeda Bold (наш `--font-display`)
- Точка над `i` — **терракотовый стикер-круг** (рифма с `Sticker` из `DESIGN_GUIDE §4.4`)
- Под словом — **hand-drawn underline** в стиле `HandDrawnUnderline`, variant 2-3, цвет терракота, толщина 4-5px
- Два цветовых варианта: `#2E2824` на `#FFF9ED` (светлый) и `#FFF9ED` на `#2E2824` (тёмный), акцент `#D97757`
- Фавикон: только точка-стикер + буква `P`

SVG-файлы:
- `frontend/public/brand/profit/logo.svg` — полный wordmark
- `frontend/public/brand/profit/logo-dark.svg` — вариант для тёмной темы
- `frontend/public/brand/profit/wordmark.svg` — без подчёркивания, для шапки сайта
- `frontend/public/brand/profit/favicon.svg`
- `frontend/public/brand/profit/LOGO_BRIEF.md` — дизайн-бриф и AI-промпты

### 6.3 Brand-specific word forms (`askForm`)

Кроме `displayName`/`shortName`, каждый бренд несёт словоформу для обращения («Спроси X» / «Ask X») **на каждый поддерживаемый язык**. Это нужно, потому что в русском имя `Пропиташка` склоняется по падежам, а `PROfit` — нет.

- Frontend: `BrandData.askForm: Record<BrandLang, string>` + хелпер `brandAskForm(lang, data)` из `lib/brand.ts`.
- Backend: `BrandData.ask_form: dict[str, str]` + функция `brand.ask_form(lang)` из `app/brand.py`.
- API: поле `ask_form` в `GET /api/brand` (на случай RSC/middleware, которым нужны все формы сразу).

В i18n-ключах используем только «префикс» (например, `ai_hero_pre = "Спроси"`). Само имя подставляется в JSX через `brandAskForm(lang)`, так что locale-файлы остаются brand-agnostic.

**Как добавить новую формулировку:**
1. Придумать префикс на 5 языках, положить в ключ `ai_<что-то>_pre` в `locales/*.json`.
2. Если форма имени отличается от дефолтной — дополнить `askForm` словарь в `brand.config.ts` **и** `brand.py` (должны совпадать).
3. В JSX: `{t("ai_<что-то>_pre")} {brandAskForm(lang)}`.

## 7. Deploy runbook

### 7.1 Первое внедрение (один раз)

```bash
# локально
git checkout freemium-stars
git add .
git commit -m "brand: introduce dual-brand parity (PROpitashka ↔ PROfit)"
git push origin freemium-stars

# на сервере (workdir: /opt/propitashka-freemium)
ssh root@82.38.66.177
cd /opt/propitashka-freemium
git pull origin freemium-stars

# ВАЖНО: compose подставляет ${BRAND} и ${NEXT_PUBLIC_BRAND} из переменных
# shell-среды или из файла .env (БЕЗ суффикса). Наш env-файл называется
# .env.freemium — его нужно явно передать через --env-file, иначе
# переменные подставятся дефолтами из compose-файла (propitashka).
docker compose -f docker-compose.freemium.yml --env-file .env.freemium \
  up -d --build
```

### 7.2 Переключение бренда (ежедневный сценарий)

**Один скрипт делает всё:**

```bash
ssh root@82.38.66.177
cd /opt/propitashka-freemium

# → PROfit (на порту 3201)
./scripts/switch-brand.sh profit

# → PROpitashka (на том же порту 3201)
./scripts/switch-brand.sh propitashka
```

Что делает скрипт (см. `scripts/switch-brand.sh` и §9):
1. Меняет `BRAND=` и `NEXT_PUBLIC_BRAND=` в `.env.freemium`.
2. Пересобирает frontend с новым `NEXT_PUBLIC_BRAND` (~2 мин — билд-тайм).
3. Ребилдит / рестартует backend (~5–15 с — BRAND читается на каждый запрос).
4. Делает smoke-test: `curl /api/brand` → сверяет `name` с ожидаемым.

**Проверить вручную после переключения:**

```bash
# на сервере
curl -s http://localhost:3201/api/brand | python3 -m json.tool
# должно вернуть {"name":"profit", "display_name":"PROfit", ...}

# или HTML-титул
curl -s http://localhost:3201/ | grep -oE '<title>[^<]+'
# → <title>PROfit — AI-наставник по питанию и тренировкам
```

**Важные нюансы:**
- Первый пуш после обновления кода — руками: `git pull && docker compose -f docker-compose.freemium.yml --env-file .env.freemium up -d --build`. `switch-brand.sh` делает только brand-switch, не pull.
- Пока Telegram-бот один (`@PROpitashka_test_bot`), он отвечает от имени активного бренда (тексты бота брендируются из `brand.display_name()` в backend). При желании можно создать отдельного бота `@PROfit_bot` и переключать `NEXT_PUBLIC_BOT_USERNAME` + `TELEGRAM_BOT_TOKEN` через тот же `.env.freemium`.

### 7.3 Секреты

Переключение бренда не требует ввода секретов. `.env.freemium` содержит все токены для обоих брендов, на сервере никогда не редактируется руками — только скриптом.

## 8. Если выбран Вариант A (две ветки)

(Оставляю пустым до явного выбора — заполню при необходимости.)

## 9. `scripts/switch-brand.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

BRAND="${1:-}"
if [[ "$BRAND" != "profit" && "$BRAND" != "propitashka" ]]; then
  echo "usage: $0 profit|propitashka" >&2
  exit 1
fi

cd "$(dirname "$0")/.."

sed -i.bak "s/^BRAND=.*/BRAND=${BRAND}/" .env.freemium
sed -i.bak "s/^NEXT_PUBLIC_BRAND=.*/NEXT_PUBLIC_BRAND=${BRAND}/" .env.freemium
rm -f .env.freemium.bak

echo "→ switching to $BRAND"
docker compose -f docker-compose.freemium.yml up -d --force-recreate backend_freemium frontend_freemium
echo "→ done"
```

## 10. Acceptance criteria

- [ ] `BRAND=profit` запускается → `http://host:3201` отображает PROfit
- [ ] `BRAND=propitashka` запускается → тот же URL отображает PROpitashka
- [ ] Смена бренда ≤ 30 сек (Вариант 4.1)
- [ ] Ни один файл (кроме `brand.config.ts`, `brand.py`, `/public/brand/*`) не содержит литерала имени бренда
- [ ] AI-чат обращается к пользователю от лица правильного бренда (проверяется через `/api/ai/chat` с обоими значениями `BRAND`)
- [ ] Логотипы, favicon, OG-image — разные для разных брендов
- [ ] `git diff` между ветками `freemium-stars` и `main` не растёт со временем за счёт бренд-специфичных правок
- [ ] Документация `README.md` / `DEPLOYMENT_GUIDE.md` обновлена с инструкцией по переключению
