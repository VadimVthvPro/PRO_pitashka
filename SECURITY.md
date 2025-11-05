# 🔒 Безопасность PROpitashka

Этот документ описывает меры безопасности, реализованные в проекте PROpitashka, и рекомендации по их использованию.

## 📋 Содержание

- [Защита админ-панели](#защита-админ-панели)
- [Защита базы данных](#защита-базы-данных)
- [Защита API ключей](#защита-api-ключей)
- [Мониторинг и аудит](#мониторинг-и-аудит)
- [Резервное копирование](#резервное-копирование)
- [Юридические требования](#юридические-требования)

---

## Защита админ-панели

### ⚠️ КРИТИЧНО: Смена дефолтного пароля

**При первом запуске админ-панели необходимо сменить дефолтный пароль `admin`.**

#### Автоматическая смена (рекомендуется)

При первом входе система автоматически запросит смену пароля.

#### Ручная смена

```bash
# Интерактивный режим
python scripts/change_admin_password.py

# Генерация случайного безопасного пароля
python scripts/change_admin_password.py --generate
```

### Требования к паролю

- ✅ Минимум 12 символов
- ✅ Заглавные буквы (A-Z)
- ✅ Строчные буквы (a-z)
- ✅ Цифры (0-9)
- ✅ Спецсимволы (!@#$%^&* и т.д.)

### Защита от brute-force атак

Система автоматически:
- Блокирует аккаунт на 30 минут после 5 неудачных попыток входа
- Логирует все попытки входа (успешные и неудачные)
- Отображает количество оставшихся попыток

### Просмотр логов безопасности

```sql
-- Последние 50 попыток входа
SELECT * FROM admin_login_log 
ORDER BY login_attempt_at DESC 
LIMIT 50;

-- Неудачные попытки за последние 24 часа
SELECT 
    admin_username,
    COUNT(*) as failed_attempts,
    MAX(login_attempt_at) as last_attempt
FROM admin_login_log
WHERE success = FALSE
  AND login_attempt_at > NOW() - INTERVAL '24 hours'
GROUP BY admin_username
ORDER BY failed_attempts DESC;
```

---

## Защита базы данных

### Разделение прав доступа

Проект использует двух пользователей БД:

1. **propitashka_user** (чтение/запись) - для бота
2. **propitashka_admin** (полный доступ) - для админ-панели

### Включение SSL

Для продакшена рекомендуется включить SSL:

```env
DB_SSLMODE=require
DB_SSL_ENABLED=true
```

### Создание пользователей БД

```sql
-- Создание основного пользователя для бота
CREATE USER propitashka_user WITH PASSWORD 'secure_password_here';

-- Выдача прав на чтение/запись в таблицы
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO propitashka_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO propitashka_user;

-- Создание администратора БД
CREATE USER propitashka_admin WITH PASSWORD 'admin_secure_password';
GRANT ALL PRIVILEGES ON DATABASE propitashka TO propitashka_admin;
```

---

## Защита API ключей

### ❌ НЕ КОММИТЬТЕ .env В GIT!

**Файл `.env` уже добавлен в `.gitignore`, но будьте осторожны:**

```bash
# Проверьте, что .env в gitignore
grep -q "^\.env$" .gitignore && echo "✅ OK" || echo "❌ ДОБАВЬТЕ .env В .gitignore!"

# Удалите .env из истории Git, если случайно закоммитили
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch .env" \
  --prune-empty --tag-name-filter cat -- --all
```

### Хранение секретов на продакшене

✅ Используйте:
- Environment variables на сервере
- Secrets в CI/CD (GitHub Secrets, GitLab CI/CD Variables)
- Менеджеры секретов (AWS Secrets Manager, HashiCorp Vault)

### Ротация API ключей

Рекомендуется менять API ключи каждые 90 дней:

```bash
# 1. Получите новый ключ от Google AI Studio
# 2. Обновите .env
nano .env  # Измените GEMINI_API_KEY

# 3. Перезапустите бота
./restart_bot.sh
```

---

## Мониторинг и аудит

### Запуск аудита безопасности

```bash
python scripts/security_audit.py
```

Аудит проверяет:
- ✅ Смена дефолтного пароля админа
- ✅ Наличие .env в .gitignore
- ✅ Отсутствие хардкод путей
- ✅ Включение SSL для БД
- ✅ Корректность структуры assets
- ✅ Применение миграций
- ✅ И многое другое...

### Настройка Sentry (опционально)

1. Зарегистрируйтесь на [sentry.io](https://sentry.io)
2. Создайте новый проект (Python)
3. Добавьте DSN в `.env`:

```env
SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1
```

4. Установите SDK:

```bash
pip install sentry-sdk
```

---

## Резервное копирование

### Автоматические бэкапы БД

Создайте скрипт `scripts/backup_db.sh`:

```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/path/to/backups"
DB_NAME="propitashka"

# Создаем директорию, если не существует
mkdir -p $BACKUP_DIR

# Создаем бэкап
pg_dump -U postgres $DB_NAME | gzip > $BACKUP_DIR/backup_$DATE.sql.gz

# Удаляем бэкапы старше 30 дней
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +30 -delete

echo "✅ Backup completed: backup_$DATE.sql.gz"
```

Настройте cron job:

```bash
# Открыть crontab
crontab -e

# Добавить задачу (каждый день в 2:00 AM)
0 2 * * * /path/to/scripts/backup_db.sh >> /var/log/propitashka_backup.log 2>&1
```

### Восстановление из бэкапа

```bash
# Распаковать и восстановить
gunzip -c /path/to/backups/backup_20251031_020000.sql.gz | psql -U postgres propitashka
```

---

## Юридические требования

### Privacy Policy на HTTPS

**GDPR/PDPA требуют размещения политики конфиденциальности на доступном HTTPS URL.**

#### Вариант 1: GitHub Pages (бесплатно)

```bash
# 1. Создайте репозиторий на GitHub
# 2. Запушьте только docs/
git init
git add docs/
git commit -m "Add privacy policy"
git remote add origin https://github.com/yourusername/propitashka-privacy.git
git push -u origin main

# 3. Включите GitHub Pages
# Settings → Pages → Source: main branch, folder: /docs
```

URL: `https://yourusername.github.io/propitashka-privacy/privacy_policy.html`

#### Вариант 2: Netlify (рекомендуется)

```bash
# 1. Установите Netlify CLI
npm install -g netlify-cli

# 2. Залогиньтесь
netlify login

# 3. Деплой
cd docs/
netlify deploy --prod
```

URL: `https://propitashka-privacy.netlify.app`

#### Обновление ссылки в боте

После размещения обновите в `.env`:

```env
PRIVACY_POLICY_URL=https://yourusername.github.io/propitashka-privacy/privacy_policy.html
```

### Экспорт данных пользователя (GDPR)

```sql
-- Экспорт всех данных конкретного пользователя
COPY (
    SELECT * FROM user_main WHERE user_id = $USER_ID
    UNION ALL
    SELECT * FROM food WHERE user_id = $USER_ID
    UNION ALL
    SELECT * FROM user_training WHERE user_id = $USER_ID
    UNION ALL
    SELECT * FROM water WHERE user_id = $USER_ID
    UNION ALL
    SELECT * FROM user_health WHERE user_id = $USER_ID
    UNION ALL
    SELECT * FROM user_aims WHERE user_id = $USER_ID
) TO '/tmp/user_data_export.csv' CSV HEADER;
```

### Удаление данных пользователя (право на забвение)

```sql
-- Полное удаление пользователя и всех связанных данных
BEGIN;

DELETE FROM food WHERE user_id = $USER_ID;
DELETE FROM user_training WHERE user_id = $USER_ID;
DELETE FROM water WHERE user_id = $USER_ID;
DELETE FROM user_health WHERE user_id = $USER_ID;
DELETE FROM user_aims WHERE user_id = $USER_ID;
DELETE FROM user_lang WHERE user_id = $USER_ID;
DELETE FROM user_main WHERE user_id = $USER_ID;

COMMIT;
```

---

## 📋 Контрольный список безопасности

Перед развертыванием на продакшн:

- [ ] Сменен дефолтный пароль админки
- [ ] Включен SSL для базы данных
- [ ] API ключи хранятся в environment variables
- [ ] Настроены автоматические бэкапы
- [ ] Включен rate limiting
- [ ] Настроены алерты о подозрительной активности
- [ ] Логируются все попытки входа в админку
- [ ] Privacy Policy размещена на HTTPS
- [ ] Проведен security audit
- [ ] Настроены мониторинг и алертинг
- [ ] Документация обновлена

---

## 🆘 Реагирование на инциденты

### Подозрение на взлом админки

```sql
-- 1. Немедленно смените пароль
UPDATE admin_users SET password_hash = 'new_bcrypt_hash_here' WHERE username = 'admin';

-- 2. Заблокируйте все сессии
UPDATE admin_users SET session_token = NULL, session_expires_at = NULL;

-- 3. Проверьте логи
SELECT * FROM admin_login_log WHERE success = TRUE ORDER BY login_attempt_at DESC LIMIT 100;

-- 4. Проверьте изменения в БД
SELECT * FROM pg_stat_activity WHERE datname = 'propitashka';
```

### Утечка API ключа

```bash
# 1. Немедленно отзовите старый ключ в Google AI Studio
# 2. Сгенерируйте новый
# 3. Обновите .env на всех серверах
# 4. Перезапустите все инстансы бота
# 5. Проверьте логи на подозрительную активность
```

---

## 📞 Контакты

При обнаружении уязвимостей: security@propitashka.com


