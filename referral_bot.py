#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
РЕФЕРАЛЬНЫЙ БОТ PROPITASHKA
============================
Управляет реферальной программой, подписками и переходами в основной бот.

Автор: AI Assistant
Дата: 2025-10-31
"""

import asyncio
import logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from config import config
import psycopg2

# ============================================
# КОНФИГУРАЦИЯ
# ============================================

REFERRAL_BOT_TOKEN = "7711613851:AAFuWdI8YA77YuUFGHnGHjr8ju1v93mE4TE"
MAIN_BOT_USERNAME = "PROpitashka_bot"  # Замените на username вашего основного бота

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('referral_bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('ReferralBot')

# ============================================
# ПОДКЛЮЧЕНИЕ К БД
# ============================================

try:
    conn = psycopg2.connect(
        dbname=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        host=config.DB_HOST,
        port=config.DB_PORT
    )
    conn.autocommit = True
    cursor = conn.cursor()
    logger.info("✅ Database connection established")
except Exception as e:
    logger.error(f"❌ Database connection error: {e}")
    exit(1)

# ============================================
# FSM СОСТОЯНИЯ
# ============================================

class SubscriptionFlow(StatesGroup):
    choosing_plan = State()
    payment_method = State()

# ============================================
# ИНИЦИАЛИЗАЦИЯ БОТА
# ============================================

storage = MemoryStorage()
bot = Bot(token=REFERRAL_BOT_TOKEN)
dp = Dispatcher(storage=storage)

# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

def get_or_create_user(user_id: int, username: str = None, first_name: str = None):
    """Получает пользователя или создает нового"""
    try:
        # Проверяем есть ли пользователь
        cursor.execute("SELECT user_id, referral_code FROM user_main WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()
        
        if result:
            return result
        
        # Создаем нового пользователя
        cursor.execute("""
            INSERT INTO user_main (user_id, user_name)
            VALUES (%s, %s)
            RETURNING user_id, referral_code
        """, (user_id, first_name or username or f"User{user_id}"))
        
        result = cursor.fetchone()
        
        # Генерируем реферальный код если его нет
        if not result[1]:
            cursor.execute("""
                UPDATE user_main
                SET referral_code = %s
                WHERE user_id = %s
                RETURNING referral_code
            """, (f"REF{user_id}{datetime.now().strftime('%m%d')}", user_id))
            result = (user_id, cursor.fetchone()[0])
        
        # Создаем бесплатную подписку
        cursor.execute("""
            INSERT INTO subscriptions (user_id, subscription_type, is_active)
            VALUES (%s, 'free', TRUE)
        """, (user_id,))
        
        logger.info(f"New user created: {user_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error in get_or_create_user: {e}")
        return None

def get_subscription_info(user_id: int):
    """Получает информацию о подписке пользователя"""
    try:
        cursor.execute("""
            SELECT 
                s.subscription_type,
                s.is_active,
                s.end_date,
                um.is_premium,
                um.premium_until
            FROM subscriptions s
            JOIN user_main um ON s.user_id = um.user_id
            WHERE s.user_id = %s AND s.is_active = TRUE
            ORDER BY s.created_at DESC
            LIMIT 1
        """, (user_id,))
        
        return cursor.fetchone()
    except Exception as e:
        logger.error(f"Error getting subscription info: {e}")
        return None

# ============================================
# КЛАВИАТУРЫ
# ============================================

def get_main_menu_keyboard():
    """Главное меню"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Реферальная программа", callback_data="referral_program")],
        [InlineKeyboardButton(text="💎 Премиум подписка", callback_data="premium_plans")],
        [InlineKeyboardButton(text="📊 Моя статистика", callback_data="my_stats")],
        [InlineKeyboardButton(text="🤖 Перейти в основной бот", url=f"https://t.me/{MAIN_BOT_USERNAME}")],
    ])
    return keyboard

