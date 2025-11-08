# 🏋️ Новая Система Тренировок - Руководство по Интеграции

## 📋 Обзор

Создана полностью новая система управления тренировками с:
- ✅ 20 типами тренировок с мультиязычной поддержкой
- ✅ Продвинутым расчетом калорий (учет возраста, веса, роста, пола)
- ✅ Инлайн-клавиатурами с пагинацией
- ✅ Поддержкой 5 языков (ru, en, de, fr, es)
- ✅ Интеграцией с существующей системой сводки

---

## 📂 Структура Новых Файлов

```
PROpitashka/
├── migrations/
│   └── 001_create_training_system.sql      # SQL миграция
├── app/
│   ├── domain/
│   │   └── workouts/
│   │       ├── __init__.py
│   │       └── workout_service.py          # Сервис тренировок
│   └── presentation/
│       └── bot/
│           ├── keyboards/
│           │   ├── __init__.py
│           │   └── workout_keyboards.py    # Клавиатуры с пагинацией
│           └── routers/
│               └── workout_handlers.py     # Обработчики событий
```

---

## 🚀 Шаг 1: Запуск Миграции БД

### Выполните SQL миграцию:

```bash
psql -U postgres -d propitashka -f migrations/001_create_training_system.sql
```

### Что создаст миграция:

1. **Таблица `training_types`** - 20 типов тренировок с названиями на 5 языках
2. **Таблица `training_coefficients`** - Коэффициенты для расчета калорий
3. **Обновление `user_training`** - Добавлены поля `training_type_id`, `training_name`
4. **Функции PostgreSQL** - Расчет калорий с учетом всех параметров
5. **Представления** - Статистика тренировок

### Проверка успешности миграции:

```sql
-- Проверить созданные таблицы
\dt

-- Посмотреть список тренировок
SELECT id, name_ru, name_en, emoji, base_coefficient 
FROM training_types 
ORDER BY id;

-- Проверить функции
SELECT calculate_training_calories(1, YOUR_USER_ID, 30);
```

---

## 🔧 Шаг 2: Интеграция в main.py

### 2.1. Добавить импорты в начало файла:

```python
# После существующих импортов добавить:
from app.domain.workouts.workout_service import get_workout_service
from app.presentation.bot.routers.workout_handlers import get_workout_router, WorkoutStates
```

### 2.2. Создать экземпляр сервиса тренировок:

```python
# После строки с conn = psycopg2.connect(...) добавить:
workout_service = get_workout_service(conn)
```

### 2.3. Зарегистрировать роутер тренировок:

```python
# После dp = Dispatcher(storage=storage) добавить:
workout_router = get_workout_router()
dp.include_router(workout_router)
```

### 2.4. Обновить класс REG (FSM States):

```python
class REG(StatesGroup):
    # ... существующие состояния ...
    
    # УДАЛИТЬ старое состояние:
    # types = State()  # <-- УДАЛИТЬ ЭТУ СТРОКУ
    
    # Новые состояния добавлять НЕ НУЖНО - они в WorkoutStates
```

### 2.5. Удалить старые обработчики:

**УДАЛИТЬ эти функции из main.py:**

```python
# УДАЛИТЬ ВСЁ:
@dp.message(F.text.in_({'Добавить тренировки', ...}))
async def tren(message: Message, state: FSMContext):
    # ... весь код функции ...

@dp.message(REG.types)
async def tren_type(message: Message, state: FSMContext):
    # ... весь код функции ...

def intensiv(intensiv, id):
    # ... весь код функции ...
```

### 2.6. Настроить dependency injection для роутера:

Нужно передать `db_connection` и `workout_service` в middleware или через параметры роутера.

**Вариант 1: Через middleware (рекомендуется)**

```python
from aiogram import BaseMiddleware
from typing import Callable, Dict, Any, Awaitable

class DatabaseMiddleware(BaseMiddleware):
    def __init__(self, db_connection, workout_service):
        super().__init__()
        self.db_connection = db_connection
        self.workout_service = workout_service
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        data["db_connection"] = self.db_connection
        data["workout_service"] = self.workout_service
        return await handler(event, data)

# Регистрация middleware
dp.update.middleware(DatabaseMiddleware(conn, workout_service))
```

**Вариант 2: Глобальные переменные (временное решение)**

В `workout_handlers.py` в начале файла:

```python
_db_connection = None
_workout_service = None

def init_workout_handlers(db_connection, workout_service):
    global _db_connection, _workout_service
    _db_connection = db_connection
    _workout_service = workout_service
```

В `main.py`:

```python
from app.presentation.bot.routers.workout_handlers import init_workout_handlers

# После создания подключения
init_workout_handlers(conn, workout_service)
```

---

## 🗑️ Шаг 3: Удаление Старого Кода

### 3.1. В keyboards.py удалить:

```python
# УДАЛИТЬ эту клавиатуру:
tren = ReplyKeyboardMarkup(
    keyboard = [
        [
            KeyboardButton(text=l.printer_with_given(leng, "kbtren1")),
            KeyboardButton(text=l.printer_with_given(leng, "kbtren2")),
            KeyboardButton(text=l.printer_with_given(leng, "kbtren3")),
        ]
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
)

# И убрать 'tren' из словаря kb внизу файла
```

---

## 🌍 Шаг 4: Обновление Локализации

### Обновить файлы локализации (уже включено в .po файлы):

Убедитесь что в `messages.po` есть:
- `TrenType` - Выбор тренировки
- `trenMIN` - Запрос длительности
- `TrenCal` - Результат тренировки
- `weight` - Запрос веса

