import gettext
import psycopg2




def printer(user_id, com):
    conn = psycopg2.connect(dbname='propitashka', user='postgres', password='vadamahjkl', host='localhost', port="5432")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT lang FROM user_lang WHERE user_id = {}".format(user_id )
    )
    leng= cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    lenguag = gettext.translation('messages', localedir='locales', languages=[leng], fallback=False)
    lenguag.install()
    _ = lenguag.gettext  # Greek
    ngettext = lenguag.ngettext
    return _(com)


def printer_with_given(leng, com):
 #   lengu = gettext.translation('messages', localedir='locales', languages=[leng], fallback=False)
 #   lengu.install()
    _ = leng.gettext  # Greek
    ngettext = leng.ngettext
    return _(com)