def get_premium_plans_keyboard():
    """Клавиатура с тарифами"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 1 месяц - 199₽", callback_data="plan_monthly_199")],
        [InlineKeyboardButton(text="📅 3 месяца - 499₽ (-16%)", callback_data="plan_3months_499")],
        [InlineKeyboardButton(text="📅 12 месяцев - 1499₽ (-38%)", callback_data="plan_yearly_1499")],
        [InlineKeyboardButton(text="🎁 Пригласить друга (бесплатно)", callback_data="referral_program")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")],
    ])
    return keyboard

def get_payment_keyboard(plan_code: str):
    """Клавиатура выбора способа оплаты"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Банковская карта", callback_data=f"pay_card_{plan_code}")],
        [InlineKeyboardButton(text="💰 ЮMoney", callback_data=f"pay_yoomoney_{plan_code}")],
        [InlineKeyboardButton(text="₿ Криптовалюта", callback_data=f"pay_crypto_{plan_code}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="premium_plans")],
    ])
    return keyboard

# ============================================
# ОБРАБОТЧИКИ КОМАНД
# ============================================

@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    
    # Проверяем реферальный код в аргументах
    args = message.text.split()
    referral_code = args[1] if len(args) > 1 else None
    
    # Создаем или получаем пользователя
    user_data = get_or_create_user(user_id, username, first_name)
    
    if not user_data:
        await message.answer("❌ Ошибка при создании аккаунта. Попробуйте позже.")
        return
    
    # Обрабатываем реферальный код
    if referral_code and referral_code.startswith('REF'):
        try:
            # Находим реферера
            cursor.execute("""
                SELECT user_id, user_name 
                FROM user_main 
                WHERE referral_code = %s
            """, (referral_code,))
            
            referrer = cursor.fetchone()
            
            if referrer and referrer[0] != user_id:
                referrer_id = referrer[0]
                referrer_name = referrer[1]
                
                # Проверяем, не использован ли уже этот реферальный код
                cursor.execute("""
                    SELECT id FROM referrals 
                    WHERE referred_id = %s
                """, (user_id,))
                
                if not cursor.fetchone():
                    # Создаем реферальную связь
                    cursor.execute("""
                        INSERT INTO referrals (referrer_id, referred_id, referral_code, status)
                        VALUES (%s, %s, %s, 'pending')
                    """, (referrer_id, user_id, referral_code))
                    
                    # Обновляем referred_by
                    cursor.execute("""
                        UPDATE user_main
                        SET referred_by = %s
                        WHERE user_id = %s
                    """, (referrer_id, user_id))
                    
                    logger.info(f"User {user_id} registered via referral from {referrer_id}")
                    
                    await message.answer(
                        f"🎉 Вы перешли по реферальной ссылке от <b>{referrer_name}</b>!\n\n"
                        f"После регистрации в основном боте вы оба получите бонусы! 🎁",
                        parse_mode='HTML'
                    )
        except Exception as e:
            logger.error(f"Error processing referral code: {e}")
    
    # Приветственное сообщение
    welcome_text = f"""
👋 <b>Добро пожаловать в PROpitashka!</b>

Я помогу вам:
• 🎁 Получить премиум через реферальную программу
• 💎 Оформить платную подписку
• 📊 Отслеживать статистику рефералов
• 🤖 Перейти в основной бот для работы с питанием

<b>Ваш уникальный реферальный код:</b>
<code>{user_data[1]}</code>

💡 <b>Пригласите друзей и получите:</b>
• 7 дней премиума за каждого друга
• Безлимитный доступ ко всем функциям
• Отсутствие рекламы

Выберите действие ниже 👇
"""
    
    await message.answer(
        welcome_text,
        parse_mode='HTML',
        reply_markup=get_main_menu_keyboard()
    )
    
    logger.info(f"User {user_id} started referral bot")

# ============================================
# ОБРАБОТЧИКИ CALLBACK
# ============================================

@dp.callback_query(F.data == "back_to_menu")
async def callback_back_to_menu(callback: CallbackQuery):
    """Возврат в главное меню"""
    await callback.message.edit_text(
        "🏠 <b>Главное меню</b>\n\nВыберите действие:",
        parse_mode='HTML',
        reply_markup=get_main_menu_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "referral_program")