**НЕ НУЖНО** добавлять новые ключи - используются существующие!

---

## 📊 Шаг 5: Обновление Сводки (Опционально)

Чтобы в сводке отображались названия тренировок, обновите функцию `svodka()` в main.py:

### В секции показа тренировок за день:

```python
# БЫЛО:
cursor.execute("""
    SELECT COALESCE(SUM(training_cal), 0), COALESCE(SUM(tren_time), 0)
    FROM user_training 
    WHERE date = CURRENT_DATE AND user_id = %s
""", (user_id,))

# СТАЛО:
cursor.execute("""
    SELECT 
        training_name,
        tren_time,
        training_cal
    FROM user_training 
    WHERE date = CURRENT_DATE AND user_id = %s
    ORDER BY id DESC
""", (user_id,))
trainings_today = cursor.fetchall()

# Форматирование списка тренировок
if trainings_today:
    training_list = "\n".join([
        f"• {row[0]}: {row[1]} мин, {row[2]:.1f} ккал"
        for row in trainings_today
    ])
    total_training_cal = sum(row[2] for row in trainings_today)
else:
    training_list = "Нет тренировок"
    total_training_cal = 0
```

---

## ✅ Шаг 6: Тестирование

### Тестовый сценарий:

1. **Запуск бота**: `python main.py`
2. **Выбор языка**: Проверить для ru/en/de/fr/es
3. **Добавление тренировки**:
   - Нажать "Добавить тренировки"
   - Проверить пагинацию (должно быть 3-4 страницы с 20 тренировками)
   - Выбрать тренировку
   - Ввести длительность
   - Проверить результат
4. **Проверка сводки**: Убедиться, что тренировка отображается
5. **Проверка БД**:
   ```sql
   SELECT * FROM user_training WHERE user_id = YOUR_ID ORDER BY date DESC LIMIT 5;
   ```

### Проверка разных языков:

```sql
-- Английский
SELECT name_en FROM training_types LIMIT 5;

-- Немецкий
SELECT name_de FROM training_types LIMIT 5;

-- Французский
SELECT name_fr FROM training_types LIMIT 5;

-- Испанский
SELECT name_es FROM training_types LIMIT 5;
```

---

## 🐛 Решение Проблем

### Проблема: "Тренировки не отображаются"

**Решение:**
```sql
SELECT COUNT(*) FROM training_types WHERE is_active = TRUE;
-- Должно быть 20
```

### Проблема: "Ошибка расчета калорий"

**Решение:**
```sql
-- Проверить параметры пользователя
SELECT * FROM user_health WHERE user_id = YOUR_ID ORDER BY date DESC LIMIT 1;
SELECT * FROM user_main WHERE user_id = YOUR_ID;

-- Проверить функцию расчета
SELECT calculate_training_calories(1, YOUR_ID, 30);
```

### Проблема: "Кнопки не работают"

**Решение:**
- Проверить регистрацию роутера: `dp.include_router(workout_router)`
- Проверить dependency injection (db_connection, workout_service)
- Проверить логи: `tail -f bot.log`

### Проблема: "Пагинация не работает"

**Решение:**
```python
# Убедитесь что обработчик зарегистрирован:
@workout_router.callback_query(F.data.startswith("workout_page_"))
async def handle_page_navigation(...):
    ...
```

---

## 📈 Статистика и Мониторинг

### Просмотр статистики тренировок:

```sql
-- Топ тренировок
SELECT * FROM v_training_statistics ORDER BY total_sessions DESC;

-- Активность пользователя
SELECT 
    user_id,
    COUNT(*) as total_workouts,
    SUM(tren_time) as total_minutes,
    SUM(training_cal) as total_calories
FROM user_training
WHERE date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY user_id
ORDER BY total_workouts DESC;
```

---

## 🔄 Откат Изменений (если нужно)

Если что-то пошло не так:

```sql
-- Откат миграции
DROP TABLE IF EXISTS training_coefficients CASCADE;
DROP TABLE IF EXISTS training_types CASCADE;
DROP FUNCTION IF EXISTS calculate_training_calories;
DROP FUNCTION IF EXISTS get_age_group_modifier;
DROP FUNCTION IF EXISTS get_weight_category_modifier;
DROP FUNCTION IF EXISTS get_height_category_modifier;
DROP FUNCTION IF EXISTS get_gender_modifier;

-- Восстановить старую структуру user_training
ALTER TABLE user_training DROP COLUMN IF EXISTS training_type_id;
ALTER TABLE user_training DROP COLUMN IF EXISTS training_name;
ALTER TABLE user_training DROP COLUMN IF EXISTS updated_at;
```

---

## 📝 Следующие Шаги

1. ✅ Выполнить миграцию БД
2. ✅ Интегрировать код в main.py
3. ✅ Удалить старые обработчики
4. ✅ Протестировать на всех языках
5. ⏳ Обновить сводку (опционально)
6. ⏳ Добавить аналитику тренировок
7. ⏳ Создать админ-панель для управления тренировками

---

## 🎯 Основные Преимущества Новой Системы

1. **Точный расчет калорий** - Учитывает все параметры пользователя
2. **Масштабируемость** - Легко добавить новые тренировки через БД
3. **Мультиязычность** - Полная поддержка 5 языков
4. **UX** - Удобная пагинация и навигация
5. **Расширяемость** - Модульная архитектура

---

## 🆘 Поддержка

При возникновении проблем:
1. Проверьте логи: `tail -f bot.log`
2. Проверьте БД: SQL запросы выше
3. Проверьте middleware и dependency injection
4. Создайте issue с описанием проблемы


