# PROfit — Logo Brief & Prompts

> Бриф на логотип `PROfit` и готовые промпты для AI-генераторов (DALL·E 3, Midjourney, Imagen).
> Текущие SVG-ассеты собраны программно из примитивов дизайн-системы (см. §2). Этот документ нужен, если вы захотите сгенерировать **альтернативу через AI** и потом вручную подогнать под сетку.

---

## 0. TL;DR — чего хотим

`PROfit` — **только текст, никаких абстрактных иконок**. Единственная «графика» — терракотовая точка-стикер и hand-drawn подчёркивание. Логотип должен **физически рифмоваться** с PROpitashka: одинаковый шрифт, одинаковая терракота, одинаковая рукописная манера. Пользователь не должен думать «это два разных продукта» — должен думать «это один бренд, две реинкарнации».

---

## 1. Source of truth

| Где | Что |
|---|---|
| `DESIGN_GUIDE.md` §3 (типографика) | `Pobeda Bold` как display-шрифт. Используется и в PROpitashka, и в PROfit. |
| `DESIGN_GUIDE.md` §4.4 (Sticker) | Форма стикер-круга, терракотовый акцент `#D97757` |
| `DESIGN_GUIDE.md` §4 (HandDrawnUnderline) | Rough-manner подчёркивания: `variant 2–3`, толщина 4–5px |
| `BRAND_ARCHITECTURE.md` §6.2 | Архитектурные решения по ассетам |
| `frontend/public/brand/profit/*.svg` | **Текущие работающие SVG** (их забирает Docker-билд) |

**Палитра (фиксированная, не менять без обновления `--accent`):**

| Роль | Цвет | HEX | Токен |
|---|---|---|---|
| Текст (светлая тема) | Кофейный чёрный | `#2E2824` | `--fg` |
| Акцент (точка, подчёркивание) | Терракота | `#D97757` | `--accent` |
| Фон (светлая тема) | Крем | `#FFF9ED` | `--bg` |
| Текст (тёмная тема) | Крем | `#FFF9ED` | `--fg-dark` |
| Фон (тёмная тема) | Кофейный чёрный | `#2E2824` | `--bg-dark` |

---

## 2. Концепция (что собрано в `logo.svg`)

```
PROfit.
────── ← HandDrawnUnderline, цвет #D97757, variant 2-3, weight 4-5px
```

1. **Wordmark** — слово `PROfit`, шрифт **Pobeda Bold**, `font-size: 96px` в логотипе-эталоне.
2. **Кейсинг** — `PRO` капсом (подчёркивает "профессиональное"), `fit` — lowercase (подчёркивает мягкий AI-companion-тон). **`f`, `i`, `t` по высоте x-height** — контраст к заглавным.
3. **Точка-стикер** над `i`:
   - Форма — идеальный круг, **диаметр ≈ 0.55em** (по x-height).
   - Цвет — терракота `#D97757`.
   - Лёгкий наклон фигуры 4–6° (имитация наклеенного стикера).
4. **Hand-drawn underline** под всем словом:
   - Вариант из `components/hand/HandDrawnUnderline.tsx` (variant `2` или `3`).
   - Цвет — терракота.
   - Толщина 4–5px при высоте wordmark 96px.
5. **Завершающая точка** после слова (опционально) — **та же терракота**, форма — сплющенный квадрат как в существующем PROpitashka-логотипе (рифма).
6. **Без теней, без градиентов, без outline.** Flat, как плакат.

### 2.1 Варианты, которые уже лежат в репо

| Файл | Когда использовать |
|---|---|
| `logo.svg` | Полный wordmark + подчёркивание, для заглушек и OG-изображений |
| `logo-dark.svg` | То же, для тёмной темы (инвертирован текст) |
| `wordmark.svg` | **Только слово без подчёркивания** — для шапки сайта, где над логотипом идёт навигация |
| `favicon.svg` | Только точка-стикер + буква **`P`** (весь `PROfit` не читается в 16×16) |

---

## 3. Don'ts

