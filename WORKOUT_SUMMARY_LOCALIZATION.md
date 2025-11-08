# 📋 Локализация Сводки Тренировок

Документация всех новых ключей локализации для системы сводки тренировок.

## 🌍 Поддерживаемые Языки

- 🇷🇺 Русский (ru)
- 🇬🇧 Английский (en)
- 🇩🇪 Немецкий (de)
- 🇫🇷 Французский (fr)
- 🇪🇸 Испанский (es)

## 📝 Ключи Локализации

### Сводка За День

#### `workout_summary_day_title`
**Назначение**: Заголовок сводки тренировок за текущий день

**Примеры**:
- 🇷🇺 `"🏋️ Тренировки за сегодня:"`
- 🇬🇧 `"🏋️ Today's Workouts:"`
- 🇩🇪 `"🏋️ Heutige Trainings:"`
- 🇫🇷 `"🏋️ Entraînements d'aujourd'hui :"`
- 🇪🇸 `"🏋️ Entrenamientos de hoy:"`

#### `workout_summary_day_empty`
**Назначение**: Сообщение когда нет тренировок за день

**Примеры**:
- 🇷🇺 `"Сегодня тренировок не было."`
- 🇬🇧 `"No workouts today."`
- 🇩🇪 `"Heute keine Trainings."`
- 🇫🇷 `"Aucun entraînement aujourd'hui."`
- 🇪🇸 `"No hay entrenamientos hoy."`

#### `workout_summary_day_item`
**Назначение**: Формат для отображения одной тренировки
**Параметры**: `{название} {длительность} {калории}`

**Примеры**:
- 🇷🇺 `"• {} — {} мин, {} ккал"`
- 🇬🇧 `"• {} — {} min, {} kcal"`
- 🇩🇪 `"• {} — {} Min, {} kcal"`
- 🇫🇷 `"• {} — {} min, {} kcal"`
- 🇪🇸 `"• {} — {} min, {} kcal"`

**Пример использования**:
```python
l.printer(user_id, 'workout_summary_day_item').format("Йога", 30, 120)
# Результат: "• Йога — 30 мин, 120 ккал"
```

#### `workout_summary_day_total`
**Назначение**: Итоговая сводка за день
**Параметры**: `{время} {калории}`

**Примеры**:
- 🇷🇺 `"\\n📊 Итого за день:\\n⏱ Время: {} мин\\n🔥 Калории: {} ккал"`
- 🇬🇧 `"\\n📊 Today's Total:\\n⏱ Duration: {} min\\n🔥 Calories: {} kcal"`
- 🇩🇪 `"\\n📊 Heute insgesamt:\\n⏱ Dauer: {} Min\\n🔥 Kalorien: {} kcal"`
- 🇫🇷 `"\\n📊 Total du jour :\\n⏱ Durée : {} min\\n🔥 Calories : {} kcal"`
- 🇪🇸 `"\\n📊 Total del día:\\n⏱ Duración: {} min\\n🔥 Calorías: {} kcal"`

---

### Сводка За Неделю

#### `workout_summary_week_title`
**Назначение**: Заголовок сводки тренировок за неделю

**Примеры**:
- 🇷🇺 `"🏋️ Тренировки за неделю:"`
- 🇬🇧 `"🏋️ This Week's Workouts:"`
- 🇩🇪 `"🏋️ Trainings dieser Woche:"`
- 🇫🇷 `"🏋️ Entraînements de la semaine :"`
- 🇪🇸 `"🏋️ Entrenamientos de la semana:"`

#### `workout_summary_week_empty`
**Назначение**: Сообщение когда нет тренировок за неделю

**Примеры**:
- 🇷🇺 `"На этой неделе тренировок не было."`
- 🇬🇧 `"No workouts this week."`
- 🇩🇪 `"Diese Woche keine Trainings."`
- 🇫🇷 `"Aucun entraînement cette semaine."`
- 🇪🇸 `"No hay entrenamientos esta semana."`

