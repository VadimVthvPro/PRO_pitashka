#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
РЕКЛАМНЫЙ БОТ PROPITASHKA
=========================
Принимает рекламные материалы от администратора и сохраняет их в БД
для последующей рассылки бесплатным пользователям основного бота.

Автор: AI Assistant
Дата: 2025-10-31
"""

import asyncio
import logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message
from config import config
import psycopg2

# ============================================
# КОНФИГУРАЦИЯ
# ============================================

AD_BOT_TOKEN = "8355852802:AAFnZgJ9dJ5Pjs3JP4tz8wUnvrCAfP8S-xk"
ADMIN_USER_IDS = [954467391]  # Добавьте свой Telegram ID

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ad_bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('AdBot')

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
# ИНИЦИАЛИЗАЦИЯ БОТА
# ============================================

bot = Bot(token=AD_BOT_TOKEN)
dp = Dispatcher()

# ============================================
# MIDDLEWARE ДЛЯ ПРОВЕРКИ АДМИНА
# ============================================

def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором"""
    return user_id in ADMIN_USER_IDS

# ============================================
# ОБРАБОТЧИКИ КОМАНД
# ============================================

@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.answer("⛔ У вас нет доступа к этому боту.")
        logger.warning(f"Unauthorized access attempt by user {user_id}")
        return
    
    welcome_text = """
🤖 <b>Рекламный Бот PROpitashka</b>

Добро пожаловать в панель управления рекламой!

📤 <b>Как отправить рекламу:</b>
1. Отправьте мне текст, фото, видео или документ
2. Я автоматически сохраню его в базу данных
3. Реклама начнет показываться бесплатным пользователям

📊 <b>Доступные команды:</b>
/start - Показать это сообщение
/stats - Статистика рекламных материалов
/list - Список всех реклам
/activate [id] - Активировать рекламу
/deactivate [id] - Деактивировать рекламу
/delete [id] - Удалить рекламу

<i>Все сообщения автоматически сохраняются как реклама.</i>
"""
    
    await message.answer(welcome_text, parse_mode='HTML')
    logger.info(f"Admin {user_id} started the ad bot")

@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    """Показывает статистику рекламных материалов"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.answer("⛔ У вас нет доступа к этому боту.")
        return
    
    try:
        # Получаем общую статистику
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN is_active THEN 1 END) as active,
                SUM(impressions_count) as total_impressions,
                SUM(clicks_count) as total_clicks
            FROM advertisements
        """)
        stats = cursor.fetchone()
        
        total, active, impressions, clicks = stats
        ctr = (clicks / impressions * 100) if impressions and impressions > 0 else 0
        
        stats_text = f"""
📊 <b>Статистика рекламы</b>

📦 Всего материалов: {total}
✅ Активных: {active}
👁 Показов: {impressions or 0}
🖱 Кликов: {clicks or 0}
📈 CTR: {ctr:.2f}%

<i>Используйте /list для просмотра всех реклам</i>
"""
        
        await message.answer(stats_text, parse_mode='HTML')
        logger.info(f"Admin {user_id} viewed stats")
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        await message.answer("❌ Ошибка при получении статистики")

@dp.message(Command("list"))
async def cmd_list(message: Message):
    """Показывает список всех рекламных материалов"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.answer("⛔ У вас нет доступа к этому боту.")
        return
    
    try:
        cursor.execute("""
            SELECT 
                id, 
                title, 
                media_type, 
                is_active, 
                impressions_count,
                clicks_count,
                created_at
            FROM advertisements
            ORDER BY created_at DESC
            LIMIT 20
        """)
        
        ads = cursor.fetchall()
        
        if not ads:
            await message.answer("📭 Рекламных материалов пока нет.")
            return
        
        list_text = "📋 <b>Список рекламных материалов:</b>\n\n"
        
        for ad in ads:
            ad_id, title, media_type, is_active, impressions, clicks, created_at = ad
            status = "✅" if is_active else "❌"
            
            list_text += f"{status} <b>ID {ad_id}</b> | {media_type}\n"
            list_text += f"   📊 Показов: {impressions} | Кликов: {clicks}\n"
            list_text += f"   📅 {created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
        
        list_text += "\n💡 <i>Используйте /activate или /deactivate для управления</i>"
        
        await message.answer(list_text, parse_mode='HTML')
        logger.info(f"Admin {user_id} viewed ad list")
        
    except Exception as e:
        logger.error(f"Error listing ads: {e}")
        await message.answer("❌ Ошибка при получении списка")

@dp.message(Command("activate"))
async def cmd_activate(message: Message):
    """Активирует рекламу по ID"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.answer("⛔ У вас нет доступа к этому боту.")
        return
    
    try:
        args = message.text.split()
        if len(args) < 2:
            await message.answer("❌ Укажите ID рекламы: /activate [id]")
            return
        
        ad_id = int(args[1])
        
        cursor.execute("""
            UPDATE advertisements 
            SET is_active = TRUE 
            WHERE id = %s
            RETURNING id
        """, (ad_id,))
        
        if cursor.fetchone():
            await message.answer(f"✅ Реклама ID {ad_id} активирована!")
            logger.info(f"Admin {user_id} activated ad {ad_id}")
        else:
            await message.answer(f"❌ Реклама с ID {ad_id} не найдена")
            
    except ValueError:
        await message.answer("❌ Неверный формат ID")
    except Exception as e:
        logger.error(f"Error activating ad: {e}")
        await message.answer("❌ Ошибка при активации")

