#!/usr/bin/env python3
"""
Финальное исправление admin_of_bases.py
Исправляет проблему с автоматическим заполнением поля id
"""

# Читаем файл
with open('admin_of_bases.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Новая улучшенная функция is_auto_column
new_is_auto_column = '''def is_auto_column(table_name, column_name):
    """Проверить, должна ли колонка заполняться автоматически."""
    # Временные метки всегда автоматические
    if column_name in ['created_at', 'updated_at', 'last_login']:
        return True
    
    # В user_main поле user_id НЕ автоматическое (это Telegram ID, вводится вручную)
    if table_name == 'user_main' and column_name == 'user_id':
        return False
    
    # В user_aims user_id является первичным ключом, но НЕ автоматический
    if table_name == 'user_aims' and column_name == 'user_id':
        return False
    
    # В user_lang user_id является первичным ключом, но НЕ автоматический  
    if table_name == 'user_lang' and column_name == 'user_id':
        return False
    
    # В water нет первичного ключа, user_id НЕ автоматический
    if table_name == 'water' and column_name == 'user_id':
        return False
    
    # Во ВСЕХ остальных случаях 'id' - автоматическое (SERIAL)
    if column_name == 'id':
        return True
    
    return False
'''

# Заменяем функцию
import re
pattern = r'def is_auto_column\(table_name, column_name\):.*?(?=\ndef |\nclass )'
content = re.sub(pattern, new_is_auto_column + '\n', content, flags=re.DOTALL)

# Сохраняем
with open('admin_of_bases.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Функция is_auto_column заменена!")
print("\n📋 Логика:")
print("  - id во ВСЕХ таблицах (кроме user_main) = АВТОМАТИЧЕСКИ")
print("  - user_id в user_main = ВРУЧНУЮ (Telegram ID)")
print("  - user_id в других таблицах = выбор из списка")
print("  - timestamps = АВТОМАТИЧЕСКИ")





