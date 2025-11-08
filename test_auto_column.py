#!/usr/bin/env python3
"""Тест функции is_auto_column"""
import sys
sys.path.insert(0, '.')

from admin_of_bases import is_auto_column, get_db_connection

# Тестируем функцию
print("=== Тестирование is_auto_column ===\n")

test_cases = [
    ('food', 'id'),
    ('food', 'user_id'),
    ('user_main', 'user_id'),
    ('user_health', 'id'),
    ('user_training', 'id'),
    ('food', 'name_of_food'),
    ('food', 'created_at'),
]

for table, column in test_cases:
    result = is_auto_column(table, column)
    print(f"{table}.{column}: {result}")

print("\n=== Проверяем колонки таблицы food ===")
conn = get_db_connection()
if conn:
    cursor = conn.cursor()
    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'food' ORDER BY ordinal_position")
    columns = [row[0] for row in cursor.fetchall()]
    print(f"Колонки: {columns}")
    
    for col in columns:
        is_auto = is_auto_column('food', col)
        print(f"  {col}: автоматическая = {is_auto}")
    
    cursor.close()
    conn.close()