#### `workout_summary_week_total`
**Назначение**: Итоговая сводка за неделю
**Параметры**: `{количество} {среднее_время} {средние_калории}`

**Примеры**:
- 🇷🇺 `"\\n📊 Итого за неделю:\\n🔢 Тренировок: {}\\n⏱ Среднее время: {} мин\\n🔥 Средние калории: {} ккал/день"`
- 🇬🇧 `"\\n📊 Week's Total:\\n🔢 Workouts: {}\\n⏱ Avg duration: {} min\\n🔥 Avg calories: {} kcal/day"`
- 🇩🇪 `"\\n📊 Woche insgesamt:\\n🔢 Trainings: {}\\n⏱ Durchschn. Dauer: {} Min\\n🔥 Durchschn. Kalorien: {} kcal/Tag"`
- 🇫🇷 `"\\n📊 Total de la semaine :\\n🔢 Entraînements : {}\\n⏱ Durée moyenne : {} min\\n🔥 Calories moyennes : {} kcal/jour"`
- 🇪🇸 `"\\n📊 Total de la semana:\\n🔢 Entrenamientos: {}\\n⏱ Duración promedio: {} min\\n🔥 Calorías promedio: {} kcal/día"`

---

### Топ-5 Тренировок За Месяц

#### `workout_summary_month_title`
**Назначение**: Заголовок топ-5 тренировок за месяц

**Примеры**:
- 🇷🇺 `"🏋️ Топ-5 тренировок за месяц:"`
- 🇬🇧 `"🏋️ Top 5 Workouts This Month:"`
- 🇩🇪 `"🏋️ Top 5 Trainings dieses Monats:"`
- 🇫🇷 `"🏋️ Top 5 des entraînements du mois :"`
- 🇪🇸 `"🏋️ Top 5 de entrenamientos del mes:"`

#### `workout_summary_month_empty`
**Назначение**: Сообщение когда нет тренировок за месяц

**Примеры**:
- 🇷🇺 `"В этом месяце тренировок не было."`
- 🇬🇧 `"No workouts this month."`
- 🇩🇪 `"Diesen Monat keine Trainings."`
- 🇫🇷 `"Aucun entraînement ce mois-ci."`
- 🇪🇸 `"No hay entrenamientos este mes."`

#### `workout_summary_month_item`
**Назначение**: Формат для одного элемента топа
**Параметры**: `{номер} {название} {количество_раз} {средняя_длительность}`

**Примеры**:
- 🇷🇺 `"{}. {} — {} раз(а), {} мин в среднем"`
- 🇬🇧 `"{}. {} — {} time(s), {} min avg"`
- 🇩🇪 `"{}. {} — {} Mal, {} Min durchschn."`
- 🇫🇷 `"{}. {} — {} fois, {} min moy."`
- 🇪🇸 `"{}. {} — {} veces, {} min prom."`

**Пример использования**:
```python
l.printer(user_id, 'workout_summary_month_item').format(1, "Бег", 15, 35)
# Результат: "1. Бег — 15 раз(а), 35 мин в среднем"
```

#### `workout_summary_month_total`
**Назначение**: Итоговая сводка за месяц
**Параметры**: `{всего_тренировок} {среднее_время} {средние_калории}`

**Примеры**:
- 🇷🇺 `"\\n📊 Итого за месяц:\\n🔢 Всего тренировок: {}\\n⏱ Среднее время: {} мин\\n🔥 Средние калории: {} ккал/день"`
- 🇬🇧 `"\\n📊 Month's Total:\\n🔢 Total workouts: {}\\n⏱ Avg duration: {} min\\n🔥 Avg calories: {} kcal/day"`
- 🇩🇪 `"\\n📊 Monat insgesamt:\\n🔢 Trainings gesamt: {}\\n⏱ Durchschn. Dauer: {} Min\\n🔥 Durchschn. Kalorien: {} kcal/Tag"`
- 🇫🇷 `"\\n📊 Total du mois :\\n🔢 Total d'entraînements : {}\\n⏱ Durée moyenne : {} min\\n🔥 Calories moyennes : {} kcal/jour"`
- 🇪🇸 `"\\n📊 Total del mes:\\n🔢 Total de entrenamientos: {}\\n⏱ Duración promedio: {} min\\n🔥 Calorías promedio: {} kcal/día"`

