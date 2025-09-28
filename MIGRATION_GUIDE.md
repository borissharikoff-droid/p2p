# Руководство по миграции на улучшенную архитектуру

## 🚀 Что изменилось

### ✅ Улучшения архитектуры:

1. **Модульная структура** - код разделен на логические компоненты:
   - `config.py` - централизованная конфигурация
   - `exceptions.py` - кастомные исключения
   - `validators.py` - валидация данных
   - `handlers/` - обработчики функциональности
   - `telegram_bot_refactored.py` - основной файл бота

2. **Типизация** - добавлена полная типизация для лучшей читаемости и отладки

3. **Обработка ошибок** - специфичные исключения вместо общих

4. **Конфигурация** - все настройки вынесены в отдельный модуль

5. **Валидация** - централизованная валидация данных

## 📁 Новая структура файлов

```
тг парсерэ/
├── config.py                    # Конфигурация
├── exceptions.py                # Кастомные исключения
├── validators.py                # Валидаторы
├── handlers/                    # Обработчики
│   ├── __init__.py
│   ├── rate_handler.py          # Обработчик курсов
│   ├── wallet_handler.py        # Обработчик кошельков
│   └── inline_handler.py        # Обработчик inline запросов
├── telegram_bot_refactored.py   # Основной файл бота
├── telegram_bot.py              # Старый файл (можно удалить)
├── bestchange_parser.py         # Парсер (обновлен)
├── database.py                  # БД (обновлен)
├── cache_manager.py             # Кэш (обновлен)
├── Procfile                     # Обновлен для Railway
└── requirements.txt             # Без изменений
```

## 🔄 Миграция

### Шаг 1: Обновление Railway

1. **Замените основной файл:**
   ```bash
   # В Railway замените telegram_bot.py на telegram_bot_refactored.py
   ```

2. **Обновите Procfile:**
   ```
   web: python telegram_bot_refactored.py
   ```

### Шаг 2: Переменные окружения

Все существующие переменные окружения остаются совместимыми:

```env
BOT_TOKEN=your_bot_token
CACHE_DURATION=60
RATE_LIMIT_COOLDOWN=30
MAX_WALLETS_PER_USER=10
CLEANUP_INTERVAL=3600
PRICE_CHECK_INTERVAL=300
SUPPORT_URL=https://t.me/doxpublisher
DATABASE_PATH=bot_database.db
DATABASE_CLEANUP_DAYS=7
CACHE_DIRECTORY=cache
CACHE_MAX_AGE_HOURS=24
PORT=8080
HOST=0.0.0.0
```

### Шаг 3: Тестирование

1. **Локальное тестирование:**
   ```bash
   python telegram_bot_refactored.py
   ```

2. **Проверка health check:**
   ```bash
   curl http://localhost:8080/health
   ```

## 🆕 Новые возможности

### 1. Улучшенная конфигурация
```python
from config import bot_config, db_config, cache_config

# Использование
cache_duration = bot_config.cache_duration
max_wallets = bot_config.max_wallets_per_user
```

### 2. Специфичные исключения
```python
from exceptions import BestChangeError, DatabaseError, ValidationError

try:
    result = parser.run()
except BestChangeError as e:
    logger.error(f"Ошибка парсинга: {e}")
```

### 3. Валидация данных
```python
from validators import validate_wallet_address, validate_amount

# Валидация адреса кошелька
validate_wallet_address("TQn9Y2khEsLJW1ChVWFMSMeRDow5KcbLSE")

# Валидация суммы
amount = validate_amount("1000.50")
```

### 4. Модульные обработчики
```python
from handlers import RateHandler, WalletHandler, InlineHandler

# Каждый обработчик отвечает за свою область
rate_handler = RateHandler(db, cache)
wallet_handler = WalletHandler(db)
inline_handler = InlineHandler(db, rate_handler)
```

## 🔧 Совместимость

### ✅ Что остается без изменений:
- Все команды бота (`/start`, `/help`, `/stats`)
- Все callback'и и inline запросы
- База данных и структура таблиц
- Кэширование и rate limiting
- Health check endpoints
- Railway deployment

### ⚠️ Что изменилось:
- Структура кода (модули вместо монолита)
- Обработка ошибок (специфичные исключения)
- Конфигурация (централизованная)
- Типизация (полная типизация)

## 🚨 Откат

Если что-то пойдет не так, можно быстро откатиться:

1. **Верните старый Procfile:**
   ```
   web: python telegram_bot.py
   ```

2. **Или переименуйте файлы:**
   ```bash
   mv telegram_bot_refactored.py telegram_bot_new.py
   mv telegram_bot.py telegram_bot_refactored.py
   mv telegram_bot_new.py telegram_bot.py
   ```

## 📊 Преимущества новой архитектуры

1. **Читаемость** - код легче понимать и поддерживать
2. **Тестируемость** - каждый модуль можно тестировать отдельно
3. **Расширяемость** - легко добавлять новые функции
4. **Отладка** - специфичные исключения упрощают поиск ошибок
5. **Конфигурация** - все настройки в одном месте
6. **Типизация** - меньше ошибок во время разработки

## 🎯 Следующие шаги

После успешной миграции можно:

1. **Добавить unit тесты** для каждого модуля
2. **Реализовать отслеживание курсов** (заглушки уже есть)
3. **Добавить Redis** для кэширования
4. **Улучшить логирование** (структурированные логи)
5. **Добавить метрики** и мониторинг

## 🆘 Поддержка

Если возникли проблемы:
1. Проверьте логи в Railway
2. Убедитесь, что все переменные окружения установлены
3. Проверьте health check endpoint
4. При необходимости откатитесь к старой версии