@dp.message(Command("deactivate"))
async def cmd_deactivate(message: Message):
    """Деактивирует рекламу по ID"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.answer("⛔ У вас нет доступа к этому боту.")
        return
    
    try:
        args = message.text.split()
        if len(args) < 2:
            await message.answer("❌ Укажите ID рекламы: /deactivate [id]")
            return
        
        ad_id = int(args[1])
        
        cursor.execute("""
            UPDATE advertisements 
            SET is_active = FALSE 
            WHERE id = %s
            RETURNING id
        """, (ad_id,))
        
        if cursor.fetchone():
            await message.answer(f"✅ Реклама ID {ad_id} деактивирована!")
            logger.info(f"Admin {user_id} deactivated ad {ad_id}")
        else:
            await message.answer(f"❌ Реклама с ID {ad_id} не найдена")
            
    except ValueError:
        await message.answer("❌ Неверный формат ID")
    except Exception as e:
        logger.error(f"Error deactivating ad: {e}")
        await message.answer("❌ Ошибка при деактивации")

@dp.message(Command("delete"))
async def cmd_delete(message: Message):
    """Удаляет рекламу по ID"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.answer("⛔ У вас нет доступа к этому боту.")
        return
    
    try:
        args = message.text.split()
        if len(args) < 2:
            await message.answer("❌ Укажите ID рекламы: /delete [id]")
            return
        
        ad_id = int(args[1])
        
        cursor.execute("""
            DELETE FROM advertisements 
            WHERE id = %s
            RETURNING id
        """, (ad_id,))
        
        if cursor.fetchone():
            await message.answer(f"✅ Реклама ID {ad_id} удалена!")
            logger.info(f"Admin {user_id} deleted ad {ad_id}")
        else:
            await message.answer(f"❌ Реклама с ID {ad_id} не найдена")
            
    except ValueError:
        await message.answer("❌ Неверный формат ID")
    except Exception as e:
        logger.error(f"Error deleting ad: {e}")
        await message.answer("❌ Ошибка при удалении")

# ============================================
# ОБРАБОТЧИК РЕКЛАМНЫХ МАТЕРИАЛОВ
# ============================================

@dp.message(F.content_type.in_(['text', 'photo', 'video', 'document']))
async def handle_ad_content(message: Message):
    """Обрабатывает входящие рекламные материалы от админа"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.answer("⛔ У вас нет доступа к этому боту.")
        return
    
    try:
        # Определяем тип контента
        if message.photo:
            media_type = 'photo'
            media_file_id = message.photo[-1].file_id
            content = message.caption or "Рекламное фото"
            title = content[:50] if len(content) > 50 else content
        elif message.video:
            media_type = 'video'
            media_file_id = message.video.file_id
            content = message.caption or "Рекламное видео"
            title = content[:50] if len(content) > 50 else content
        elif message.document:
            media_type = 'document'
            media_file_id = message.document.file_id
            content = message.caption or "Рекламный документ"
            title = content[:50] if len(content) > 50 else content
        else:
            media_type = 'text'
            media_file_id = None
            content = message.text
            title = content[:50] if len(content) > 50 else content
        
        # Сохраняем в БД
        cursor.execute("""
            INSERT INTO advertisements 
            (title, content, media_type, media_file_id, is_active, priority)
            VALUES (%s, %s, %s, %s, TRUE, 5)
            RETURNING id
        """, (title, content, media_type, media_file_id))
        
        ad_id = cursor.fetchone()[0]
        
        await message.answer(
            f"✅ <b>Реклама сохранена!</b>\n\n"
            f"🆔 ID: {ad_id}\n"
            f"📝 Тип: {media_type}\n"
            f"📊 Статус: Активна\n\n"
            f"<i>Реклама будет показываться бесплатным пользователям.</i>",
            parse_mode='HTML'
        )
        
        logger.info(f"Admin {user_id} added new ad (ID: {ad_id}, type: {media_type})")
        
    except Exception as e:
        logger.error(f"Error saving ad: {e}")
        await message.answer("❌ Ошибка при сохранении рекламы")

# ============================================
# ЗАПУСК БОТА
# ============================================

async def main():
    """Главная функция запуска бота"""
    logger.info("🚀 Ad Bot starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Ad Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")

