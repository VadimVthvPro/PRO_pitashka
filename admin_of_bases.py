import tkinter as tk
from tkinter import ttk, messagebox, Spinbox
import psycopg2
from datetime import datetime

def center_window(window, width, height):
    """Функция для центрирования окна на экране."""
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = (screen_width // 2) - (width // 2)
    y = (screen_height // 2) - (height // 2)
    window.geometry(f"{width}x{height}+{x}+{y}")

def get_db_connection(user="postgres", password="000"):
    """Функция для подключения к базе данных."""
    try:
        conn = psycopg2.connect(
            dbname='propitashka',
            user=user,
            password=password,
            host='localhost',
            port="5432"
        )
        return conn
    except psycopg2.Error as e:
        messagebox.showerror("Ошибка подключения", f"Не удалось подключиться к базе данных: {e}")
        return None

class Application:
    def __init__(self, root):
        self.root = root
        self.column_mapping = {
            "user_id": "Id пользователя",
            "user_name": "Имя пользователя",
            "user_sex": "Пол",
            "date_of_birth": "Возраст",
            "food_id": "Номер записи",
            "name_of_food": "Название блюда",
            "b": "Белки",
            "g": "Жиры",
            "u": "Углеводы",
            "cal": "Калорийность",
            "date": "Дата",
            "aim_id": "Номер записи",
            "user_aim": "Цель пользователя",
            "daily_cal": "Дневное количество калорий",
            "health_id": "Номер записи",
            "imt": "ИМТ",
            "imt_str": "Расшифровка ИМТ",
            "weight": "Вес",
            "height": "Рост",
            "lang": "Язык пользователя",
            "training_id": "Номер записи",
            "training_cal": "Сожжённые калории",
            "tren_time": "Продолжительность тренировки",
            "water_id": "Номер записи",
            "count": "Количество",
            "data": "Дата"
        }
        self.initialize_ui()

    def initialize_ui(self):
        """Инициализация интерфейса."""
        self.frame = ttk.Frame(self.root)
        self.frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.entry()

    def entry(self):
        """Функция для создания интерфейса входа."""
        self.label_name = ttk.Label(self.frame, text="Имя пользователя:")
        self.label_name.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.entry_name = ttk.Entry(self.frame, width=20)
        self.entry_name.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self.label_pas = ttk.Label(self.frame, text="Пароль:")
        self.label_pas.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.entry_pas = ttk.Entry(self.frame, width=20, show="*")
        self.entry_pas.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        self.button_frame = ttk.Frame(self.frame)
        self.button_frame.grid(row=2, column=0, columnspan=2, sticky="e", padx=5, pady=5)

        self.button = ttk.Button(self.button_frame, text="Ок", command=self.submit, width=10)
        self.button.pack(side="left", padx=5)

        self.cancel_button = ttk.Button(self.button_frame, text="Отмена", command=self.close_window, width=10)
        self.cancel_button.pack(side="left", padx=5)

        self.error_label = ttk.Label(self.frame, text="", font=("Arial", 12))
        self.error_label.grid(row=3, column=0, columnspan=2, sticky="ew")

        self.frame.columnconfigure(1, weight=1)
        self.frame.rowconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)
        self.frame.rowconfigure(2, weight=1)
        self.frame.rowconfigure(3, weight=1)

    def submit(self):
        """Функция для обработки входа пользователя."""
        name = self.entry_name.get()
        pas = self.entry_pas.get()
        print(f"Имя: {name}")
        print(f"Пароль: {pas}")

        try:
            conn = get_db_connection(name, pas)
            if conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM user_main")
                data = cursor.fetchall()

                if data:
                    self.show_main_window()
                else:
                    self.error_label.config(text="Неверное имя пользователя или пароль", foreground="red")

                cursor.close()
                conn.close()
            else:
                self.error_label.config(text="Не удалось подключиться к базе данных", foreground="red")

        except Exception as e:
            self.error_label.config(text="Неверное имя пользователя или пароль", foreground="red")
            print(f"Ошибка: {str(e)}")

    def show_main_window(self):
        """Функция для отображения главного окна с вкладками."""
        self.frame.pack_forget()
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True)

        window_width = 1200
        window_height = 800
        center_window(self.root, window_width, window_height)
        self.root.title("PROпиташка")
        self.root.minsize(800, 600)

        self.create_tabs()

    def create_tabs(self):
        """Функция для создания вкладок."""
        tabs = [
            ("Главная", ["user_id", "user_name", "user_sex", "date_of_birth"],
             "SELECT user_id, user_name, user_sex, date_of_birth FROM user_main", "user_main"),
            ("Еда", ["food_id", "user_id", "name_of_food", "b", "g", "u", "cal", "date"],
             "SELECT food_id, user_id, name_of_food, b, g, u, cal, date FROM food", "food"),
            ("Цели", ["aim_id", "user_id", "user_aim", "daily_cal"],
             "SELECT aim_id, user_id, user_aim, daily_cal FROM user_aims", "user_aims"),
            ("Здоровье", ["health_id", "user_id", "imt", "imt_str", "cal", "date", "weight", "height"],
             "SELECT health_id, user_id, imt, imt_str, cal, date, weight, height FROM user_health", "user_health"),
            ("Язык", ["user_id", "lang"],
             "SELECT user_id, lang FROM user_lang", "user_lang"),
            ("Тренировки", ["training_id", "user_id", "date", "training_cal", "tren_time"],
             "SELECT training_id, user_id, date, training_cal, tren_time FROM user_training", "user_training"),
            ("Вода", ["water_id", "user_id", "count", "data"],
             "SELECT water_id, user_id, count, data FROM water", "water")
        ]

        for tab_name, columns, query, table_name in tabs:
            tab = ttk.Frame(self.notebook)
            self.notebook.add(tab, text=tab_name)
            self.create_table(tab, columns, query, table_name)

    def create_table(self, tab, columns, query, table_name):
        """Функция для создания таблицы на вкладке."""
        container = ttk.Frame(tab)
        container.grid(row=2, column=0, sticky="nsew")

        tree = ttk.Treeview(container, columns=columns, show="headings")
        style = ttk.Style()
        style.configure("Treeview.Heading", font=("Arial", 12, "bold"))

        for col in columns:
            tree.heading(col, text=self.column_mapping[col], command=lambda c=col: self.sort_treeview(tree, c, False))

        h_scroll = ttk.Scrollbar(container, orient="horizontal", command=tree.xview)
        tree.configure(xscrollcommand=h_scroll.set)
        h_scroll.grid(row=1, column=0, sticky="ew")

        v_scroll = ttk.Scrollbar(container, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=v_scroll.set)
        v_scroll.grid(row=0, column=1, sticky="ns")

        tree.grid(row=0, column=0, sticky="nsew")

        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)
        tab.rowconfigure(2, weight=1)
        tab.columnconfigure(0, weight=1)

        def load_data():
            try:
                conn = get_db_connection()
                if conn:
                    cursor = conn.cursor()
                    cursor.execute(query)
                    rows = cursor.fetchall()

                    for row in tree.get_children():
                        tree.delete(row)

                    for row in rows:
                        tree.insert("", "end", values=row)

                    cursor.close()
                    conn.close()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось загрузить данные: {e}")

        load_data()

        filter_frame = ttk.Frame(tab)
        filter_frame.grid(row=0, column=0, sticky="ew", pady=5)

        filter_label = ttk.Label(filter_frame, text="Фильтр:")
        filter_label.pack(side="left", padx=5)

        filter_entry = ttk.Entry(filter_frame)
        filter_entry.pack(side="left", padx=5, fill="x", expand=True)

        def apply_filter():
            filter_text = filter_entry.get().lower()
            for row in tree.get_children():
                tree.delete(row)

            try:
                conn = get_db_connection()
                if conn:
                    cursor = conn.cursor()
                    cursor.execute(query)
                    rows = cursor.fetchall()

                    for row in rows:
                        if any(filter_text in str(cell).lower() for cell in row):
                            tree.insert("", "end", values=row)

                    cursor.close()
                    conn.close()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось применить фильтр: {e}")

        filter_button = ttk.Button(filter_frame, text="Искать", command=apply_filter)
        filter_button.pack(side="left", padx=5)

        button_frame = ttk.Frame(tab)
        button_frame.grid(row=1, column=0, sticky="ew", pady=5)

        refresh_button = ttk.Button(button_frame, text="Обновить", command=load_data)
        refresh_button.pack(side="left", padx=5)

        add_button = ttk.Button(button_frame, text="Добавить запись", command=lambda: self.add_record(tree, columns, table_name, load_data))
        add_button.pack(side="left", padx=5)

        delete_button = ttk.Button(button_frame, text="Удалить строку", command=lambda: self.delete_record(tree, table_name, load_data))
        delete_button.pack(side="left", padx=5)

        tree.bind("<Double-1>", lambda event: self.edit_cell(event, tree, columns, table_name, load_data))

    def sort_treeview(self, tree, col, reverse):
        """Сортировка данных в Treeview по выбранному столбцу."""
        data = [(tree.set(item, col), item) for item in tree.get_children("")]
        data.sort(reverse=reverse)

        for index, (val, item) in enumerate(data):
            tree.move(item, "", index)

        tree.heading(col, command=lambda: self.sort_treeview(tree, col, not reverse))

    def delete_record(self, tree, table_name, load_data):
        """Функция для удаления выбранных строк."""
        selected_items = tree.selection()
        if not selected_items:
            messagebox.showwarning("Предупреждение", "Выберите строки для удаления.")
            return

        confirm = messagebox.askyesno("Подтверждение", "Вы уверены, что хотите удалить выбранные строки?")
        if not confirm:
            return

        try:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()

                for item in selected_items:
                    values = tree.item(item, "values")
                    primary_key_value = values[0]

                    if table_name == "user_main":
                        self.delete_related_records(cursor, primary_key_value)

                    primary_key_column = "user_id" if table_name == "user_main" or table_name == "user_lang" or table_name == "user_aims" else f"{table_name.split('_')[-1]}_id"
                    cursor.execute(f"DELETE FROM {table_name} WHERE {primary_key_column} = %s", (primary_key_value,))

                conn.commit()
                cursor.close()
                conn.close()

                load_data()
                messagebox.showinfo("Успех", "Строки успешно удалены.")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось удалить строки: {e}")

    def delete_related_records(self, cursor, user_id):
        """Функция для удаления связанных записей из всех таблиц по user_id."""
        related_tables = ["food", "user_aims", "user_health", "user_lang", "user_training", "water"]
        for table in related_tables:
            cursor.execute(f"DELETE FROM {table} WHERE user_id = %s", (user_id,))

    def add_record(self, tree, columns, table_name, load_data):
        """Функция для добавления новой записи."""
        add_window = tk.Toplevel()
        add_window.title("Добавить запись")
        window_width = 600
        window_height = len(columns) * 50 + 150
        center_window(add_window, window_width, window_height)
        add_window.minsize(600, 300)

        entries = []
        user_names = []
        user_ids = []

        for i, col in enumerate(columns):
            label_text = self.column_mapping.get(col, col)
            label = ttk.Label(add_window, text=label_text)
            label.grid(row=i, column=0, padx=5, pady=5, sticky="e")

            if col == "water_id" and table_name == "water":
                entry = Spinbox(add_window, from_=0, to=99999999999999999, increment=1)
                entry.grid(row=i, column=1, padx=5, pady=5, sticky="w")
            elif col == "count" and table_name == "water":
                entry = Spinbox(add_window, from_=0, to=99999999999999999, increment=1)
                entry.grid(row=i, column=1, padx=5, pady=5, sticky="w")
            elif col == "training_id" and table_name == "user_training":
                entry = Spinbox(add_window, from_=1, to=99999999999, increment=1)
                entry.grid(row=i, column=1, padx=5, pady=5, sticky="w")
            elif col == "tren_time" and table_name == "user_training":
                entry = Spinbox(add_window, from_=1, to=99999999999, increment=1)
                entry.grid(row=i, column=1, padx=5, pady=5, sticky="w")
            elif col == "training_cal" and table_name == "user_training":
                entry = Spinbox(add_window, from_=1.0, to=9999999999999.0, increment=0.1, format="%.1f")
                entry.grid(row=i, column=1, padx=5, pady=5, sticky="w")
            elif col == "health_id" and table_name == "user_health":
                entry = Spinbox(add_window, from_=1, to=999999999999999999, increment=1)
                entry.grid(row=i, column=1, padx=5, pady=5, sticky="w")
            elif col in ["imt", "cal", "weight", "height"] and table_name == "user_health":
                entry = Spinbox(add_window, from_=1.0, to=9999999999.0, increment=0.1, format="%.1f")
                entry.grid(row=i, column=1, padx=5, pady=5, sticky="w")
            elif col == "aim_id" and table_name == "user_aims":
                entry = Spinbox(add_window, from_=0, to=999999999999, increment=1)
                entry.grid(row=i, column=1, padx=5, pady=5, sticky="w")
            elif col == "daily_cal" and table_name == "user_aims":
                entry = Spinbox(add_window, from_=0, to=999999999999, increment=1)
                entry.grid(row=i, column=1, padx=5, pady=5, sticky="w")
            elif col == "food_id" and table_name == "food":
                entry = Spinbox(add_window, from_=1, to=999999999, increment=1)
                entry.grid(row=i, column=1, padx=5, pady=5, sticky="w")
            elif col in ["b", "g", "u", "cal"] and table_name == "food":
                entry = Spinbox(add_window, from_=0.0, to=999999999.0, increment=0.1, format="%.1f")
                entry.grid(row=i, column=1, padx=5, pady=5, sticky="w")
            elif col == "user_id" and table_name == "user_main":
                entry = Spinbox(add_window, from_=1, to=999999, increment=1)
                entry.grid(row=i, column=1, padx=5, pady=5, sticky="w")
            elif col == "date_of_birth" and table_name == "user_main":
                entry = Spinbox(add_window, from_=5, to=100, increment=1)  # Ограничение возраста от 5 до 100 лет
                entry.grid(row=i, column=1, padx=5, pady=5, sticky="w")
            elif col == "user_id" and table_name != "user_main":
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT user_id, user_name FROM user_main")
                    user_data = cursor.fetchall()
                    user_ids = [str(row[0]) for row in user_data]
                    user_names = [row[1] for row in user_data]
                    cursor.close()
                    conn.close()
                except Exception as e:
                    messagebox.showerror("Ошибка", f"Не удалось загрузить user_id и user_name: {e}")
                    user_ids = []
                    user_names = []

                entry = ttk.Combobox(add_window, values=user_names)
                if user_names:
                    entry.current(0)
            elif col == "user_sex" and table_name == "user_main":
                entry = ttk.Combobox(add_window, values=["Мужчина", "Женщина"])
                entry.current(0)
            elif col == "date" or col == "data":
                entry = ttk.Entry(add_window)
                entry.insert(0, datetime.now().strftime("%d-%m-%Y"))
                entry.config(state="readonly")
            else:
                entry = ttk.Entry(add_window)

            entry.grid(row=i, column=1, padx=5, pady=5, sticky="w")
            entries.append(entry)

        def save_record():
            values = []
            for i, entry in enumerate(entries):
                if columns[i] == "user_id" and table_name != "user_main":
                    selected_user_name = entry.get().strip()
                    if selected_user_name in user_names:
                        user_id = user_ids[user_names.index(selected_user_name)]
                        values.append(user_id)
                    else:
                        messagebox.showwarning("Предупреждение", "Выберите корректное имя пользователя!")
                        return
                else:
                    if isinstance(entry, Spinbox) or isinstance(entry, ttk.Combobox):
                        values.append(entry.get().strip())
                    else:
                        values.append(entry.get().strip())

            if any(not value for value in values):
                messagebox.showwarning("Предупреждение", "Заполните все поля!")
                return

            try:
                conn = get_db_connection()
                if conn:
                    cursor = conn.cursor()
                    placeholders = ', '.join(['%s'] * len(columns))
                    query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
                    cursor.execute(query, values)
                    conn.commit()
                    cursor.close()
                    conn.close()
                    add_window.destroy()

                    load_data()
                    last_item = tree.get_children()[-1]

                    # Подсветка строки
                    if tree.exists(last_item):
                        tree.tag_configure("highlight", foreground="green")  # Зелёный цвет текста
                        tree.item(last_item, tags=("highlight",))

                    # Сброс подсветки через 20 секунд
                    def reset_highlight():
                        if tree.exists(last_item):
                            tree.item(last_item, tags=())

                    tree.after(20000, reset_highlight)
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось добавить запись: {e}")

        button_frame = ttk.Frame(add_window)
        button_frame.grid(row=len(columns), column=0, columnspan=2, sticky="e", padx=5, pady=5)

        add_button = ttk.Button(button_frame, text="Ок", command=save_record, width=10)
        add_button.pack(side="left", padx=5)

        cancel_button = ttk.Button(button_frame, text="Отмена", command=add_window.destroy, width=10)
        cancel_button.pack(side="left", padx=5)

    def edit_cell(self, event, tree, columns, table_name, load_data):
        """Функция для редактирования ячейки при двойном клике."""
        region = tree.identify_region(event.x, event.y)
        if region != "cell":
            return

        item = tree.selection()[0]
        column = tree.identify_column(event.x)
        column_index = int(column.replace("#", "")) - 1
        column_name = columns[column_index]
        current_value = tree.set(item, column)

        entry_edit = ttk.Entry(tree, font=("Arial", 16))
        entry_edit.insert(0, current_value)
        entry_edit.select_range(0, tk.END)
        entry_edit.focus()

        def save_edit(event):
            new_value = entry_edit.get().strip()
            if new_value != current_value:
                # Валидация для поля user_sex
                if column_name == "user_sex" and new_value not in ["Мужчина", "Женщина"]:
                    messagebox.showwarning("Ошибка", "Допустимые значения: Мужчина или Женщина.")
                    return

                # Валидация для поля date_of_birth (возраст от 5 до 100 лет)
                if column_name == "date_of_birth":
                    try:
                        age = int(new_value)
                        if age < 5 or age > 100:
                            messagebox.showwarning("Ошибка", "Возраст должен быть от 5 до 100 лет.")
                            return
                    except ValueError:
                        messagebox.showwarning("Ошибка", "Введите корректное число для возраста.")
                        return

                try:
                    conn = get_db_connection()
                    if conn:
                        cursor = conn.cursor()
                        primary_key_value = tree.item(item, "values")[0]
                        primary_key_column = columns[0]
                        update_query = f"UPDATE {table_name} SET {column_name} = %s WHERE {primary_key_column} = %s"
                        cursor.execute(update_query, (new_value, primary_key_value))
                        conn.commit()
                        cursor.close()
                        conn.close()

                        # Подсветка строки
                        if tree.exists(item):
                            tree.tag_configure("highlight", foreground="green")  # Зелёный цвет текста
                            tree.item(item, tags=("highlight",))

                        # Сброс подсветки через 20 секунд
                        def reset_highlight():
                            if tree.exists(item):
                                tree.item(item, tags=())

                        tree.after(20000, reset_highlight)  # 20 секунд = 20000 миллисекунд

                        # Перезагрузка данных
                        load_data()

                        # Уничтожение окна редактирования
                        entry_edit.destroy()
                except Exception as e:
                    messagebox.showerror("Ошибка", f"Не удалось обновить запись: {e}")
            else:
                # Если данные не изменились, просто закрываем окно редактирования
                entry_edit.destroy()

        entry_edit.bind("<Return>", save_edit)
        entry_edit.bind("<FocusOut>", lambda e: entry_edit.destroy())

        x, y, width, height = tree.bbox(item, column)
        entry_edit.place(x=x, y=y, width=width, height=height * 2)

    def close_window(self):
        """Функция для закрытия окна."""
        self.root.destroy()

# Главное окно
root = tk.Tk()
root.title("Вход в систему PROпиташка")
window_width = 400
window_height = 150
center_window(root, window_width, window_height)
root.minsize(300, 120)

app = Application(root)
root.mainloop()