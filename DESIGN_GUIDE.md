# PROpitashka — Design & Code Guide

> Practical rules for adding pages, components, features — so it all feels
> like one hand drew it.
> Дополнение к `DESIGN.md` (он описывает **что** мы делаем; этот файл — **как**).

---

## 0. Главный принцип

Сайт не должен выглядеть как сгенерированный нейросетью. Это значит:

- Нет идеальной симметрии. 1 крупный элемент + 3 мелких лучше, чем 4 равных.
- Нет "чистых" выровненных блоков без акцентов. Наклони стикер на `-3deg`, повтори слово в `Arkhip`.
- Копирайт всегда живой: не "Сегодняшние калории" — а "Съел сегодня".
- Любое число, которое меняется, анимируем через `AnimatedNumber`.
- Любой новый раздел получает хотя бы один hand-drawn акцент.

---

## 1. Файловая структура (frontend)

```
frontend/src/
├── app/
│   ├── (auth)/login/              # Страницы без Sidebar
│   ├── (app)/<route>/page.tsx     # Страницы с Sidebar + BottomNav
│   └── layout.tsx                 # Шрифты, grain, transitions
├── components/
│   ├── hand/          # HandDrawnUnderline, Sticker, Highlight, HandArrow, Scribble
│   ├── motion/        # AnimatedNumber, ScrollReveal, PageTransition, TiltCard, confetti
│   ├── streak/        # StreakFlame, BadgeToast
│   ├── dashboard/     # MetricCard и подобное
│   ├── layout/        # Sidebar, BottomNav
│   └── water/         # WaterWave и прочее доменное
├── lib/
│   ├── api.ts         # fetch wrapper с auto-refresh
│   ├── copy.ts        # Живые тексты (greeting, empty state, …)
│   ├── streaks.ts     # Store streak+badges, handleActivityResponse()
│   └── i18n.ts
└── app/globals.css    # Все CSS-переменные, keyframes, utility-классы
```

**Правило:** новый доменный компонент — в папку по домену (`components/water/`, `components/food/`). Общие motion-примитивы — в `motion/`. Украшения — в `hand/`.

---

## 2. Шрифты

В `app/layout.tsx` уже подключены:

| Переменная             | Файл              | Когда использовать                                                |
| ---------------------- | ----------------- | ------------------------------------------------------------------ |
| `--font-display`       | `pobeda-bold.ttf` | Любой крупный текст: заголовки, числа, hero-манифест              |
| `--font-body`          | DM Sans           | Обычный текст, кнопки, labels                                     |
| `--font-mono`          | JetBrains Mono    | Цифры в дневнике, OTP-коды                                        |
| `--font-arkhip-stack`  | `arkhip.ttf`      | Рукописные заметки, цитаты, "заметка дня"                         |
| `--font-appetite-stack`| `appetite.ttf`    | Маленькие шутливые акценты в стикерах                             |

### Утилиты (уже есть в `globals.css`)

- `.page-title` — единый стиль для `<h1>` всех страниц
- `.page-subtitle` — подзаголовок
- `.display-number` — для анимируемых цифр (tabular-nums + Pobeda)
- `.font-display` — Pobeda напрямую

**Никогда не ставь `font-family: ...` вручную, если уже есть утилита.**

---

## 3. Цвета

Пользуйся только CSS-переменными из `globals.css`:

```css
var(--foreground)       /* основной текст */
var(--muted)            /* вторичный текст */
var(--muted-foreground) /* третичный, подписи */
var(--accent)           /* основной акцент */
var(--warning)          /* огонь, streak */
var(--destructive)      /* ошибки, at_risk */
var(--card) / --card-border
var(--input-bg) / --border
var(--color-sand) / --color-cream / --color-sage / --color-latte
```

Никогда не пиши `text-amber-500`, `bg-slate-900`. Всегда `text-[var(--warning)]` или `bg-[var(--color-sand)]`.

---

## 4. Обязательные примитивы для новой страницы

### 4.1 Заголовок

```tsx
<h1 className="page-title">
  Что-то{" "}
  <Highlight color="oklch(72% 0.15 80 / 0.5)">
    <span className="px-1">живое</span>
  </Highlight>
</h1>
```

### 4.2 Подзаголовок с контекстом

Используй `lib/copy.ts`:

```tsx
import { greeting, heroSubtitle } from "@/lib/copy";
// ...
const hello = greeting();
const subtitle = heroSubtitle();
```

