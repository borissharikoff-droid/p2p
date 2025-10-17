# 🚂 Деплой на Railway

## 📋 Инструкция по деплою

### 1. Подготовка
- ✅ Все файлы перемещены в корень репозитория
- ✅ Удален подмодул p2p/
- ✅ Добавлен .gitignore
- ✅ Настроены Procfile и railway.json

### 2. Настройка Railway

#### Создание проекта:
1. Зайдите на [Railway.app](https://railway.app)
2. Нажмите "New Project"
3. Выберите "Deploy from GitHub repo"
4. Подключите репозиторий `borissharikoff-droid/p2p`

#### Настройка переменных окружения:
В панели Railway добавьте следующие переменные:

```
BOT_TOKEN=your_telegram_bot_token
DATABASE_URL=sqlite:///bot_database.db
CACHE_DURATION=60
RATE_LIMIT_COOLDOWN=30
BESTCHANGE_URL=https://www.bestchange.com/tether-trc20-to-cash-ruble-in-msk.html
LOG_LEVEL=INFO
PORT=8080
```

### 3. Проверка деплоя

#### Health Check:
После деплоя проверьте:
```
GET https://your-app.railway.app/health
```

Ожидаемый ответ:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00",
  "service": "telegram-bot"
}
```

#### Логи:
Проверьте логи в панели Railway:
- Settings → Deployments → View Logs
- Ищите сообщения о запуске бота

### 4. Возможные проблемы

#### Проблема: "Module not found"
**Решение:** Убедитесь, что все файлы находятся в корне репозитория

#### Проблема: "BOT_TOKEN not found"
**Решение:** Проверьте переменные окружения в Railway

#### Проблема: "Port binding failed"
**Решение:** Убедитесь, что PORT=8080 установлен в переменных окружения

### 5. Структура проекта

```
p2p/
├── telegram_bot.py           # Основной файл бота
├── config.py                 # Конфигурация
├── database.py               # База данных SQLite
├── database_postgres.py      # База данных PostgreSQL
├── bestchange_parser.py      # Парсер BestChange
├── crypto_api.py             # API криптовалют
├── image_generator.py        # Генератор изображений
├── cache_manager.py          # Менеджер кэша
├── validators.py             # Валидаторы
├── exceptions.py             # Исключения
├── grinex_parser.py          # Парсер Grinex
├── handlers/                 # Обработчики команд
│   ├── __init__.py
│   ├── rate_handler.py
│   ├── wallet_handler.py
│   ├── inline_handler.py
│   └── crypto_tracking_handler.py
├── Procfile                  # Конфигурация Railway
├── railway.json              # Настройки Railway
├── requirements.txt          # Зависимости Python
├── env.template              # Шаблон переменных окружения
├── README.md                 # Документация
└── .gitignore                # Исключения Git
```

### 6. Мониторинг

После успешного деплоя:
- ✅ Бот должен отвечать на команды в Telegram
- ✅ Health check должен возвращать статус "healthy"
- ✅ Логи должны показывать успешный запуск
- ✅ Изображения с курсами должны генерироваться корректно

---

**🎉 Готово! Ваш бот должен успешно деплоиться на Railway!**
