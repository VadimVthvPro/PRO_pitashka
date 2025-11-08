"""
Клавиатуры для системы тренировок
Управление инлайн-клавиатурами с пагинацией
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict, Tuple
import math
from logger_setup import bot_logger


class WorkoutKeyboards:
    """Генератор клавиатур для тренировок"""
    
    # Количество тренировок на странице
    ITEMS_PER_PAGE = 6
    
    def __init__(self, language: str = 'ru'):
        """
        Инициализация генератора клавиатур
        
        Args:
            language: Код языка для локализации кнопок
        """
        self.language = language
        self._translations = {
            'next': {
                'ru': '➡️ Вперед',
                'en': '➡️ Next',
                'de': '➡️ Weiter',
                'fr': '➡️ Suivant',
                'es': '➡️ Siguiente'
            },
            'prev': {
                'ru': '⬅️ Назад',
                'en': '⬅️ Previous',
                'de': '⬅️ Zurück',
                'fr': '⬅️ Précédent',
                'es': '⬅️ Anterior'
            },
            'main_menu': {
                'ru': '🏠 Главное меню',
                'en': '🏠 Main Menu',
                'de': '🏠 Hauptmenü',
                'fr': '🏠 Menu principal',
                'es': '🏠 Menú principal'
            },
            'cancel': {
                'ru': '❌ Отмена',
                'en': '❌ Cancel',
                'de': '❌ Abbrechen',
                'fr': '❌ Annuler',
                'es': '❌ Cancelar'
            },
            'page': {
                'ru': 'Стр',
                'en': 'Page',
                'de': 'Seite',
                'fr': 'Page',
                'es': 'Página'
            }
        }
    
    def get_text(self, key: str) -> str:
        """
        Получить переведенный текст
        
        Args:
            key: Ключ перевода
            
        Returns:
            Переведенный текст
        """
        return self._translations.get(key, {}).get(self.language, self._translations[key]['en'])
    
    def create_training_keyboard(
        self,
        trainings: List[Dict],
        page: int = 0
    ) -> InlineKeyboardMarkup:
        """
        Создать клавиатуру со списком тренировок с пагинацией
        
        Args:
            trainings: Список тренировок с полями id, name, emoji
            page: Номер текущей страницы (начиная с 0)
            
        Returns:
            InlineKeyboardMarkup с тренировками и навигацией
        """
        keyboard = []
        
        # Вычисляем диапазон элементов для текущей страницы
        start_idx = page * self.ITEMS_PER_PAGE
        end_idx = start_idx + self.ITEMS_PER_PAGE
        page_trainings = trainings[start_idx:end_idx]
        
        # Создаем кнопки для тренировок (по 2 в ряд)
        for i in range(0, len(page_trainings), 2):
            row = []
            for j in range(2):
                if i + j < len(page_trainings):
                    training = page_trainings[i + j]
                    emoji = training.get('emoji', '')
                    name = training.get('name', '')
                    
                    # Формируем текст кнопки
                    button_text = f"{emoji} {name}" if emoji else name
                    
                    # Формируем callback_data
                    callback_data = f"workout_{training['id']}"
                    
                    row.append(InlineKeyboardButton(
                        text=button_text,
                        callback_data=callback_data
                    ))
            keyboard.append(row)
        
        # Добавляем навигационные кнопки
        total_pages = math.ceil(len(trainings) / self.ITEMS_PER_PAGE)
        
        if total_pages > 1:
            nav_row = []
            
            # Кнопка "Назад"
            if page > 0:
                nav_row.append(InlineKeyboardButton(
                    text=self.get_text('prev'),
                    callback_data=f"workout_page_{page - 1}"
                ))
            
            # Индикатор страницы
            page_indicator = f"{self.get_text('page')} {page + 1}/{total_pages}"
            nav_row.append(InlineKeyboardButton(
                text=page_indicator,
                callback_data="workout_page_info"  # Не делает ничего, просто индикатор
            ))
            
            # Кнопка "Вперед"
            if page < total_pages - 1:
                nav_row.append(InlineKeyboardButton(
                    text=self.get_text('next'),
                    callback_data=f"workout_page_{page + 1}"
                ))
            
            keyboard.append(nav_row)
        
        # Кнопка "Главное меню"
        keyboard.append([
            InlineKeyboardButton(
                text=self.get_text('main_menu'),
                callback_data="workout_main_menu"
            )
        ])
        
        bot_logger.debug(
            f"Created workout keyboard: page {page + 1}/{total_pages}, "
            f"{len(page_trainings)} items shown"
        )
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    def create_duration_cancel_keyboard(self) -> InlineKeyboardMarkup:
        """
        Создать клавиатуру с кнопкой отмены для ввода длительности
        
        Returns:
            InlineKeyboardMarkup с кнопкой отмены
        """
        keyboard = [
            [
                InlineKeyboardButton(
                    text=self.get_text('cancel'),
                    callback_data="workout_cancel"
                )
            ],
            [
                InlineKeyboardButton(
                    text=self.get_text('main_menu'),
                    callback_data="workout_main_menu"
                )
            ]
        ]
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def parse_workout_callback(callback_data: str) -> Tuple[str, int]:
        """
        Разобрать callback_data от кнопки тренировки
        
        Args:
            callback_data: Строка вида "workout_123" или "workout_page_2"
            
        Returns:
            Кортеж (тип_действия, значение)
            - ("workout", id_тренировки)
            - ("page", номер_страницы)
            - ("main_menu", 0)
            - ("cancel", 0)
            - ("unknown", 0)
        """
        parts = callback_data.split('_')
        
        if len(parts) < 2:
            bot_logger.warning(f"Invalid callback_data format: {callback_data}")
            return ("unknown", 0)
        
        action_type = parts[0]
        
        if action_type == "workout":
            if len(parts) == 2:
                # workout_123 -> выбор тренировки
                try:
                    return ("workout", int(parts[1]))
                except ValueError:
                    if parts[1] == "main":
                        return ("main_menu", 0)
                    elif parts[1] == "cancel":
                        return ("cancel", 0)
                    elif parts[1] == "page":
                        # workout_page_2
                        if len(parts) >= 3:
                            try:
                                return ("page", int(parts[2]))
                            except ValueError:
                                pass
            elif len(parts) == 3 and parts[1] == "page":
                # workout_page_2
                try:
                    return ("page", int(parts[2]))
                except ValueError:
                    pass
        
        bot_logger.warning(f"Could not parse callback_data: {callback_data}")
        return ("unknown", 0)


def create_workout_keyboards(language: str = 'ru') -> WorkoutKeyboards:
    """
    Фабричная функция для создания генератора клавиатур
    
    Args:
        language: Код языка
        
    Returns:
        Экземпляр WorkoutKeyboards
    """
    return WorkoutKeyboards(language)


# Дополнительная функция для быстрой генерации callback_data
def make_workout_callback(workout_id: int) -> str:
    """
    Сгенерировать callback_data для выбора тренировки
    
    Args:
        workout_id: ID тренировки
        
    Returns:
        Строка callback_data
    """
    return f"workout_{workout_id}"


def make_page_callback(page: int) -> str:
    """
    Сгенерировать callback_data для перехода на страницу
    
    Args:
        page: Номер страницы
        
    Returns:
        Строка callback_data
    """
    return f"workout_page_{page}"


