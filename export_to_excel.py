#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для экспорта базы данных Telegram бота в Excel формат
"""

import sqlite3
import pandas as pd
from datetime import datetime
import os


def export_database_to_excel():
    """Экспорт всех таблиц базы данных в Excel файл"""
    
    try:
        # Подключаемся к базе данных
        conn = sqlite3.connect('bot_database.db')
        
        # Создаем имя файла с текущей датой и временем
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        excel_filename = f'telegram_bot_database_{timestamp}.xlsx'
        
        print("📊 ЭКСПОРТ БАЗЫ ДАННЫХ В EXCEL")
        print("=" * 50)
        print(f"📁 Файл: {excel_filename}")
        print()
        
        # Создаем Excel writer
        with pd.ExcelWriter(excel_filename, engine='openpyxl') as writer:
            
            # 1. Таблица пользователей
            print("👥 Экспорт пользователей...")
            users_df = pd.read_sql_query("SELECT * FROM users", conn)
            users_df.to_excel(writer, sheet_name='Пользователи', index=False)
            print(f"   ✅ Экспортировано {len(users_df)} пользователей")
            
            # 2. Таблица команд
            print("💬 Экспорт команд...")
            commands_df = pd.read_sql_query("SELECT * FROM commands_log", conn)
            commands_df.to_excel(writer, sheet_name='Команды', index=False)
            print(f"   ✅ Экспортировано {len(commands_df)} команд")
            
            # 3. Таблица запросов курсов
            print("💰 Экспорт запросов курсов...")
            exchange_df = pd.read_sql_query("SELECT * FROM exchange_requests", conn)
            exchange_df.to_excel(writer, sheet_name='Запросы курсов', index=False)
            print(f"   ✅ Экспортировано {len(exchange_df)} запросов")
            
            # 4. Таблица сессий
            print("⏱️ Экспорт сессий...")
            sessions_df = pd.read_sql_query("SELECT * FROM user_sessions", conn)
            sessions_df.to_excel(writer, sheet_name='Сессии', index=False)
            print(f"   ✅ Экспортировано {len(sessions_df)} сессий")
            
            # 5. Таблица аналитики
            print("📈 Экспорт аналитики...")
            analytics_df = pd.read_sql_query("SELECT * FROM user_analytics", conn)
            analytics_df.to_excel(writer, sheet_name='Аналитика', index=False)
            print(f"   ✅ Экспортировано {len(analytics_df)} записей аналитики")
            
            # 6. Сводная статистика
            print("📊 Создание сводной статистики...")
            stats_data = []
            
            # Общая статистика
            cursor = conn.cursor()
            
            # Количество пользователей
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]
            
            # Новые пользователи сегодня
            cursor.execute("SELECT COUNT(*) FROM users WHERE DATE(first_contact_date) = DATE('now')")
            new_today = cursor.fetchone()[0]
            
            # Активные пользователи сегодня
            cursor.execute("SELECT COUNT(*) FROM users WHERE DATE(last_activity_date) = DATE('now')")
            active_today = cursor.fetchone()[0]
            
            # Общее количество команд
            cursor.execute("SELECT COUNT(*) FROM commands_log")
            total_commands = cursor.fetchone()[0]
            
            # Общее количество запросов курсов
            cursor.execute("SELECT COUNT(*) FROM exchange_requests")
            total_requests = cursor.fetchone()[0]
            
            # Статистика по командам
            cursor.execute("""
                SELECT command_name, COUNT(*) as count, AVG(response_time) as avg_time
                FROM commands_log 
                GROUP BY command_name 
                ORDER BY count DESC
            """)
            command_stats = cursor.fetchall()
            
            # Создаем DataFrame для статистики
            stats_data = [
                ['Метрика', 'Значение'],
                ['Всего пользователей', total_users],
                ['Новых пользователей сегодня', new_today],
                ['Активных пользователей сегодня', active_today],
                ['Всего команд', total_commands],
                ['Всего запросов курсов', total_requests],
                ['', ''],
                ['Статистика по командам:', ''],
            ]
            
            for command, count, avg_time in command_stats:
                stats_data.append([f'Команда {command}', f'{count} раз (ср. время: {avg_time:.2f} сек)'])
            
            stats_df = pd.DataFrame(stats_data[1:], columns=stats_data[0])
            stats_df.to_excel(writer, sheet_name='Статистика', index=False)
            print("   ✅ Создана сводная статистика")
        
        conn.close()
        
        # Проверяем размер файла
        file_size = os.path.getsize(excel_filename)
        file_size_mb = file_size / (1024 * 1024)
        
        print()
        print("🎉 ЭКСПОРТ ЗАВЕРШЕН УСПЕШНО!")
        print("=" * 50)
        print(f"📁 Файл: {excel_filename}")
        print(f"📏 Размер: {file_size_mb:.2f} MB")
        print(f"📊 Листов: 6 (Пользователи, Команды, Запросы курсов, Сессии, Аналитика, Статистика)")
        print()
        print("💡 Файл готов для открытия в Microsoft Excel или Google Sheets")
        
        return excel_filename
        
    except Exception as e:
        print(f"❌ Ошибка при экспорте: {e}")
        return None


def export_specific_table_to_excel(table_name: str):
    """Экспорт конкретной таблицы в Excel"""
    
    try:
        conn = sqlite3.connect('bot_database.db')
        
        # Проверяем, существует ли таблица
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        if not cursor.fetchone():
            print(f"❌ Таблица '{table_name}' не найдена")
            return None
        
        # Получаем данные
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
        
        # Создаем имя файла
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        excel_filename = f'{table_name}_{timestamp}.xlsx'
        
        # Экспортируем
        df.to_excel(excel_filename, index=False, sheet_name=table_name)
        
        conn.close()
        
        print(f"✅ Таблица '{table_name}' экспортирована в {excel_filename}")
        print(f"📊 Записей: {len(df)}")
        
        return excel_filename
        
    except Exception as e:
        print(f"❌ Ошибка экспорта таблицы '{table_name}': {e}")
        return None


if __name__ == "__main__":
    print("Выберите тип экспорта:")
    print("1. Полный экспорт всех таблиц в один Excel файл")
    print("2. Экспорт конкретной таблицы")
    print("3. Показать доступные таблицы")
    
    choice = input("\nВведите номер (1-3): ").strip()
    
    if choice == "1":
        export_database_to_excel()
    elif choice == "2":
        # Показываем доступные таблицы
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        print("\nДоступные таблицы:")
        for i, table in enumerate(tables, 1):
            print(f"{i}. {table}")
        
        table_choice = input("\nВведите номер таблицы: ").strip()
        try:
            table_index = int(table_choice) - 1
            if 0 <= table_index < len(tables):
                export_specific_table_to_excel(tables[table_index])
            else:
                print("❌ Неверный номер таблицы")
        except ValueError:
            print("❌ Введите корректный номер")
    elif choice == "3":
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        print("\n📋 ДОСТУПНЫЕ ТАБЛИЦЫ:")
        print("-" * 30)
        for table in tables:
            print(f"• {table}")
    else:
        print("❌ Неверный выбор. Запускаю полный экспорт...")
        export_database_to_excel()
