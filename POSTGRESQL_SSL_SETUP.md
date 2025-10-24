# 🔐 PostgreSQL SSL Configuration Guide

## Настройка SSL соединения для PostgreSQL

### Шаг 1: Генерация SSL сертификатов

```bash
# Перейдите в директорию данных PostgreSQL
cd /var/lib/postgresql/data  # Linux
# или
cd /usr/local/var/postgres    # macOS (Homebrew)

# Создайте директорию для сертификатов
sudo mkdir -p ssl
cd ssl

# Генерация приватного ключа
sudo openssl genrsa -out server.key 2048

# Генерация сертификата (действителен 365 дней)
sudo openssl req -new -x509 -days 365 -key server.key -out server.crt \
  -subj "/C=RU/ST=Moscow/L=Moscow/O=PROpitashka/CN=localhost"

# Установка правильных прав доступа
sudo chmod 600 server.key
sudo chmod 644 server.crt
sudo chown postgres:postgres server.key server.crt
```

### Шаг 2: Настройка postgresql.conf

Откройте файл конфигурации PostgreSQL:

```bash
# Найдите файл
sudo find / -name postgresql.conf 2>/dev/null

# Отредактируйте
sudo nano /etc/postgresql/14/main/postgresql.conf  # путь может отличаться
```

Добавьте или измените следующие параметры:

```conf
# SSL Configuration
ssl = on
ssl_cert_file = '/var/lib/postgresql/data/ssl/server.crt'
ssl_key_file = '/var/lib/postgresql/data/ssl/server.key'
ssl_ca_file = ''
ssl_crl_file = ''

# Предпочитать SSL соединения
ssl_prefer_server_ciphers = on
ssl_ciphers = 'HIGH:MEDIUM:+3DES:!aNULL'
```

### Шаг 3: Настройка pg_hba.conf

Откройте файл аутентификации:

```bash
sudo nano /etc/postgresql/14/main/pg_hba.conf
```

Замените строки с `host` на `hostssl` для принудительного использования SSL:

```conf
# TYPE  DATABASE        USER                ADDRESS         METHOD

# Требовать SSL для всех соединений
hostssl all             all                 0.0.0.0/0       md5
hostssl all             all                 ::/0            md5

# Для локальных соединений (без SSL)
local   all             all                                 peer

# Специфичные правила для пользователей бота
hostssl propitashka     propitashka_bot     0.0.0.0/0       md5
hostssl propitashka     propitashka_admin   0.0.0.0/0       md5
```

### Шаг 4: Перезапуск PostgreSQL

```bash
# Linux (systemd)
sudo systemctl restart postgresql

# macOS (Homebrew)
brew services restart postgresql

# Проверка статуса
sudo systemctl status postgresql  # Linux
brew services list                # macOS
```

### Шаг 5: Проверка SSL

```bash
# Проверка, что SSL включен
psql -h localhost -U postgres -d postgres -c "SHOW ssl;"

# Должно вывести: on

# Проверка текущего соединения
psql -h localhost -U postgres -d propitashka -c "SELECT version(), ssl_is_used();"

# Тест соединения с SSL
psql "host=localhost dbname=propitashka user=propitashka_bot sslmode=require"
```

### Шаг 6: Обновление .env

Обновите файл `.env` для использования SSL:

```env
# Database Configuration
DB_NAME=propitashka
DB_USER=propitashka_bot
DB_PASSWORD=your_secure_password
DB_HOST=localhost
DB_PORT=5432

# SSL Configuration
DB_SSLMODE=require
# Опции: disable, allow, prefer, require, verify-ca, verify-full

DB_SSL_ENABLED=true

# Путь к сертификату (для verify-ca или verify-full)
# DB_SSL_CERT_PATH=/path/to/server.crt
```

### Режимы SSL (sslmode)

| Режим | Описание | Безопасность |
|-------|----------|--------------|
| `disable` | SSL не используется | ❌ Низкая |
| `allow` | SSL если доступен | ⚠️ Средняя |
| `prefer` | Предпочитать SSL (по умолчанию) | ⚠️ Средняя |
| `require` | Требовать SSL | ✅ Высокая |
| `verify-ca` | SSL + проверка CA | ✅ Очень высокая |
| `verify-full` | SSL + проверка CA + hostname | ✅ Максимальная |

**Рекомендация для production:** `require` или выше

### Шаг 7: Тестирование в Python

```python
import psycopg2

# Тест соединения с SSL
try:
    conn = psycopg2.connect(
        dbname="propitashka",
        user="propitashka_bot",
        password="your_password",
        host="localhost",
        port="5432",
        sslmode="require"
    )
    
    cursor = conn.cursor()
    cursor.execute("SELECT ssl_is_used();")
    ssl_used = cursor.fetchone()[0]
    
    print(f"SSL используется: {ssl_used}")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"Ошибка: {e}")
```

### Troubleshooting

#### Ошибка: "SSL connection has been closed unexpectedly"

```bash
# Проверьте права на файлы
ls -la /var/lib/postgresql/data/ssl/

# Должно быть:
# -rw------- server.key (600)
# -rw-r--r-- server.crt (644)
```

#### Ошибка: "could not load server certificate file"

```bash
# Проверьте пути в postgresql.conf
sudo grep ssl /etc/postgresql/14/main/postgresql.conf

# Убедитесь, что файлы существуют
sudo ls -la /var/lib/postgresql/data/ssl/
```

#### Ошибка: "no pg_hba.conf entry for host"

```bash
# Проверьте pg_hba.conf
sudo cat /etc/postgresql/14/main/pg_hba.conf | grep hostssl

# Перезагрузите конфигурацию
sudo systemctl reload postgresql
```

### Для Production (Managed PostgreSQL)

Если используете managed PostgreSQL (Supabase, Neon, Render):

1. **Supabase**: SSL включен по умолчанию
   ```env
   DB_SSLMODE=require
   ```

2. **Neon**: SSL обязателен
   ```env
   DB_SSLMODE=require
   ```

3. **Render**: SSL включен по умолчанию
   ```env
   DB_SSLMODE=require
   ```

4. **AWS RDS**: Скачайте RDS CA certificate
   ```env
   DB_SSLMODE=verify-full
   DB_SSL_CERT_PATH=/path/to/rds-ca-2019-root.pem
   ```

### Проверка безопасности

```bash
# Проверка, что незашифрованные соединения блокируются
psql "host=localhost dbname=propitashka user=propitashka_bot sslmode=disable"
# Должно выдать ошибку, если настроено правильно

# Проверка шифрования
psql -h localhost -U propitashka_bot -d propitashka \
  -c "SELECT ssl_version(), ssl_cipher();"
```

### Мониторинг SSL соединений

```sql
-- Посмотреть активные SSL соединения
SELECT 
    pid,
    usename,
    application_name,
    client_addr,
    ssl,
    ssl_version,
    ssl_cipher
FROM pg_stat_ssl
JOIN pg_stat_activity ON pg_stat_ssl.pid = pg_stat_activity.pid
WHERE ssl = true;
```

---

## ✅ Checklist

- [ ] Сгенерированы SSL сертификаты
- [ ] Настроен postgresql.conf (ssl = on)
- [ ] Настроен pg_hba.conf (hostssl)
- [ ] PostgreSQL перезапущен
- [ ] SSL проверен через psql
- [ ] Обновлен .env (DB_SSLMODE=require)
- [ ] Протестировано соединение из Python
- [ ] Проверено, что незашифрованные соединения блокируются

---

**Готово! SSL настроен для PostgreSQL** 🔐

