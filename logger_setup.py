"""
Настройка логирования для бота PROpitashka
"""
import logging
import sys
from datetime import datetime

def setup_logger():
    """Настраивает логгер с выводом в файл и консоль"""
    
    # Создаем логгер
    logger = logging.getLogger('PROpitashka')
    logger.setLevel(logging.DEBUG)
    
    # Форматтер для логов
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Обработчик для файла
    file_handler = logging.FileHandler('bot.log', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # Обработчик для консоли
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # Добавляем обработчики
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# Создаем глобальный логгер
bot_logger = setup_logger()


