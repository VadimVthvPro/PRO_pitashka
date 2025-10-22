def changing_leng( l2, user_id):
    cursor.execute(f"""SELECT 
    lang 
    FROM user_lang 
    WHERE user_id = {user_id}""",
                   )

    l1 = cursor.fetchone()[0]
    cursor.execute(f"""SELECT 
    date, user_name_of_food 
    FROM user_pit 
    WHERE user_id = {user_id}""",
                   )
    dates, names = cursor.fetchall(),cursor.fetchall()
    translator = Translator(from_lang=l1, to_lang=l2)
    for i in range(len(dates)):
        pit = translator.translate(names[i])
        cursor.execute(
            f"""UPDATE 
            SET user_name_of_food = {pit} FROM user_pit 
            WHERE user_id = {datetime.datetime.now().strftime('%Y-%m-%d')} 
            AND date = {dates[i]} """,
            )
    cursor.execute(
        f"""SELECT 
        date, user_aim, user_sex, imt_str 
        FROM users 
        WHERE user_id = {user_id}""",
        )
    date, user_aim, user_sex, imt_str = cursor.fetchall(), cursor.fetchall(), cursor.fetchall(), cursor.fetchall()
    for i in range(len(dates)):
        aim = translator.translate(user_aim[i])
        sex = translator.translate(user_sex[i])
        st = translator.translate(imt_str[i])
        cursor.execute(
            f"""
            UPDATE 
            SET user_aim = {aim}, 
            user_sex = {sex}, 
            imt_str = {st} 
            FROM users 
            WHERE user_id = {datetime.datetime.now().strftime('%Y-%m-%d')} 
            AND date = {date[i]} """,
        )
    conn.commit()