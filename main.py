import psycopg2
from aiogram.filters import CommandStart
from aiogram.client.bot import DefaultBotProperties
from aiogram.enums import ParseMode
import base64
import json
from aiogram.filters import StateFilter
from config import config
import keyboards as kb
import asyncio
import datetime
from datetime import date
from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.types import Message, FSInputFile, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# Импорты для новой системы тренировок
from app.domain.workouts.workout_service import get_workout_service
from app.presentation.bot.routers.workout_handlers import get_workout_router, WorkoutStates
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command
import main_mo as l
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from translate import Translator
import requests
import re
from typing import Callable, Dict, Any, Awaitable
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.types import TelegramObject
import functools
import redis.asyncio as redis
import food_database_fallback as food_db
import google.generativeai as genai
import google.genai as genai_new
from logger_setup import bot_logger

# Импорты для календаря
from app.presentation.utils.calendar_utils import CalendarKeyboard, get_calendar_keyboard
from app.domain.calendar.calendar_service import CalendarService, calendar_cache

# ============================================
# Google Gemini Setup
# ============================================
if config.GEMINI_API_KEY:
    import os
    os.environ['GOOGLE_API_KEY'] = config.GEMINI_API_KEY
    
    # Для текстовой генерации используем старый API
    genai.configure(api_key=config.GEMINI_API_KEY)
    
    # Для загрузки файлов (фото) используем новый API
    gemini_client = genai_new.Client(api_key=config.GEMINI_API_KEY)
    
    bot_logger.info("Gemini API configured successfully with gemini-2.5-flash model (new API)")
else:
    bot_logger.error("GEMINI_API_KEY not found in .env file!")
    gemini_client = None


# ============================================
# Redis Cache Setup (опциональный)
# ============================================
try:
    redis_client = redis.from_url(config.get_redis_url(), decode_responses=True)
    REDIS_AVAILABLE = True
    bot_logger.info("Redis connection configured successfully")
except Exception as e:
    redis_client = None
    REDIS_AVAILABLE = False
    bot_logger.warning(f"Redis not available, caching disabled: {e}")

async def get_from_cache(key: str):
    """Get data from Redis cache (optional)."""
    if not REDIS_AVAILABLE or redis_client is None:
        return None
    try:
        return await redis_client.get(key)
    except Exception as e:
        bot_logger.warning(f"Redis get error for key {key}: {e}")
        return None

async def set_to_cache(key: str, value: str, ttl: int):
    """Set data to Redis cache with a TTL (optional)."""
    if not REDIS_AVAILABLE or redis_client is None:
        return False
    try:
        await redis_client.set(key, value, ex=ttl)
        return True
    except Exception as e:
        bot_logger.warning(f"Redis set error for key {key}: {e}")
        return False