Не пиши генерические "Welcome back" — используй заготовки из `copy.ts` или добавляй новые туда.

### 4.3 Hero с hand-drawn underline

```tsx
<span className="relative inline-block">
  <span className="text-[var(--accent)]">{name}</span>
  <HandDrawnUnderline
    color="var(--accent)"
    strokeWidth={4}
    variant={((name.length % 4) + 1) as 1|2|3|4}
    className="absolute left-0 -bottom-2 w-full h-3"
  />
</span>
```

### 4.4 Стикеры для акцентов

```tsx
<Sticker color="amber" font="appetite" rotate={-3} size="md">
  1 минута
</Sticker>
```

Цвета: `amber | sage | cream | sky | rose`. Шрифты: `display | arkhip | appetite`. Не перегружай страницу — 2-3 стикера максимум.

### 4.5 Empty state — всегда живой

```tsx
<div className="flex items-center gap-6 py-6">
  <Scribble variant="empty-plate" className="w-28 h-28 text-[var(--color-latte)]" />
  <div>
    <p className="text-2xl font-display">{EMPTY_COPY.food_today.title}</p>
    <p className="text-sm text-[var(--muted-foreground)] mt-1 max-w-[48ch]">
      {EMPTY_COPY.food_today.subtitle}
    </p>
  </div>
</div>
```

Варианты `Scribble`: `squiggle | empty-plate | empty-dumbbell | circle | zigzag`.

### 4.6 Scroll reveal + stagger

```tsx
<ScrollReveal delay={0.1}>
  <Stagger className="grid grid-cols-3 gap-4">
    {items.map(item => (
      <StaggerItem key={item.id}>
        <Card {...item} />
      </StaggerItem>
    ))}
  </Stagger>
</ScrollReveal>
```

### 4.7 Анимируемые числа

```tsx
<span className="display-number text-6xl">
  <AnimatedNumber value={totalCalories} />
</span>
```

---

## 5. Карточки

Не пиши стиль карточек руками. Используй `.card-base` + `.card-hover`:

```tsx
<div className="card-base card-hover p-6">
  ...
</div>
```

Для метрик на dashboard — `MetricCard` с опцией `big` для hero-метрики.

---

## 6. API-интеграция

### 6.1 `api<T>()` — всегда через обёртку

```tsx
import { api } from "@/lib/api";
const data = await api<UserDTO>("/api/users/me");
```

Обёртка сама:
- добавляет `credentials: "include"`
- бросает `Error` с сообщением из бэкенда
- авто-рефрешит токен при 401
- редиректит на `/login` если refresh не прошёл

### 6.2 Любой POST — прогоняем через `handleActivityResponse`

Эндпоинты `/api/water`, `/api/food`, `/api/workouts`, `/api/food/repeat` возвращают `{ streak, newly_earned_badges }`. Подключи это один раз:

```tsx
import { handleActivityResponse } from "@/lib/streaks";
const res = await api<MyResp>("/api/endpoint", { method: "POST", body: ... });
handleActivityResponse(res);
```

Дальше автоматом обновится пламя в sidebar и вылезут toasts.

### 6.3 Бэкенд — правила

- Любой action-endpoint, после сохранения в БД, обязан позвать `streak_service.touch_activity(pool, user_id)` если `target_date == today`.
- Возвращаемый dict должен включать `streak` и `newly_earned_badges` (может быть `None`/`[]`).
- Не писать SQL руками в роутерах — всегда через `*Repository`.

---

## 7. Motion-правила

1. **Entrance** — через `ScrollReveal`/`Stagger`, без исключений.
2. **Numeric changes** — `AnimatedNumber`.
3. **State toggles** — `motion.div` с `layoutId` и `spring` (stiffness 300-400, damping 20-28).
4. **Route transitions** — уже подключён `PageTransition`, его ничего делать не надо.
5. **Celebrations** — `fireConfetti({ y: 0.4 })` при достижении цели.
6. **Reduced motion** — каждый новый motion-component проверяет `useReducedMotion()`. Без исключений.

---

## 8. Бэкенд-правила

### 8.1 Новая миграция

```
backend/alembic/versions/NNN_description.py
```

Нумерация последовательная. `down_revision` ссылается на предыдущую. Применять:

```bash
cd backend && alembic upgrade head
```

### 8.2 Репозиторий

Все SQL — в `backend/app/repositories/*_repo.py`. В роутере — только бизнес-логика. `$1, $2, $3` параметры (не f-string). Никогда не конкатенируем пользовательский ввод в SQL.

