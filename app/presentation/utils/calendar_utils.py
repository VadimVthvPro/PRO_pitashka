"""
Утилита для рендеринга инлайн-календаря выбора даты для Telegram бота.
Поддерживает локализацию, навигацию по месяцам и валидацию дат.
"""

import calendar
from datetime import datetime, date
from typing import Optional, Tuple
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


class CalendarKeyboard:
    """Класс для создания инлайн-календаря в Telegram боте"""
    
    # Локализация названий месяцев
    MONTHS = {
        'ru': [
            'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
            'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
        ],
        'en': [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ],
        'de': [
            'Januar', 'Februar', 'März', 'April', 'Mai', 'Juni',
            'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember'
        ],
        'fr': [
            'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
            'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'
        ],
        'es': [
            'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
            'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
        ]
    }
    
    # Локализация дней недели (сокращенные)
    WEEKDAYS = {
        'ru': ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'],
        'en': ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su'],
        'de': ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'],
        'fr': ['Lu', 'Ma', 'Me', 'Je', 'Ve', 'Sa', 'Di'],
        'es': ['Lu', 'Ma', 'Mi', 'Ju', 'Vi', 'Sá', 'Do']
    }
    
    # Локализация кнопок управления
    BUTTONS = {
        'ru': {'cancel': '❌ Отмена', 'today': '📅 Сегодня'},
        'en': {'cancel': '❌ Cancel', 'today': '📅 Today'},
        'de': {'cancel': '❌ Abbrechen', 'today': '📅 Heute'},
        'fr': {'cancel': '❌ Annuler', 'today': '📅 Aujourd\'hui'},
        'es': {'cancel': '❌ Cancelar', 'today': '📅 Hoy'}
    }
    
    def __init__(self, lang: str = 'ru', min_date: Optional[date] = None, max_date: Optional[date] = None):
        """
        Инициализация календаря
        
        Args:
            lang: Код языка (ru, en, de, fr, es)
            min_date: Минимальная допустимая дата
            max_date: Максимальная допустимая дата
        """
        self.lang = lang if lang in self.MONTHS else 'ru'
        self.min_date = min_date
        self.max_date = max_date
        self._calendar = calendar.Calendar(firstweekday=0)  # Неделя начинается с понедельника
    
    def create_year_selector(self, context: str = 'birthdate', lang: str = 'ru') -> InlineKeyboardMarkup:
        """
        Создает клавиатуру выбора года рождения
        
        Args:
            context: Контекст использования
            lang: Код языка
        
        Returns:
            InlineKeyboardMarkup: Клавиатура с годами
        """
        keyboard = []
        current_year = date.today().year
        
        # Заголовок
        year_labels = {
            'ru': '📅 Выберите год рождения',
            'en': '📅 Select birth year',
            'de': '📅 Geburtsjahr wählen',
            'fr': '📅 Sélectionnez l\'année',
            'es': '📅 Seleccione el año'
        }
        keyboard.append([
            InlineKeyboardButton(text=year_labels.get(lang, year_labels['ru']), callback_data="cal_ignore")
        ])
        
        # Создаем кнопки с годами
        # Максимальный год: текущий год - 10 лет (динамический)
        # Минимальный год: 1950 (фиксированный)
        # По 4 года в ряд
        start_year = current_year - 10  # Максимальный год (самый молодой пользователь)
        end_year = 1950  # Минимальный год (фиксированный)
        
        row = []
        for year in range(start_year, end_year, -4):
            row = []
            for i in range(4):
                y = year - i
                if y >= end_year:
                    row.append(
                        InlineKeyboardButton(text=str(y), callback_data=f"cal_{context}_year_{y}")
                    )
            if row:
                keyboard.append(row)
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    def create_calendar(self, year: int, month: int, context: str = 'birthdate') -> InlineKeyboardMarkup:
        """
        Создает инлайн-клавиатуру календаря для заданного месяца и года
        
        Args:
            year: Год
            month: Месяц (1-12)
            context: Контекст использования календаря (для callback_data)
        
        Returns:
            InlineKeyboardMarkup: Клавиатура с календарем
        """
        keyboard = []
        
        # Заголовок с названием месяца и года
        header_text = f"{self.MONTHS[self.lang][month - 1]} {year}"
        keyboard.append([
            InlineKeyboardButton(text="◀", callback_data=f"cal_{context}_prev_{year}_{month}"),
            InlineKeyboardButton(text=header_text, callback_data=f"cal_{context}_changeyear"),
            InlineKeyboardButton(text="▶", callback_data=f"cal_{context}_next_{year}_{month}")
        ])
        
        # Дни недели
        weekday_row = [
            InlineKeyboardButton(text=day, callback_data="cal_ignore")
            for day in self.WEEKDAYS[self.lang]
        ]
        keyboard.append(weekday_row)
        
        # Сетка дней месяца
        month_days = self._calendar.monthdayscalendar(year, month)
        for week in month_days:
            week_buttons = []
            for day in week:
                if day == 0:
                    # Пустая ячейка
                    week_buttons.append(
                        InlineKeyboardButton(text=" ", callback_data="cal_ignore")
                    )
                else:
                    # Проверяем, доступна ли дата
                    current_date = date(year, month, day)
                    is_available = self._is_date_available(current_date)
                    
                    if is_available:
                        week_buttons.append(
                            InlineKeyboardButton(
                                text=str(day),
                                callback_data=f"cal_{context}_day_{year}_{month}_{day}"
                            )
                        )
                    else:
                        # Недоступная дата (серая)
                        week_buttons.append(
                            InlineKeyboardButton(text=f"·{day}·", callback_data="cal_ignore")
                        )
            keyboard.append(week_buttons)
        
        # Кнопка возврата к выбору года (вместо отмены)
        back_labels = {
            'ru': '🔙 Выбрать другой год',
            'en': '🔙 Change year',
            'de': '🔙 Jahr ändern',
            'fr': '🔙 Changer d\'année',
            'es': '🔙 Cambiar año'
        }
        control_buttons = [
            InlineKeyboardButton(
                text=back_labels.get(self.lang, back_labels['ru']),
                callback_data=f"cal_{context}_changeyear"
            )
        ]
        keyboard.append(control_buttons)
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    def _is_date_available(self, check_date: date) -> bool:
        """
        Проверяет, доступна ли дата для выбора
        
        Args:
            check_date: Проверяемая дата
        
        Returns:
            bool: True если дата доступна для выбора
        """
        if self.min_date and check_date < self.min_date:
            return False
        if self.max_date and check_date > self.max_date:
            return False
        return True
    
    @staticmethod
    def parse_callback(callback_data: str) -> Tuple[str, Optional[dict]]:
        """
        Парсит callback_data от календаря
        
        Args:
            callback_data: Строка callback_data
        
        Returns:
            Tuple[str, Optional[dict]]: (action, data_dict)
        """
        parts = callback_data.split('_')
        
        if len(parts) < 3:
            return 'ignore', None
        
        context = parts[1]  # birthdate или другой контекст
        action = parts[2]   # prev, next, day, changeyear, year
        
        if action == 'ignore':
            return 'ignore', None
        
        if action == 'changeyear':
            return 'changeyear', {'context': context}
        
        if action == 'year':
            year = int(parts[3])
            return 'selectyear', {'context': context, 'year': year}
        
        if action == 'prev':
            year, month = int(parts[3]), int(parts[4])
            # Переход к предыдущему месяцу
            if month == 1:
                return 'navigate', {'context': context, 'year': year - 1, 'month': 12}
            else:
                return 'navigate', {'context': context, 'year': year, 'month': month - 1}
        
        if action == 'next':
            year, month = int(parts[3]), int(parts[4])
            # Переход к следующему месяцу
            if month == 12:
                return 'navigate', {'context': context, 'year': year + 1, 'month': 1}
            else:
                return 'navigate', {'context': context, 'year': year, 'month': month + 1}
        
        if action == 'day':
            year, month, day = int(parts[3]), int(parts[4]), int(parts[5])
            return 'select', {
                'context': context,
                'date': date(year, month, day),
                'year': year,
                'month': month,
                'day': day
            }
        
        return 'ignore', None
    
    @staticmethod
    def get_birthdate_calendar(lang: str = 'ru') -> Tuple[InlineKeyboardMarkup, int, int]:
        """
        Создает календарь для выбора даты рождения (ограничен разумными рамками)
        
        Args:
            lang: Код языка
        
        Returns:
            Tuple[InlineKeyboardMarkup, int, int]: (keyboard, year, month)
        """
        # Для даты рождения: от 100 лет назад до 10 лет назад
        today = date.today()
        min_date = date(today.year - 100, 1, 1)
        max_date = date(today.year - 10, today.month, today.day)
        
        # Начинаем с даты 30 лет назад (среднее значение)
        start_date = date(today.year - 30, today.month, 1)
        
        calendar_obj = CalendarKeyboard(lang=lang, min_date=min_date, max_date=max_date)
        keyboard = calendar_obj.create_calendar(start_date.year, start_date.month, context='birthdate')
        
        return keyboard, start_date.year, start_date.month


def get_calendar_keyboard(lang: str, year: int, month: int, context: str = 'birthdate') -> InlineKeyboardMarkup:
    """
    Вспомогательная функция для быстрого создания календаря с ограничениями по возрасту
    
    Args:
        lang: Код языка
        year: Год
        month: Месяц
        context: Контекст использования
    
    Returns:
        InlineKeyboardMarkup: Клавиатура календаря
    """
    today = date.today()
    min_date = date(today.year - 100, 1, 1)
    max_date = date(today.year - 10, today.month, today.day)
    
    calendar_obj = CalendarKeyboard(lang=lang, min_date=min_date, max_date=max_date)
    return calendar_obj.create_calendar(year, month, context=context)