---

### Топ-5 Тренировок За Год

#### `workout_summary_year_title`
**Назначение**: Заголовок топ-5 тренировок за год

**Примеры**:
- 🇷🇺 `"🏋️ Топ-5 тренировок за год:"`
- 🇬🇧 `"🏋️ Top 5 Workouts This Year:"`
- 🇩🇪 `"🏋️ Top 5 Trainings dieses Jahres:"`
- 🇫🇷 `"🏋️ Top 5 des entraînements de l'année :"`
- 🇪🇸 `"🏋️ Top 5 de entrenamientos del año:"`

#### `workout_summary_year_empty`
**Назначение**: Сообщение когда нет тренировок за год

**Примеры**:
- 🇷🇺 `"В этом году тренировок не было."`
- 🇬🇧 `"No workouts this year."`
- 🇩🇪 `"Dieses Jahr keine Trainings."`
- 🇫🇷 `"Aucun entraînement cette année."`
- 🇪🇸 `"No hay entrenamientos este año."`

#### `workout_summary_year_item`
**Назначение**: Формат для одного элемента топа
**Параметры**: `{номер} {название} {количество_раз} {средняя_длительность}`

**Примеры**:
- 🇷🇺 `"{}. {} — {} раз(а), {} мин в среднем"`
- 🇬🇧 `"{}. {} — {} time(s), {} min avg"`
- 🇩🇪 `"{}. {} — {} Mal, {} Min durchschn."`
- 🇫🇷 `"{}. {} — {} fois, {} min moy."`
- 🇪🇸 `"{}. {} — {} veces, {} min prom."`

#### `workout_summary_year_total`
**Назначение**: Итоговая сводка за год
**Параметры**: `{всего_тренировок} {среднее_время} {средние_калории}`

**Примеры**:
- 🇷🇺 `"\\n📊 Итого за год:\\n🔢 Всего тренировок: {}\\n⏱ Среднее время: {} мин\\n🔥 Средние калории: {} ккал/день"`
- 🇬🇧 `"\\n📊 Year's Total:\\n🔢 Total workouts: {}\\n⏱ Avg duration: {} min\\n🔥 Avg calories: {} kcal/day"`
- 🇩🇪 `"\\n📊 Jahr insgesamt:\\n🔢 Trainings gesamt: {}\\n⏱ Durchschn. Dauer: {} Min\\n🔥 Durchschn. Kalorien: {} kcal/Tag"`
- 🇫🇷 `"\\n📊 Total de l'année :\\n🔢 Total d'entraînements : {}\\n⏱ Durée moyenne : {} min\\n🔥 Calories moyennes : {} kcal/jour"`
- 🇪🇸 `"\\n📊 Total del año:\\n🔢 Total de entrenamientos: {}\\n⏱ Duración promedio: {} min\\n🔥 Calorías promedio: {} kcal/día"`

---

### Дополнительные Ключи

#### `workout_summary_avg_duration`
**Назначение**: Средняя длительность тренировки
**Параметры**: `{минуты}`

**Примеры**:
- 🇷🇺 `"⏱ Средняя длительность тренировки: {} мин"`
- 🇬🇧 `"⏱ Average workout duration: {} min"`
- 🇩🇪 `"⏱ Durchschnittliche Trainingsdauer: {} Min"`
- 🇫🇷 `"⏱ Durée moyenne d'entraînement : {} min"`
- 🇪🇸 `"⏱ Duración promedio de entrenamiento: {} min"`

