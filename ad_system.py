#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
МОДУЛЬ РЕКЛАМНОЙ СИСТЕМЫ
=========================
Управляет показом рекламы бесплатным пользователям основного бота.

Автор: AI Assistant
Дата: 2025-10-31
"""

import random
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple
import psycopg2
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger('AdSystem')

# ============================================
# КОНФИГУРАЦИЯ РЕКЛАМЫ
# ============================================

# Минимальный интервал между показами рекламы (в минутах)
MIN_AD_INTERVAL = 120  # 2 часа

# Максимальное количество показов в день
MAX_ADS_PER_DAY = 5

# Вероятность показа рекламы (0.0 - 1.0)
AD_SHOW_PROBABILITY = 0.3  # 30% шанс при каждом запросе

# ============================================
# ОСНОВНЫЕ ФУНКЦИИ
# ============================================

def is_premium_user(cursor, user_id: int) -> bool:
    """
    Проверяет, является ли пользователь премиум
    
    Args:
        cursor: Курсор БД
        user_id: ID пользователя
    
    Returns:
        True если пользователь премиум, False иначе
    """
    try:
        cursor.execute("""
            SELECT is_premium, premium_until
            FROM user_main
            WHERE user_id = %s
        """, (user_id,))
        
        result = cursor.fetchone()
        
        if not result:
            return False
        
        is_premium, premium_until = result
        
        # Проверяем не истек ли премиум
        if is_premium and premium_until:
            if premium_until > datetime.now():
                return True
            else:
                # Премиум истек, обновляем статус
                cursor.execute("""
                    UPDATE user_main
                    SET is_premium = FALSE, premium_until = NULL
                    WHERE user_id = %s
                """, (user_id,))
                return False
        
        return is_premium
        
    except Exception as e:
        logger.error(f"Error checking premium status for user {user_id}: {e}")
        return False

def should_show_ad(cursor, user_id: int) -> bool:
    """
    Определяет, нужно ли показывать рекламу пользователю
    
    Args:
        cursor: Курсор БД
        user_id: ID пользователя
    
    Returns:
        True если нужно показать рекламу, False иначе
    """
    try:
        # Премиум пользователям не показываем рекламу
        if is_premium_user(cursor, user_id):
            return False
        
        # Проверяем время последнего показа
        cursor.execute("""
            SELECT last_ad_shown
            FROM user_main
            WHERE user_id = %s
        """, (user_id,))
        
        result = cursor.fetchone()
        
        if result and result[0]:
            last_shown = result[0]
            time_since_last = (datetime.now() - last_shown).total_seconds() / 60
            
            if time_since_last < MIN_AD_INTERVAL:
                return False
        
        # Проверяем количество показов за сегодня
        cursor.execute("""
            SELECT COUNT(*)
            FROM ad_views
            WHERE user_id = %s 
            AND viewed_at >= CURRENT_DATE
        """, (user_id,))
        
        today_count = cursor.fetchone()[0]
        
        if today_count >= MAX_ADS_PER_DAY:
            return False
        
        # Случайная проверка (чтобы не показывать рекламу слишком часто)
        return random.random() < AD_SHOW_PROBABILITY
        
    except Exception as e:
        logger.error(f"Error in should_show_ad for user {user_id}: {e}")
        return False

def get_random_ad(cursor) -> Optional[Tuple]:
    """
    Получает случайную активную рекламу из БД
    
    Args:
        cursor: Курсор БД
    
    Returns:
        Кортеж с данными рекламы или None
    """
    try:
        # Получаем все активные рекламы
        cursor.execute("""
            SELECT 
                id, 
                title, 
                content, 
                media_type, 
                media_file_id,
                priority
            FROM advertisements
            WHERE is_active = TRUE
            AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
            ORDER BY priority DESC, RANDOM()
            LIMIT 1
        """)
        
        return cursor.fetchone()
        
    except Exception as e:
        logger.error(f"Error getting random ad: {e}")
        return None

async def show_ad_to_user(bot: Bot, cursor, user_id: int, chat_id: int) -> bool:
    """
    Показывает рекламу пользователю
    
    Args:
        bot: Экземпляр бота
        cursor: Курсор БД
        user_id: ID пользователя
        chat_id: ID чата
    
    Returns:
        True если реклама показана, False иначе
    """
    try:
        # Проверяем, нужно ли показывать рекламу
        if not should_show_ad(cursor, user_id):
            return False
        
        # Получаем рекламу
        ad_data = get_random_ad(cursor)
        
        if not ad_data:
            logger.warning("No active ads available")
            return False
        
        ad_id, title, content, media_type, media_file_id, priority = ad_data
        
        # Создаем клавиатуру
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💎 Отключить рекламу (Премиум)", callback_data="get_premium")],
        ])
        
        # Отправляем рекламу в зависимости от типа
        if media_type == 'photo' and media_file_id:
            await bot.send_photo(
                chat_id=chat_id,
                photo=media_file_id,
                caption=f"📢 <b>Реклама</b>\n\n{content}",
                reply_markup=keyboard,
                parse_mode='HTML'
            )
        elif media_type == 'video' and media_file_id:
            await bot.send_video(
                chat_id=chat_id,
                video=media_file_id,
                caption=f"📢 <b>Реклама</b>\n\n{content}",
                reply_markup=keyboard,
                parse_mode='HTML'
            )
        elif media_type == 'document' and media_file_id:
            await bot.send_document(
                chat_id=chat_id,
                document=media_file_id,
                caption=f"📢 <b>Реклама</b>\n\n{content}",
                reply_markup=keyboard,
                parse_mode='HTML'
            )
        else:
            await bot.send_message(
                chat_id=chat_id,
                text=f"📢 <b>Реклама</b>\n\n{content}",
                reply_markup=keyboard,
                parse_mode='HTML'
            )
        
        # Записываем просмотр
        cursor.execute("""
            INSERT INTO ad_views (user_id, ad_id)
            VALUES (%s, %s)
        """, (user_id, ad_id))
        
        # Обновляем счетчик показов
        cursor.execute("""
            UPDATE advertisements
            SET impressions_count = impressions_count + 1
            WHERE id = %s
        """, (ad_id,))
        
        # Обновляем время последнего показа
        cursor.execute("""
            UPDATE user_main
            SET last_ad_shown = CURRENT_TIMESTAMP
            WHERE user_id = %s
        """, (user_id,))
        
        logger.info(f"Ad {ad_id} shown to user {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error showing ad to user {user_id}: {e}")
        return False

def record_ad_click(cursor, user_id: int, ad_id: int):
    """
    Записывает клик по рекламе
    
    Args:
        cursor: Курсор БД
        user_id: ID пользователя
        ad_id: ID рекламы
    """
    try:
        # Обновляем статус клика в просмотрах
        cursor.execute("""
            UPDATE ad_views
            SET clicked = TRUE
            WHERE user_id = %s AND ad_id = %s
            AND id = (
                SELECT id FROM ad_views
                WHERE user_id = %s AND ad_id = %s
                ORDER BY viewed_at DESC
                LIMIT 1
            )
        """, (user_id, ad_id, user_id, ad_id))
        
        # Увеличиваем счетчик кликов
        cursor.execute("""
            UPDATE advertisements
            SET clicks_count = clicks_count + 1
            WHERE id = %s
        """, (ad_id,))
        
        logger.info(f"User {user_id} clicked on ad {ad_id}")
        
    except Exception as e:
        logger.error(f"Error recording ad click: {e}")

# ============================================
# ФУНКЦИИ ПРОВЕРКИ ПОДПИСКИ
# ============================================

async def check_expired_subscriptions(cursor):
    """
    Проверяет истекшие подписки и деактивирует их
    Эта функция должна вызываться периодически (например, раз в день)
    """
    try:
        # Деактивируем истекшие подписки
        cursor.execute("""
            UPDATE subscriptions
            SET is_active = FALSE
            WHERE is_active = TRUE
            AND end_date IS NOT NULL
            AND end_date < CURRENT_TIMESTAMP
            RETURNING user_id
        """)
        
        expired_users = cursor.fetchall()
        
        # Обновляем статус премиум у пользователей
        for (user_id,) in expired_users:
            cursor.execute("""
                UPDATE user_main
                SET is_premium = FALSE, premium_until = NULL
                WHERE user_id = %s
            """, (user_id,))
            
            logger.info(f"Subscription expired for user {user_id}")
        
        if expired_users:
            logger.info(f"Deactivated {len(expired_users)} expired subscriptions")
        
    except Exception as e:
        logger.error(f"Error checking expired subscriptions: {e}")

def get_user_premium_info(cursor, user_id: int) -> dict:
    """
    Получает информацию о премиум-статусе пользователя
    
    Args:
        cursor: Курсор БД
        user_id: ID пользователя
    
    Returns:
        Словарь с информацией о премиуме
    """
    try:
        cursor.execute("""
            SELECT 
                um.is_premium,
                um.premium_until,
                s.subscription_type,
                s.end_date
            FROM user_main um
            LEFT JOIN subscriptions s ON um.user_id = s.user_id AND s.is_active = TRUE
            WHERE um.user_id = %s
        """, (user_id,))
        
        result = cursor.fetchone()
        
        if not result:
            return {
                'is_premium': False,
                'premium_until': None,
                'subscription_type': 'free',
                'days_left': 0
            }
        
        is_premium, premium_until, sub_type, end_date = result
        
        days_left = 0
        if premium_until:
            days_left = (premium_until - datetime.now()).days
            if days_left < 0:
                days_left = 0
        
        return {
            'is_premium': is_premium,
            'premium_until': premium_until,
            'subscription_type': sub_type or 'free',
            'days_left': days_left
        }
        
    except Exception as e:
        logger.error(f"Error getting premium info for user {user_id}: {e}")
        return {
            'is_premium': False,
            'premium_until': None,
            'subscription_type': 'free',
            'days_left': 0
        }


