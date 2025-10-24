# 🚀 Инструкция по заливке проекта на GitHub

## Шаг 1: Создайте репозиторий на GitHub

1. Перейдите на https://github.com/new
2. Введите название репозитория: `PROpitashka`
3. Описание: `AI-Powered Nutrition & Fitness Telegram Bot`
4. Выберите **Public** или **Private**
5. **НЕ** добавляйте README, .gitignore или лицензию (они уже есть)
6. Нажмите **Create repository**

## Шаг 2: Подключите локальный репозиторий

После создания репозитория GitHub покажет команды. Используйте эти:

```bash
cd /Users/VadimVthv/Desktop/PROpitashka

# Добавьте remote (замените YOUR_USERNAME на ваш username)
git remote add origin https://github.com/YOUR_USERNAME/PROpitashka.git

# Или используйте SSH (если настроен)
# git remote add origin git@github.com:YOUR_USERNAME/PROpitashka.git

# Проверьте, что remote добавлен
git remote -v

# Залейте код
git push -u origin main
```

## Шаг 3: Проверьте результат

Откройте ваш репозиторий на GitHub и убедитесь, что:
- ✅ Все файлы загружены
- ✅ README.md отображается на главной странице
- ✅ `.env` файл **НЕ** загружен (он в .gitignore)
- ✅ История коммитов видна

## 🔐 Важно: Безопасность

### Что НЕ должно попасть в GitHub:
- ❌ `.env` файл с секретами
- ❌ `logs/` директория с логами
- ❌ `__pycache__/` и другие временные файлы
- ❌ Собранные приложения (.app файлы)

Все это уже исключено через `.gitignore`

### Проверка перед пушем:

```bash
# Убедитесь, что .env не в staging
git status

# Проверьте, что .env в .gitignore
cat .gitignore | grep .env
```

## 📝 Настройка GitHub Secrets (для CI/CD)

Если планируете настроить автоматический деплой:

1. Перейдите в Settings → Secrets and variables → Actions
2. Добавьте секреты:
   - `TELEGRAM_TOKEN`
   - `GEMINI_API_KEY`
   - `DB_PASSWORD`
   - И другие из `.env`

## 🎯 Следующие шаги

После заливки на GitHub:

1. ✅ Добавьте описание проекта
2. ✅ Добавьте topics/tags: `telegram-bot`, `python`, `ai`, `nutrition`, `fitness`
3. ✅ Настройте GitHub Pages для политики конфиденциальности (опционально)
4. ✅ Создайте первый Release (v1.0.0)

## 🐛 Возможные проблемы

### Ошибка: "remote origin already exists"
```bash
git remote remove origin
git remote add origin https://github.com/YOUR_USERNAME/PROpitashka.git
```

### Ошибка: "failed to push some refs"
```bash
# Если репозиторий не пустой
git pull origin main --rebase
git push -u origin main
```

### Ошибка: "Permission denied"
```bash
# Проверьте SSH ключи или используйте HTTPS с токеном
# Создайте Personal Access Token на GitHub
```

---

**Готово! Проект готов к публикации на GitHub** 🎉