# ============================================
# Retry Decorator
# ============================================
def async_retry(max_attempts: int, delay: float, exceptions: tuple):
    """
    Декоратор для повторного выполнения асинхронной функции при возникновении исключений.
    """
    def decorator(async_func):
        @functools.wraps(async_func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return await async_func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts - 1:
                        raise  # Последняя попытка, пробрасываем исключение
                    print(f"Попытка {attempt + 1}/{max_attempts} не удалась: {e}. Повтор через {delay} сек.")
                    await asyncio.sleep(delay)
        return wrapper
    return decorator

GIF_LIBRARY = {
    "Жим штанги лёжа": "https://i.giphy.com/media/v1.Y2lkPTc5MGI3NjExcnIycmluczlwMG92cXV0N3BpbG14ajdibzNxa2owc3M5N3U2cTNleCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/3tCMXFyNBabv8f6DoW/giphy.gif",
}

# GigaChat, DeepSeek, YandexGPT - удалены, используется только Gemini

# ============================================
# Middleware for Privacy Consent
# ============================================
class PrivacyConsentMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Мы хотим проверить только сообщения и колбэки от пользователей
        if not isinstance(event, (types.Message, types.CallbackQuery)):
            return await handler(event, data)

        user_id = event.from_user.id
        
        # Пропускаем команду /start и ответы на запрос согласия
        if isinstance(event, types.Message) and event.text and event.text.startswith('/start'):
            return await handler(event, data)
        if isinstance(event, types.CallbackQuery) and event.data in ['accept_privacy', 'decline_privacy']:
            return await handler(event, data)

        # Проверяем согласие в базе данных
        cursor.execute("SELECT privacy_consent_given FROM user_main WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()

        if not result or not result[0]:
            # Если согласия нет, отправляем напоминание
            await bot.send_message(
                user_id,
                "Пожалуйста, дайте свое согласие на обработку персональных данных, чтобы продолжить. "
                "Отправьте /start, чтобы увидеть запрос снова.",
                reply_markup=kb.privacy_consent_keyboard()
            )
            return  # Блокируем дальнейшую обработку

        # Если согласие есть, продолжаем
        return await handler(event, data)

languages = {'Русский 🇷🇺': 'ru', 'English 🇬🇧': 'en', 'Deutsch 🇩🇪': 'de', 'Française 🇫🇷': 'fr', 'Spanish 🇪🇸': 'es'}
llaallallaa = {'ru': 'Русский 🇷🇺', 'en': 'English 🇬🇧', 'de': 'Deutsch 🇩🇪', 'fr': 'Française 🇫🇷', 'es': 'Spanish 🇪🇸'}

tren_list = [["Жим штанги лёжа", "Bench press", "Banc de musculation", "Bankdrücken", "Press de banca"],
             ["Подъём на бицепс", "Curl de bíceps", "Bizepscurl", "Flexion des biceps", "Biceps curl"],
             ["Подтягивания", "Pull-ups", "Tractions", "Klimmzüge", "Pull-ups"]]

TOKEN = config.TELEGRAM_TOKEN





# ============================================
# Middleware для Dependency Injection
# ============================================

class DatabaseMiddleware(BaseMiddleware):
    """Middleware для передачи db_connection и workout_service в обработчики"""
    
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


# Подключение к БД и создание сервисов
conn = psycopg2.connect(**config.get_db_config())
conn.autocommit = True  # Включаем автокоммит для немедленного сохранения данных
cursor = conn.cursor()

# Создание сервиса тренировок
workout_service = get_workout_service(conn)
bot_logger.info("Database connection established with autocommit enabled")

bot = Bot(TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Регистрация роутера тренировок
workout_router = get_workout_router()
dp.include_router(workout_router)

# Register middleware
dp.update.middleware(PrivacyConsentMiddleware())
dp.update.middleware(DatabaseMiddleware(conn, workout_service))

# ВАЖНО: Регистрируем AI chat router ПОСЛЕДНИМ, чтобы он обрабатывал
# только те сообщения, которые не обработали другие хэндлеры
# ai_chat_router будет определен в конце файла перед main()
# и зарегистрирован здесь после инициализации всех хэндлеров


class REG(StatesGroup):
    height = State()
    age = State()
    age_calendar = State()  # Новое состояние для выбора даты в календаре
    sex = State()
    want = State()
    weight = State()
    length = State()
    food = State()
    food_list = State()
    food_photo = State()
    grams = State()
    food_meals = State()
    train = State()
    tren_choiser = State()
    svo = State()
    leng = State()
    leng2 = State()
    grams1 = State()
    new_weight = State()
    tren_ai = State()
    new_height = State()
    ai_ans = State()


@dp.message(CommandStart())
async def command_start(message: Message, state: FSMContext):
    """Handles the /start command - shows language selection first."""
    user_id = message.from_user.id
    bot_logger.info(f"User {user_id} (@{message.from_user.username}) sent /start")
    
    # ВАЖНО: Очищаем состояние FSM при старте
    await state.clear()
    bot_logger.info(f"FSM state cleared for user {user_id} on /start")
    
    # Извлекаем и парсим deep link параметры
    start_payload = message.text.split(' ')[1] if len(message.text.split(' ')) > 1 else None
    utm_source, utm_medium, utm_campaign, ref_code = None, None, None, None

    if start_payload:
        params = start_payload.split('_')
        if params[0] == 'ref' and len(params) > 1:
            ref_code = params[1]
            utm_source = params[1]
        elif params[0] == 'utm' and len(params) >= 4:
            utm_source = params[1]
            utm_medium = params[2]
            utm_campaign = params[3]

    # Создаем или обновляем пользователя в БД
    cursor.execute("SELECT privacy_consent_given, ref_code FROM user_main WHERE user_id = %s", (user_id,))
    result = cursor.fetchone()
    
    if result and (ref_code and not result[1]):
        cursor.execute(
            """
            UPDATE user_main 
            SET utm_source = %s, utm_medium = %s, utm_campaign = %s, ref_code = %s
            WHERE user_id = %s;
            """,
            (utm_source, utm_medium, utm_campaign, ref_code, user_id)
        )
        conn.commit()
    
    if not result:
        # Если пользователь новый, создаем запись
        cursor.execute(
            """
            INSERT INTO user_main (user_id, user_name, utm_source, utm_medium, utm_campaign, ref_code)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id) DO NOTHING;
            """,
            (user_id, message.from_user.first_name, utm_source, utm_medium, utm_campaign, ref_code)
        )
        conn.commit()

    # Всегда показываем выбор языка (независимо от того, новый пользователь или вернувшийся)
    welcome_text = (
        "🎉 <b>Добро пожаловать в PROpitashka!</b>\n\n"
        "Я — ваш персональный помощник по питанию и фитнесу.\n\n"
        "Сначала выберите язык / Select language 👇"
    )
    
    # Создаем ReplyKeyboard для выбора языка
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
    lang_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Русский 🇷🇺")],
            [KeyboardButton(text="English 🇬🇧")],
            [KeyboardButton(text="Deutsch 🇩🇪")],
            [KeyboardButton(text="Française 🇫🇷")],
            [KeyboardButton(text="Spanish 🇪🇸")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await message.answer(
        welcome_text,
        reply_markup=lang_keyboard
    )

@dp.callback_query(F.data.in_(['accept_privacy', 'decline_privacy']))
async def handle_privacy_consent(callback_query: CallbackQuery, state: FSMContext):
    """Handles user's response to the privacy policy."""
    user_id = callback_query.from_user.id
    
    # Получаем язык пользователя
    cursor.execute("SELECT lang FROM user_lang WHERE user_id = %s", (user_id,))
    result = cursor.fetchone()
    lang_code = result[0] if result else 'en'
    
    if callback_query.data == 'accept_privacy':
        # Пользователь согласился
        cursor.execute(
            """
            UPDATE user_main 
            SET privacy_consent_given = TRUE, privacy_consent_at = NOW() 
            WHERE user_id = %s;
            """,
            (user_id,)
        )
        conn.commit()
        bot_logger.info(f"User {user_id} accepted privacy policy")
        
        # Удаляем старое сообщение с политикой
        try:
            await callback_query.message.delete()
        except:
            pass
        
        # Используем callback_query.message как основу, но передаем правильный user_id
        await show_registration_menu(callback_query.message, lang_code, user_id_override=user_id)
    else:
        # Пользователь отказался - показываем сообщение на его языке
        decline_messages = {
            'ru': (
                "❌ К сожалению, без вашего согласия на обработку данных использование бота невозможно.\n\n"
                "Если вы передумаете, просто отправьте команду /start снова."
            ),
            'en': (
                "❌ Unfortunately, without your consent to data processing, using the bot is not possible.\n\n"
                "If you change your mind, just send the /start command again."
            ),
            'de': (
                "❌ Leider ist die Nutzung des Bots ohne Ihre Zustimmung zur Datenverarbeitung nicht möglich.\n\n"
                "Wenn Sie Ihre Meinung ändern, senden Sie einfach den Befehl /start erneut."
            ),
            'fr': (
                "❌ Malheureusement, sans votre consentement au traitement des données, l'utilisation du bot n'est pas possible.\n\n"
                "Si vous changez d'avis, envoyez simplement la commande /start à nouveau."
            ),
            'es': (
                "❌ Desafortunadamente, sin su consentimiento para el procesamiento de datos, no es posible usar el bot.\n\n"
                "Si cambia de opinión, simplemente envíe el comando /start nuevamente."
            )
        }
        
        await callback_query.message.edit_text(
            decline_messages.get(lang_code, decline_messages['en']),
            reply_markup=None
        )
    
    await callback_query.answer()


# Обработчик выбора языка (стандартная клавиатура)
@dp.message(F.text.in_(['Русский 🇷🇺', 'English 🇬🇧', 'Deutsch 🇩🇪', 'Française 🇫🇷', 'Spanish 🇪🇸']))
async def handle_language_selection(message: Message, state: FSMContext):
    """Обработчик выбора языка - показывает политику конфиденциальности"""
    user_id = message.from_user.id
    
    # Определяем код языка по тексту
    lang_map = {
        'Русский 🇷🇺': 'ru',
        'English 🇬🇧': 'en',
        'Deutsch 🇩🇪': 'de',
        'Française 🇫🇷': 'fr',
        'Spanish 🇪🇸': 'es'
    }
    lang_code = lang_map.get(message.text, 'en')
    bot_logger.info(f"User {user_id} selected language: {lang_code}")

    # Сохраняем язык в БД
    cursor.execute(
        """
        INSERT INTO user_lang (user_id, lang)
        VALUES (%s, %s)
        ON CONFLICT (user_id)
        DO UPDATE SET lang = EXCLUDED.lang;
        """,
        (user_id, lang_code)
    )
    conn.commit()
    bot_logger.info(f"Language {lang_code} saved for user {user_id}")
    
    # Проверяем, давал ли пользователь согласие на политику конфиденциальности
    cursor.execute("SELECT privacy_consent_given FROM user_main WHERE user_id = %s", (user_id,))
    result = cursor.fetchone()
    
    if result and result[0]:
        # Если уже давал согласие, переходим сразу к меню регистрации
        bot_logger.info(f"User {user_id} already gave consent, showing registration menu")
        await show_registration_menu(message, lang_code)
        return
    
    # Если ещё не давал согласие, показываем политику конфиденциальности на выбранном языке
    privacy_file = f'privacy_policy_{lang_code}.txt'
    try:
        with open(privacy_file, 'r', encoding='utf-8') as f:
            privacy_text = f.read()
        # Берём первые 3500 символов для отображения
        privacy_preview = privacy_text[:3500]
        if len(privacy_text) > 3500:
            truncate_msg = {
                'ru': "\n\n... (полный текст выше)",
                'en': "\n\n... (full text above)",
                'de': "\n\n... (vollständiger Text oben)",
                'fr': "\n\n... (texte complet ci-dessus)",
                'es': "\n\n... (texto completo arriba)"
            }
            privacy_preview += truncate_msg.get(lang_code, "\n\n... (full text above)")
    except Exception as e:
        bot_logger.warning(f"Could not load privacy policy file {privacy_file}: {e}")
        privacy_preview = {
            'ru': "Политика конфиденциальности доступна по запросу.",
            'en': "Privacy policy available upon request.",
            'de': "Datenschutzrichtlinie auf Anfrage verfügbar.",
            'fr': "Politique de confidentialité disponible sur demande.",
            'es': "Política de privacidad disponible bajo petición."
        }.get(lang_code, "Privacy policy available upon request.")

    # Тексты приветствия на разных языках
    welcome_texts = {
        'ru': (
        "🎉 <b>Добро пожаловать в PROpitashka!</b>\n\n"
            "Прежде чем начать, пожалуйста, ознакомьтесь с нашей политикой конфиденциальности:\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        ),
        'en': (
            "🎉 <b>Welcome to PROpitashka!</b>\n\n"
            "Before we start, please review our privacy policy:\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        ),
        'de': (
            "🎉 <b>Willkommen bei PROpitashka!</b>\n\n"
            "Bevor wir beginnen, lesen Sie bitte unsere Datenschutzrichtlinie:\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        ),
        'fr': (
            "🎉 <b>Bienvenue sur PROpitashka!</b>\n\n"
            "Avant de commencer, veuillez consulter notre politique de confidentialité:\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        ),
        'es': (
            "🎉 <b>¡Bienvenido a PROpitashka!</b>\n\n"
            "Antes de comenzar, revise nuestra política de privacidad:\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        )
    }
    
    footer_texts = {
        'ru': (
            "\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Нажимая «✅ Принять», вы соглашаетесь с условиями использования."
        ),
        'en': (
            "\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "By clicking «✅ Accept», you agree to the terms of use."
        ),
        'de': (
            "\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Durch Klicken auf «✅ Akzeptieren» stimmen Sie den Nutzungsbedingungen zu."
        ),
        'fr': (
            "\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "En cliquant sur «✅ Accepter», vous acceptez les conditions d'utilisation."
        ),
        'es': (
            "\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Al hacer clic en «✅ Aceptar», acepta los términos de uso."
        )
    }
    
    privacy_msg = (
        welcome_texts.get(lang_code, welcome_texts['en']) +
        privacy_preview +
        footer_texts.get(lang_code, footer_texts['en'])
    )
    
    await message.answer(
        privacy_msg,
        reply_markup=kb.privacy_consent_keyboard(lang_code),
        disable_web_page_preview=True
    )


async def show_registration_menu(message: Message, lang_code: str, user_id_override=None):
    """Показывает меню регистрации/входа с картинкой"""
    # Используем переданный user_id если он есть, иначе берем из message
    user_id = user_id_override if user_id_override else message.from_user.id
    bot_logger.info(f"Showing registration menu to user {user_id}")
    
    # Словарь перевода языков
    lang_names = {
        'ru': 'Русский 🇷🇺',
        'en': 'English 🇬🇧',
        'de': 'Deutsch 🇩🇪',
        'fr': 'Française 🇫🇷',
        'es': 'Spanish 🇪🇸'
    }
    
    # Получаем имя пользователя
    try:
        from aiogram.types import User
        user_info = await bot.get_chat(user_id)
        first_name = user_info.first_name or "друг"
    except:
        first_name = "друг"
    
    # Тексты приветствия на разных языках
    welcome_messages = {
        'ru': (
            f"✅ Выбран язык: {lang_names[lang_code]}\n\n"
            f"👋 Привет, {first_name}!\n\n"
            "Теперь давайте настроим ваш профиль.\n\n"
            "• Нажмите <b>«Регистрация»</b>, чтобы указать ваши параметры "
            "(рост, вес, цель), и я рассчитаю оптимальную норму калорий.\n\n"
            "• Если вы уже регистрировались, нажмите <b>«Вход»</b>."
        ),
        'en': (
            f"✅ Language selected: {lang_names[lang_code]}\n\n"
            f"👋 Hello, {first_name}!\n\n"
            "Now let's set up your profile.\n\n"
            "• Press <b>\"Registration\"</b> to enter your parameters "
            "(height, weight, goal), and I'll calculate your optimal calorie intake.\n\n"
            "• If you've already registered, press <b>\"Entry\"</b>."
        ),
        'de': (
            f"✅ Sprache ausgewählt: {lang_names[lang_code]}\n\n"
            f"👋 Hallo, {first_name}!\n\n"
            "Jetzt richten wir Ihr Profil ein.\n\n"
            "• Drücken Sie <b>\"Anmeldung\"</b>, um Ihre Parameter einzugeben "
            "(Größe, Gewicht, Ziel), und ich berechne Ihre optimale Kalorienaufnahme.\n\n"
            "• Wenn Sie sich bereits registriert haben, drücken Sie <b>\"Eintrag\"</b>."
        ),
        'fr': (
            f"✅ Langue sélectionnée: {lang_names[lang_code]}\n\n"
            f"👋 Bonjour, {first_name}!\n\n"
            "Maintenant, configurons votre profil.\n\n"
            "• Appuyez sur <b>\"Enregistrement\"</b> pour saisir vos paramètres "
            "(taille, poids, objectif), et je calculerai votre apport calorique optimal.\n\n"
            "• Si vous êtes déjà inscrit, appuyez sur <b>\"Entrée\"</b>."
        ),
        'es': (
            f"✅ Idioma seleccionado: {lang_names[lang_code]}\n\n"
            f"👋 ¡Hola, {first_name}!\n\n"
            "Ahora configuremos tu perfil.\n\n"
            "• Presiona <b>\"Inscripción\"</b> para ingresar tus parámetros "
            "(altura, peso, objetivo), y calcularé tu ingesta calórica óptima.\n\n"
            "• Si ya te registraste, presiona <b>\"Entrada\"</b>."
        )
    }
    
    welcome_text = welcome_messages.get(lang_code, welcome_messages['en'])
    
    # Создаём клавиатуру
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
    buttons_text = {
        'ru': ['Регистрация', 'Вход'],
        'en': ['Registration', 'Entry'],
        'de': ['Anmeldung', 'Eintrag'],
        'fr': ['Enregistrement', 'Entrée'],
        'es': ['Inscripción', 'Entrada']
    }
    
    lang_buttons = buttons_text.get(lang_code, buttons_text['en'])
    start_menu_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=lang_buttons[0]), KeyboardButton(text=lang_buttons[1])]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    # Отправляем фото с меню
    try:
        await bot.send_photo(
            user_id,
            photo=FSInputFile(path='/Users/VadimVthv/Desktop/PROpitashka/new_logo.jpg'),
            caption=welcome_text,
            reply_markup=start_menu_keyboard
        )
        bot_logger.info(f"Welcome message with photo sent to user {user_id}")
    except Exception as e:
        # Если фото не загружается, отправляем просто текст
        bot_logger.error(f"Failed to send photo to user {user_id}: {e}")
        print(f"Ошибка загрузки фото: {e}")
        await bot.send_message(
            user_id,
            text=welcome_text,
            reply_markup=start_menu_keyboard
        )



@dp.message(Command('privacy'))
async def send_privacy_policy(message: Message):
    """Отправляет полный текст политики конфиденциальности"""
    try:
        with open('PRIVACY_POLICY.txt', 'r', encoding='utf-8') as f:
            privacy_text = f.read()
        
        # Разбиваем текст на части по 4000 символов (лимит Telegram)
        max_length = 4000
        parts = [privacy_text[i:i+max_length] for i in range(0, len(privacy_text), max_length)]
        
        await message.answer(
            f"📄 <b>Политика конфиденциальности и условия использования</b>\n\n"
            f"Всего частей: {len(parts)}"
        )
        
        for i, part in enumerate(parts, 1):
            await message.answer(
                f"<i>Часть {i}/{len(parts)}</i>\n\n"
                f"<pre>{part}</pre>"
            )
            await asyncio.sleep(0.5)  # Задержка между сообщениями
            
    except FileNotFoundError:
        await message.answer(
            "📄 Политика конфиденциальности временно недоступна. "
            "Пожалуйста, свяжитесь с поддержкой через /support"
        )


@dp.message(F.text.in_({'Вход', 'Entry', 'Entrée', 'Entrada', 'Eintrag'}))
async def entrance(message: Message, state: FSMContext):
    """Обработчик входа - показывает информацию о пользователе из БД"""
    user_id = message.from_user.id
    bot_logger.info(f"User {user_id} requesting entrance")
    
    # ВАЖНО: Очищаем состояние FSM при входе
    await state.clear()
    bot_logger.info(f"FSM state cleared for user {user_id}")
    
    try:
        # Используем параметризованный запрос для безопасности
        cursor.execute("""
            SELECT imt, imt_str, cal, weight, height 
            FROM user_health 
            WHERE user_id = %s
            ORDER BY date DESC
            LIMIT 1
        """, (user_id,))
        user_data = cursor.fetchone()
        
        if not user_data:
            bot_logger.warning(f"User {user_id} tried to login but no data found in user_health")
            
            # Получаем язык пользователя для правильного сообщения
            cursor.execute("SELECT lang FROM user_lang WHERE user_id = %s", (user_id,))
            lang_result = cursor.fetchone()
            lang_code = lang_result[0] if lang_result else 'ru'
            
            # Сообщения на разных языках
            no_data_messages = {
                'ru': "⚠️ Данные не найдены.\n\nПохоже, вы ещё не прошли регистрацию.\nПожалуйста, нажмите кнопку <b>«Регистрация»</b> ниже.",
                'en': "⚠️ No data found.\n\nIt seems you haven't registered yet.\nPlease press the <b>\"Registration\"</b> button below.",
                'de': "⚠️ Keine Daten gefunden.\n\nEs scheint, dass Sie sich noch nicht registriert haben.\nBitte drücken Sie die Schaltfläche <b>\"Anmeldung\"</b> unten.",
                'fr': "⚠️ Aucune donnée trouvée.\n\nIl semble que vous ne vous soyez pas encore inscrit.\nVeuillez appuyer sur le bouton <b>\"Enregistrement\"</b> ci-dessous.",
                'es': "⚠️ No se encontraron datos.\n\nParece que aún no te has registrado.\nPor favor, presiona el botón <b>\"Inscripción\"</b> a continuación."
            }
            
            # Создаём клавиатуру с кнопкой регистрации
            from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
            registration_buttons = {
                'ru': 'Регистрация',
                'en': 'Registration',
                'de': 'Anmeldung',
                'fr': 'Enregistrement',
                'es': 'Inscripción'
            }
            
            reg_keyboard = ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text=registration_buttons.get(lang_code, 'Registration'))]],
                resize_keyboard=True,
                one_time_keyboard=True
            )
            
            await message.answer(
                no_data_messages.get(lang_code, no_data_messages['en']),
                reply_markup=reg_keyboard
            )
            return
        
        # Распаковываем данные
        imt, imt_str, cal, weight, height = float(user_data[0]), user_data[1], float(user_data[2]), float(user_data[3]), float(user_data[4])
        bot_logger.info(f"User {user_id} entrance successful: weight={weight}, height={height}, imt={imt}")
        
        # Отправляем информацию пользователю
        await bot.send_message(
            message.chat.id,
            text=l.printer(user_id, 'info').format(
                message.from_user.first_name, 
                weight, 
                height, 
                imt,
                imt_str
            )
        )
        await message.answer(
            text=l.printer(user_id, 'SuccesfulReg'),
            reply_markup=kb.keyboard(user_id, 'main_menu')
        )
        
    except Exception as e:
        bot_logger.error(f"Error during entrance for user {user_id}: {e}")
        await message.answer(
            "⚠️ Произошла ошибка при получении данных. Попробуйте снова или пройдите регистрацию.",
            reply_markup=kb.keyboard(user_id, 'main_menu')
        )


@dp.message(F.text.in_({'Регистрация', "Anmeldung", 'Registration', 'Enregistrement', 'Inscripción'}))
async def registration(message: Message, state: FSMContext):
    # Очищаем предыдущее состояние перед началом новой регистрации
    await state.clear()
    bot_logger.info(f"FSM state cleared for user {message.from_user.id} before registration")
    
    await state.set_state(REG.height)
    await bot.send_message(message.chat.id, text=l.printer(message.from_user.id, 'height'))


@dp.message(REG.height)
async def height(message: Message, state: FSMContext):
    try:
        height_value = float(message.text.replace(',', '.'))
        
        # Валидация: рост должен быть в диапазоне 100-250 см
        if not (100 <= height_value <= 250):
            await message.answer(
                l.printer(message.from_user.id, 'height') + "\n\n⚠️ Введите реалистичное значение роста (100-250 см)."
            )
            return
        
        await state.update_data(height=height_value)
        await state.set_state(REG.age_calendar)
        
        # Получаем язык пользователя для календаря
        cursor.execute("SELECT lang FROM user_lang WHERE user_id = %s", (message.from_user.id,))
        lang_result = cursor.fetchone()
        lang_code = lang_result[0] if lang_result else 'ru'
        
        # Показываем выбор года (новый UX)
        # Минимальная дата: 1950 год (фиксированный)
        # Максимальная дата: текущий год - 10 лет (динамический)
        min_date, max_date = CalendarService.get_age_range_dates()
        
        calendar_obj = CalendarKeyboard(lang=lang_code, min_date=min_date, max_date=max_date)
        keyboard = calendar_obj.create_year_selector(context='birthdate', lang=lang_code)
        
        # Сохраняем в состоянии
        await state.update_data(calendar_lang=lang_code)
        
        year_prompts = {
            'ru': "📅 Выберите год рождения:",
            'en': "📅 Select your birth year:",
            'de': "📅 Wählen Sie Ihr Geburtsjahr:",
            'fr': "📅 Sélectionnez votre année de naissance:",
            'es': "📅 Seleccione su año de nacimiento:"
        }
        prompt_message = year_prompts.get(lang_code, year_prompts['ru'])
        await message.answer(prompt_message, reply_markup=keyboard)
        
    except ValueError:
        await state.set_state(REG.height)
        await bot.send_message(message.chat.id, text=l.printer(message.from_user.id, 'height') + "\n\n⚠️ Введите числовое значение.")


@dp.message(REG.age)
async def age(message: Message, state: FSMContext):
    """Обработчик даты рождения пользователя в формате ДД-ММ-ГГГГ"""
    birthdate_str = message.text.strip()
    
    # Валидируем дату рождения с локализованными сообщениями
    is_valid, error_msg = validate_birthdate(birthdate_str, message.from_user.id)
    
    if not is_valid:
        await message.answer(
            l.printer(message.from_user.id, 'age') + f"\n\n⚠️ {error_msg}"
        )
        return
    
    # Сохраняем дату рождения
    await state.update_data(age=birthdate_str)
    await state.set_state(REG.sex)
    await message.answer(l.printer(message.from_user.id, 'sex'),
                             reply_markup=kb.keyboard(message.from_user.id, 'sex'))


# ============================================
# Обработчики календаря для выбора даты рождения
# ============================================

@dp.callback_query(F.data.startswith('cal_'), REG.age_calendar)
async def handle_calendar_callback(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик callback-запросов от инлайн-календаря
    """
    user_id = callback.from_user.id
    
    # Получаем данные из состояния
    data_state = await state.get_data()
    lang_code = data_state.get('calendar_lang', 'ru')
    
    # Парсим callback_data
    action, data = CalendarKeyboard.parse_callback(callback.data)
    
    if action == 'ignore':
        # Игнорируем нажатие (например, на заголовок или пустую ячейку)
        await callback.answer()
        return
    
    elif action == 'selectyear':
        # Пользователь выбрал год - показываем календарь этого года
        selected_year = data['year']
        
        # Получаем диапазон допустимых дат
        min_date, max_date = CalendarService.get_age_range_dates()
        
        calendar_obj = CalendarKeyboard(lang=lang_code, min_date=min_date, max_date=max_date)
        keyboard = calendar_obj.create_calendar(selected_year, 1, context='birthdate')
        
        # Сохраняем выбранный год
        await state.update_data(calendar_year=selected_year, calendar_month=1)
        
        month_prompts = {
            'ru': f"📅 Выберите день и месяц {selected_year} года:",
            'en': f"📅 Select day and month of {selected_year}:",
            'de': f"📅 Wählen Sie Tag und Monat {selected_year}:",
            'fr': f"📅 Sélectionnez le jour et le mois de {selected_year}:",
            'es': f"📅 Seleccione el día y el mes de {selected_year}:"
        }
        prompt_message = month_prompts.get(lang_code, month_prompts['ru'])
        
        await callback.message.edit_text(prompt_message, reply_markup=keyboard)
        await callback.answer()
        return
    
    elif action == 'changeyear':
        # Возврат к выбору года
        min_date, max_date = CalendarService.get_age_range_dates()
        
        calendar_obj = CalendarKeyboard(lang=lang_code, min_date=min_date, max_date=max_date)
        keyboard = calendar_obj.create_year_selector(context='birthdate', lang=lang_code)
        
        year_prompts = {
            'ru': "📅 Выберите год рождения:",
            'en': "📅 Select your birth year:",
            'de': "📅 Wählen Sie Ihr Geburtsjahr:",
            'fr': "📅 Sélectionnez votre année de naissance:",
            'es': "📅 Seleccione su año de nacimiento:"
        }
        prompt_message = year_prompts.get(lang_code, year_prompts['ru'])
        
        await callback.message.edit_text(prompt_message, reply_markup=keyboard)
        await callback.answer()
        return
    
    elif action == 'navigate':
        # Навигация по месяцам
        year = data['year']
        month = data['month']
        
        # Обновляем состояние с новым годом и месяцем
        await state.update_data(calendar_year=year, calendar_month=month)
        
        # Генерируем новую клавиатуру с актуальными ограничениями
        min_date, max_date = CalendarService.get_age_range_dates()
        today_date = date.today()
        calendar_obj = CalendarKeyboard(lang=lang_code, min_date=min_date, max_date=max_date)
        keyboard = calendar_obj.create_calendar(year, month, context='birthdate')
        
        # Обновляем сообщение с новой клавиатурой
        prompt_message = CalendarService.get_calendar_prompt_message(lang_code)
        await callback.message.edit_text(prompt_message, reply_markup=keyboard)
        await callback.answer()
        return
    
    elif action == 'select':
        # Выбрана конкретная дата
        selected_date = data['date']
        
        # Валидируем выбранную дату
        is_valid, error_key = CalendarService.validate_birthdate(selected_date)
        
        if not is_valid:
            # Показываем ошибку валидации
            error_message = CalendarService.get_localized_error_message(error_key, lang_code)
            await callback.answer(f"⚠️ {error_message}", show_alert=True)
            return
        
        # Дата валидна - сохраняем ее
        formatted_date = CalendarService.format_date(selected_date)
        await state.update_data(age=formatted_date)
        
        # Показываем подтверждение
        confirmation_message = CalendarService.get_date_confirmation_message(selected_date, lang_code)
        await callback.message.edit_text(confirmation_message)
        
        # Переходим к следующему шагу (выбор пола)
        await state.set_state(REG.sex)
        await callback.message.answer(
            l.printer(user_id, 'sex'),
            reply_markup=kb.keyboard(user_id, 'sex')
        )
        await callback.answer()
        return
    
    # На случай неизвестного action
    await callback.answer()


@dp.message(REG.sex)
async def sex(message: Message, state: FSMContext):
    await state.update_data(sex=message.text)
    await state.set_state(REG.want)
    await message.answer(l.printer(message.from_user.id, 'aim'), reply_markup=kb.keyboard(message.from_user.id, 'want'))


@dp.message(REG.want)
async def want(message: Message, state: FSMContext):
    await state.update_data(want=message.text)
    await state.set_state(REG.weight)
    await message.answer(l.printer(message.from_user.id, 'weight'), reply_markup=types.ReplyKeyboardRemove())


@dp.message(REG.weight)
async def wei(message: Message, state: FSMContext):
    try:
        weight_text = message.text.replace(',', '.')
        weight = float(weight_text)
        
        # Валидация: вес должен быть в диапазоне 30-300 кг
        if not (30 <= weight <= 300):
            await message.answer(
                l.printer(message.from_user.id, 'weight') + "\n\n⚠️ Введите реалистичное значение веса (30-300 кг)."
            )
            return
        
        await state.update_data(weight=weight)
        data = await state.get_data()
        height, sex, birthdate, aim = data['height'], data['sex'], data['age'], data['want']
        height, sex = float(height), str(sex)
        
        # Вычисляем текущий возраст из даты рождения
        age = calculate_age_from_birthdate(birthdate)
        
        imt = round(weight / ((height / 100) ** 2), 3)
        imt_using_words = calculate_imt_description(imt, message)
        cal = float(calculate_calories(sex, weight, height, age, message))

        # Сохраняем данные о здоровье
        bot_logger.info(f"Inserting user_health: user_id={message.from_user.id}, imt={imt}, cal={cal}, weight={weight}, height={height}")
        cursor.execute("""
            INSERT INTO user_health (user_id, imt, imt_str, cal, date, weight, height) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (message.from_user.id, imt, imt_using_words, cal, datetime.datetime.now().strftime('%Y-%m-%d'), weight, height))
        bot_logger.info("user_health inserted successfully")
        
        # Сохраняем данные пользователя в user_main (дата рождения в формате ДД-ММ-ГГГГ)
        bot_logger.info(f"Inserting/updating user_main: user_id={message.from_user.id}, sex={sex}, birthdate={birthdate}")
        cursor.execute("""
            INSERT INTO user_main (user_id, user_name, user_sex, date_of_birth)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id)
            DO UPDATE SET user_sex = EXCLUDED.user_sex, date_of_birth = EXCLUDED.date_of_birth;
            """, (message.from_user.id, message.from_user.first_name, sex, birthdate))
        bot_logger.info("user_main inserted/updated successfully")
        
        # Сохраняем цели пользователя в user_aims
        bot_logger.info(f"Inserting/updating user_aims: user_id={message.from_user.id}, aim={aim}, cal={cal}")
        cursor.execute("""
            INSERT INTO user_aims (user_id, user_aim, daily_cal)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id)
            DO UPDATE SET user_aim = EXCLUDED.user_aim, daily_cal = EXCLUDED.daily_cal;
            """, (message.from_user.id, aim, cal))
        bot_logger.info("user_aims inserted/updated successfully")

        conn.commit()
        bot_logger.info(f"User {message.from_user.id} registered successfully: sex={sex}, birthdate={birthdate}, age={age}, weight={weight}, height={height}, all data committed to DB")
        await bot.send_message(
            message.chat.id,
            text=l.printer(message.from_user.id, 'info').format(message.from_user.first_name, weight, height, imt,
                                                                imt_using_words)
        )
        await message.answer(text=l.printer(message.from_user.id, 'SuccesfulReg'),
                             reply_markup=kb.keyboard(message.from_user.id, 'main_menu'))
        await state.clear()
    except Exception as e:
        bot_logger.error(f"Error during registration for user {message.from_user.id}: {e}")
        print(f"Ошибка регистрации: {e}")
        await message.answer(
            "⚠️ Произошла ошибка при сохранении данных. Попробуйте снова или вернитесь в главное меню.",
            reply_markup=kb.keyboard(message.from_user.id, 'main_menu')
        )
        await state.clear()


def calculate_imt_description(imt, message: Message):
    if round(imt) < 15:
        return l.printer(message.from_user.id, 'imt1')
    elif round(imt) in range(14, 18):
        return l.printer(message.from_user.id, 'imt2')
    elif round(imt) in range(18, 25):
        return l.printer(message.from_user.id, 'imt3')
    elif round(imt) in range(25, 30):
        return l.printer(message.from_user.id, 'imt4')
    else:
        return l.printer(message.from_user.id, 'imt5')


def calculate_calories(sex, weight, height, age, message):
    if sex == l.printer(message.from_user.id, 'kbMAN'):
        return (10 * weight) + (6.25 * height) - (5 * age) + 5
    elif sex == l.printer(message.from_user.id, 'kbWOMAN'):
        return (10 * weight) + (6.25 * height) - (5 * age) - 161


def markdown_to_telegram_html(text):
    """
    Преобразует Markdown в HTML-форматирование Telegram
    """
    import re
    
    # Заменяем ## заголовки на жирный текст с переносами
    text = re.sub(r'##\s*(.+?)(?:\n|$)', r'\n<b>\1</b>\n\n', text)
    
    # Заменяем ### заголовки на жирный текст
    text = re.sub(r'###\s*(.+?)(?:\n|$)', r'\n<b>\1</b>\n', text)
    
    # Заменяем **жирный** на <b>жирный</b>
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    
    # Заменяем *курсив* на <i>курсив</i> (только одиночные звездочки, не в начале строки для списков)
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<i>\1</i>', text)
    
    # Заменяем разделители --- на переносы
    text = re.sub(r'\n---\n', r'\n\n', text)
    
    # Заменяем `код` на <code>код</code>
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    
    # Убираем множественные переносы (больше 2 подряд)
    text = re.sub(r'\n{3,}', r'\n\n', text)
    
    return text.strip()


def split_message(text, user_id):
    a = list(text.split("\n"))
    cursor.execute("SELECT lang FROM user_lang WHERE user_id = {}".format(user_id))
    ll = cursor.fetchone()[0]
    b = ''
    translator = Translator(from_lang='ru', to_lang=ll)
    for i in range(len(a)):
        b = b + translator.translate(a[i]) + '\n'

    # Применяем форматирование Markdown -> HTML
    formatted_text = markdown_to_telegram_html(text)

    max_length = 4096
    return [formatted_text[i:i + max_length] for i in range(0, len(formatted_text), max_length)]


def calculate_age_from_birthdate(birthdate: str) -> int:
    """
    Вычисляет текущий возраст из даты рождения в формате ДД-ММ-ГГГГ
    
    Args:
        birthdate: Дата рождения в формате 'ДД-ММ-ГГГГ' (строка)
    
    Returns:
        Текущий возраст в годах
    """
    try:
        # Парсим дату рождения
        birth_day, birth_month, birth_year = map(int, birthdate.split('-'))
        birth_date = datetime.datetime(birth_year, birth_month, birth_day)
        
        # Получаем текущую дату
        today = datetime.datetime.now()
        
        # Вычисляем возраст
        age = today.year - birth_date.year
        
        # Проверяем, был ли уже день рождения в этом году
        if (today.month, today.day) < (birth_date.month, birth_date.day):
            age -= 1
            
        return age
    except Exception as e:
        bot_logger.error(f"Error calculating age from birthdate {birthdate}: {e}")
        return 0


def validate_birthdate(birthdate_str: str, user_id: int) -> tuple[bool, str]:
    """
    Валидирует дату рождения с локализованными сообщениями об ошибках
    
    Args:
        birthdate_str: Дата в формате ДД-ММ-ГГГГ
        user_id: ID пользователя для локализации
    
    Returns:
        (is_valid, error_message)
    """
    try:
        # Получаем язык пользователя
        cursor.execute("SELECT lang FROM user_lang WHERE user_id = %s", (user_id,))
        lang_result = cursor.fetchone()
        lang_code = lang_result[0] if lang_result else 'ru'
        
        # Словари с сообщениями об ошибках
        error_messages = {
            'format': {
                'ru': "Неверный формат. Используйте ДД-ММ-ГГГГ (например, 15-05-1990)",
                'en': "Invalid format. Use DD-MM-YYYY (e.g., 15-05-1990)",
                'de': "Ungültiges Format. Verwenden Sie TT-MM-JJJJ (z.B. 15-05-1990)",
                'fr': "Format invalide. Utilisez JJ-MM-AAAA (par exemple, 15-05-1990)",
                'es': "Formato inválido. Use DD-MM-AAAA (por ejemplo, 15-05-1990)"
            },
            'day': {
                'ru': "День должен быть от 1 до 31",
                'en': "Day must be between 1 and 31",
                'de': "Tag muss zwischen 1 und 31 liegen",
                'fr': "Le jour doit être entre 1 et 31",
                'es': "El día debe estar entre 1 y 31"
            },
            'month': {
                'ru': "Месяц должен быть от 1 до 12",
                'en': "Month must be between 1 and 12",
                'de': "Monat muss zwischen 1 und 12 liegen",
                'fr': "Le mois doit être entre 1 et 12",
                'es': "El mes debe estar entre 1 y 12"
            },
            'year': {
                'ru': "Год должен быть в диапазоне {}-{}",
                'en': "Year must be between {} and {}",
                'de': "Jahr muss zwischen {} und {} liegen",
                'fr': "L'année doit être entre {} et {}",
                'es': "El año debe estar entre {} y {}"
            },
            'invalid': {
                'ru': "Такой даты не существует в календаре",
                'en': "This date does not exist in the calendar",
                'de': "Dieses Datum existiert nicht im Kalender",
                'fr': "Cette date n'existe pas dans le calendrier",
                'es': "Esta fecha no existe en el calendario"
            },
            'numbers': {
                'ru': "Дата должна содержать только цифры",
                'en': "Date must contain only numbers",
                'de': "Datum darf nur Zahlen enthalten",
                'fr': "La date ne doit contenir que des chiffres",
                'es': "La fecha debe contener solo números"
            }
        }
        
        # Проверяем формат
        parts = birthdate_str.split('-')
        if len(parts) != 3:
            return False, error_messages['format'].get(lang_code, error_messages['format']['en'])
        
        day, month, year = map(int, parts)
        
        # Проверяем диапазоны
        if not (1 <= day <= 31):
            return False, error_messages['day'].get(lang_code, error_messages['day']['en'])
        if not (1 <= month <= 12):
            return False, error_messages['month'].get(lang_code, error_messages['month']['en'])
        
        current_year = datetime.datetime.now().year
        min_year = current_year - 120  # Максимум 120 лет
        max_year = current_year - 10   # Минимум 10 лет
        
        if not (min_year <= year <= max_year):
            msg_template = error_messages['year'].get(lang_code, error_messages['year']['en'])
            return False, msg_template.format(min_year, max_year)
        
        # Проверяем, что дата существует
        try:
            datetime.datetime(year, month, day)
        except ValueError:
            return False, error_messages['invalid'].get(lang_code, error_messages['invalid']['en'])
        
        return True, ""
        
    except ValueError:
        return False, error_messages['numbers'].get(lang_code, error_messages['numbers']['en'])


def is_not_none(variable):
    return 0 if variable is None else variable


# DeepSeek удалён - функция больше не используется


@async_retry(max_attempts=config.API_RETRY_ATTEMPTS, delay=config.API_RETRY_DELAY, exceptions=(Exception,))
async def generate(zap, cache_key: str = None, cache_ttl: int = config.CACHE_TTL_AI_RESPONSES):
    """
    Генерирует ответ от AI через Google Gemini, используя кэширование.
    """
    # 1. Проверяем кэш
    if cache_key:
        cached_response = await get_from_cache(cache_key)
        if cached_response:
            bot_logger.info(f"Response found in cache: {cache_key}")
            return cached_response

    # 2. Если в кэше нет, генерируем новый ответ через Gemini
    try:
        # Используем старый API для текстовой генерации
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = await asyncio.to_thread(
            model.generate_content,
            zap
        )
        result = response.text

        # 3. Сохраняем в кэш
        if cache_key and result:
            await set_to_cache(cache_key, result, cache_ttl)
            bot_logger.info(f"Response saved to cache: {cache_key}")

        return result
        
    except Exception as e:
        bot_logger.error(f"Error generating AI response: {str(e)}")
        raise  # Пробрасываем исключение для retry-декоратора

# СТАРЫЙ ОБРАБОТЧИК tren УДАЛЁН - используется новая система из workout_handlers.py


@dp.message(StateFilter("waiting_for_weight"))
async def set_weight_and_continue(message: Message, state: FSMContext):
    try:
        weight = float(message.text)
    except ValueError:
        await message.answer("Введите число — ваш вес в кг.")
        return

    # Сохраняем вес в БД
    cursor.execute(
        """INSERT INTO user_health (user_id, date, weight)
           VALUES (%s, CURRENT_DATE, %s)
           ON CONFLICT (user_id, date) DO UPDATE SET weight = EXCLUDED.weight""",
        (message.from_user.id, weight)
    )
    conn.commit()

    # Возвращаемся в обычный сценарий
    await state.set_state(REG.length)
    await tren_len(message, state)
@dp.message(REG.length)
async def tren_len(message: Message, state: FSMContext):
    user_id = message.from_user.id

    data = await state.get_data()
    waiting_for_weight = data.get("waiting_for_weight", False)

    # Ветка: пользователь вводит вес по нашему запросу
    if waiting_for_weight:
        # 1) Парсим вес
        text = message.text.strip().replace(",", ".")
        try:
            weight = float(text)
            if not (25 <= weight <= 400):
                await message.answer("Введите реальный вес в кг (например, 72.5).")
                return
        except ValueError:
            await message.answer("Введите число — ваш вес в кг (например, 72.5).")
            return

        # 2) Пишем вес в БД через SELECT/UPDATE/INSERT (без ON CONFLICT)
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
        conn.commit()

        # 3) Сбрасываем флаг ожидания веса и продолжаем расчёт
        await state.update_data(waiting_for_weight=False)

        # Проверим, что у нас есть нужные данные тренировки
        data = await state.get_data()
        tren_type = data.get("types")
        length_str = data.get("length")
        if not tren_type or not length_str:
            await message.answer("Не хватает данных тренировки. Пожалуйста, выберите тип и длительность заново.")
            await state.clear()
            return

        try:
            time_min = int(length_str)
            if time_min <= 0:
                await message.answer("Длительность должна быть больше 0 минут.")
                return
        except ValueError:
            await message.answer("Длительность должна быть числом (в минутах).")
            return

        intensivity = intensiv(tren_type, user_id)
        if intensivity is None:
            await message.answer("Не удалось распознать тип тренировки. Выберите тип ещё раз.")
            await state.clear()
            return

        tren_cal = round((weight * intensivity * time_min / 24), 3)

        cursor.execute(
            "INSERT INTO user_training (user_id, date, training_cal, tren_time) VALUES (%s, CURRENT_DATE, %s, %s)",
            (user_id, tren_cal, time_min)
        )
        conn.commit()

        cursor.execute(
            "SELECT COALESCE(SUM(training_cal), 0) FROM user_training WHERE date = CURRENT_DATE AND user_id = %s",
            (user_id,)
        )
        result = cursor.fetchone()[0]

        await bot.send_message(message.chat.id, text=l.printer(user_id, 'TrenCal').format(tren_cal))
        await bot.send_message(
            message.chat.id,
            text=l.printer(user_id, 'TrenCalDay').format(message.from_user.first_name, result),
            reply_markup=kb.keyboard(user_id, 'main_menu')
        )
        await state.clear()
        return

    # Ветка: обычный ход — пришла длительность, пробуем взять вес
    await state.update_data(length=message.text)
    data = await state.get_data()

    # 1) Проверяем корректность длительности
    try:
        time_min = int(data['length'])
        # Валидация: длительность тренировки 1-300 минут
        if not (1 <= time_min <= 300):
            await message.answer("⚠️ Введите реалистичную длительность тренировки (1-300 минут).")
            return
    except (ValueError, KeyError):
        await message.answer("⚠️ Длительность должна быть числом (в минутах).")
        return

    # 2) Пробуем получить вес на сегодня
    cursor.execute(
        "SELECT weight FROM user_health WHERE user_id = %s AND date = CURRENT_DATE",
        (user_id,)
    )
    row = cursor.fetchone()

    if not row or row[0] is None:
        # Запрашиваем вес и ждём новое сообщение в этом же состоянии
        await message.answer("Введите свой вес (кг):")
        await state.update_data(waiting_for_weight=True)
        return

    weight = float(row[0])

    # 3) Считаем калории
    tren_type = data.get("types")
    intensivity = intensiv(tren_type, user_id)
    if intensivity is None:
        await message.answer("Не удалось распознать тип тренировки. Выберите тип ещё раз.")
        await state.clear()
        return

    tren_cal = round((weight * intensivity * time_min / 24), 3)

    cursor.execute(
        "INSERT INTO user_training (user_id, date, training_cal, tren_time) VALUES (%s, CURRENT_DATE, %s, %s)",
        (user_id, tren_cal, time_min)
    )
    conn.commit()

    cursor.execute(
        "SELECT COALESCE(SUM(training_cal), 0) FROM user_training WHERE date = CURRENT_DATE AND user_id = %s",
        (user_id,)
    )
    result = cursor.fetchone()[0]

    await bot.send_message(message.chat.id, text=l.printer(user_id, 'TrenCal').format(tren_cal))
    await bot.send_message(
        message.chat.id,
        text=l.printer(user_id, 'TrenCalDay').format(message.from_user.first_name, result),
        reply_markup=kb.keyboard(user_id, 'main_menu')
    )
    await state.clear()


def replace_none_with_zero_in_list(lst, index):
    if 0 <= index < len(lst):
        if lst[index] is None:  # Проверяем, является ли элемент None
            lst[index] = 0  # Заменяем на 0
    return lst


@dp.message(F.text.in_({'Ввести еду за день', "Das Essen des Tages einführen", "Enter a day's worth of food",
                        "Introducir la comida del día", 'Présenter les aliments du jour'}))
async def food1(message: Message, state: FSMContext):
    # Очищаем состояние при входе в раздел
    await state.clear()
    
    # Удаляем предыдущую клавиатуру
    await message.answer("⏳", reply_markup=types.ReplyKeyboardRemove())
    
    await message.answer(text=l.printer(message.from_user.id, 'ChooseTheWay'),
                         reply_markup=kb.keyboard(message.from_user.id, 'food'))
    await state.set_state(REG.food)


@dp.message(REG.food)
async def foodchoise(message: Message, state: FSMContext):
    await state.update_data(food=message.text)
    await state.set_state(REG.food_photo)

    data = await state.get_data()
    if data['food'] == l.printer(message.from_user.id, 'kbfood2'):
        await message.answer(text=l.printer(message.from_user.id, 'SendMes'), reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(REG.food_list)

    if data['food'] == l.printer(message.from_user.id, 'kbfood1'):
        await message.answer(text=l.printer(message.from_user.id, 'SengFoto'), reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(REG.food_photo)


@dp.message(REG.food_list)
async def names(message: Message, state: FSMContext):
    await state.update_data(food_list=message.text.split(","))
    await bot.send_message(message.chat.id, text=l.printer(message.from_user.id, 'gram'))
    await state.set_state(REG.grams)


@dp.message(REG.food_photo)
async def handle_photo(message: Message, state: FSMContext):
    """Обработчик фото еды - распознаёт что на фото, считает БЖУ и сохраняет в БД"""
    user_id = message.from_user.id
    bot_logger.info(f"User {user_id} sent food photo for recognition")
    
        # Проверяем что это фото
    if not message.photo:
            await message.answer("⚠️ Пожалуйста, отправьте фото еды.")
            return
        
    await state.update_data(food_photo=message.photo)
    data = await state.get_data()
    photo = data['food_photo'][-1]

        # Показываем что обрабатываем
    processing_msg = await message.answer("🔍 Анализирую фото еды...")
        
        # Скачиваем фото
    file_info = await bot.get_file(photo.file_id)
    
    @async_retry(max_attempts=config.API_RETRY_ATTEMPTS, delay=config.API_RETRY_DELAY, exceptions=(Exception,))
    async def download_file_with_retry(file_info):
        return await bot.download_file(file_info.file_path)

    downloaded_file = await download_file_with_retry(file_info)
    save_path = f'photo_{user_id}.jpg'
        
        # Сохраняем файл
    with open(save_path, 'wb') as photo_file:
            photo_file.write(downloaded_file.read())
        
    bot_logger.info(f"Photo saved for user {user_id}: {save_path}")
        
        # Загружаем фото в Gemini
    try:
            # Используем новый API Gemini для загрузки файла
            import google.generativeai as genai
            import json
            import re
            
            uploaded_file = genai.upload_file(save_path)
            bot_logger.info(f"Photo uploaded to Gemini: {uploaded_file.uri}")
            
            # Создаём промпт для распознавания
            prompt = l.printer(user_id, 'food_recognition_prompt')
            
            # Генерируем ответ с фото
            model = genai.GenerativeModel('gemini-2.5-flash')
            response = model.generate_content([prompt, uploaded_file])
            
            if response and response.text:
                ai_response = response.text
                bot_logger.info(f"Food recognition successful for user {user_id}")
                
                # Удаляем сообщение "Анализирую..."
                await bot.delete_message(chat_id=message.chat.id, message_id=processing_msg.message_id)
                
                # Извлекаем JSON из ответа
                json_data = None
                user_message = ai_response
                
                # Ищем JSON блок в ответе
                json_match = re.search(r'```json\s*(\[.*?\])\s*```', ai_response, re.DOTALL)
                if json_match:
                    try:
                        json_str = json_match.group(1)
                        json_data = json.loads(json_str)
                        # Убираем JSON из сообщения пользователю
                        user_message = ai_response[:json_match.start()].strip()
                        bot_logger.info(f"Extracted JSON data for user {user_id}: {json_data}")
                    except json.JSONDecodeError as e:
                        bot_logger.error(f"Failed to parse JSON for user {user_id}: {e}")
                
                # Форматируем и отправляем ответ пользователю
                formatted_response = markdown_to_telegram_html(user_message)
                await message.answer(formatted_response, parse_mode='HTML')
                
                # Если JSON данные извлечены - сохраняем в БД
                if json_data and isinstance(json_data, list) and len(json_data) > 0:
                    total_cal = 0
                    dishes_count = 0
                    
                    for item in json_data:
                        try:
                            name = item.get('name', 'Неизвестное блюдо')
                            weight = float(item.get('weight', 0))
                            b_per_100 = float(item.get('b', 0))
                            g_per_100 = float(item.get('g', 0))
                            u_per_100 = float(item.get('u', 0))
                            cal_per_100 = float(item.get('cal', 0))
                            
                            # Пересчитываем на фактический вес
                            b = round(b_per_100 * weight / 100, 3)
                            g = round(g_per_100 * weight / 100, 3)
                            u = round(u_per_100 * weight / 100, 3)
                            food_cal = round(cal_per_100 * weight / 100, 3)
                            
                            # Сохраняем в БД
                            cursor.execute("""
                                INSERT INTO food (
                                    user_id,
                                    date,
                                    name_of_food,
                                    b,
                                    g,
                                    u,
                                    cal
                                )
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                            """, (
                                user_id,
                                datetime.datetime.now().strftime('%Y-%m-%d'),
                                name,
                                b,
                                g,
                                u,
                                food_cal
                            ))
                            conn.commit()
                            
                            total_cal += food_cal
                            dishes_count += 1
                            bot_logger.info(f"Saved food item for user {user_id}: {name}, {food_cal} kcal")
                            
                        except Exception as e:
                            bot_logger.error(f"Error saving food item for user {user_id}: {e}")
                            continue
                    
                    # Подтверждение сохранения
                    if dishes_count > 0:
                        await message.answer(
                            l.printer(user_id, 'food_saved').format(dishes_count, round(total_cal, 1)),
                            reply_markup=kb.keyboard(user_id, 'main_menu')
                        )
                    else:
                        await message.answer(
                            l.printer(user_id, 'food_data_error'),
                            reply_markup=kb.keyboard(user_id, 'main_menu')
                        )
                else:
                    # JSON не найден - просим уточнить
                    await message.answer(
                        l.printer(user_id, 'food_data_error'),
                        reply_markup=kb.keyboard(user_id, 'main_menu')
                    )
                    bot_logger.warning(f"No JSON data found in AI response for user {user_id}")
            else:
                await message.answer(
                    "⚠️ Не удалось распознать еду на фото. Попробуйте сделать фото поближе и чётче.",
                    reply_markup=kb.keyboard(user_id, 'main_menu')
                )
            
            # Удаляем файл
            import os
            if os.path.exists(save_path):
                os.remove(save_path)
                
    except Exception as e:
        bot_logger.error(f"Error recognizing food photo for user {user_id}: {e}")
        try:
            await bot.delete_message(chat_id=message.chat.id, message_id=processing_msg.message_id)
        except:
            pass
        await message.answer(
            "⚠️ Произошла ошибка при распознавании фото. Попробуйте ещё раз или введите еду вручную.",
            reply_markup=kb.keyboard(user_id, 'main_menu')
        )
    
    await state.clear()


@dp.message(F.text.in_(
    {'Присоединиться к чату', "Dem Chatraum beitreten", "Join the chat room", "Rejoindre le salon de discussion",
     'Unirse a la sala de chat'}) | 
    F.text.startswith('Присоединиться к чату') | 
    F.text.startswith('Dem Chatraum beitreten') | 
    F.text.startswith('Join the chat room') | 
    F.text.startswith('Rejoindre le salon de discussion') | 
    F.text.startswith('Unirse a la sala de chat'))
async def chat(message: Message):
    user_id = message.from_user.id
    join_message = l.printer(user_id, 'join_chat_message')
    
    await message.answer(
        text=join_message + '\n\nhttps://t.me/+QVhMA2topDgzOWVi',
        reply_markup=kb.keyboard(user_id, 'main_menu')
    )


@dp.message(F.text.in_({'Добавить выпитый стаканчик воды', "Añade un vaso de agua", "Ajoutez un verre d'eau potable",
                        "Add a drunken glass of water", 'Ein getrunkenes Glas Wasser hinzufügen'}))
async def chating(message: Message):
    cursor.execute("""
        INSERT INTO water (user_id, data, count)
        VALUES (%s, CURRENT_DATE, 1)
        ON CONFLICT (user_id, data)
        DO UPDATE SET count = water.count + 1
        RETURNING count;
    """, (message.from_user.id,))
    drank = cursor.fetchone()[0]
    conn.commit()

    await message.answer(text=l.printer(message.from_user.id, 'cup'),
                         reply_markup=kb.keyboard(message.from_user.id, 'main_menu'))


@dp.message(REG.grams1)
async def grams1(message: Message, state: FSMContext):
    try:
        await state.update_data(grams1=message.text)
        data = await state.get_data()
        raw_grams = data.get('grams1')
        name_a = data['food_list']
        cursor.execute("SELECT lang FROM user_lang WHERE user_id = %s", (message.from_user.id,))
        ll = cursor.fetchone()[0]
        translator = Translator(from_lang="ru", to_lang=ll)

        grams_list = [item.strip() for item in raw_grams.split(',') if item.strip()]
        if len(grams_list) != len(name_a):
            await message.answer(
                l.printer(message.from_user.id, 'gram')
                + "\n\n⚠️ Количество граммов должно соответствовать количеству продуктов."
            )
            await state.set_state(REG.grams1)
            return

        try:
            grams_values = [float(item.replace(',', '.')) for item in grams_list]
        except ValueError:
            await message.answer(
                l.printer(message.from_user.id, 'gram')
                + "\n\n⚠️ Введите количество граммов числом (например: 120 или 120,5)."
            )
            await state.set_state(REG.grams1)
            return

        a = '{"name":{cal:"",b:””, g:””, u:””}, }'
        prod_kbgu = await generate(
            f'Представь кбжу {name_a} в виде чисел в формате файла json {a}')
        pattern = r'\"(\w+)\":\s*{\s*\"cal\":\s*(\d+\.?\d*),\s*\"b\":\s*(\d+\.?\d*),\s*\"g\":\s*(\d+\.?\d*),\s*\"u\":\s*(\d+\.?\d*)\s*}'

        # Результирующий словарь
        result = {}

        # Поиск всех совпадений
        matches = re.findall(pattern, prod_kbgu)
        for match in matches:
            dish, cal, b, g, u = match
            result[dish] = {
                "cal": float(cal),
                "b": float(b),
                "g": float(g),
                "u": float(u)
            }

        # Преобразование в JSON
        result_json = json.dumps(result, ensure_ascii=False, indent=4)
        print("Извлеченные данные в формате JSON:")
        print(result_json)

        # Преобразование JSON-строки в словарь
        json_data = json.loads(result_json)

        sanitized_names = [re.sub(r"\W+", "", dish.lower()) for dish in name_a]

        # Расчет БЖУ и калорий для каждого блюда
        for dish_name, sanitized_key, weight in zip(name_a, sanitized_names, grams_values):
            possible_keys = {
                dish_name,
                dish_name.lower(),
                dish_name.replace(" ", ""),
                dish_name.lower().replace(" ", ""),
                sanitized_key,
            }
            nutrition_data = next((json_data.get(key) for key in possible_keys if key in json_data), None)
            if nutrition_data:
                b = round(float(nutrition_data["b"]) * weight / 100, 3)
                g = round(float(nutrition_data["g"]) * weight / 100, 3)
                u = round(float(nutrition_data["u"]) * weight / 100, 3)
                food_cal = round(float(nutrition_data["cal"]) * weight / 100, 3)
                try:
                    translated_name = translator.translate(dish_name) or dish_name
                except Exception:
                    translated_name = dish_name
                print(b, g, u, food_cal, translated_name)
                cursor.execute(
                    """
                    INSERT INTO food (
                        user_id,
                        date,
                        name_of_food,
                        b,
                        g,
                        u,
                        cal
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        message.from_user.id,
                        datetime.datetime.now().strftime('%Y-%m-%d'),
                        translated_name.title(),
                        b,
                        g,
                        u,
                        food_cal,
                    ),
                )
                conn.commit()
            else:
                await message.answer(f"⚠️ Не удалось найти информацию о продукте: {dish_name}")

        await message.answer(text=l.printer(message.from_user.id, "InfoInBase"),
                             reply_markup=kb.keyboard(message.from_user.id, 'main_menu'))
        await state.clear()
    except:
        await message.answer(text=l.printer(message.from_user.id, 'SendMes'), reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(REG.food_list)


@dp.message(REG.grams)
async def grams(message: Message, state: FSMContext):
    try:
        await state.update_data(grams=message.text)
        data = await state.get_data()
        raw_grams = data['grams']
        name_a = [dish.strip() for dish in data['food_list']]
        cursor.execute("SELECT lang FROM user_lang WHERE user_id = %s", (message.from_user.id,))
        ll = cursor.fetchone()[0]
        translator = Translator(from_lang=ll, to_lang="ru")

        grams_list = [item.strip() for item in raw_grams.split(',') if item.strip()]
        if len(grams_list) != len(name_a):
            await message.answer(
                l.printer(message.from_user.id, 'gram')
                + "\n\n⚠️ Количество граммов должно соответствовать количеству продуктов."
            )
            await state.set_state(REG.grams)
            return

        try:
            grams_values = [float(item.replace(',', '.')) for item in grams_list]
        except ValueError:
            await message.answer(
                l.printer(message.from_user.id, 'gram')
                + "\n\n⚠️ Введите количество граммов числом (например: 120 или 120,5)."
            )
            await state.set_state(REG.grams)
            return

        name_b = [re.sub(r"\W+", "", dish.lower()) for dish in name_a]
        
        # Пробуем получить данные от AI
        try:
            # Используем локализованный промпт
            food_list_str = ", ".join(name_a)
            prompt = l.printer(message.from_user.id, 'food_kbju_prompt').format(food_list_str)
            prod_kbgu = await generate(prompt)
            
            bot_logger.info(f"AI response for food KBJU: {prod_kbgu[:200]}...")
            
            pattern = r'\"(\w+)\":\s*\{\s*\"cal\":\s*(\d+\.?\d*),\s*\"b\":\s*(\d+\.?\d*),\s*\"g\":\s*(\d+\.?\d*),\s*\"u\":\s*(\d+\.?\d*)\s*\}'

            # Результирующий словарь
            result = {}

            # Поиск всех совпадений
            matches = re.findall(pattern, prod_kbgu)
            for match in matches:
                dish, cal, b, g, u = match
                result[dish] = {
                    "cal": float(cal),
                    "b": float(b),
                    "g": float(g),
                    "u": float(u)
                }

            # Преобразование в JSON
            result_json = json.dumps(result, ensure_ascii=False, indent=4)
            bot_logger.info(f"Extracted JSON data: {result_json}")

            # Преобразование JSON-строки в словарь
            json_data = json.loads(result_json)
        except Exception as e:
            bot_logger.warning(f"AI failed, using fallback database: {e}")
            json_data = {}
            # Fallback: используем локальную базу данных
            for original_name, dish_name in zip(name_a, name_b):
                fallback_data = food_db.find_food_in_database(original_name)
                if not fallback_data:
                    fallback_data = food_db.find_food_in_database(dish_name)
                if fallback_data:
                    json_data[dish_name] = fallback_data
                    bot_logger.info(f"Found {original_name} in fallback database")

        # Расчет БЖУ и калорий для каждого блюда
        for original_name, sanitized_key, weight in zip(name_a, name_b, grams_values):
            
            # Проверка в AI-данных или fallback-базе
            nutrition_data = json_data.get(sanitized_key) or json_data.get(original_name) or json_data.get(original_name.lower())
            if nutrition_data:
                b = round(float(nutrition_data["b"]) * weight / 100, 3)
                g = round(float(nutrition_data["g"]) * weight / 100, 3)
                u = round(float(nutrition_data["u"]) * weight / 100, 3)
                food_cal = round(float(nutrition_data["cal"]) * weight / 100, 3)
                try:
                    translated_name = translator.translate(original_name) or original_name
                except Exception:
                    translated_name = original_name
                print(b, g, u, food_cal, translated_name)
                cursor.execute(
                    """
                    INSERT INTO food (
                        user_id,
                        date,
                        name_of_food,
                        b,
                        g,
                        u,
                        cal
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        message.from_user.id,
                        datetime.datetime.now().strftime('%Y-%m-%d'),
                        translated_name.title(),
                        b,
                        g,
                        u,
                        food_cal,
                    ),
                )
                conn.commit()
            else:
                # Если продукт не найден ни в AI, ни в fallback
                await message.answer(f"⚠️ Не удалось найти информацию о продукте: {original_name}")

        await message.answer(text=l.printer(message.from_user.id, "InfoInBase"),
                             reply_markup=kb.keyboard(message.from_user.id, 'main_menu'))
        await state.clear()
    except Exception as e:
        print(f"Error in grams handler: {e}")
        await message.answer(text=l.printer(message.from_user.id, 'SendMes'), reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(REG.food_list)


@dp.message(F.text.in_({'Недельный план питания и тренировок', "Wöchentlicher Ernährungs- und Trainingsplan",
                        "Plan semanal de nutrición y entrenamiento", "Weekly nutrition and exercise plan",
                        'Plan semanal de dieta y entrenamiento'}))
async def ai(message: Message, state: FSMContext):
    await message.answer(text=l.printer(message.from_user.id, 'InProcess'))
    cursor.execute(
        "SELECT lang FROM user_lang WHERE user_id = {}".format(message.from_user.id)
    )
    ll = cursor.fetchone()[0]
    translator = Translator(from_lang=ll, to_lang='ru')
    cursor.execute(
        "SELECT user_aim, daily_cal FROM user_aims WHERE user_id = {}".format(message.from_user.id)
    )
    aim, cal = cursor.fetchone()
    cursor.execute(
        f"SELECT user_sex, date_of_birth FROM user_main WHERE user_id = {message.from_user.id} "
    )
    sex, birthdate = cursor.fetchone()
    cursor.execute(
        f"SELECT imt, weight, height FROM user_health WHERE user_id = {message.from_user.id}"
    )
    imt, weight, height = cursor.fetchone()
    
    # Вычисляем текущий возраст из даты рождения
    age = calculate_age_from_birthdate(birthdate)
    
    aim, cal, sex, age, imt, weight, height = translator.translate(aim), cal, translator.translate(
        sex), age, imt, weight, height
    
    # Создаем уникальный ключ для кэша на основе параметров пользователя
    cache_key_pit = f"plan:pit:{message.from_user.id}:{sex}:{height}:{age}:{imt}:{aim}"
    
    zap_pit = l.printer(message.from_user.id, 'pitforweek').format(sex, height, age, imt, aim)
    plan_pit = await generate(zap_pit, cache_key=cache_key_pit, cache_ttl=config.CACHE_TTL_RECIPES)
    
    cache_key_tren = f"plan:tren:{message.from_user.id}:{sex}:{height}:{age}:{imt}:{aim}"

    zap_tren = l.printer(message.from_user.id, 'trenforweek').format(sex, height, age, imt, aim, plan_pit)
    plan_train = await generate(zap_tren, cache_key=cache_key_tren, cache_ttl=config.CACHE_TTL_RECIPES)

    try:
        if plan_pit and plan_train:
            # Разделяем длинные сообщения на части
            for part in split_message(plan_pit, message.from_user.id):
                await message.answer(part, parse_mode='HTML')

            for part in split_message(plan_train, message.from_user.id):
                await message.answer(part, parse_mode='HTML')

            await message.answer(
                text=l.printer(message.from_user.id, 'recommend'),
                reply_markup=kb.keyboard(message.from_user.id, 'main_menu'))

        else:
            await bot.send_message(message.chat.id, text="Not enough info about user",
                                   reply_markup=kb.keyboard(message.from_user.id, 'main_menu'))
    except Exception as e:
        print(f"Ошибка при генерации плана: {str(e)}")
        return f"Ошибка при генерации плана: {e}"


@dp.message(F.text.in_({'Помочь с рецептом', "Ayuda con una receta", "Hilfe bei einem Rezept", "Aide pour une recette",
                        'Help with the recipe'}))
async def ai_food(message: Message, state: FSMContext):
    await message.answer(text=l.printer(message.from_user.id, 'choosemeal'),
                         reply_markup=kb.keyboard(message.from_user.id, 'meals'))
    await state.set_state(REG.food_meals)


@dp.message(REG.food_meals)
async def ai_food_meals(message: Message, state: FSMContext):
    await state.update_data(food_meals=message.text)
    data = await state.get_data()
    cursor.execute(f"SELECT lang FROM user_lang WHERE user_id = {message.from_user.id}",
                   )

    ll = cursor.fetchone()[0]
    translator = Translator(from_lang=ll, to_lang="ru")
    meal = translator.translate(data['food_meals'])
    zap = l.printer(message.from_user.id, 'mealai').format(meal)
    await message.answer(text=l.printer(message.from_user.id, 'InProcess'))
    
    cache_key = f"recipe:{meal.replace(' ', '_').lower()}"

    plan_pit = await generate(zap, cache_key=cache_key, cache_ttl=config.CACHE_TTL_RECIPES)
    try:
        if plan_pit:
            # Разделяем длинные сообщения на части
            for part in split_message(plan_pit, message.from_user.id):
                await bot.send_message(message.chat.id, text=part,
                                       reply_markup=kb.keyboard(message.from_user.id, 'main_menu'),
                                       parse_mode='HTML')
        else:
            await bot.send_message(message.chat.id, text="Не удалось получить данные пользователя.",
                                   reply_markup=kb.keyboard(message.from_user.id, 'main_menu'))
    except Exception as e:
        print(f"Ошибка при генерации плана: {str(e)}")
        return f"Ошибка при генерации плана: {e}"
    await state.clear()


@dp.message(F.text.in_({'Помочь с тренировкой', "Help with training", "Aide à la formation", "Hilfe bei der Ausbildung",
                        "Ayuda a la formación"}))
async def ai_food(message: Message, state: FSMContext):
    await message.answer(text=l.printer(message.from_user.id, 'trenchoose'),
                         reply_markup=kb.keyboard(message.from_user.id, 'tren_type'))
    await state.set_state(REG.train)


@dp.message(REG.train)
async def train(message: Message, state: FSMContext):
    await state.update_data(train=message.text)
    data = await state.get_data()
    cursor.execute(f"SELECT lang FROM user_lang WHERE user_id = {message.from_user.id}",
                   )

    ll = cursor.fetchone()[0]
    translator = Translator(from_lang=ll, to_lang="ru")
    type_tren = translator.translate(data['train'])
    await state.clear()
    await message.answer(text=l.printer(message.from_user.id, 'InProcess'))
    cursor.execute(
        f"SELECT imt FROM user_health WHERE date = '{datetime.datetime.now().strftime('%Y-%m-%d')}' AND user_id = {message.from_user.id}")
    imt = float(cursor.fetchone()[0])
    zap = l.printer(message.from_user.id, 'trenai').format(type_tren, imt)
    
    cache_key = f"training:{type_tren.replace(' ', '_').lower()}:{round(imt)}"

    tren = await generate(zap, cache_key=cache_key, cache_ttl=config.CACHE_TTL_RECIPES)
    await state.update_data(tren_ai=tren)

    try:
        if tren:
            for part in split_message(tren, message.from_user.id):
                await bot.send_message(message.chat.id, text=part,
                                       reply_markup=kb.keyboard(message.from_user.id, 'tren_choise'),
                                       parse_mode='HTML')
                await state.set_state(REG.tren_choiser)


        else:
            await bot.send_message(message.chat.id, text="Не удалось получить данные пользователя.",
                                   reply_markup=kb.keyboard(message.from_user.id, 'main_menu'))
    except Exception as e:
        print(f"Ошибка при генерации плана: {str(e)}")
        return f"Ошибка при генерации плана: {e}"


@dp.message(REG.tren_choiser)
async def choising(message: Message, state: FSMContext):
    await state.update_data(tren_choiser=message.text)
    data = await state.get_data()
    mes = data['tren_choiser']
    if mes == l.printer(message.from_user.id, 'return'):
        await message.answer(text=l.printer(message.from_user.id, 'ret2main'),
                             reply_markup=kb.keyboard(message.from_user.id, 'main_menu'))
    else:
        c = 0
        tren = data["tren_ai"]
        for i in range(len(tren_list)):
            for m in range(len(tren_list[i])):
                if tren_list[i][m] in tren:
                    gif_url = GIF_LIBRARY.get(tren_list[i][0], None)

                    if gif_url:
                        await bot.send_animation(
                            chat_id=message.chat.id,
                            animation=gif_url,
                            caption=l.printer(message.from_user.id, 'correct_tech').format(tren_list[i][m]),
                            reply_markup=kb.keyboard(message.from_user.id, 'main_menu')
                        )
                    else:
                        c = c + 1
        if c > 0:
            gif_url = "https://media.giphy.com/media/xT9IgIc0lryrxvqVGM/giphy.gif"
            await bot.send_animation(
                chat_id=message.chat.id,
                animation=gif_url,
                reply_markup=kb.keyboard(message.from_user.id, 'main_menu')
            )

        await message.answer(text=l.printer(message.from_user.id, "ret2main"),
                             reply_markup=kb.keyboard(message.from_user.id, 'main_menu'))

    await state.clear()


@dp.message(F.text.in_(
    {'Вход в програму', 'Acceder al programa', "Aufnahme in das Programm", "Entrée dans le programme",
     "Entering the program"}))
async def ais(message: Message, state: FSMContext):
    await message.answer(text=l.printer(message.from_user.id, 'begining'),
                         reply_markup=kb.keyboard(message.from_user.id, 'main_menu')
                         )


@dp.message(F.text.in_(
    {'Смена языка', "Change language", "Changement de langue", "Änderung der Sprache", "Cambio lingüístico"}))
async def leng2(message: Message, state: FSMContext):
    await state.set_state(REG.leng2)
    await message.answer(text='Please, chose your lenguage:',
                         reply_markup=kb.keyboard(message.from_user.id, 'lenguage'))


@dp.message(REG.leng2)
async def start2(message: Message, state: FSMContext):
    await state.update_data(leng2=message.text)
    data = await state.get_data()
    cursor.execute(f"""

    UPDATE user_lang SET lang='{languages[data['leng2']]}' WHERE user_id = {message.from_user.id};

            """
                   )
    conn.commit()
    await message.answer(text=data['leng2'], reply_markup=kb.keyboard(message.from_user.id, 'main_menu'))
    await state.clear()


@dp.message(F.text.in_({'Сводка', "Resumen", "Zusammenfassung", "Résumé", "Summary"}))
async def svod(message: Message, state: FSMContext):
    """Обработчик сводки - проверяет наличие веса/роста в БД"""
    user_id = message.from_user.id
    
    # Очищаем состояние при входе в раздел
    await state.clear()
    
    # Удаляем предыдущую клавиатуру
    await message.answer("⏳", reply_markup=types.ReplyKeyboardRemove())
    
    # Проверяем, есть ли данные о весе и росте за сегодня
    cursor.execute("""
        SELECT weight, height FROM user_health 
        WHERE user_id = %s AND date = %s
        ORDER BY date DESC LIMIT 1
    """, (user_id, datetime.datetime.now().strftime('%Y-%m-%d')))
    today_data = cursor.fetchone()
    
    if today_data and today_data[0] and today_data[1]:
        # Если есть данные за сегодня, используем их
        bot_logger.info(f"User {user_id} has weight/height data for today: weight={today_data[0]}, height={today_data[1]}")
        await state.update_data(new_weight=today_data[0], new_height=today_data[1])
        await message.answer(text=l.printer(user_id, 'svoPERIOD'),
                           reply_markup=kb.keyboard(user_id, 'svo'))
        await state.set_state(REG.svo)
    else:
        # Если нет данных за сегодня, проверяем данные за текущий месяц
        cursor.execute("""
            SELECT weight, height FROM user_health 
            WHERE user_id = %s AND date >= DATE_TRUNC('month', CURRENT_DATE)
            ORDER BY date DESC LIMIT 1
        """, (user_id,))
        month_data = cursor.fetchone()
        
        if month_data and month_data[0] and month_data[1]:
            # Есть данные за месяц, используем их
            bot_logger.info(f"User {user_id} has weight/height data for this month: weight={month_data[0]}, height={month_data[1]}")
            await state.update_data(new_weight=month_data[0], new_height=month_data[1])
            await message.answer(text=l.printer(user_id, 'svoPERIOD'),
                               reply_markup=kb.keyboard(user_id, 'svo'))
            await state.set_state(REG.svo)
        else:
            # Нет данных, запрашиваем у пользователя
            bot_logger.info(f"User {user_id} has no weight/height data, requesting input")
            await state.set_state(REG.new_weight)
            await message.answer(l.printer(user_id, 'weight'), reply_markup=types.ReplyKeyboardRemove())



@dp.message(REG.new_weight)
async def new_we(message: Message, state: FSMContext):
    await state.update_data(new_weight=message.text)
    await state.set_state(REG.new_height)
    await message.answer(l.printer(message.from_user.id, 'height'))


@dp.message(REG.new_height)
async def new_he(message: Message, state: FSMContext):
    await state.update_data(new_height=float(message.text))
    await message.answer(text=l.printer(message.from_user.id, 'svoPERIOD'),
                         reply_markup=kb.keyboard(message.from_user.id, 'svo'))
    await state.set_state(REG.svo)


@dp.message(REG.svo)
async def svodka(message: Message, state: FSMContext):
    try:
        await state.update_data(tren_choiser=message.text)
        data = await state.get_data()
        mes = data['tren_choiser']
        new_weight = data['new_weight']
        new_height = float(data['new_height'])
        if "," in str(new_weight):
            we1 = str(new_weight).split(",")
            new_weight = int(we1[0]) + int(we1[1]) / 10 ** len(we1[1])
        else:
            new_weight = float(new_weight)
        
        # Получаем пол и возраст пользователя
        cursor.execute("""
            SELECT user_sex, date_of_birth FROM user_main WHERE user_id = %s
        """, (message.from_user.id,))
        result = cursor.fetchone()
        
        if not result:
            bot_logger.error(f"User {message.from_user.id} not found in user_main")
            await message.answer("⚠️ Ошибка: данные пользователя не найдены. Пожалуйста, пройдите регистрацию заново.",
                               reply_markup=kb.keyboard(message.from_user.id, 'main_menu'))
            await state.clear()
            return
        
        sex = result[0]
        birthdate = result[1]
        
        # Проверяем что пол и дата рождения не None
        if not sex or not birthdate:
            bot_logger.error(f"User {message.from_user.id} has incomplete data: sex={sex}, birthdate={birthdate}")
            await message.answer("⚠️ Ошибка: не все данные заполнены. Пожалуйста, пройдите регистрацию заново.",
                               reply_markup=kb.keyboard(message.from_user.id, 'main_menu'))
            await state.clear()
            return
            
        # Вычисляем текущий возраст из даты рождения
        age = calculate_age_from_birthdate(birthdate)
        bot_logger.info(f"User {message.from_user.id} requesting summary: sex={sex}, birthdate={birthdate}, age={age}")
        
        await state.clear()
        imt = round(new_weight / ((new_height / 100) ** 2), 3)
        imt_using_words = calculate_imt_description(imt, message)
        cal = float(calculate_calories(sex, new_weight, new_height, age, message))

        cursor.execute(f"""
                        INSERT INTO user_health (user_id,imt,imt_str,cal,date, weight, height) VALUES ({message.from_user.id},{imt},'{imt_using_words}',{cal},'{datetime.datetime.now().strftime('%Y-%m-%d')}', {new_weight}, {new_height} )
                        ;
        """)
        conn.commit()
    except Exception as e:
        bot_logger.error(f"Error in svodka for user {message.from_user.id}: {e}")
        await message.answer("⚠️ Произошла ошибка. Попробуйте снова или вернитесь в главное меню.",
                           reply_markup=kb.keyboard(message.from_user.id, 'main_menu'))
        await state.clear()
        return
    
    try:
        if mes == 'День' or mes == "Day" or mes == "Jour" or mes == "Tag" or mes == "Día":
            # ===== ТРЕНИРОВКИ =====
            # Получаем список тренировок за день
            cursor.execute("""
                SELECT training_name, tren_time, training_cal 
                FROM user_training 
                WHERE date = %s AND user_id = %s
                ORDER BY id
            """, (datetime.datetime.now().strftime('%Y-%m-%d'), message.from_user.id))
            trainings_today = cursor.fetchall()
            
            # Форматируем список тренировок
            trainings_text = ""
            if trainings_today:
                trainings_text = "\n\n" + l.printer(message.from_user.id, 'workout_summary_day_title') + "\n"
                for training_name, duration, calories in trainings_today:
                    trainings_text += l.printer(message.from_user.id, 'workout_summary_day_item').format(
                        training_name, duration, round(calories, 1)
                    ) + "\n"
            
            # Сумма калорий от тренировок (используем старое поле training_cal)
            cursor.execute("SELECT SUM(training_cal) FROM user_training WHERE date = '{}' AND user_id = {}".format(
                datetime.datetime.now().strftime('%Y-%m-%d'), message.from_user.id))
            result_tren = cursor.fetchone()
            col_call_tren = result_tren[0] if result_tren[0] else 0
            cursor.execute("SELECT SUM(cal) FROM food WHERE date = '{}' AND user_id = {}".format(
                datetime.datetime.now().strftime('%Y-%m-%d'), message.from_user.id))
            result_cal_food = cursor.fetchone()
            col_cal_food = result_cal_food[0] if result_cal_food[0] else 0
            cursor.execute("SELECT SUM(b) FROM food WHERE date = '{}' AND user_id = {}".format(
                datetime.datetime.now().strftime('%Y-%m-%d'), message.from_user.id))
            result_b = cursor.fetchone()
            col_b = round(result_b[0], 3) if result_b[0] else 0
            cursor.execute("SELECT SUM(g) FROM food WHERE date = '{}' AND user_id = {}".format(
                datetime.datetime.now().strftime('%Y-%m-%d'), message.from_user.id))
            result_g = cursor.fetchone()
            col_g = round(result_g[0], 3) if result_g[0] else 0
            cursor.execute("SELECT SUM(u) FROM food WHERE date = '{}' AND user_id = {}".format(
                datetime.datetime.now().strftime('%Y-%m-%d'), message.from_user.id))
            result_u = cursor.fetchone()
            col_u = round(result_u[0], 3) if result_u[0] else 0
            cursor.execute("SELECT SUM(count) FROM water WHERE data = '{}' AND user_id = {}".format(
                datetime.datetime.now().strftime('%Y-%m-%d'), message.from_user.id))
            result_wat = cursor.fetchone()
            col_wat = round(result_wat[0], 3) if result_wat[0] else 0
            cursor.execute("SELECT name_of_food FROM food WHERE date = '{}' AND user_id = {}".format(
                datetime.datetime.now().strftime('%Y-%m-%d'), message.from_user.id))
            ff = ''
            result_ff = cursor.fetchall()
            for i in result_ff:
                ff += str(i[0])
                ff += ', '

            await bot.send_message(message.chat.id,
                                   text=l.printer(message.from_user.id, 'svoDAY').format(message.from_user.first_name,
                                                                                         datetime.datetime.now().strftime(
                                                                                             '%Y-%m-%d'),
                                                                                         round(col_call_tren,
                                                                                               3) if col_call_tren else 0,
                                                                                         ff, round(col_cal_food,
                                                                                                   3) if col_cal_food else 0,
                                                                                         col_b if col_b else 0,
                                                                                         col_g if col_g else 0,
                                                                                         col_u if col_u else 0,
                                                                                         col_wat * 300 if col_wat else 0) + trainings_text
                                   , reply_markup=kb.keyboard(message.from_user.id, 'main_menu'))
        elif mes == 'Месяц' or mes == "Mes" or mes == "Monat" or mes == "Mois" or mes == "Month":
            weight_month = []
            sr_b = []
            sr_g = []
            sr_u = []
            sr_cal = []
            sr_w = []
            sr_tren = []
            sr_food_cal = []  # Добавляем калории еды
            
            # Получаем количество дней в текущем месяце
            import calendar
            current_year = datetime.datetime.now().year
            current_month = datetime.datetime.now().month
            _, days_in_month = calendar.monthrange(current_year, current_month)
            
            for i in range(1, days_in_month + 1):
                datee = f'{str(current_year)}-{str(current_month).zfill(2)}-{str(i).zfill(2)}'
                
                # Вес (только один раз берём данные)
                cursor.execute(
                    "SELECT weight FROM user_health WHERE user_id = {} AND date = '{}' ".format(message.from_user.id, datee))
                weight_data = cursor.fetchall()
                if weight_data:
                    weight_month.append(weight_data)
                
                # БЖУ
                cursor.execute(
                    "SELECT sum(b) FROM food WHERE user_id = {} AND date = '{}'".format(message.from_user.id, datee))
                b_data = cursor.fetchone()
                if b_data and b_data[0] is not None:
                    sr_b.append(b_data[0])
                    
                cursor.execute(
                    "SELECT sum(g) FROM food WHERE user_id = {} AND date = '{}'".format(message.from_user.id, datee))
                g_data = cursor.fetchone()
                if g_data and g_data[0] is not None:
                    sr_g.append(g_data[0])
                    
                cursor.execute(
                    "SELECT sum(u) FROM food WHERE user_id = {} AND date = '{}'".format(message.from_user.id, datee))
                u_data = cursor.fetchone()
                if u_data and u_data[0] is not None:
                    sr_u.append(u_data[0])
                
                # Калории еды
                cursor.execute(
                    "SELECT sum(cal) FROM food WHERE user_id = {} AND date = '{}'".format(message.from_user.id, datee))
                food_cal_data = cursor.fetchone()
                if food_cal_data and food_cal_data[0] is not None:
                    sr_food_cal.append(food_cal_data[0])
                
                # Вода
                cursor.execute(
                    "SELECT sum(count) FROM water WHERE user_id = {} AND data = '{}'".format(message.from_user.id, datee))
                w_data = cursor.fetchone()
                if w_data and w_data[0] is not None:
                    sr_w.append(w_data[0])
                    bot_logger.info(f"User {message.from_user.id} - water for {datee}: {w_data[0]} glasses")
                
                # Калории тренировок
                cursor.execute(
                    "SELECT sum(training_cal) FROM user_training WHERE user_id = {} AND date = '{}'".format(
                    message.from_user.id, datee))
                cal_data = cursor.fetchone()
                if cal_data and cal_data[0] is not None:
                    sr_cal.append(cal_data[0])
                
                # Время тренировок
                cursor.execute(
                    "SELECT sum(tren_time) FROM user_training WHERE user_id = {} AND date = '{}'".format(
                    message.from_user.id, datee))
                time_data = cursor.fetchone()
                if time_data and time_data[0] is not None:
                    sr_tren.append(time_data[0])
            
            # Фильтруем None значения
                new_sr_b = list(filter(is_not_none, sr_b))
                new_sr_g = list(filter(is_not_none, sr_g))
                new_sr_u = list(filter(is_not_none, sr_u))
                new_sr_w = list(filter(is_not_none, sr_w))
                new_sr_cal = list(filter(is_not_none, sr_cal))
                new_sr_tren = list(filter(is_not_none, sr_tren))
            new_sr_food_cal = list(filter(is_not_none, sr_food_cal))
            
            # Вычисляем средние значения (только по дням когда были данные)
            avg_b = round(sum(new_sr_b) / len(new_sr_b), 3) if new_sr_b and len(new_sr_b) > 0 else 0
            avg_g = round(sum(new_sr_g) / len(new_sr_g), 3) if new_sr_g and len(new_sr_g) > 0 else 0
            avg_u = round(sum(new_sr_u) / len(new_sr_u), 3) if new_sr_u and len(new_sr_u) > 0 else 0
            avg_w = round(sum(new_sr_w) / len(new_sr_w) * 300, 1) if new_sr_w and len(new_sr_w) > 0 else 0
            avg_food_cal = round(sum(new_sr_food_cal) / len(new_sr_food_cal), 1) if new_sr_food_cal and len(new_sr_food_cal) > 0 else 0
            
            bot_logger.info(f"User {message.from_user.id} monthly water calc: sr_w={sr_w}, new_sr_w={new_sr_w}, sum={sum(new_sr_w) if new_sr_w else 0}, len={len(new_sr_w) if new_sr_w else 0}, avg_w={avg_w}ml")
            
            # Безопасный расчёт среднего времени тренировок
            avg_training_time = round(sum(new_sr_tren) / len(new_sr_tren), 3) if new_sr_tren and len(new_sr_tren) > 0 else 0
            
            # Безопасный расчёт среднего числа сожжённых калорий
            avg_calories_burned = round(sum(new_sr_cal) / len(new_sr_cal), 3) if new_sr_cal and len(new_sr_cal) > 0 else 0
            
            # Вес
            if weight_month:
                weig_1 = weight_month[0][0]
                weig_2 = new_weight
            else:
                weig_1 = new_weight
                weig_2 = new_weight
            
            # ===== ТОП-5 ТРЕНИРОВОК ЗА МЕСЯЦ =====
            cursor.execute("""
                SELECT training_name, COUNT(*) as count, ROUND(AVG(tren_time), 1) as avg_duration
                FROM user_training
                WHERE user_id = %s 
                    AND EXTRACT(YEAR FROM date) = %s
                    AND EXTRACT(MONTH FROM date) = %s
                GROUP BY training_name
                ORDER BY count DESC, avg_duration DESC
                LIMIT 5
            """, (message.from_user.id, current_year, current_month))
            top_trainings = cursor.fetchall()
            
            trainings_top_text = ""
            if top_trainings:
                trainings_top_text = "\n\n" + l.printer(message.from_user.id, 'workout_summary_month_title') + "\n"
                for idx, (training_name, count, avg_dur) in enumerate(top_trainings, 1):
                    trainings_top_text += l.printer(message.from_user.id, 'workout_summary_month_item').format(
                        idx, training_name, int(count), int(avg_dur) if avg_dur else 0
                    ) + "\n"
            
            # Формируем сообщение
            bot_logger.info(f"Monthly summary for user {message.from_user.id}: w_days={len(new_sr_w)}, avg_w={avg_w}ml")
            await bot.send_message(message.chat.id, text=l.printer(message.from_user.id, 'svoMONTH').format(
                message.from_user.first_name, weig_1[0] if isinstance(weig_1, tuple) else weig_1, weig_2, 
                avg_training_time, avg_calories_burned, avg_food_cal, avg_b, avg_g, avg_u, avg_w) + trainings_top_text,
                                   reply_markup=kb.keyboard(message.from_user.id, 'main_menu'))
        elif mes == 'Год' or mes == "Year" or mes == "Année" or mes == "Jahr" or mes == "Año":
            all_data = []
            total_food_cal = 0
            total_b = 0
            total_g = 0
            total_u = 0
            total_w_glasses = 0  # Общее количество стаканов
            water_days_count = 0  # Количество дней с водой
            weight_data_all = []
            food_months_with_data = set()

            current_date = datetime.datetime.now()

            for i in range(12):
                current_month = current_date.month - i
                current_year = current_date.year

                if current_month <= 0:
                    current_year -= 1
                    current_month += 12

                first_day_of_month = datetime.date(current_year, current_month, 1)
                if current_month == 12:
                    last_day_of_month = datetime.date(current_year + 1, 1, 1) - datetime.timedelta(days=1)
                else:
                    last_day_of_month = datetime.date(current_year, current_month + 1, 1) - datetime.timedelta(days=1)

                cursor.execute("""
                        SELECT SUM(cal), SUM(b), SUM(g), SUM(u)
                        FROM food 
                        WHERE date >= '{}' AND date <= '{}' AND user_id = {}
                    """.format(
                    first_day_of_month.strftime('%Y-%m-%d'), last_day_of_month.strftime('%Y-%m-%d'),
                    message.from_user.id))
                result_food = cursor.fetchone()
                
                # Считаем воду по дням, а не общую сумму за месяц
                cursor.execute("""
                    SELECT data, SUM(count) 
                              FROM water
                              WHERE data >= '{}' AND data <= '{}' AND user_id = {}
                    GROUP BY data
                          """.format(
                    first_day_of_month.strftime('%Y-%m-%d'), last_day_of_month.strftime('%Y-%m-%d'),
                    message.from_user.id))
                water_days = cursor.fetchall()
                
                if result_food and result_food[0]:
                    all_data.append(result_food)
                    total_food_cal += result_food[0]
                    total_b += result_food[1] if result_food[1] else 0
                    total_g += result_food[2] if result_food[2] else 0
                    total_u += result_food[3] if result_food[3] else 0
                    food_months_with_data.add((current_year, current_month))
                    
                # Подсчитываем воду по дням
                if water_days:
                    for day_water in water_days:
                        total_w_glasses += day_water[1]  # Сумма стаканов
                        water_days_count += 1  # Количество дней

                cursor.execute("""
                        SELECT weight 
                        FROM user_health
                        WHERE date >= '{}' AND date <= '{}' AND user_id = {}
                        ORDER BY date ASC
                    """.format(first_day_of_month.strftime('%Y-%m-%d'), last_day_of_month.strftime('%Y-%m-%d'),
                               message.from_user.id))
                weight_data = cursor.fetchall()

                if weight_data:
                    weight_data_all.extend(weight_data)

            if weight_data_all:
                weight_data_all.sort(key=lambda x: x[0])
                start_weight = weight_data_all[0][0]
                end_weight = new_weight
            else:
                start_weight = 'no info'
                end_weight = 'no info'

            cursor.execute("""
                    SELECT AVG(training_cal) 
                    FROM user_training 
                    WHERE user_id = {}
                """.format(message.from_user.id, ))
            result_train = cursor.fetchone()
            avg_train_cal = result_train[0] if result_train and result_train[0] else 0

            avg_food_cal = total_food_cal / len(food_months_with_data) if food_months_with_data else 0
            avg_b = round(total_b / len(food_months_with_data), 3) if food_months_with_data else 0
            avg_g = round(total_g / len(food_months_with_data), 3) if food_months_with_data else 0
            avg_u = round(total_u / len(food_months_with_data), 3) if food_months_with_data else 0
            
            # Считаем среднее воды по ДНЯМ когда пили (а не по месяцам!)
            avg_w = round((total_w_glasses / water_days_count) * 300, 1) if water_days_count > 0 else 0
            
            bot_logger.info(f"Yearly summary for user {message.from_user.id}: water_days={water_days_count}, total_glasses={total_w_glasses}, avg_w={avg_w}ml")
            
            all_data = list(filter(is_not_none, all_data))
            
            # Безопасное получение данных из all_data
            if all_data and len(all_data) > 0:
                last_food_cal = round(float(all_data[-1][0]), 3) if all_data[-1][0] else 0
                first_food_cal = round(float(all_data[0][0]), 3) if all_data[0][0] else 0
                last_b = round(all_data[-1][1], 3) if all_data[-1][1] else 0
                last_g = round(all_data[-1][2], 3) if all_data[-1][2] else 0
                last_u = round(all_data[-1][3], 3) if all_data[-1][3] else 0
                first_b = round(all_data[0][1], 3) if all_data[0][1] else 0
                first_g = round(all_data[0][2], 3) if all_data[0][2] else 0
                first_u = round(all_data[0][3], 3) if all_data[0][3] else 0
            else:
                last_food_cal = first_food_cal = 0
                last_b = last_g = last_u = 0
                first_b = first_g = first_u = 0
            
            # ===== ТОП-5 ТРЕНИРОВОК ЗА ГОД =====
            cursor.execute("""
                SELECT training_name, COUNT(*) as count, ROUND(AVG(tren_time), 1) as avg_duration
                FROM user_training
                WHERE user_id = %s 
                    AND EXTRACT(YEAR FROM date) = %s
                GROUP BY training_name
                ORDER BY count DESC, avg_duration DESC
                LIMIT 5
            """, (message.from_user.id, datetime.datetime.now().year))
            top_trainings_year = cursor.fetchall()
            
            trainings_year_text = ""
            if top_trainings_year:
                trainings_year_text = "\n\n" + l.printer(message.from_user.id, 'workout_summary_year_title') + "\n"
                for idx, (training_name, count, avg_dur) in enumerate(top_trainings_year, 1):
                    trainings_year_text += l.printer(message.from_user.id, 'workout_summary_year_item').format(
                        idx, training_name, int(count), int(avg_dur) if avg_dur else 0
                    ) + "\n"
            
            await bot.send_message(message.chat.id,
                                   text=l.printer(message.from_user.id, 'svoYEAR').format('\n', start_weight,
                                                                                          end_weight, '\n',
                                                                                          round(avg_train_cal, 3), '\n',
                                                                                          round(avg_food_cal, 3), '\n',
                                                                                          last_food_cal,
                                                                                          first_food_cal,
                                                                                          avg_b, avg_g, avg_u,
                                                                                          last_b, last_g, last_u,
                                                                                          first_b, first_g, first_u,
                                                                                          avg_w) + trainings_year_text,
                                   reply_markup=kb.keyboard(message.from_user.id, 'main_menu'))
    except Exception as e:
        print(f"Ошибка при генерации плана: {str(e)}")
        return f"Ошибка при генерации плана: {e}"


#    except :
#       await state.set_state(REG.new_weight)
#       await message.answer(l.printer(message.from_user.id, 'weight'), reply_markup=types.ReplyKeyboardRemove())


# ============================================
# AI Chat Functions - Контекстное общение с ИИ
# ============================================

async def save_message_to_history(user_id: int, message_type: str, message_text: str):
    """
    Сохраняет сообщение в историю чата
    
    Args:
        user_id: ID пользователя
        message_type: 'user' или 'bot'
        message_text: Текст сообщения
    """
    try:
        cursor.execute("""
            INSERT INTO chat_history (user_id, message_type, message_text)
            VALUES (%s, %s, %s)
        """, (user_id, message_type, message_text))
        conn.commit()
    except Exception as e:
        bot_logger.error(f"Error saving message to history for user {user_id}: {e}")


async def get_chat_context(user_id: int, limit: int = 10) -> str:
    """
    Получает последние N сообщений из истории для контекста
    
    Args:
        user_id: ID пользователя
        limit: Количество последних сообщений
    
    Returns:
        Отформатированная строка с историей сообщений
    """
    try:
        cursor.execute("""
            SELECT message_type, message_text, created_at
            FROM chat_history
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """, (user_id, limit))
        
        messages = cursor.fetchall()
        
        if not messages:
            return "История сообщений пуста."
        
        # Переворачиваем список, чтобы показать старые сообщения первыми
        messages.reverse()
        
        context = []
        for msg_type, msg_text, created_at in messages:
            if msg_type == 'user':
                context.append(f"👤 Пользователь: {msg_text}")
            else:
                context.append(f"🤖 Бот: {msg_text[:100]}{'...' if len(msg_text) > 100 else ''}")
        
        return "\n".join(context)
        
    except Exception as e:
        bot_logger.error(f"Error getting chat context for user {user_id}: {e}")
        return "История сообщений недоступна."


async def get_user_info_for_ai(user_id: int) -> str:
    """
    Собирает информацию о пользователе для передачи ИИ
    
    Args:
        user_id: ID пользователя
    
    Returns:
        Отформатированная строка с данными пользователя
    """
    try:
        info_parts = []
        
        # Получаем основные данные
        cursor.execute("""
            SELECT user_sex, date_of_birth 
            FROM user_main 
            WHERE user_id = %s
        """, (user_id,))
        user_main = cursor.fetchone()
        
        if user_main:
            sex, birthdate = user_main
            if birthdate:
                age = calculate_age_from_birthdate(birthdate)
                info_parts.append(f"• Возраст: {age} лет")
            if sex:
                info_parts.append(f"• Пол: {sex}")
        
        # Получаем данные о здоровье
        cursor.execute("""
            SELECT imt, weight, height
            FROM user_health
            WHERE user_id = %s
            ORDER BY date DESC
            LIMIT 1
        """, (user_id,))
        health = cursor.fetchone()
        
        if health:
            imt, weight, height = health
            if imt:
                info_parts.append(f"• ИМТ: {imt}")
            if weight:
                info_parts.append(f"• Вес: {weight} кг")
            if height:
                info_parts.append(f"• Рост: {height} см")
        
        # Получаем цели
        cursor.execute("""
            SELECT user_aim, daily_cal
            FROM user_aims
            WHERE user_id = %s
        """, (user_id,))
        aims = cursor.fetchone()
        
        if aims:
            aim, cal = aims
            if aim:
                info_parts.append(f"• Цель: {aim}")
            if cal:
                info_parts.append(f"• Дневная норма калорий: {cal} ккал")
        
        if not info_parts:
            return "Данные пользователя отсутствуют (возможно, пользователь не прошёл регистрацию)."
        
        return "\n".join(info_parts)
        
    except Exception as e:
        bot_logger.error(f"Error getting user info for AI for user {user_id}: {e}")
        return "Ошибка получения данных пользователя."


async def handle_ai_chat(message: Message):
    """
    Обрабатывает произвольные текстовые сообщения через AI-чат
    
    Args:
        message: Сообщение от пользователя
    """
    user_id = message.from_user.id
    user_text = message.text
    
    bot_logger.info(f"User {user_id} sent free-form message to AI chat: {user_text[:50]}...")
    
    try:
        # Сохраняем сообщение пользователя в историю
        await save_message_to_history(user_id, 'user', user_text)
        
        # Показываем "думает..."
        thinking_msg = await message.answer(l.printer(user_id, 'ai_thinking'))
        
        # Собираем данные пользователя
        user_info = await get_user_info_for_ai(user_id)
        
        # Получаем контекст последних сообщений
        chat_context = await get_chat_context(user_id, limit=10)
        
        # Формируем системный промпт
        system_prompt = l.printer(user_id, 'ai_chat_system').format(
            user_info,
            chat_context,
            user_text
        )
        
        # Создаём ключ кэша для этого запроса
        cache_key = f"ai_chat:{user_id}:{hash(user_text)}"
        
        # Генерируем ответ через ИИ
        ai_response = await generate(system_prompt, cache_key=cache_key, cache_ttl=1800)  # 30 минут кэш
        
        if not ai_response:
            await message.answer("⚠️ Не удалось получить ответ от нейросети. Попробуйте позже.")
            await bot.delete_message(chat_id=message.chat.id, message_id=thinking_msg.message_id)
            return
        
        # Удаляем "думает..."
        await bot.delete_message(chat_id=message.chat.id, message_id=thinking_msg.message_id)
        
        # Сохраняем ответ бота в историю
        await save_message_to_history(user_id, 'bot', ai_response)
        
        # Отправляем ответ с форматированием
        formatted_response = markdown_to_telegram_html(ai_response)
        
        # Разбиваем на части если слишком длинный
        max_length = 4096
        if len(formatted_response) <= max_length:
            await message.answer(formatted_response, parse_mode='HTML')
        else:
            # Отправляем по частям
            parts = [formatted_response[i:i + max_length] for i in range(0, len(formatted_response), max_length)]
            for part in parts:
                await message.answer(part, parse_mode='HTML')
        
        bot_logger.info(f"AI chat response sent to user {user_id}")
        
    except Exception as e:
        bot_logger.error(f"Error in AI chat for user {user_id}: {e}")
        await message.answer(
            "⚠️ Произошла ошибка при обработке вашего сообщения. Пожалуйста, попробуйте позже.",
            reply_markup=kb.keyboard(user_id, 'main_menu')
        )


# ============================================
# Catch-All Router - AI Chat для необработанных сообщений
# Должен быть зарегистрирован ПОСЛЕДНИМ через include_router
# ============================================

# Создаем отдельный роутер для catch-all
ai_chat_router = Router(name='ai_chat_router')

@ai_chat_router.message(F.text)
async def catch_all_text_messages(message: Message, state: FSMContext):
    """
    Обрабатывает все необработанные текстовые сообщения через AI-чат
    Этот роутер должен быть зарегистрирован ПОСЛЕДНИМ
    """
    current_state = await state.get_state()
    
    # Если пользователь находится в каком-то состоянии FSM - не перехватываем
    if current_state is not None:
        return
    
    # Проверяем что пользователь зарегистрирован
    try:
        cursor.execute("SELECT user_id FROM user_main WHERE user_id = %s", (message.from_user.id,))
        if not cursor.fetchone():
            bot_logger.info(f"User {message.from_user.id} sent message but not registered, ignoring")
            return
    except Exception as e:
        bot_logger.error(f"Error checking user registration: {e}")
        return
    
    bot_logger.info(f"User {message.from_user.id} sent free-form message to AI chat: {message.text[:50]}...")
    
    # Передаём в AI-чат
    await handle_ai_chat(message)


# ============================================
# Регистрация AI Chat Router ПОСЛЕДНИМ
# ============================================
# КРИТИЧЕСКИ ВАЖНО: Этот роутер должен быть зарегистрирован после всех других,
# чтобы catch-all хэндлер не перехватывал сообщения, предназначенные для других хэндлеров
dp.include_router(ai_chat_router)
bot_logger.info("AI Chat router registered as catch-all (last priority)")


# ============================================
# Main Function
# ============================================

async def main():
    # Register middleware
    dp.update.middleware(PrivacyConsentMiddleware())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())