#### `workout_summary_total_calories`
**Назначение**: Всего сожженных калорий
**Параметры**: `{калории}`

**Примеры**:
- 🇷🇺 `"🔥 Всего сожжено калорий: {} ккал"`
- 🇬🇧 `"🔥 Total calories burned: {} kcal"`
- 🇩🇪 `"🔥 Verbrannte Kalorien gesamt: {} kcal"`
- 🇫🇷 `"🔥 Total des calories brûlées : {} kcal"`
- 🇪🇸 `"🔥 Total de calorías quemadas: {} kcal"`

---

## 💻 Примеры Использования В Коде

### Сводка За День
```python
import main_mo as l

user_id = 123456
workouts = [("Йога", 30, 120), ("Бег", 45, 300)]

# Заголовок
message = l.printer(user_id, 'workout_summary_day_title') + "\\n\\n"

# Список тренировок
for name, duration, calories in workouts:
    message += l.printer(user_id, 'workout_summary_day_item').format(name, duration, calories) + "\\n"

# Итого
total_duration = sum(w[1] for w in workouts)
total_calories = sum(w[2] for w in workouts)
message += l.printer(user_id, 'workout_summary_day_total').format(total_duration, total_calories)

await bot.send_message(user_id, message)
```

### Топ-5 За Месяц
```python
import main_mo as l

user_id = 123456
top_workouts = [
    ("Бег", 15, 35),
    ("Йога", 12, 30),
    ("Плавание", 8, 45),
    ("Велосипед", 7, 40),
    ("Силовая", 5, 50)
]

# Заголовок
message = l.printer(user_id, 'workout_summary_month_title') + "\\n\\n"

# Топ-5
for i, (name, count, avg_duration) in enumerate(top_workouts, 1):
    message += l.printer(user_id, 'workout_summary_month_item').format(i, name, count, avg_duration) + "\\n"

# Итого
total_workouts = sum(w[1] for w in top_workouts)
avg_duration = sum(w[1] * w[2] for w in top_workouts) // total_workouts
avg_calories = 250  # Рассчитывается отдельно
message += l.printer(user_id, 'workout_summary_month_total').format(total_workouts, avg_duration, avg_calories)

await bot.send_message(user_id, message)
```

---

## 📊 SQL Запросы Для Сводки

### Тренировки За День
```sql
SELECT 
    training_name,
    duration,
    calories_burned
FROM user_training
WHERE user_id = %s 
    AND DATE(training_date) = CURRENT_DATE
ORDER BY training_date DESC;
```

### Топ-5 За Месяц
```sql
SELECT 
    training_name,
    COUNT(*) as count,
    ROUND(AVG(duration)) as avg_duration
FROM user_training
WHERE user_id = %s 
    AND training_date >= DATE_TRUNC('month', CURRENT_DATE)
GROUP BY training_name
ORDER BY count DESC
LIMIT 5;
```

### Топ-5 За Год
```sql
SELECT 
    training_name,
    COUNT(*) as count,
    ROUND(AVG(duration)) as avg_duration
FROM user_training
WHERE user_id = %s 
    AND training_date >= DATE_TRUNC('year', CURRENT_DATE)
GROUP BY training_name
ORDER BY count DESC
LIMIT 5;
```

---

## ✅ Статус Компиляции

Все локализации скомпилированы в `.mo` файлы:
- ✅ `locales/ru/LC_MESSAGES/messages.mo`
- ✅ `locales/en/LC_MESSAGES/messages.mo`
- ✅ `locales/de/LC_MESSAGES/messages.mo`
- ✅ `locales/fr/LC_MESSAGES/messages.mo`
- ✅ `locales/es/LC_MESSAGES/messages.mo`

---

## 🎉 Готово К Использованию!

Все ключи локализации добавлены и готовы к использованию в коде!

