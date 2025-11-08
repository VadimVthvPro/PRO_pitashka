"""
Роутеры (обработчики) для системы тренировок
Обработка callback запросов и текстовых сообщений
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram import types
from typing import Optional
import psycopg2

# Импорты из других модулей проекта
from logger_setup import bot_logger
from app.domain.workouts.workout_service import WorkoutService
from app.presentation.bot.keyboards.workout_keyboards import WorkoutKeyboards
import main_mo as l
import keyboards as kb


# ============================================
# FSM States для тренировок
# ============================================

class WorkoutStates(StatesGroup):
    """Состояния для процесса добавления тренировки"""
    selecting_workout = State()  # Выбор тренировки из списка
    entering_duration = State()   # Ввод длительности
    entering_weight = State()      # Ввод веса (если нужно)


# ============================================
# Создание роутера
# ============================================

workout_router = Router(name='workout_router')


# ============================================
# Вспомогательные функции
# ============================================

def get_user_language(user_id: int, cursor) -> str:
    """
    Получить язык пользователя из БД
    
    Args:
        user_id: ID пользователя
        cursor: Курсор БД
        
    Returns:
        Код языка (ru, en, de, fr, es)
    """
    try:
        cursor.execute("SELECT lang FROM user_lang WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()
        return result[0] if result else 'ru'
    except Exception as e:
        bot_logger.error(f"Error getting user language: {e}")
        return 'ru'


async def send_workout_list(
    message: Message,
    user_id: int,
    page: int,
    workout_service: WorkoutService,
    cursor
):
    """
    Отправить пользователю список тренировок
    
    Args:
        message: Сообщение пользователя
        user_id: ID пользователя
        page: Номер страницы
        workout_service: Сервис тренировок
        cursor: Курсор БД
    """
    language = get_user_language(user_id, cursor)
    
    # Получаем список тренировок
    trainings = workout_service.get_training_types(language=language)
    
    if not trainings:
        await message.answer(
            l.printer(user_id, 'unhappy'),
            reply_markup=kb.keyboard(user_id, 'main_menu')
        )
        return
    
    # Создаем клавиатуру
    keyboard_gen = WorkoutKeyboards(language=language)
    keyboard = keyboard_gen.create_training_keyboard(trainings, page=page)
    
    # Отправляем сообщение
    text = l.printer(user_id, 'TrenType')
    await message.answer(text, reply_markup=keyboard)
    
    bot_logger.info(f"Sent workout list to user {user_id}, page {page}, language {language}")


async def edit_workout_list(
    callback: CallbackQuery,
    user_id: int,
    page: int,
    workout_service: WorkoutService,
    cursor
):
    """
    Редактировать сообщение со списком тренировок (при пагинации)
    
    Args:
        callback: Callback запрос
        user_id: ID пользователя
        page: Номер страницы
        workout_service: Сервис тренировок
        cursor: Курсор БД
    """
    language = get_user_language(user_id, cursor)
    
    # Получаем список тренировок
    trainings = workout_service.get_training_types(language=language)
    
    # Создаем клавиатуру
    keyboard_gen = WorkoutKeyboards(language=language)
    keyboard = keyboard_gen.create_training_keyboard(trainings, page=page)
    
    # Редактируем сообщение
    text = l.printer(user_id, 'TrenType')
    
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception as e:
        # Если не удалось отредактировать (например, контент не изменился)
        bot_logger.debug(f"Could not edit message: {e}")
    
    await callback.answer()


# ============================================
# Обработчики
# ============================================

@workout_router.message(
    F.text.in_({
        'Добавить тренировки', 
        'Añadir formación', 
        'Add training', 
        'Ajouter une formation', 
        'Ausbildung hinzufügen'
    })
)
async def start_workout_selection(
    message: Message, 
    state: FSMContext,
    db_connection,
    workout_service: WorkoutService
):
    """
    Начало процесса добавления тренировки
    Показывает список доступных тренировок
    """
    user_id = message.from_user.id
    cursor = db_connection.cursor()
    
    # Удаляем предыдущую клавиатуру
    await message.answer("⏳", reply_markup=types.ReplyKeyboardRemove())
    
    # Отправляем список тренировок
    await send_workout_list(
        message=message,
        user_id=user_id,
        page=0,
        workout_service=workout_service,
        cursor=cursor
    )
    
    # Устанавливаем состояние
    await state.set_state(WorkoutStates.selecting_workout)
    await state.update_data(current_page=0)
    
    bot_logger.info(f"User {user_id} started workout selection")


@workout_router.callback_query(F.data.startswith("workout_page_"))
async def handle_page_navigation(
    callback: CallbackQuery,
    state: FSMContext,
    db_connection,
    workout_service: WorkoutService
):
    """
    Обработка навигации по страницам списка тренировок
    """
    user_id = callback.from_user.id
    cursor = db_connection.cursor()
    
    # Парсим callback_data
    try:
        page_str = callback.data.split("_")[-1]
        if page_str == "info":
            # Это просто индикатор страницы, игнорируем
            await callback.answer()
            return
        page = int(page_str)
    except (ValueError, IndexError):
        bot_logger.error(f"Invalid page callback: {callback.data}")
        await callback.answer("❌ Ошибка")
        return
    
    # Обновляем сообщение с новой страницей
    await edit_workout_list(
        callback=callback,
        user_id=user_id,
        page=page,
        workout_service=workout_service,
        cursor=cursor
    )
    
    # Сохраняем текущую страницу
    await state.update_data(current_page=page)
    
    bot_logger.debug(f"User {user_id} navigated to page {page}")


@workout_router.callback_query(F.data.startswith("workout_") & ~F.data.contains("page") & ~F.data.contains("main_menu") & ~F.data.contains("cancel"))
async def handle_workout_selection(
    callback: CallbackQuery,
    state: FSMContext,
    db_connection,
    workout_service: WorkoutService
):
    """
    Обработка выбора конкретной тренировки
    Запрашивает длительность тренировки
    """
    user_id = callback.from_user.id
    cursor = db_connection.cursor()
    language = get_user_language(user_id, cursor)
    
    # Парсим ID тренировки
    try:
        workout_id = int(callback.data.split("_")[1])
    except (ValueError, IndexError):
        bot_logger.error(f"Invalid workout callback: {callback.data}")
        await callback.answer("❌ Ошибка")
        return
    
    # Получаем информацию о тренировке
    training = workout_service.get_training_by_id(workout_id, language)
    
    if not training:
        await callback.answer("❌ Тренировка не найдена")
        return
    
    # Сохраняем выбранную тренировку
    await state.update_data(
        selected_workout_id=workout_id,
        selected_workout_name=training['name'],
        selected_workout_emoji=training.get('emoji', '')
    )
    
    # Переходим к вводу длительности
    await state.set_state(WorkoutStates.entering_duration)
    
    # Создаем клавиатуру с кнопкой отмены
    keyboard_gen = WorkoutKeyboards(language=language)
    cancel_keyboard = keyboard_gen.create_duration_cancel_keyboard()
    
    # Отправляем запрос длительности
    emoji = training.get('emoji', '')
    workout_display_name = f"{emoji} {training['name']}" if emoji else training['name']
    
    # Подставляем название тренировки в шаблон
    duration_text = l.printer(user_id, 'trenMIN').format(workout_display_name)
    
    await callback.message.edit_text(
        duration_text,
        reply_markup=cancel_keyboard
    )
    
    await callback.answer()
    
    bot_logger.info(f"User {user_id} selected workout {workout_id}: {training['name']}")


@workout_router.message(WorkoutStates.entering_duration)
async def handle_duration_input(
    message: Message,
    state: FSMContext,
    db_connection,
    workout_service: WorkoutService
):
    """
    Обработка ввода длительности тренировки
    Рассчитывает калории и сохраняет тренировку
    """
    user_id = message.from_user.id
    cursor = db_connection.cursor()
    language = get_user_language(user_id, cursor)
    
    # Валидация длительности
    try:
        duration = int(message.text.strip())
        
        if not (1 <= duration <= 300):
            await message.answer(
                "⚠️ " + l.printer(user_id, 'trenMIN') + "\n\n(1-300 минут)"
            )
            return
    except ValueError:
        await message.answer(
            "⚠️ " + l.printer(user_id, 'trenMIN') + "\n\nВведите число."
        )
        return
    
    # Получаем данные о выбранной тренировке
    data = await state.get_data()
    workout_id = data.get('selected_workout_id')
    workout_name = data.get('selected_workout_name')
    workout_emoji = data.get('selected_workout_emoji', '')
    
    if not workout_id:
        await message.answer("❌ Ошибка: тренировка не выбрана")
        await state.clear()
        return
    
    # Проверяем наличие веса пользователя
    cursor.execute(
        "SELECT weight FROM user_health WHERE user_id = %s AND date = CURRENT_DATE",
        (user_id,)
    )
    weight_row = cursor.fetchone()
    
    if not weight_row or weight_row[0] is None:
        # Запрашиваем вес
        await message.answer(
            l.printer(user_id, 'weight')
        )
        await state.set_state(WorkoutStates.entering_weight)
        await state.update_data(duration=duration)
        return
    
    # Рассчитываем калории
    calories = workout_service.calculate_training_calories(
        training_id=workout_id,
        user_id=user_id,
        duration_minutes=duration
    )
    
    if calories is None:
        await message.answer(
            "❌ Ошибка расчета калорий. Проверьте ваши параметры (вес, рост, возраст)."
        )
        await state.clear()
        return
    
    # Сохраняем тренировку
    workout_display_name = f"{workout_emoji} {workout_name}" if workout_emoji else workout_name
    
    success = workout_service.save_training(
        user_id=user_id,
        training_id=workout_id,
        training_name=workout_display_name,
        duration_minutes=duration,
        calories=calories
    )
    
    if not success:
        await message.answer("❌ Ошибка сохранения тренировки")
        await state.clear()
        return
    
    # Получаем суммарные калории за день
    total_calories = workout_service.get_today_total_calories(user_id)
    
    # Отправляем результат
    result_text = (
        f"🎉 Отлично!\n\n"
        f"<b>{workout_display_name}</b>\n"
        f"⏱ {duration} мин\n"
        f"🔥 {calories:.1f} ккал\n\n"
        f"Всего за сегодня: <b>{total_calories:.1f} ккал</b>"
    )
    
    await message.answer(
        result_text,
        reply_markup=kb.keyboard(user_id, 'main_menu')
    )
    
    # Очищаем состояние
    await state.clear()
    
    bot_logger.info(
        f"User {user_id} completed workout: {workout_name}, "
        f"duration={duration}min, calories={calories}kcal"
    )


@workout_router.message(WorkoutStates.entering_weight)
async def handle_weight_input_for_workout(
    message: Message,
    state: FSMContext,
    db_connection,
    workout_service: WorkoutService
):
    """
    Обработка ввода веса при добавлении тренировки
    """
    user_id = message.from_user.id
    cursor = db_connection.cursor()
    
    # Валидация веса
    try:
        weight_text = message.text.strip().replace(',', '.')
        weight = float(weight_text)
        
        if not (30 <= weight <= 300):
            await message.answer(
                l.printer(user_id, 'weight') + "\n\n⚠️ (30-300 кг)"
            )
            return
    except ValueError:
        await message.answer(
            l.printer(user_id, 'weight') + "\n\n⚠️ Введите число."
        )
        return
    
    # Сохраняем вес
    try:
        cursor.execute(
            "SELECT 1 FROM user_health WHERE user_id = %s AND date = CURRENT_DATE",
            (user_id,)
        )
        exists = cursor.fetchone() is not None
        
        if exists:
            cursor.execute(
                "UPDATE user_health SET weight = %s WHERE user_id = %s AND date = CURRENT_DATE",
                (weight, user_id)
            )
        else:
            cursor.execute(
                "INSERT INTO user_health (user_id, date, weight) VALUES (%s, CURRENT_DATE, %s)",
                (user_id, weight)
            )
        db_connection.commit()
    except Exception as e:
        bot_logger.error(f"Error saving weight: {e}")
        await message.answer("❌ Ошибка сохранения веса")
        await state.clear()
        return
    
    # Возвращаемся к расчету калорий
    data = await state.get_data()
    duration = data.get('duration')
    workout_id = data.get('selected_workout_id')
    workout_name = data.get('selected_workout_name')
    workout_emoji = data.get('selected_workout_emoji', '')
    
    if not duration or not workout_id:
        await message.answer("❌ Ошибка: данные тренировки потеряны")
        await state.clear()
        return
    
    # Рассчитываем калории
    calories = workout_service.calculate_training_calories(
        training_id=workout_id,
        user_id=user_id,
        duration_minutes=duration
    )
    
    if calories is None:
        await message.answer("❌ Ошибка расчета калорий")
        await state.clear()
        return
    
    # Сохраняем тренировку
    workout_display_name = f"{workout_emoji} {workout_name}" if workout_emoji else workout_name
    
    success = workout_service.save_training(
        user_id=user_id,
        training_id=workout_id,
        training_name=workout_display_name,
        duration_minutes=duration,
        calories=calories
    )
    
    if not success:
        await message.answer("❌ Ошибка сохранения тренировки")
        await state.clear()
        return
    
    # Получаем суммарные калории за день
    total_calories = workout_service.get_today_total_calories(user_id)
    
    # Отправляем результат
    result_text = (
        f"🎉 Отлично!\n\n"
        f"<b>{workout_display_name}</b>\n"
        f"⏱ {duration} мин\n"
        f"🔥 {calories:.1f} ккал\n\n"
        f"Всего за сегодня: <b>{total_calories:.1f} ккал</b>"
    )
    
    await message.answer(
        result_text,
        reply_markup=kb.keyboard(user_id, 'main_menu')
    )
    
    # Очищаем состояние
    await state.clear()
    
    bot_logger.info(
        f"User {user_id} completed workout after weight input: {workout_name}, "
        f"duration={duration}min, calories={calories}kcal"
    )


@workout_router.callback_query(F.data == "workout_main_menu")
async def handle_main_menu_return(
    callback: CallbackQuery,
    state: FSMContext
):
    """
    Обработка возврата в главное меню
    """
    user_id = callback.from_user.id
    
    await callback.message.answer(
        "🏠 Главное меню",
        reply_markup=kb.keyboard(user_id, 'main_menu')
    )
    
    await callback.message.delete()
    await state.clear()
    await callback.answer()
    
    bot_logger.info(f"User {user_id} returned to main menu from workouts")


@workout_router.callback_query(F.data == "workout_cancel")
async def handle_workout_cancel(
    callback: CallbackQuery,
    state: FSMContext
):
    """
    Обработка отмены добавления тренировки
    """
    user_id = callback.from_user.id
    
    await callback.message.answer(
        "❌ Отменено",
        reply_markup=kb.keyboard(user_id, 'main_menu')
    )
    
    await callback.message.delete()
    await state.clear()
    await callback.answer()
    
    bot_logger.info(f"User {user_id} cancelled workout addition")


# ============================================
# Функция для регистрации роутера
# ============================================

def get_workout_router() -> Router:
    """Получить роутер для тренировок"""
    return workout_router


