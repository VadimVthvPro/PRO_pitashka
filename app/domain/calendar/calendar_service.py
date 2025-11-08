"""
Сервис для работы с датами и календарем.
Содержит бизнес-логику валидации дат, вычисления возраста и т.д.
"""

from datetime import date, datetime
from typing import Tuple, Optional


class DateValidationError(Exception):
    """Исключение для ошибок валидации даты"""
    pass


class CalendarService:
    """Сервис для работы с датами и календарем"""
    
    # Минимальный возраст для регистрации
    MIN_AGE = 10
    # Минимальный год рождения (фиксированный)
    MIN_BIRTH_YEAR = 1950
    
    @staticmethod
    def validate_birthdate(birthdate: date, min_age: int = MIN_AGE) -> Tuple[bool, Optional[str]]:
        """
        Валидирует дату рождения
        
        Args:
            birthdate: Дата рождения
            min_age: Минимальный возраст
        
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_key)
            error_key может быть: 'too_young', 'too_old', 'future_date', None
        """
        today = date.today()
        
        # Проверка, что дата не в будущем
        if birthdate > today:
            return False, 'future_date'
        
        # Вычисляем возраст
        age = CalendarService.calculate_age(birthdate)
        
        # Проверка минимального возраста
        if age < min_age:
            return False, 'too_young'
        
        # Проверка минимального года (1950)
        if birthdate.year < CalendarService.MIN_BIRTH_YEAR:
            return False, 'too_old'
        
        return True, None
    
    @staticmethod
    def calculate_age(birthdate: date, reference_date: Optional[date] = None) -> int:
        """
        Вычисляет возраст на основе даты рождения
        
        Args:
            birthdate: Дата рождения
            reference_date: Дата относительно которой вычисляется возраст (по умолчанию сегодня)
        
        Returns:
            int: Возраст в годах
        """
        if reference_date is None:
            reference_date = date.today()
        
        age = reference_date.year - birthdate.year
        
        # Корректируем если день рождения еще не наступил в этом году
        if (reference_date.month, reference_date.day) < (birthdate.month, birthdate.day):
            age -= 1
        
        return age
    
    @staticmethod
    def format_date(date_obj: date, format_str: str = '%d-%m-%Y') -> str:
        """
        Форматирует дату в строку
        
        Args:
            date_obj: Объект даты
            format_str: Формат строки (по умолчанию ДД-ММ-ГГГГ)
        
        Returns:
            str: Отформатированная дата
        """
        return date_obj.strftime(format_str)
    
    @staticmethod
    def parse_date(date_str: str, format_str: str = '%d-%m-%Y') -> Optional[date]:
        """
        Парсит строку в дату
        
        Args:
            date_str: Строка с датой
            format_str: Формат строки
        
        Returns:
            Optional[date]: Объект даты или None если парсинг не удался
        """
        try:
            return datetime.strptime(date_str, format_str).date()
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def get_age_range_dates(min_age: int = MIN_AGE) -> Tuple[date, date]:
        """
        Возвращает диапазон дат для допустимого возраста
        
        Args:
            min_age: Минимальный возраст
        
        Returns:
            Tuple[date, date]: (min_date, max_date)
        """
        today = date.today()
        
        # Максимальная дата (для минимального возраста)
        max_date = date(today.year - min_age, today.month, today.day)
        
        # Минимальная дата (фиксированный год 1950)
        min_date = date(CalendarService.MIN_BIRTH_YEAR, 1, 1)
        
        return min_date, max_date
    
    @staticmethod
    def get_localized_error_message(error_key: str, lang: str, age_info: Optional[dict] = None) -> str:
        """
        Возвращает локализованное сообщение об ошибке
        
        Args:
            error_key: Ключ ошибки ('too_young', 'too_old', 'future_date')
            lang: Код языка
            age_info: Дополнительная информация о возрасте
        
        Returns:
            str: Локализованное сообщение
        """
        messages = {
            'too_young': {
                'ru': f"Вам должно быть не менее {CalendarService.MIN_AGE} лет для использования бота",
                'en': f"You must be at least {CalendarService.MIN_AGE} years old to use the bot",
                'de': f"Sie müssen mindestens {CalendarService.MIN_AGE} Jahre alt sein, um den Bot zu verwenden",
                'fr': f"Vous devez avoir au moins {CalendarService.MIN_AGE} ans pour utiliser le bot",
                'es': f"Debes tener al menos {CalendarService.MIN_AGE} años para usar el bot"
            },
            'too_old': {
                'ru': f"Дата рождения должна быть не ранее {CalendarService.MIN_BIRTH_YEAR} года",
                'en': f"Birth date must be {CalendarService.MIN_BIRTH_YEAR} or later",
                'de': f"Das Geburtsdatum muss {CalendarService.MIN_BIRTH_YEAR} oder später sein",
                'fr': f"La date de naissance doit être {CalendarService.MIN_BIRTH_YEAR} ou plus tard",
                'es': f"La fecha de nacimiento debe ser {CalendarService.MIN_BIRTH_YEAR} o posterior"
            },
            'future_date': {
                'ru': "Дата рождения не может быть в будущем",
                'en': "Birth date cannot be in the future",
                'de': "Das Geburtsdatum kann nicht in der Zukunft liegen",
                'fr': "La date de naissance ne peut pas être dans le futur",
                'es': "La fecha de nacimiento no puede estar en el futuro"
            }
        }
        
        error_dict = messages.get(error_key, {})
        return error_dict.get(lang, error_dict.get('en', 'Invalid date'))
    
    @staticmethod
    def get_calendar_prompt_message(lang: str) -> str:
        """
        Возвращает приглашение для выбора даты
        
        Args:
            lang: Код языка
        
        Returns:
            str: Локализованное сообщение
        """
        messages = {
            'ru': "📅 Выберите дату рождения в календаре ниже:",
            'en': "📅 Select your birth date in the calendar below:",
            'de': "📅 Wählen Sie Ihr Geburtsdatum im Kalender unten aus:",
            'fr': "📅 Sélectionnez votre date de naissance dans le calendrier ci-dessous:",
            'es': "📅 Seleccione su fecha de nacimiento en el calendario a continuación:"
        }
        return messages.get(lang, messages['en'])
    
    @staticmethod
    def get_date_confirmation_message(selected_date: date, lang: str) -> str:
        """
        Возвращает сообщение подтверждения выбранной даты
        
        Args:
            selected_date: Выбранная дата
            lang: Код языка
        
        Returns:
            str: Локализованное сообщение с датой
        """
        formatted_date = CalendarService.format_date(selected_date)
        age = CalendarService.calculate_age(selected_date)
        
        messages = {
            'ru': f"✅ Выбрана дата рождения: {formatted_date}\nВаш возраст: {age} лет",
            'en': f"✅ Birth date selected: {formatted_date}\nYour age: {age} years",
            'de': f"✅ Geburtsdatum ausgewählt: {formatted_date}\nIhr Alter: {age} Jahre",
            'fr': f"✅ Date de naissance sélectionnée: {formatted_date}\nVotre âge: {age} ans",
            'es': f"✅ Fecha de nacimiento seleccionada: {formatted_date}\nSu edad: {age} años"
        }
        return messages.get(lang, messages['en'])


# Кэш для календарей (опционально)
class CalendarCache:
    """Простой кэш для хранения отрендеренных календарей"""
    
    def __init__(self):
        self._cache = {}
    
    def get(self, key: str):
        """Получить из кэша"""
        return self._cache.get(key)
    
    def set(self, key: str, value):
        """Сохранить в кэш"""
        self._cache[key] = value
    
    def clear(self):
        """Очистить кэш"""
        self._cache.clear()
    
    @staticmethod
    def generate_key(lang: str, year: int, month: int, context: str = 'birthdate') -> str:
        """Генерирует ключ кэша"""
        return f"cal_{context}_{lang}_{year}_{month}"


# Глобальный экземпляр кэша
calendar_cache = CalendarCache()