### 8.3 Новый роутер

1. Создать файл `backend/app/routers/<name>.py`.
2. Импортировать и зарегистрировать в `backend/app/main.py`:
   ```python
   app.include_router(name.router, prefix="/api/name", tags=["name"])
   ```
3. Pydantic-модели — в `backend/app/models/<name>.py`.

### 8.4 Streak integration

Любой новый "реальный" action (запись в дневник):

```python
from app.services import streak_service
# ... сохранили в БД ...
if target_date == date.today():
    update = await streak_service.touch_activity(db, user_id)
    streak = {...}
    new_badges = update.newly_earned_badges
return {..., "streak": streak, "newly_earned_badges": new_badges}
```

---

## 9. Добавление новой ачивки

1. Добавь строку в `backend/alembic/versions/004_streaks_badges.py` или новой миграции (обычно новая):

   ```sql
   INSERT INTO badges (code, title, description, icon, tier, category, sort_order)
   VALUES ('my_code', 'Название', 'Описание', 'solar:icon-bold-duotone', 'silver', 'food', 250);
   ```

2. Добавь условие в `backend/app/services/streak_service.py::_evaluate_badges`:

   ```python
   if await repo.my_condition(user_id):
       await try_grant("my_code")
   ```

3. Если нужен новый запрос — добавь метод в `StreakRepository`.

Tier styles берутся автоматически из `BadgeToast` / `/achievements`.

---

## 10. Иконки

Используем только `@iconify/react` с пакетом `@iconify-json/solar` (стиль `bold-duotone`).

```tsx
import { Icon } from "@iconify/react";
<Icon icon="solar:fire-bold-duotone" width={24} />
```

Не импортируем из `lucide-react`, `react-icons`, никаких эмодзи в UI (в копирайте можно, если очень уместно).

Список часто используемых иконок:

- `solar:home-2-bold-duotone` — главная
- `solar:plate-bold-duotone` — еда
- `solar:dumbbell-large-bold-duotone` — тренировки
- `solar:cup-bold-duotone` — вода
- `solar:graph-new-up-bold-duotone` — прогресс
- `solar:magic-stick-3-bold-duotone` — AI
- `solar:fire-bold-duotone` — streak
- `solar:medal-ribbon-star-bold-duotone` — достижения
- `solar:refresh-circle-bold-duotone` — повторить
- `solar:add-circle-bold-duotone` — добавить
- `solar:camera-bold-duotone` — фото
- `solar:pen-bold-duotone` — вручную

---

## 11. Доступность и респонсив

- Мобильные страницы не имеют сайдбара, только `BottomNav` (до `lg:`).
- Любой input должен уметь ужиматься: `min-w-0`, `size={1}` (для OTP). Flex без `min-w-0` на inputах ломает layout.
- `aria-hidden` — для декоративных SVG.
- Кнопки — минимум 44px высоты.
- OTP и подобные цифровые поля — `inputMode="numeric"`, `autoComplete="one-time-code"`.

---

## 12. Чеклист перед коммитом

- [ ] ReadLints чист
- [ ] Страница использует `.page-title` или `page-title` style
- [ ] Заголовок содержит `Highlight` / `HandDrawnUnderline` / стикер
- [ ] Есть хотя бы один empty state с `Scribble`
- [ ] Числа через `AnimatedNumber`
- [ ] Entrance-анимация через `ScrollReveal` или `Stagger`
- [ ] POST-запросы прогнаны через `handleActivityResponse`
- [ ] `useReducedMotion()` проверяется в любых animate
- [ ] Нет захардкоженных цветов — только CSS-переменные
- [ ] Иконки из `solar:*-bold-duotone`
- [ ] Копирайт живой, не AI-slop

---

## 13. Что нельзя (Anti-patterns)

- Gradient text, glassmorphism, фиолетовые градиенты, cyan-on-dark
- Карточки внутри карточек внутри карточек
- "Hero metric + 3 равных stat" (скучно). Делай асимметрию.
- Загружать внешние шрифты с Google Fonts — у нас все локальные
- Inline-стили для цветов / шрифтов / размеров, когда есть utility
- Копирайт-заглушки вроде `Welcome back, {user}!`, `Lorem ipsum`
- Модалки без `AnimatePresence`
- Spinner из `lucide-react::Loader2` — используй skeleton или Solar-иконку
- Оставлять спаны `w-full` на flex inputах без `min-w-0`