**Запрещено:**
- Рисовать фигурки человечков, еды, гантель, графиков, «взлетающих стрелок», плюсиков, галочек.
- Использовать любой шрифт кроме `Pobeda Bold` в логотипе.
- Делать градиенты по тексту/точке.
- Делать точку над `i` фотореалистичной (ягода/яблоко/апельсин) — это стикер, не фрукт.
- Использовать синий, зелёный, фиолетовый. **Только терракота `#D97757` как акцент.**
- Stylize `PROFIT` капсом полностью — это ломает «мягкий» AI-companion-тон.
- Stylize `Profit` полным title-case — теряется рифма с `PROpitashka` (где тоже `PRO` капсом).

---

## 4. AI-промпты (если захотим сгенерировать альтернативу)

> **Важно.** AI-генератор выдаст растровую картинку. Это — для moodboard/референсов. Прод-ассет всё равно пересобирается в SVG вручную из примитивов.

### 4.1 DALL·E 3 / ChatGPT Image

```
Minimalist wordmark logo for a wellness app called "PROfit".
Text-only, no illustrations, no icons, no symbols, no characters.
Typography: heavy sans-serif display font, similar to "Pobeda Bold" —
geometric, slightly condensed, strong verticals.
Case mix: "PRO" in uppercase, "fit" in lowercase (x-height letters).
Color: coffee-black text (#2E2824) on a cream background (#FFF9ED).
The dot over the lowercase "i" is replaced with a terracotta (#D97757)
sticker-circle, slightly rotated 5 degrees as if stuck on.
Below the word, a single hand-drawn wobbly underline in the same
terracotta color, thickness roughly 5px relative to the wordmark height.
No shadow. No gradient. No outline. No frame. No tagline.
Flat, poster-like, Scandinavian editorial feel.
Aspect ratio 16:9, lots of negative space around the wordmark.
```

### 4.2 Midjourney v6

```
PROfit wordmark logo, text-only, heavy geometric sans-serif display font,
"PRO" uppercase + "fit" lowercase, coffee-black type on cream background,
terracotta sticker-dot over the i, rough hand-drawn terracotta underline
beneath the word, flat poster style, Scandinavian editorial,
no illustration, no icon, no mascot --ar 16:9 --style raw --stylize 150
```

**Параметры:**
- `--ar 16:9` — пропорции как у `og-image.png`.
- `--style raw` — убирает «MJ-залипуху» с кинематографичным светом.
- `--stylize 150` — умеренная стилизация, чтобы не сильно отходить от брифа.

### 4.3 Референс-промпт для parity-проверки с PROpitashka

Если будете генерировать **пару** (Profit + Propitashka) в одной сессии:

```
Two wordmark logos side by side, identical typographic treatment:
heavy geometric sans-serif, coffee-black on cream,
terracotta sticker-dot over the i in each word,
rough hand-drawn terracotta underline beneath each.
Left: "PROpitashka" | Right: "PROfit".
Both wordmarks share the same x-height, baseline, and optical weight.
Flat, poster-like, no illustrations, no icons, no mascots,
ample negative space. --ar 21:9 --style raw
```

---

## 5. Validation checklist

Перед тем как замёржить новую версию лого:

- [ ] Wordmark собран в `Pobeda Bold` (не Inter, не Geist, не SF).
- [ ] Точка над `i` — ровный круг терракоты `#D97757`, не овал, не сердечко.
- [ ] Подчёркивание rough-manner (видны шероховатости), не прямая линия.
- [ ] Работает на `#FFF9ED` **и** на `#2E2824` (есть светлый и тёмный варианты).
- [ ] Favicon читается в 16×16 и 32×32 (там только `P` + dot).
- [ ] SVG оптимизирован (SVGO): без id, без data-name, без inline style.
- [ ] Размер каждого SVG ≤ 3 KB.
- [ ] Пара с PROpitashka-логотипом визуально согласована (один шрифт, одна точка, одно подчёркивание).

---

## 6. Куда класть новые версии

1. Перезаписать файлы в `frontend/public/brand/profit/`.
2. Прогнать `docker compose -f docker-compose.freemium.yml build frontend` (рестарт ≈ 2–3 мин — фронт ребилдится из-за `NEXT_PUBLIC_BRAND`).
3. Проверить на прод-домене, что favicon и OG в шапке свежие (Ctrl+F5).

**Секреты.** Логотипы — публичные ассеты, коммитим открыто. Никогда не кладите в этот же каталог `.env`, ключи, токены — только SVG/PNG/ICO.
