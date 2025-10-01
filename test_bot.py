#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Локальный тестовый бот для разработки
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Настройка логирования для тестирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('test_bot.log')
    ]
)

logger = logging.getLogger(__name__)

def setup_test_environment():
    """Настройка тестового окружения"""
    
    # Проверяем наличие тестового токена
    test_token = os.getenv('TEST_BOT_TOKEN')
    if not test_token:
        print("❌ TEST_BOT_TOKEN не найден!")
        print("📝 Создайте тестового бота через @BotFather и добавьте токен в .env файл:")
        print("   TEST_BOT_TOKEN=your_test_bot_token_here")
        return False
    
    # Устанавливаем тестовый токен как основной
    os.environ['BOT_TOKEN'] = test_token
    
    # Настройки для локального тестирования
    os.environ['CACHE_DURATION'] = '10'  # Короткий кэш для тестирования
    os.environ['RATE_LIMIT_COOLDOWN'] = '5'  # Короткий rate limit
    os.environ['DATABASE_PATH'] = 'test_bot_database.db'  # Отдельная БД для тестов
    os.environ['CACHE_DIRECTORY'] = 'test_cache'  # Отдельный кэш для тестов
    
    print("✅ Тестовое окружение настроено")
    print(f"🤖 Тестовый бот: {test_token[:10]}...")
    print(f"💾 Тестовая БД: test_bot_database.db")
    print(f"📁 Тестовый кэш: test_cache/")
    
    return True

def main():
    """Запуск тестового бота"""
    
    print("🧪 Запуск локального тестового бота...")
    
    if not setup_test_environment():
        return
    
    try:
        # Импортируем основной код бота
        from telegram_bot import main as bot_main
        
        print("🚀 Запуск бота...")
        print("📱 Бот готов к тестированию!")
        print("🛑 Для остановки нажмите Ctrl+C")
        
        # Запускаем бота
        bot_main()
        
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Ошибка запуска тестового бота: {e}")
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    main()
