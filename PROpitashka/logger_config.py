"""
Модуль конфигурации логирования для Telegram бота PROpitashka
Сохраняет логи в файлы и базу данных PostgreSQL
"""
import logging
import psycopg2
from logging.handlers import RotatingFileHandler
import os
from datetime import datetime


class DatabaseHandler(logging.Handler):
    """
    Кастомный handler для записи логов в PostgreSQL
    """
    def __init__(self, db_config):
        logging.Handler.__init__(self)
        self.db_config = db_config
        self._create_table()
    
    def _create_table(self):
        """Создаёт таблицу для логов, если её нет"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bot_logs (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    level VARCHAR(10),
                    logger_name VARCHAR(100),
                    message TEXT,
                    user_id BIGINT,
                    username VARCHAR(100),
                    function_name VARCHAR(100),
                    line_number INTEGER,
                    error_traceback TEXT
                );
                
                CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON bot_logs(timestamp);
                CREATE INDEX IF NOT EXISTS idx_logs_level ON bot_logs(level);
                CREATE INDEX IF NOT EXISTS idx_logs_user_id ON bot_logs(user_id);
            """)
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Ошибка создания таблицы логов: {e}")
    
    def emit(self, record):
        """Записывает лог в базу данных"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            # Извлекаем дополнительную информацию из record
            user_id = getattr(record, 'user_id', None)
            username = getattr(record, 'username', None)
            error_traceback = getattr(record, 'exc_text', None)
            
            cursor.execute("""
                INSERT INTO bot_logs 
                (level, logger_name, message, user_id, username, function_name, line_number, error_traceback)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                record.levelname,
                record.name,
                self.format(record),
                user_id,
                username,
                record.funcName,
                record.lineno,
                error_traceback
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            # Если не удалось записать в БД, выводим в консоль
            print(f"Ошибка записи лога в БД: {e}")


def setup_logger(name='bot_logger', log_dir='logs'):
    """
    Настраивает логгер с записью в файлы и базу данных
    
    Args:
        name: Имя логгера
        log_dir: Директория для хранения лог-файлов
    
    Returns:
        Настроенный объект logger
    """
    # Создаём директорию для логов, если её нет
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Создаём логгер
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # Очищаем существующие handlers (для избежания дублирования)
    if logger.handlers:
        logger.handlers.clear()
    
    # Формат для логов
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(funcName)s() - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 1. Handler для записи всех логов в файл с ротацией
    all_logs_handler = RotatingFileHandler(
        os.path.join(log_dir, 'bot_all.log'),
        maxBytes=10 * 1024 * 1024,  # 10 МБ
        backupCount=10,
        encoding='utf-8'
    )
    all_logs_handler.setLevel(logging.DEBUG)
    all_logs_handler.setFormatter(detailed_formatter)
    
    # 2. Handler для записи только ошибок в отдельный файл
    error_logs_handler = RotatingFileHandler(
        os.path.join(log_dir, 'bot_errors.log'),
        maxBytes=5 * 1024 * 1024,  # 5 МБ
        backupCount=10,
        encoding='utf-8'
    )
    error_logs_handler.setLevel(logging.ERROR)
    error_logs_handler.setFormatter(detailed_formatter)
    
    # 3. Handler для консоли (для разработки)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    
    # 4. Handler для записи в базу данных
    try:
        # Import centralized database config
        import sys
        current_dir = os.path.dirname(__file__)
        sys.path.insert(0, current_dir)
        from db_config import DB_CONFIG
        
        db_handler = DatabaseHandler(DB_CONFIG)
        db_handler.setLevel(logging.INFO)  # В БД пишем только INFO и выше
        db_handler.setFormatter(simple_formatter)
        logger.addHandler(db_handler)
    except Exception as e:
        print(f"Failed to connect DatabaseHandler: {e}")
    
    # Добавляем handlers к логгеру
    logger.addHandler(all_logs_handler)
    logger.addHandler(error_logs_handler)
    logger.addHandler(console_handler)
    
    return logger


def log_user_action(logger, user, action, details=""):
    """
    Вспомогательная функция для логирования действий пользователя
    
    Args:
        logger: Объект логгера
        user: Объект пользователя Telegram
        action: Описание действия
        details: Дополнительные детали
    """
    log_message = f"Пользователь @{user.username} (ID: {user.id}) - {action}"
    if details:
        log_message += f" | {details}"
    
    # Добавляем дополнительные атрибуты к логу
    extra = {
        'user_id': user.id,
        'username': user.username or 'NoUsername'
    }
    
    logger.info(log_message, extra=extra)


def log_error(logger, user, error, context=""):
    """
    Вспомогательная функция для логирования ошибок
    
    Args:
        logger: Объект логгера
        user: Объект пользователя Telegram (может быть None)
        error: Объект исключения
        context: Контекст ошибки
    """
    user_info = f"@{user.username} (ID: {user.id})" if user else "Системная ошибка"
    log_message = f"{user_info} - {context}: {type(error).__name__}: {str(error)}"
    
    extra = {}
    if user:
        extra = {
            'user_id': user.id,
            'username': user.username or 'NoUsername'
        }
    
    logger.error(log_message, exc_info=True, extra=extra)