async def callback_referral_program(callback: CallbackQuery):
    """Информация о реферальной программе"""
    user_id = callback.from_user.id
    
    try:
        # Получаем реферальный код
        cursor.execute("""
            SELECT referral_code, total_referrals, is_premium, premium_until
            FROM user_main
            WHERE user_id = %s
        """, (user_id,))
        
        user_data = cursor.fetchone()
        if not user_data:
            await callback.answer("❌ Ошибка при получении данных", show_alert=True)
            return
        
        referral_code, total_refs, is_premium, premium_until = user_data
        
        # Получаем статистику рефералов
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN status = 'activated' THEN 1 END) as activated
            FROM referrals
            WHERE referrer_id = %s
        """, (user_id,))
        
        stats = cursor.fetchone()
        total_referred = stats[0] if stats else 0
        activated = stats[1] if stats else 0
        
        premium_info = ""
        if is_premium and premium_until:
            premium_info = f"\n\n💎 <b>Премиум активен до:</b> {premium_until.strftime('%d.%m.%Y')}"
        
        referral_link = f"https://t.me/{(await bot.get_me()).username}?start={referral_code}"
        
        text = f"""
🎁 <b>Реферальная программа</b>

<b>Ваш реферальный код:</b>
<code>{referral_code}</code>

<b>Ваша реферальная ссылка:</b>
{referral_link}

📊 <b>Статистика:</b>
• Приглашено: {total_referred}
• Активировано: {activated}
• Премиум дней получено: {activated * 7}
{premium_info}

💡 <b>Как это работает:</b>
1. Поделитесь своей ссылкой с друзьями
2. Когда друг зарегистрируется - вы оба получите по 7 дней премиума
3. Чем больше друзей - тем дольше премиум!

<b>Преимущества премиума:</b>
✅ Без рекламы
✅ Приоритетная поддержка
✅ Расширенная аналитика
✅ Эксклюзивные рецепты
"""
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📤 Поделиться ссылкой", url=f"https://t.me/share/url?url={referral_link}&text=Попробуй PROpitashka - лучший бот для здорового питания!")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")],
        ])
        
        await callback.message.edit_text(text, parse_mode='HTML', reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in referral_program: {e}")
        await callback.answer("❌ Ошибка при получении данных", show_alert=True)

@dp.callback_query(F.data == "premium_plans")
async def callback_premium_plans(callback: CallbackQuery):
    """Показывает тарифные планы"""
    text = """
💎 <b>Премиум подписка PROpitashka</b>

<b>Что входит в премиум:</b>
✅ Без рекламы
✅ Приоритетная поддержка 24/7
✅ Расширенная статистика и аналитика
✅ Эксклюзивные рецепты и тренировки
✅ Персональные рекомендации от AI
✅ Экспорт данных в PDF
✅ Интеграция с Apple Health / Google Fit

<b>Выберите тариф:</b>
"""
    
    await callback.message.edit_text(
        text,
        parse_mode='HTML',
        reply_markup=get_premium_plans_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("plan_"))
async def callback_plan_selected(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора тарифного плана"""
    plan_code = callback.data.replace("plan_", "")
    
    plan_info = {
        "monthly_199": ("1 месяц", 199, 1),
        "3months_499": ("3 месяца", 499, 3),
        "yearly_1499": ("12 месяцев", 1499, 12)
    }
    
    if plan_code not in plan_info:
        await callback.answer("❌ Неверный план", show_alert=True)
        return
    
    plan_name, price, months = plan_info[plan_code]
    
    await state.update_data(plan_code=plan_code, plan_name=plan_name, price=price, months=months)
    
    text = f"""
💳 <b>Оплата подписки</b>

<b>Тариф:</b> {plan_name}
<b>Стоимость:</b> {price} ₽

Выберите способ оплаты:
"""
    
    await callback.message.edit_text(
        text,
        parse_mode='HTML',
        reply_markup=get_payment_keyboard(plan_code)
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("pay_"))
async def callback_payment_method(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора способа оплаты"""
    payment_data = callback.data.replace("pay_", "").split("_")
    payment_method = payment_data[0]
    
    data = await state.get_data()
    plan_name = data.get('plan_name')
    price = data.get('price')
    
    # Здесь должна быть интеграция с платежной системой
    # Для демонстрации просто показываем инструкции
    
    payment_methods = {
        "card": "💳 Банковская карта",
        "yoomoney": "💰 ЮMoney",
        "crypto": "₿ Криптовалюта"
    }
    
    text = f"""
{payment_methods.get(payment_method, '💳')} <b>Оплата</b>

<b>Тариф:</b> {plan_name}
<b>Сумма:</b> {price} ₽

🔄 <b>Инструкции по оплате:</b>

<i>Здесь будет ссылка на оплату через выбранный способ.
Для полной интеграции необходимо подключить платежный шлюз (ЮKassa, CryptoBot и т.д.)</i>

📝 После оплаты премиум будет активирован автоматически.

<b>Контакты для помощи:</b>
@support_propitashka
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"paid_{payment_data[1]}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="premium_plans")],
    ])
    
    await callback.message.edit_text(text, parse_mode='HTML', reply_markup=keyboard)
    await callback.answer()
    
    logger.info(f"User {callback.from_user.id} selected payment method: {payment_method}")

