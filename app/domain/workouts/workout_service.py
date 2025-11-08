"""
Сервис для работы с тренировками
Отвечает за получение списка тренировок, расчет калорий и сохранение данных
"""
import psycopg2
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from logger_setup import bot_logger


class WorkoutService:
    """Сервис управления тренировками"""
    
    def __init__(self, db_connection):
        """
        Инициализация сервиса
        
        Args:
            db_connection: Подключение к PostgreSQL
        """
        self.conn = db_connection
        self.cursor = db_connection.cursor()
        self._cache = {}  # Кэш для списка тренировок
        
    def get_training_types(self, language: str = 'ru', active_only: bool = True) -> List[Dict]:
        """
        Получить список всех типов тренировок
        
        Args:
            language: Код языка (ru, en, de, fr, es)
            active_only: Только активные тренировки
            
        Returns:
            Список словарей с информацией о тренировках
        """
        cache_key = f"trainings_{language}_{active_only}"
        
        # Проверяем кэш
        if cache_key in self._cache:
            bot_logger.debug(f"Returning cached training types for {language}")
            return self._cache[cache_key]
        
        try:
            # Определяем колонку названия по языку
            name_column = f"name_{language}"
            description_column = f"description_{language}"
            
            query = f"""
                SELECT 
                    id,
                    {name_column} as name,
                    emoji,
                    {description_column} as description,
                    base_coefficient
                FROM training_types
                WHERE is_active = %s
                ORDER BY id
            """
            
            self.cursor.execute(query, (active_only,))
            rows = self.cursor.fetchall()
            
            result = []
            for row in rows:
                result.append({
                    'id': row[0],
                    'name': row[1],
                    'emoji': row[2] or '',
                    'description': row[3] or '',
                    'base_coefficient': float(row[4])
                })
            
            # Кэшируем результат
            self._cache[cache_key] = result
            bot_logger.info(f"Loaded {len(result)} training types for language {language}")
            
            return result
            
        except Exception as e:
            bot_logger.error(f"Error loading training types: {e}")
            raise
    
    def get_training_by_id(self, training_id: int, language: str = 'ru') -> Optional[Dict]:
        """
        Получить информацию о конкретной тренировке
        
        Args:
            training_id: ID тренировки
            language: Код языка
            
        Returns:
            Словарь с информацией о тренировке или None
        """
        trainings = self.get_training_types(language)
        for training in trainings:
            if training['id'] == training_id:
                return training
        return None
    
    def get_training_name(self, training_id: int, language: str = 'ru') -> str:
        """
        Получить название тренировки на нужном языке
        
        Args:
            training_id: ID тренировки
            language: Код языка
            
        Returns:
            Название тренировки
        """
        training = self.get_training_by_id(training_id, language)
        if training:
            emoji = training['emoji'] + ' ' if training['emoji'] else ''
            return f"{emoji}{training['name']}"
        return "Unknown"
    
    def get_user_parameters(self, user_id: int) -> Optional[Dict]:
        """
        Получить параметры пользователя для расчета калорий
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Словарь с параметрами пользователя
        """
        try:
            query = """
                SELECT 
                    uh.weight,
                    uh.height,
                    EXTRACT(YEAR FROM AGE(TO_DATE(um.date_of_birth, 'DD-MM-YYYY')))::INTEGER as age,
                    um.user_sex as gender
                FROM user_health uh
                JOIN user_main um ON um.user_id = uh.user_id
                WHERE uh.user_id = %s
                ORDER BY uh.date DESC
                LIMIT 1
            """
            
            self.cursor.execute(query, (user_id,))
            row = self.cursor.fetchone()
            
            if not row:
                bot_logger.warning(f"No parameters found for user {user_id}")
                return None
            
            params = {
                'weight': float(row[0]) if row[0] else None,
                'height': float(row[1]) if row[1] else None,
                'age': int(row[2]) if row[2] else None,
                'gender': str(row[3]) if row[3] else None
            }
            
            bot_logger.debug(f"User {user_id} parameters: {params}")
            return params
            
        except Exception as e:
            bot_logger.error(f"Error getting user parameters: {e}")
            return None
    
    def calculate_training_calories(
        self, 
        training_id: int, 
        user_id: int, 
        duration_minutes: int
    ) -> Optional[float]:
        """
        Рассчитать количество сожженных калорий
        Использует функцию PostgreSQL для точного расчета
        
        Args:
            training_id: ID тренировки
            user_id: ID пользователя
            duration_minutes: Длительность тренировки в минутах
            
        Returns:
            Количество сожженных калорий или None в случае ошибки
        """
        try:
            # Валидация входных данных
            if not (1 <= duration_minutes <= 300):
                bot_logger.error(f"Invalid duration: {duration_minutes}")
                return None
            
            # Вызываем функцию PostgreSQL для расчета
            query = """
                SELECT calculate_training_calories(%s, %s, %s)
            """
            
            self.cursor.execute(query, (training_id, user_id, duration_minutes))
            result = self.cursor.fetchone()
            
            if result and result[0]:
                calories = round(float(result[0]), 3)
                bot_logger.info(
                    f"Calculated calories for user {user_id}, "
                    f"training {training_id}, duration {duration_minutes}min: {calories} kcal"
                )
                return calories
            
            bot_logger.warning("Calories calculation returned None")
            return None
            
        except Exception as e:
            bot_logger.error(f"Error calculating calories: {e}")
            return None
    
    def save_training(
        self,
        user_id: int,
        training_id: int,
        training_name: str,
        duration_minutes: int,
        calories: float,
        date: Optional[str] = None
    ) -> bool:
        """
        Сохранить тренировку в БД
        
        Args:
            user_id: ID пользователя
            training_id: ID типа тренировки
            training_name: Название тренировки (на языке пользователя)
            duration_minutes: Длительность в минутах
            calories: Количество сожженных калорий
            date: Дата тренировки (по умолчанию сегодня)
            
        Returns:
            True если успешно сохранено, False в случае ошибки
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        try:
            query = """
                INSERT INTO user_training (
                    user_id, 
                    training_type_id, 
                    training_name, 
                    date, 
                    tren_time, 
                    training_cal
                )
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            self.cursor.execute(
                query,
                (user_id, training_id, training_name, date, duration_minutes, calories)
            )
            self.conn.commit()
            
            bot_logger.info(
                f"Training saved: user={user_id}, training={training_name}, "
                f"duration={duration_minutes}min, calories={calories}kcal"
            )
            return True
            
        except Exception as e:
            bot_logger.error(f"Error saving training: {e}")
            self.conn.rollback()
            return False
    
    def get_today_total_calories(self, user_id: int) -> float:
        """
        Получить суммарные калории за сегодня
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Суммарное количество сожженных калорий
        """
        try:
            query = """
                SELECT COALESCE(SUM(training_cal), 0) 
                FROM user_training 
                WHERE date = CURRENT_DATE AND user_id = %s
            """
            
            self.cursor.execute(query, (user_id,))
            result = self.cursor.fetchone()
            
            return float(result[0]) if result else 0.0
            
        except Exception as e:
            bot_logger.error(f"Error getting today's total calories: {e}")
            return 0.0
    
    def get_trainings_by_period(
        self,
        user_id: int,
        start_date: str,
        end_date: str
    ) -> List[Dict]:
        """
        Получить список тренировок за период
        
        Args:
            user_id: ID пользователя
            start_date: Начальная дата (YYYY-MM-DD)
            end_date: Конечная дата (YYYY-MM-DD)
            
        Returns:
            Список словарей с информацией о тренировках
        """
        try:
            query = """
                SELECT 
                    date,
                    training_name,
                    tren_time,
                    training_cal
                FROM user_training
                WHERE user_id = %s 
                    AND date >= %s 
                    AND date <= %s
                ORDER BY date DESC, id DESC
            """
            
            self.cursor.execute(query, (user_id, start_date, end_date))
            rows = self.cursor.fetchall()
            
            result = []
            for row in rows:
                result.append({
                    'date': row[0].strftime('%Y-%m-%d') if row[0] else None,
                    'name': row[1],
                    'duration': int(row[2]) if row[2] else 0,
                    'calories': float(row[3]) if row[3] else 0.0
                })
            
            return result
            
        except Exception as e:
            bot_logger.error(f"Error getting trainings by period: {e}")
            return []
    
    def get_training_statistics(self, user_id: int, days: int = 30) -> Dict:
        """
        Получить статистику тренировок пользователя
        
        Args:
            user_id: ID пользователя
            days: Количество дней для анализа
            
        Returns:
            Словарь со статистикой
        """
        try:
            query = """
                SELECT 
                    COUNT(*) as total_sessions,
                    SUM(tren_time) as total_minutes,
                    SUM(training_cal) as total_calories,
                    AVG(training_cal) as avg_calories,
                    training_name,
                    COUNT(*) as training_count
                FROM user_training
                WHERE user_id = %s 
                    AND date >= CURRENT_DATE - INTERVAL '%s days'
                GROUP BY training_name
                ORDER BY training_count DESC
                LIMIT 3
            """
            
            self.cursor.execute(query, (user_id, days))
            rows = self.cursor.fetchall()
            
            # Также получаем общую статистику
            query_total = """
                SELECT 
                    COUNT(*) as total_sessions,
                    SUM(tren_time) as total_minutes,
                    SUM(training_cal) as total_calories
                FROM user_training
                WHERE user_id = %s 
                    AND date >= CURRENT_DATE - INTERVAL '%s days'
            """
            
            self.cursor.execute(query_total, (user_id, days))
            total = self.cursor.fetchone()
            
            top_trainings = []
            for row in rows:
                top_trainings.append({
                    'name': row[4],
                    'count': int(row[5])
                })
            
            return {
                'total_sessions': int(total[0]) if total and total[0] else 0,
                'total_minutes': int(total[1]) if total and total[1] else 0,
                'total_calories': float(total[2]) if total and total[2] else 0.0,
                'top_trainings': top_trainings
            }
            
        except Exception as e:
            bot_logger.error(f"Error getting training statistics: {e}")
            return {
                'total_sessions': 0,
                'total_minutes': 0,
                'total_calories': 0.0,
                'top_trainings': []
            }
    
    def clear_cache(self):
        """Очистить кэш тренировок"""
        self._cache.clear()
        bot_logger.debug("Training cache cleared")


# Вспомогательные функции для работы вне класса

def format_training_summary(trainings: List[Dict], language: str = 'ru') -> str:
    """
    Форматировать список тренировок для отображения
    
    Args:
        trainings: Список тренировок
        language: Язык для форматирования
        
    Returns:
        Отформатированная строка
    """
    if not trainings:
        messages = {
            'ru': 'Нет тренировок за этот период',
            'en': 'No workouts for this period',
            'de': 'Keine Trainings für diesen Zeitraum',
            'fr': 'Aucun entraînement pour cette période',
            'es': 'No hay entrenamientos para este período'
        }
        return messages.get(language, messages['en'])
    
    lines = []
    for i, training in enumerate(trainings, 1):
        line = f"{i}. {training['name']} - {training['duration']} мин, {training['calories']:.1f} ккал"
        lines.append(line)
    
    return '\n'.join(lines)


def get_workout_service(db_connection) -> WorkoutService:
    """
    Фабричная функция для создания сервиса
    
    Args:
        db_connection: Подключение к БД
        
    Returns:
        Экземпляр WorkoutService
    """
    return WorkoutService(db_connection)


