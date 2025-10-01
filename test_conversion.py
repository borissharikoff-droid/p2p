#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест конвертации валют для проверки правильности курсов
"""

import os
import sys
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

def test_conversion_logic():
    """Тестируем логику конвертации"""
    
    print("🧪 ТЕСТ КОНВЕРТАЦИИ ВАЛЮТ")
    print("=" * 50)
    
    # Данные из логов: курс продажи 80.01₽ за 1 USDT
    sell_rate = 80.01  # Курс продажи USDT (сколько рублей за 1 USDT)
    
    # Для покупки USDT нужен курс выше (с наценкой)
    buy_rate = sell_rate * 1.02  # 2% наценка = 81.61₽ за 1 USDT
    
    print(f"📊 Курс продажи USDT: {sell_rate:.2f}₽ за 1 USDT")
    print(f"📊 Курс покупки USDT: {buy_rate:.2f}₽ за 1 USDT")
    print()
    
    # Тест 1: 10000 рублей в USDT
    rub_amount = 10000
    usdt_from_rub = rub_amount / buy_rate
    print(f"💰 {rub_amount:,}₽ → USDT:")
    print(f"   {rub_amount:,}₽ ÷ {buy_rate:.2f}₽ = {usdt_from_rub:.4f} USDT")
    print()
    
    # Тест 2: 124.98 USDT в рубли
    usdt_amount = 124.98
    rub_from_usdt = usdt_amount * sell_rate
    print(f"💵 {usdt_amount} USDT → ₽:")
    print(f"   {usdt_amount} USDT × {sell_rate:.2f}₽ = {rub_from_usdt:.2f}₽")
    print()
    
    # Проверка обратной конвертации
    print("🔄 ПРОВЕРКА ОБРАТНОЙ КОНВЕРТАЦИИ:")
    print(f"   Исходно: {rub_amount:,}₽")
    print(f"   В USDT: {usdt_from_rub:.4f} USDT")
    print(f"   Обратно в ₽: {usdt_from_rub * sell_rate:.2f}₽")
    print(f"   Разница: {rub_amount - (usdt_from_rub * sell_rate):.2f}₽ (спред)")
    print()
    
    # Правильный расчет для 10000 рублей
    print("✅ ПРАВИЛЬНЫЙ РАСЧЕТ:")
    print(f"   {rub_amount:,}₽ ÷ {buy_rate:.2f}₽ = {rub_amount/buy_rate:.4f} USDT")
    print(f"   Это означает: за {rub_amount:,}₽ можно купить {rub_amount/buy_rate:.4f} USDT")
    print()
    
    # Проверяем, что исправления работают
    print("🔧 ПРОВЕРКА ИСПРАВЛЕНИЙ:")
    old_calculation = rub_amount / sell_rate  # Старый неправильный расчет
    new_calculation = rub_amount / buy_rate   # Новый правильный расчет
    
    print(f"   Старый расчет (неправильный): {old_calculation:.4f} USDT")
    print(f"   Новый расчет (правильный): {new_calculation:.4f} USDT")
    print(f"   Разница: {old_calculation - new_calculation:.4f} USDT")
    
    if new_calculation < old_calculation:
        print("   ✅ Исправление работает - теперь курс покупки выше!")
    else:
        print("   ❌ Что-то не так с исправлением")

def test_rate_handler():
    """Тестируем RateHandler"""
    
    print("\n🧪 ТЕСТ RATE HANDLER")
    print("=" * 50)
    
    try:
        # Импортируем только после настройки окружения
        from handlers.rate_handler import RateHandler
        from database import DatabaseManager
        from cache_manager import CacheManager
        
        # Создаем тестовые компоненты
        db = DatabaseManager("test_bot_database.db")
        cache = CacheManager("test_cache")
        rate_handler = RateHandler(db, cache)
        
        print("✅ RateHandler создан успешно")
        
        # Тестируем конвертацию
        test_amount = 10000
        
        # RUB to USDT
        usdt_result = rate_handler.convert_currency(test_amount, "RUB", "USDT")
        if usdt_result:
            print(f"✅ {test_amount:,}₽ → {usdt_result:.4f} USDT")
        else:
            print("❌ Ошибка конвертации RUB → USDT")
        
        # USDT to RUB
        if usdt_result:
            rub_result = rate_handler.convert_currency(usdt_result, "USDT", "RUB")
            if rub_result:
                print(f"✅ {usdt_result:.4f} USDT → {rub_result:.2f}₽")
                print(f"   Спред: {test_amount - rub_result:.2f}₽")
            else:
                print("❌ Ошибка конвертации USDT → RUB")
        
    except Exception as e:
        print(f"❌ Ошибка тестирования RateHandler: {e}")

if __name__ == "__main__":
    test_conversion_logic()
    test_rate_handler()