@dp.callback_query(F.data.startswith("paid_"))
async def callback_payment_confirmed(callback: CallbackQuery, state: FSMContext):
    """Подтверждение оплаты (для демо)"""
    # В реальной системе здесь должна быть проверка оплаты через API платежной системы
    
    await callback.answer(
        "✅ Спасибо! Проверяем оплату...\n\n"
        "После подтверждения премиум будет активирован автоматически.",
        show_alert=True
    )
    
    await callback.message.edit_text(
        "🎉 <b>Заявка на активацию премиума принята!</b>\n\n"
        "Обычно проверка занимает 5-10 минут.\n"
        "Мы отправим уведомление, когда премиум будет активирован.\n\n"
        "📧 На вопросы ответим в @support_propitashka",
        parse_mode='HTML',
        reply_markup=get_main_menu_keyboard()
    )

@dp.callback_query(F.data == "my_stats")
async def callback_my_stats(callback: CallbackQuery):
    """Показывает статистику пользователя"""
    user_id = callback.from_user.id
    
    try:
        # Получаем данные пользователя
        cursor.execute("""
            SELECT 
                um.is_premium,
                um.premium_until,
                um.total_referrals,
                s.subscription_type,
                s.start_date
            FROM user_main um
            LEFT JOIN subscriptions s ON um.user_id = s.user_id AND s.is_active = TRUE
            WHERE um.user_id = %s
        """, (user_id,))
        
        data = cursor.fetchone()
        if not data:
            await callback.answer("❌ Ошибка при получении данных", show_alert=True)
            return
        
        is_premium, premium_until, total_refs, sub_type, start_date = data
        
        # Статус подписки
        if is_premium and premium_until:
            status_text = f"💎 Премиум до {premium_until.strftime('%d.%m.%Y')}"
        else:
            status_text = "🆓 Бесплатная"
        
        # Дней с момента регистрации
        days_registered = (datetime.now() - start_date).days if start_date else 0
        
        text = f"""
📊 <b>Ваша статистика</b>

<b>Подписка:</b> {status_text}
<b>Тип:</b> {sub_type or 'free'}

<b>Реферальная программа:</b>
• Приглашено друзей: {total_refs or 0}
• Получено премиум дней: {(total_refs or 0) * 7}

<b>Использование бота:</b>
• Дней с регистрации: {days_registered}

💡 <i>Пригласите друзей и получите больше дней премиума!</i>
"""
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎁 Пригласить друзей", callback_data="referral_program")],
            [InlineKeyboardButton(text="💎 Купить премиум", callback_data="premium_plans")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")],
        ])
        
        await callback.message.edit_text(text, parse_mode='HTML', reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in my_stats: {e}")
        await callback.answer("❌ Ошибка при получении статистики", show_alert=True)

# ============================================
# ЗАПУСК БОТА
# ============================================

async def main():
    """Главная функция запуска бота"""
    logger.info("🚀 Referral Bot starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Referral Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")

