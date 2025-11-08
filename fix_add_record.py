#!/usr/bin/env python3
"""
Скрипт для исправления функции add_record в admin_of_bases.py
"""

import re

# Читаем файл
with open('admin_of_bases.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Новая функция add_record с правильной обработкой всех полей
new_add_record = '''    def add_record(self, tree, columns, table_name, load_data):
        """УЛУЧШЕННОЕ окно добавления новой записи с обработкой user_id."""
        add_window = tk.Toplevel()
        add_window.title(f"Добавить запись в таблицу '{table_name}'")
        
        # Адаптивный размер окна
        window_height = min(len(columns) * 70 + 200, 900)
        window_width = 800
        center_window(add_window, window_width, window_height)
        add_window.minsize(700, 400)

        # Canvas с прокруткой для большого количества полей
        main_frame = ttk.Frame(add_window)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        canvas = Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        entries = []
        user_names = []
        user_ids = []
        training_type_names = []
        training_type_ids = []
        pk = get_primary_key(table_name)

        for i, col in enumerate(columns):
            label_text = self.column_mapping.get(col, col.replace('_', ' ').title())
            label = ttk.Label(scrollable_frame, text=label_text + ":", font=FONT_MEDIUM)
            label.grid(row=i, column=0, padx=15, pady=10, sticky="e")

            # Автоматические поля (первичные ключи, timestamps)
            if col == pk or col in ['created_at', 'updated_at', 'last_login']:
                entry = ttk.Entry(scrollable_frame, width=30, font=FONT_MEDIUM, state="disabled")
                entry.insert(0, "Автоматически")
                entry.grid(row=i, column=1, padx=15, pady=10, sticky="w")
                
            # user_id для других таблиц - комбобокс с никнеймами
            elif col == "user_id" and table_name != "user_main":
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT user_id, user_name FROM user_main ORDER BY user_id")
                    user_data = cursor.fetchall()
                    user_ids = [str(row[0]) for row in user_data]
                    user_names = [f"{row[0]}: {row[1]}" for row in user_data]
                    cursor.close()
                    conn.close()
                except Exception as e:
                    messagebox.showerror("Ошибка", f"Не удалось загрузить пользователей: {e}")
                    user_ids = []
                    user_names = []

                entry = ttk.Combobox(scrollable_frame, values=user_names, width=28, font=FONT_MEDIUM, state="readonly")
                if user_names:
                    entry.current(0)
                entry.grid(row=i, column=1, padx=15, pady=10, sticky="w")
                
            # training_type_id - комбобокс с типами тренировок
            elif col == "training_type_id":
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT id, name_ru FROM training_types WHERE is_active = TRUE ORDER BY name_ru")
                    training_data = cursor.fetchall()
                    training_type_ids = [str(row[0]) for row in training_data]
                    training_type_names = [f"{row[0]}: {row[1]}" for row in training_data]
                    cursor.close()
                    conn.close()
                except Exception as e:
                    messagebox.showerror("Ошибка", f"Не удалось загрузить типы тренировок: {e}")
                    training_type_ids = []
                    training_type_names = []

                entry = ttk.Combobox(scrollable_frame, values=training_type_names, width=28, font=FONT_MEDIUM, state="readonly")
                if training_type_names:
                    entry.current(0)
                entry.grid(row=i, column=1, padx=15, pady=10, sticky="w")
                
            # user_sex - комбобокс
            elif col == "user_sex":
                entry = ttk.Combobox(scrollable_frame, values=["Мужской", "Женский"], width=28, font=FONT_MEDIUM, state="readonly")
                entry.current(0)
                entry.grid(row=i, column=1, padx=15, pady=10, sticky="w")
                
            # lang - комбобокс
            elif col == "lang":
                entry = ttk.Combobox(scrollable_frame, values=["ru", "en", "de", "fr", "es"], width=28, font=FONT_MEDIUM, state="readonly")
                entry.current(0)
                entry.grid(row=i, column=1, padx=15, pady=10, sticky="w")
                
            # message_type - комбобокс
            elif col == "message_type":
                entry = ttk.Combobox(scrollable_frame, values=["user", "bot"], width=28, font=FONT_MEDIUM, state="readonly")
                entry.current(0)
                entry.grid(row=i, column=1, padx=15, pady=10, sticky="w")
                
            # is_active - комбобокс
            elif col == "is_active":
                entry = ttk.Combobox(scrollable_frame, values=["TRUE", "FALSE"], width=28, font=FONT_MEDIUM, state="readonly")
                entry.current(0)
                entry.grid(row=i, column=1, padx=15, pady=10, sticky="w")
                
            # date/data - автозаполнение текущей датой
            elif col in ['date', 'data']:
                entry = ttk.Entry(scrollable_frame, width=30, font=FONT_MEDIUM)
                entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
                entry.grid(row=i, column=1, padx=15, pady=10, sticky="w")
                
            else:
                entry = ttk.Entry(scrollable_frame, width=30, font=FONT_MEDIUM)
                entry.grid(row=i, column=1, padx=15, pady=10, sticky="w")
            
            entries.append(entry)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def save_record():
            values = []
            filtered_columns = []
            
            for i, col in enumerate(columns):
                entry = entries[i]
                
                # Пропускаем автоматические поля
                if entry.cget('state') == 'disabled':
                    continue
                
                # Обработка user_id
                if col == "user_id" and table_name != "user_main":
                    selected_user = entry.get().strip()
                    if selected_user and ':' in selected_user:
                        user_id = selected_user.split(':')[0]
                        values.append(user_id)
                    else:
                        messagebox.showwarning("Предупреждение", "Выберите корректного пользователя!")
                        return
                        
                # Обработка training_type_id
                elif col == "training_type_id":
                    selected_training = entry.get().strip()
                    if selected_training and ':' in selected_training:
                        training_id = selected_training.split(':')[0]
                        values.append(training_id)
                    else:
                        messagebox.showwarning("Предупреждение", "Выберите корректный тип тренировки!")
                        return
                        
                else:
                    value = entry.get().strip()
                    values.append(value if value else None)
                
                filtered_columns.append(col)

            try:
                conn = get_db_connection()
                if conn:
                    cursor = conn.cursor()
                    placeholders = ', '.join(['%s'] * len(filtered_columns))
                    query = f"INSERT INTO {table_name} ({', '.join(filtered_columns)}) VALUES ({placeholders})"
                    cursor.execute(query, values)
                    conn.commit()
                    cursor.close()
                    conn.close()
                    add_window.destroy()
                    load_data()
                    messagebox.showinfo("Успех", "Запись успешно добавлена!")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось добавить запись: {e}")

        button_frame = ttk.Frame(add_window)
        button_frame.pack(side="bottom", fill="x", padx=10, pady=15)

        add_button = ttk.Button(button_frame, text="✅ Сохранить", command=save_record, width=18)
        add_button.pack(side="left", padx=5)

        cancel_button = ttk.Button(button_frame, text="❌ Отмена", command=add_window.destroy, width=18)
        cancel_button.pack(side="left", padx=5)
'''

# Находим начало и конец старой функции
pattern = r'    def add_record\(self,.*?\n(?=    def \w+\()'
match = re.search(pattern, content, re.DOTALL)

if match:
    # Заменяем функцию
    content = content[:match.start()] + new_add_record + '\n' + content[match.end():]
    
    # Сохраняем
    with open('admin_of_bases.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Функция add_record успешно заменена!")
    print("🔧 Основные изменения:")
    print("   - Добавлен комбобокс для user_id с никнеймами пользователей")
    print("   - Добавлен комбобокс для training_type_id")
    print("   - Исправлена обработка значений в save_record")
    print("   - Добавлены комбобоксы для всех справочных полей")
else:
    print("❌ Не удалось найти функцию add_record")

