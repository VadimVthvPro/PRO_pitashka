import gettext
import psycopg2
from config import config


def printer(user_id, com):
    """
    Возвращает локализованную строку для пользователя на основе его языковых настроек.
    
    Args:
        user_id: ID пользователя Telegram
        com: Ключ строки для перевода
    
    Returns:
        Локализованная строка
    """
    conn = psycopg2.connect(**config.get_db_config())
    cursor = conn.cursor()
    cursor.execute("SELECT lang FROM user_lang WHERE user_id = %s", (user_id,))
    result = cursor.fetchone()
    leng = result[0] if result else 'ru'
    conn.commit()
    cursor.close()
    
    lenguag = gettext.translation('messages', localedir='locales', languages=[leng], fallback=True)
    lenguag.install()
    _ = lenguag.gettext
    ngettext = lenguag.ngettext
    return _(com)


def printer_with_given(leng, com):
 #   lengu = gettext.translation('messages', localedir='locales', languages=[leng], fallback=False)
 #   lengu.install()
    _ = leng.gettext  # Greek
    ngettext = leng.ngettext
    return _(com)
