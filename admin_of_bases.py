import tkinter as tk
from tkinter import ttk, messagebox, Spinbox, Frame, Canvas
import psycopg2
from datetime import datetime
import sys
import os
import bcrypt

# Add parent directory to path to import config
sys.path.insert(0, os.path.dirname(__file__))
from config import config

def center_window(window, width, height):
    """Функция для центрирования окна на экране."""
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = (screen_width // 2) - (width // 2)
    y = (screen_height // 2) - (height // 2)
    window.geometry(f"{width}x{height}+{x}+{y}")

def get_db_connection():
    """Функция для подключения к базе данных (с правами администратора)."""
    try:
        # Используем конфигурацию из .env файла
        # Сначала пробуем admin credentials, если не заданы - используем обычные
        db_config = config.get_db_config(admin=True)
        
        # Если ADMIN_DB_PASSWORD пустой, используем обычные credentials
        if not db_config.get('password'):
            db_config = config.get_db_config(admin=False)
        
        conn = psycopg2.connect(**db_config)
        return conn
    except psycopg2.Error as e:
        messagebox.showerror("Ошибка подключения", f"Не удалось подключиться к базе данных: {e}")
        return None

class ScrollableNotebook(ttk.Frame):
    """Виджет Notebook с прокручиваемыми вкладками"""
    def __init__(self, parent, *args, **kwargs):
        ttk.Frame.__init__(self, parent, *args, **kwargs)
        
        # Создаем canvas для прокрутки вкладок
        self.canvas = Canvas(self, height=30, highlightthickness=0)
        self.canvas.pack(side="top", fill="x", expand=False)
        
        # Фрейм для кнопок вкладок
        self.tab_frame = ttk.Frame(self.canvas)
        self.canvas_frame = self.canvas.create_window((0, 0), window=self.tab_frame, anchor="nw")
        
        # Горизонтальная прокрутка
        self.h_scroll = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        self.h_scroll.pack(side="top", fill="x")
        self.canvas.configure(xscrollcommand=self.h_scroll.set)
        
        # Контейнер для содержимого вкладок
        self.content_frame = ttk.Frame(self)
        self.content_frame.pack(side="top", fill="both", expand=True)
        
        self.tabs = []
        self.tab_buttons = []
        self.current_tab = None
        
        # Обновление области прокрутки
        self.tab_frame.bind("<Configure>", self._on_frame_configure)
        
    def _on_frame_configure(self, event=None):
        """Обновление области прокрутки canvas"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
    def add(self, child, text=""):
        """Добавить вкладку"""
        # Создаем кнопку для вкладки
        btn = ttk.Button(
            self.tab_frame, 
            text=text, 
            command=lambda idx=len(self.tabs): self.select_tab(idx),
            style="Tab.TButton"
        )
        btn.pack(side="left", padx=2, pady=2)
        
        self.tab_buttons.append(btn)
        self.tabs.append((child, text))
        
        # Прячем child в content_frame
        child.place(in_=self.content_frame, x=0, y=0, relwidth=1, relheight=1)
        child.lower()
        
        # Если это первая вкладка, выбираем её
        if len(self.tabs) == 1:
            self.select_tab(0)
            
    def select_tab(self, index):
        """Выбрать вкладку по индексу"""
        if 0 <= index < len(self.tabs):
            # Снимаем выделение со всех кнопок
            for btn in self.tab_buttons:
                btn.state(["!pressed", "!active"])
            
            # Выделяем текущую кнопку
            self.tab_buttons[index].state(["pressed"])
            
            # Скрываем все вкладки
            for tab, _ in self.tabs:
                tab.lower()
            
            # Показываем выбранную вкладку
            self.tabs[index][0].lift()
            self.current_tab = index

class Application:
    def __init__(self, root):
        self.root = root
        
        # Расширенный маппинг колонок на русский язык
        self.column_mapping = {
            # user_main
            "user_id": "ID пользователя",
            "user_name": "Имя пользователя",
            "user_sex": "Пол",
            "date_of_birth": "Возраст",
            
            # food
            "food_id": "ID записи",  # Для обратной совместимости
            "id": "ID",
            "name_of_food": "Название блюда",
            "b": "Белки (г)",
            "g": "Жиры (г)",
            "u": "Углеводы (г)",
            "cal": "Калорийность",
            "date": "Дата",
            
            # user_aims (без aim_id, т.к. user_id - первичный ключ)
            "aim_id": "ID цели",  # Для обратной совместимости
            "user_aim": "Цель пользователя",
            "daily_cal": "Дневная норма (ккал)",
            
            # user_health
            "health_id": "ID записи",  # Для обратной совместимости
            "imt": "ИМТ",
            "imt_str": "Расшифровка ИМТ",
            "weight": "Вес (кг)",
            "height": "Рост (см)",
            
            # user_lang
            "lang": "Язык",
            
            # user_training
            "training_id": "ID тренировки",  # Для обратной совместимости
            "training_cal": "Сожжено калорий",
            "tren_time": "Длительность (мин)",
            "training_type_id": "ID типа тренировки",
            "training_name": "Название тренировки",
            "updated_at": "Дата обновления",
            
            # water
            "count": "Количество (стаканов)",
            "data": "Дата",
            
            # training_types
            "id": "ID",
            "name_ru": "Название (RU)",
            "name_en": "Название (EN)",
            "name_de": "Название (DE)",
            "name_fr": "Название (FR)",
            "name_es": "Название (ES)",
            "base_coefficient": "Базовый коэффициент",
            "emoji": "Эмодзи",
            "description_ru": "Описание (RU)",
            "description_en": "Описание (EN)",
            "description_de": "Описание (DE)",
            "description_fr": "Описание (FR)",
            "description_es": "Описание (ES)",
            "is_active": "Активен",
            "created_at": "Дата создания",
            
            # training_coefficients
            "gender_male_modifier": "Модификатор (мужской)",
            "gender_female_modifier": "Модификатор (женский)",
            "age_18_25_modifier": "Модификатор (18-25 лет)",
            "age_26_35_modifier": "Модификатор (26-35 лет)",
            "age_36_45_modifier": "Модификатор (36-45 лет)",
            "age_46_55_modifier": "Модификатор (46-55 лет)",
            "age_56_plus_modifier": "Модификатор (56+ лет)",
            "weight_under_60_modifier": "Модификатор (вес <60)",
            "weight_60_70_modifier": "Модификатор (вес 60-70)",
            "weight_71_80_modifier": "Модификатор (вес 71-80)",
            "weight_81_90_modifier": "Модификатор (вес 81-90)",
            "weight_91_100_modifier": "Модификатор (вес 91-100)",
            "weight_over_100_modifier": "Модификатор (вес >100)",
            "height_under_160_modifier": "Модификатор (рост <160)",
            "height_160_175_modifier": "Модификатор (рост 160-175)",
            "height_over_175_modifier": "Модификатор (рост >175)",
            
            # chat_history
            "message_type": "Тип сообщения",
            "message_text": "Текст сообщения",
            
            # admin_users
            "username": "Имя пользователя",
            "password_hash": "Хеш пароля",
            "last_login": "Последний вход"
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

        self.button = ttk.Button(self.button_frame, text="Войти", command=self.submit, width=10)
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
        username = self.entry_name.get()
        password = self.entry_pas.get()

        if not username or not password:
            self.error_label.config(text="Имя пользователя и пароль не могут быть пустыми", foreground="red")
            return

        conn = get_db_connection()
        if not conn:
            return  # Сообщение об ошибке уже показано в get_db_connection

        try:
            cursor = conn.cursor()
            cursor.execute("SELECT password_hash FROM admin_users WHERE username = %s", (username,))
            result = cursor.fetchone()

            if result:
                password_hash = result[0]
                if bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8')):
                    # Пароль верный, обновляем last_login
                    cursor.execute("UPDATE admin_users SET last_login = NOW() WHERE username = %s", (username,))
                    conn.commit()
                    self.show_main_window()
                else:
                    self.error_label.config(text="Неверное имя пользователя или пароль", foreground="red")
            else:
                self.error_label.config(text="Неверное имя пользователя или пароль", foreground="red")

            cursor.close()
            conn.close()

        except Exception as e:
            self.error_label.config(text=f"Ошибка аутентификации: {e}", foreground="red")
            print(f"Ошибка: {str(e)}")
            if conn:
                conn.close()

    def show_main_window(self):
        """Функция для отображения главного окна с вкладками."""
        self.frame.pack_forget()
        
        # Используем ScrollableNotebook вместо обычного Notebook
        self.notebook = ScrollableNotebook(self.root)
        self.notebook.pack(fill="both", expand=True)

        window_width = 1400
        window_height = 900
        center_window(self.root, window_width, window_height)
        self.root.title("PROпиташка - Администрирование базы данных")
        self.root.minsize(1000, 700)

        self.create_tabs()

    def create_tabs(self):
        """Функция для создания вкладок со всеми таблицами."""
        tabs = [
            # Основные таблицы
            ("👤 Пользователи", 
             ["user_id", "user_name", "user_sex", "date_of_birth"],
             "SELECT user_id, user_name, user_sex, date_of_birth FROM user_main ORDER BY user_id", 
             "user_main"),
            
            ("🍽️ Питание", 
             ["id", "user_id", "name_of_food", "b", "g", "u", "cal", "date"],
             "SELECT id, user_id, name_of_food, b, g, u, cal, date FROM food ORDER BY date DESC, id DESC", 
             "food"),
            
            ("🎯 Цели", 
             ["user_id", "user_aim", "daily_cal"],
             "SELECT user_id, user_aim, daily_cal FROM user_aims ORDER BY user_id", 
             "user_aims"),
            
            ("💪 Здоровье", 
             ["id", "user_id", "imt", "imt_str", "cal", "date", "weight", "height"],
             "SELECT id, user_id, imt, imt_str, cal, date, weight, height FROM user_health ORDER BY date DESC", 
             "user_health"),
            
            ("🌐 Языки", 
             ["user_id", "lang"],
             "SELECT user_id, lang FROM user_lang ORDER BY user_id", 
             "user_lang"),
            
            ("🏃 Тренировки", 
             ["id", "user_id", "date", "training_cal", "tren_time", "training_type_id", "training_name"],
             "SELECT id, user_id, date, training_cal, tren_time, training_type_id, training_name FROM user_training ORDER BY date DESC", 
             "user_training"),
            
            ("💧 Вода", 
             ["user_id", "data", "count"],
             "SELECT user_id, data, count FROM water ORDER BY data DESC", 
             "water"),
            
            # Новые таблицы системы тренировок
            ("🏋️ Типы тренировок", 
             ["id", "name_ru", "name_en", "name_de", "name_fr", "name_es", "base_coefficient", "emoji", "is_active"],
             "SELECT id, name_ru, name_en, name_de, name_fr, name_es, base_coefficient, emoji, is_active FROM training_types ORDER BY id", 
             "training_types"),
            
            ("📊 Коэффициенты", 
             ["id", "training_type_id", "gender_male_modifier", "gender_female_modifier", "age_18_25_modifier", "age_26_35_modifier"],
             "SELECT id, training_type_id, gender_male_modifier, gender_female_modifier, age_18_25_modifier, age_26_35_modifier FROM training_coefficients ORDER BY id", 
             "training_coefficients"),
            
            ("💬 История чата", 
             ["id", "user_id", "message_type", "message_text", "created_at"],
             "SELECT id, user_id, message_type, LEFT(message_text, 100), created_at FROM chat_history ORDER BY created_at DESC LIMIT 1000", 
             "chat_history"),
            
            ("👨‍💼 Администраторы", 
             ["id", "username", "last_login", "created_at"],
             "SELECT id, username, last_login, created_at FROM admin_users ORDER BY id", 
             "admin_users")
        ]

        for tab_name, columns, query, table_name in tabs:
            tab = ttk.Frame(self.notebook)
            self.notebook.add(tab, text=tab_name)
            self.create_table(tab, columns, query, table_name)

    def create_table(self, tab, columns, query, table_name):
        """Функция для создания таблицы на вкладке."""
        container = ttk.Frame(tab)
        container.grid(row=2, column=0, sticky="nsew")

        # Маппинг колонок для отображения
        display_columns = [self.column_mapping.get(col, col) for col in columns]
        
        tree = ttk.Treeview(container, columns=columns, show="headings")
        style = ttk.Style()
        style.configure("Treeview.Heading", font=("Arial", 11, "bold"), padding=5)
        style.configure("Treeview", font=("Arial", 10), rowheight=25)

        for i, col in enumerate(columns):
            tree.heading(col, text=display_columns[i], 
                        command=lambda c=col: self.sort_treeview(tree, c, False))
            # Настройка ширины колонок
            tree.column(col, width=150, minwidth=100)

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
        filter_frame.grid(row=0, column=0, sticky="ew", pady=5, padx=5)

        filter_label = ttk.Label(filter_frame, text="🔍 Фильтр:")
        filter_label.pack(side="left", padx=5)

        filter_entry = ttk.Entry(filter_frame, width=40)
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

        clear_filter_button = ttk.Button(filter_frame, text="Сбросить", command=load_data)
        clear_filter_button.pack(side="left", padx=5)

        button_frame = ttk.Frame(tab)
        button_frame.grid(row=1, column=0, sticky="ew", pady=5, padx=5)

        refresh_button = ttk.Button(button_frame, text="🔄 Обновить", command=load_data)
        refresh_button.pack(side="left", padx=5)

        # Ограничение добавления для некоторых таблиц
        if table_name not in ["training_coefficients", "admin_users"]:
            add_button = ttk.Button(button_frame, text="➕ Добавить запись", 
                                   command=lambda: self.add_record(tree, columns, table_name, load_data))
            add_button.pack(side="left", padx=5)

        delete_button = ttk.Button(button_frame, text="🗑️ Удалить строку", 
                                   command=lambda: self.delete_record(tree, table_name, load_data))
        delete_button.pack(side="left", padx=5)

        # Счётчик записей
        count_label = ttk.Label(button_frame, text=f"Всего записей: {len(tree.get_children())}", 
                               font=("Arial", 10, "italic"))
        count_label.pack(side="right", padx=10)

        # Обновление счётчика при загрузке
        def load_data_with_count():
            load_data()
            count_label.config(text=f"Всего записей: {len(tree.get_children())}")

        # Заменяем load_data на load_data_with_count
        refresh_button.config(command=load_data_with_count)
        if table_name not in ["training_coefficients", "admin_users"]:
            add_button.config(command=lambda: self.add_record(tree, columns, table_name, load_data_with_count))
        delete_button.config(command=lambda: self.delete_record(tree, table_name, load_data_with_count))
        clear_filter_button.config(command=load_data_with_count)

        tree.bind("<Double-1>", lambda event: self.edit_cell(event, tree, columns, table_name, load_data_with_count))

    def sort_treeview(self, tree, col, reverse):
        """Сортировка данных в Treeview по выбранному столбцу."""
        data = [(tree.set(item, col), item) for item in tree.get_children("")]
        
        # Попытка числовой сортировки
        try:
            data.sort(key=lambda x: float(x[0]) if x[0] else 0, reverse=reverse)
        except ValueError:
            # Если не получается преобразовать в число, сортируем как строки
            data.sort(reverse=reverse)

        for index, (val, item) in enumerate(data):
            tree.move(item, "", index)

        tree.heading(col, command=lambda: self.sort_treeview(tree, col, not reverse))

    def delete_record(self, tree, table_name, load_data):
        """Функция для удаления выбранных строк с каскадным удалением."""
        selected_items = tree.selection()
        if not selected_items:
            messagebox.showwarning("Предупреждение", "Выберите строки для удаления.")
            return

        confirm = messagebox.askyesno("Подтверждение", 
                                     f"Вы уверены, что хотите удалить {len(selected_items)} строк(и)?")
        if not confirm:
            return

        try:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()

                for item in selected_items:
                    values = tree.item(item, "values")
                    primary_key_value = values[0]

                    # Каскадное удаление для user_main
                    if table_name == "user_main":
                        self.delete_related_records(cursor, primary_key_value)

                    # Определение имени первичного ключа
                    if table_name == "user_main":
                        primary_key_column = "user_id"
                    elif table_name == "user_lang":
                        primary_key_column = "user_id"
                    elif table_name == "user_aims":
                        primary_key_column = "user_id"
                    elif table_name == "water":
                        # water не имеет первичного ключа, используем комбинацию
                        primary_key_column = "user_id"
                    elif table_name in ["food", "user_health", "user_training", "training_types", "training_coefficients", "chat_history", "admin_users"]:
                        # Эти таблицы используют 'id' как первичный ключ
                        primary_key_column = "id"
                    else:
                        primary_key_column = "id"
                    
                    cursor.execute(f"DELETE FROM {table_name} WHERE {primary_key_column} = %s", (primary_key_value,))

                conn.commit()
                cursor.close()
                conn.close()

                load_data()
                messagebox.showinfo("Успех", f"Удалено {len(selected_items)} строк(и).")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось удалить строки: {e}")
            if conn:
                conn.rollback()

    def delete_related_records(self, cursor, user_id):
        """Функция для каскадного удаления связанных записей из всех таблиц по user_id."""
        related_tables = [
            "chat_history",      # История чата
            "food",              # Питание
            "user_aims",         # Цели
            "user_health",       # Здоровье
            "user_lang",         # Язык
            "user_training",     # Тренировки
            "water"              # Вода
        ]
        
        for table in related_tables:
            try:
                cursor.execute(f"DELETE FROM {table} WHERE user_id = %s", (user_id,))
            except Exception as e:
                print(f"Ошибка удаления из {table}: {e}")

    def add_record(self, tree, columns, table_name, load_data):
        """Функция для добавления новой записи."""
        add_window = tk.Toplevel()
        add_window.title(f"Добавить запись в таблицу '{table_name}'")
        window_width = 700
        window_height = min(len(columns) * 60 + 150, 800)
        center_window(add_window, window_width, window_height)
        add_window.minsize(600, 300)

        # Создаем canvas с прокруткой для большого количества полей
        canvas = Canvas(add_window)
        scrollbar = ttk.Scrollbar(add_window, orient="vertical", command=canvas.yview)
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

        for i, col in enumerate(columns):
            label_text = self.column_mapping.get(col, col)
            label = ttk.Label(scrollable_frame, text=label_text + ":")
            label.grid(row=i, column=0, padx=10, pady=8, sticky="e")

            # Специальные поля для различных таблиц
            if col == "count" and table_name == "water":
                entry = Spinbox(scrollable_frame, from_=0, to=99, increment=1, width=25)
                entry.grid(row=i, column=1, padx=10, pady=8, sticky="w")
                
            elif col in ["id", "tren_time"] and table_name == "user_training":
                entry = Spinbox(scrollable_frame, from_=1, to=99999, increment=1, width=25)
                entry.grid(row=i, column=1, padx=10, pady=8, sticky="w")
                
            elif col == "training_cal" and table_name == "user_training":
                entry = Spinbox(scrollable_frame, from_=1.0, to=9999.0, increment=0.1, format="%.1f", width=25)
                entry.grid(row=i, column=1, padx=10, pady=8, sticky="w")
                
            elif col == "training_type_id" and table_name == "user_training":
                # Загружаем типы тренировок
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

                entry = ttk.Combobox(scrollable_frame, values=training_type_names, width=23, state="readonly")
                if training_type_names:
                    entry.current(0)
                entry.grid(row=i, column=1, padx=10, pady=8, sticky="w")
                
            elif col == "id" and table_name == "user_health":
                entry = Spinbox(scrollable_frame, from_=1, to=999999, increment=1, width=25)
                entry.grid(row=i, column=1, padx=10, pady=8, sticky="w")
                
            elif col in ["imt", "cal", "weight", "height"] and table_name == "user_health":
                entry = Spinbox(scrollable_frame, from_=1.0, to=999.0, increment=0.1, format="%.1f", width=25)
                entry.grid(row=i, column=1, padx=10, pady=8, sticky="w")
                
            elif col == "aim_id" and table_name == "user_aims":
                # aim_id не существует - user_id является первичным ключом
                entry = ttk.Entry(scrollable_frame, width=25, state="disabled")
                entry.insert(0, "Автоматически")
                entry.grid(row=i, column=1, padx=10, pady=8, sticky="w")
                
            elif col == "daily_cal" and table_name == "user_aims":
                entry = Spinbox(scrollable_frame, from_=500, to=10000, increment=50, width=25)
                entry.grid(row=i, column=1, padx=10, pady=8, sticky="w")
                
            elif col == "id" and table_name == "food":
                entry = Spinbox(scrollable_frame, from_=1, to=999999, increment=1, width=25)
                entry.grid(row=i, column=1, padx=10, pady=8, sticky="w")
                
            elif col in ["b", "g", "u", "cal"] and table_name == "food":
                entry = Spinbox(scrollable_frame, from_=0.0, to=999.0, increment=0.1, format="%.1f", width=25)
                entry.grid(row=i, column=1, padx=10, pady=8, sticky="w")
                
            elif col == "user_id" and table_name == "user_main":
                entry = Spinbox(scrollable_frame, from_=1, to=999999999, increment=1, width=25)
                entry.grid(row=i, column=1, padx=10, pady=8, sticky="w")
                
            elif col == "date_of_birth" and table_name == "user_main":
                entry = Spinbox(scrollable_frame, from_=5, to=100, increment=1, width=25)
                entry.grid(row=i, column=1, padx=10, pady=8, sticky="w")
                
            elif col == "user_id" and table_name != "user_main":
                # Загружаем пользователей
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

                entry = ttk.Combobox(scrollable_frame, values=user_names, width=23, state="readonly")
                if user_names:
                    entry.current(0)
                entry.grid(row=i, column=1, padx=10, pady=8, sticky="w")
                
            elif col == "user_sex" and table_name == "user_main":
                entry = ttk.Combobox(scrollable_frame, values=["Мужской", "Женский"], width=23, state="readonly")
                entry.current(0)
                entry.grid(row=i, column=1, padx=10, pady=8, sticky="w")
                
            elif col == "lang" and table_name == "user_lang":
                entry = ttk.Combobox(scrollable_frame, values=["ru", "en", "de", "fr", "es"], width=23, state="readonly")
                entry.current(0)
                entry.grid(row=i, column=1, padx=10, pady=8, sticky="w")
                
            elif col == "user_aim" and table_name == "user_aims":
                entry = ttk.Combobox(scrollable_frame, 
                                    values=["Похудение", "Набор массы", "Поддержание формы"], 
                                    width=23)
                entry.current(0)
                entry.grid(row=i, column=1, padx=10, pady=8, sticky="w")
                
            elif col == "message_type" and table_name == "chat_history":
                entry = ttk.Combobox(scrollable_frame, values=["user", "bot"], width=23, state="readonly")
                entry.current(0)
                entry.grid(row=i, column=1, padx=10, pady=8, sticky="w")
                
            elif col in ["date", "data"] and table_name not in ["chat_history"]:
                entry = ttk.Entry(scrollable_frame, width=25)
                entry.insert(0, datetime.now().strftime("%d-%m-%Y"))
                entry.grid(row=i, column=1, padx=10, pady=8, sticky="w")
                
            elif col == "is_active" and table_name == "training_types":
                entry = ttk.Combobox(scrollable_frame, values=["TRUE", "FALSE"], width=23, state="readonly")
                entry.current(0)
                entry.grid(row=i, column=1, padx=10, pady=8, sticky="w")
                
            elif col in ["base_coefficient"] and table_name == "training_types":
                entry = Spinbox(scrollable_frame, from_=0.0, to=20.0, increment=0.1, format="%.2f", width=25)
                entry.grid(row=i, column=1, padx=10, pady=8, sticky="w")
                
            elif "modifier" in col and table_name == "training_coefficients":
                entry = Spinbox(scrollable_frame, from_=0.0, to=2.0, increment=0.01, format="%.3f", width=25)
                entry.insert(0, "1.000")
                entry.grid(row=i, column=1, padx=10, pady=8, sticky="w")
                
            else:
                entry = ttk.Entry(scrollable_frame, width=25)
                entry.grid(row=i, column=1, padx=10, pady=8, sticky="w")

            entries.append(entry)

        canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y")

        def save_record():
            values = []
            for i, entry in enumerate(entries):
                col = columns[i]
                
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
                elif col == "training_type_id" and table_name == "user_training":
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

            # Проверка заполненности обязательных полей
            if any(v is None or v == '' for i, v in enumerate(values) if columns[i] not in ['updated_at', 'created_at']):
                messagebox.showwarning("Предупреждение", "Заполните все обязательные поля!")
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
                    
                    # Подсветка добавленной записи
                    if tree.get_children():
                        last_item = tree.get_children()[-1]
                        if tree.exists(last_item):
                            tree.tag_configure("highlight", foreground="green")
                            tree.item(last_item, tags=("highlight",))
                            tree.see(last_item)

                            def reset_highlight():
                                if tree.exists(last_item):
                                    tree.item(last_item, tags=())

                            tree.after(20000, reset_highlight)
                            
                    messagebox.showinfo("Успех", "Запись успешно добавлена!")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось добавить запись: {e}")

        button_frame = ttk.Frame(add_window)
        button_frame.pack(side="bottom", fill="x", padx=10, pady=10)

        add_button = ttk.Button(button_frame, text="✅ Сохранить", command=save_record, width=15)
        add_button.pack(side="left", padx=5)

        cancel_button = ttk.Button(button_frame, text="❌ Отмена", command=add_window.destroy, width=15)
        cancel_button.pack(side="left", padx=5)

    def edit_cell(self, event, tree, columns, table_name, load_data):
        """Функция для редактирования ячейки при двойном клике."""
        region = tree.identify_region(event.x, event.y)
        if region != "cell":
            return

        if not tree.selection():
            return
            
        item = tree.selection()[0]
        column = tree.identify_column(event.x)
        column_index = int(column.replace("#", "")) - 1
        
        if column_index < 0 or column_index >= len(columns):
            return
            
        column_name = columns[column_index]
        current_value = tree.set(item, column)

        # Запрет редактирования первичных ключей и некоторых полей
        restricted_columns = ["id", "user_id", "food_id", "health_id", "aim_id", 
                             "training_id", "created_at", "password_hash"]
        if column_name in restricted_columns and table_name != "user_main":
            messagebox.showinfo("Информация", "Это поле нельзя редактировать напрямую")
            return

        # Создание поля для редактирования
        entry_edit = ttk.Entry(tree, font=("Arial", 12))
        entry_edit.insert(0, current_value)
        entry_edit.select_range(0, tk.END)
        entry_edit.focus()

        def save_edit(event=None):
            new_value = entry_edit.get().strip()
            if new_value == current_value:
                entry_edit.destroy()
                return

            # Валидация для специальных полей
            if column_name == "user_sex" and new_value not in ["Мужской", "Женский", "Мужчина", "Женщина"]:
                messagebox.showwarning("Ошибка", "Допустимые значения: Мужской, Женский")
                entry_edit.destroy()
                return

            if column_name == "date_of_birth":
                try:
                    age = int(new_value)
                    if age < 5 or age > 100:
                        messagebox.showwarning("Ошибка", "Возраст должен быть от 5 до 100 лет")
                        entry_edit.destroy()
                        return
                except ValueError:
                    messagebox.showwarning("Ошибка", "Введите корректное число для возраста")
                    entry_edit.destroy()
                    return

            if column_name == "lang" and new_value not in ["ru", "en", "de", "fr", "es"]:
                messagebox.showwarning("Ошибка", "Допустимые значения: ru, en, de, fr, es")
                entry_edit.destroy()
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

                    # Подсветка изменённой строки
                    if tree.exists(item):
                        tree.tag_configure("highlight", foreground="blue")
                        tree.item(item, tags=("highlight",))

                        def reset_highlight():
                            if tree.exists(item):
                                tree.item(item, tags=())

                        tree.after(10000, reset_highlight)

                    load_data()
                    entry_edit.destroy()
                    messagebox.showinfo("Успех", "Запись успешно обновлена!")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось обновить запись: {e}")
                entry_edit.destroy()

        entry_edit.bind("<Return>", save_edit)
        entry_edit.bind("<Escape>", lambda e: entry_edit.destroy())
        entry_edit.bind("<FocusOut>", lambda e: entry_edit.destroy())

        # Позиционирование поля редактирования
        try:
            x, y, width, height = tree.bbox(item, column)
            entry_edit.place(x=x, y=y, width=width, height=height)
        except:
            entry_edit.destroy()

    def close_window(self):
        """Функция для закрытия окна."""
        self.root.destroy()

# Главное окно
root = tk.Tk()
root.title("PROпиташка - Вход в систему администрирования")
window_width = 450
window_height = 180
center_window(root, window_width, window_height)
root.minsize(400, 150)

app = Application(root)
root.mainloop()
