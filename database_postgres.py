#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль для работы с базой данных PostgreSQL
"""

import psycopg2
import psycopg2.extras
import logging
import os
from datetime import datetime
from typing import Optional, Dict, List, Tuple, Union, Any
import json
from exceptions import DatabaseError

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Менеджер базы данных PostgreSQL"""
    
    def __init__(self):
        """Инициализация подключения к PostgreSQL"""
        self.connection_string = self._get_connection_string()
        self.init_database()
    
    def _get_connection_string(self) -> str:
        """Получить строку подключения к PostgreSQL"""
        # Для Railway
        if os.getenv('DATABASE_URL'):
            return os.getenv('DATABASE_URL')
        
        # Для локальной разработки
        return "postgresql://postgres:password@localhost:5432/telegram_bot"
    
    @contextmanager
    def get_connection(self):
        """Контекстный менеджер для подключения к БД"""
        conn = None
        try:
            conn = psycopg2.connect(self.connection_string)
            conn.autocommit = False
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Ошибка подключения к PostgreSQL: {e}")
            raise DatabaseError(f"Ошибка подключения к БД: {e}")
        finally:
            if conn:
                conn.close()
    
    def init_database(self) -> None:
        """Инициализация таблиц базы данных"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Создаем таблицу пользователей
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id BIGINT PRIMARY KEY,
                        username VARCHAR(255),
                        first_name VARCHAR(255),
                        last_activity_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        total_commands INTEGER DEFAULT 0,
                        last_rate_request TIMESTAMP
                    )
                ''')
                
                # Создаем таблицу логов команд
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS commands_log (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        command_name VARCHAR(255) NOT NULL,
                        message_text TEXT,
                        response_time REAL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')
                
                # Создаем таблицу отслеживания криптовалют
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS crypto_tracking (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        crypto VARCHAR(10) NOT NULL,
                        threshold REAL DEFAULT 5.0,
                        is_active BOOLEAN DEFAULT TRUE,
                        last_price REAL,
                        last_notification TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id),
                        UNIQUE(user_id, crypto)
                    )
                ''')
                
                # Создаем индексы для оптимизации
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_crypto_tracking_user_active 
                    ON crypto_tracking(user_id, is_active)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_crypto_tracking_active 
                    ON crypto_tracking(is_active) WHERE is_active = TRUE
                ''')
                
                conn.commit()
                logger.info("База данных PostgreSQL инициализирована успешно")
                
        except Exception as e:
            logger.error(f"Ошибка инициализации PostgreSQL: {e}")
            raise DatabaseError(f"Ошибка инициализации БД: {e}")
    
    def add_or_update_user(self, user_data: Dict[str, Any]) -> bool:
        """Добавить или обновить пользователя"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO users (user_id, username, first_name, last_activity_date, total_commands)
                    VALUES (%s, %s, %s, CURRENT_TIMESTAMP, 0)
                    ON CONFLICT (user_id) 
                    DO UPDATE SET 
                        username = EXCLUDED.username,
                        first_name = EXCLUDED.first_name,
                        last_activity_date = CURRENT_TIMESTAMP
                ''', (
                    user_data['user_id'],
                    user_data.get('username'),
                    user_data.get('first_name')
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Ошибка добавления/обновления пользователя: {e}")
            return False
    
    def log_command(self, user_id: int, command_name: str, message_text: str = "", response_time: float = 0) -> bool:
        """Записать команду в лог"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Добавляем запись в лог команд
                cursor.execute('''
                    INSERT INTO commands_log 
                    (user_id, command_name, message_text, response_time)
                    VALUES (%s, %s, %s, %s)
                ''', (user_id, command_name, message_text, response_time))
                
                # Обновляем счетчик команд у пользователя
                cursor.execute('''
                    UPDATE users 
                    SET total_commands = total_commands + 1,
                        last_activity_date = CURRENT_TIMESTAMP
                    WHERE user_id = %s
                ''', (user_id,))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Ошибка записи команды: {e}")
            return False
    
    def get_user_stats(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получить статистику пользователя"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                
                cursor.execute('''
                    SELECT 
                        u.user_id,
                        u.username,
                        u.first_name,
                        u.total_commands,
                        u.last_activity_date,
                        COUNT(ct.id) as active_trackings
                    FROM users u
                    LEFT JOIN crypto_tracking ct ON u.user_id = ct.user_id AND ct.is_active = TRUE
                    WHERE u.user_id = %s
                    GROUP BY u.user_id, u.username, u.first_name, u.total_commands, u.last_activity_date
                ''', (user_id,))
                
                result = cursor.fetchone()
                if result:
                    return dict(result)
                return None
                
        except Exception as e:
            logger.error(f"Ошибка получения статистики пользователя: {e}")
            return None
    
    def get_tracking_settings(self, user_id: int) -> List[Dict[str, Any]]:
        """Получить настройки отслеживания пользователя"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                
                cursor.execute('''
                    SELECT crypto, threshold, is_active, last_price, last_notification
                    FROM crypto_tracking
                    WHERE user_id = %s
                    ORDER BY crypto
                ''', (user_id,))
                
                results = cursor.fetchall()
                return [dict(row) for row in results]
                
        except Exception as e:
            logger.error(f"Ошибка получения настроек отслеживания: {e}")
            return []
    
    def toggle_crypto_tracking(self, user_id: int, crypto: str) -> bool:
        """Переключить отслеживание криптовалюты"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Проверяем, существует ли запись
                cursor.execute('''
                    SELECT is_active FROM crypto_tracking
                    WHERE user_id = %s AND crypto = %s
                ''', (user_id, crypto))
                
                result = cursor.fetchone()
                
                if result:
                    # Переключаем существующую запись
                    new_status = not bool(result[0])
                    logger.info(f"🔄 Переключаем отслеживание {crypto} для пользователя {user_id}: {result[0]} -> {new_status}")
                    cursor.execute('''
                        UPDATE crypto_tracking
                        SET is_active = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = %s AND crypto = %s
                    ''', (new_status, user_id, crypto))
                else:
                    # Создаем новую запись с порогом по умолчанию
                    logger.info(f"➕ Создаем новое отслеживание {crypto} для пользователя {user_id} с порогом 5.0%")
                    cursor.execute('''
                        INSERT INTO crypto_tracking (user_id, crypto, is_active, threshold)
                        VALUES (%s, %s, TRUE, 5.0)
                    ''', (user_id, crypto))
                    new_status = True
                
                conn.commit()
                logger.info(f"✅ Отслеживание {crypto} для пользователя {user_id}: {'активно' if new_status else 'неактивно'}")
                
                # Проверяем, что запись действительно создалась
                cursor.execute('''
                    SELECT user_id, crypto, is_active, threshold FROM crypto_tracking
                    WHERE user_id = %s AND crypto = %s
                ''', (user_id, crypto))
                check_result = cursor.fetchone()
                logger.info(f"🔍 Проверка записи после создания: {check_result}")
                
                # Дополнительная проверка - считаем все записи
                cursor.execute('SELECT COUNT(*) FROM crypto_tracking')
                total_after = cursor.fetchone()[0]
                logger.info(f"📊 Всего записей в БД после создания: {total_after}")
                
                return new_status
                
        except Exception as e:
            logger.error(f"Ошибка переключения отслеживания: {e}")
            return False
    
    def set_crypto_threshold(self, user_id: int, crypto: str, threshold: float) -> bool:
        """Установить порог для конкретной криптовалюты"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE crypto_tracking
                    SET threshold = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s AND crypto = %s
                ''', (threshold, user_id, crypto))
                
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Ошибка установки порога: {e}")
            return False
    
    def get_active_trackings(self) -> List[Dict[str, Any]]:
        """Получить все активные отслеживания для проверки уведомлений"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cursor.execute('''
                    SELECT user_id, crypto, threshold, last_price, last_notification
                    FROM crypto_tracking
                    WHERE is_active = TRUE
                    ORDER BY user_id, crypto
                ''')
                
                rows = cursor.fetchall()
                logger.info(f"🔍 Найдено {len(rows)} активных отслеживаний в базе данных")
                
                # Дополнительная отладка
                if len(rows) == 0:
                    # Проверяем, есть ли вообще записи в таблице
                    cursor.execute('SELECT COUNT(*) FROM crypto_tracking')
                    total_count = cursor.fetchone()[0]
                    logger.info(f"📊 Всего записей в crypto_tracking: {total_count}")
                    
                    if total_count > 0:
                        # Проверяем, какие записи есть
                        cursor.execute('SELECT user_id, crypto, is_active FROM crypto_tracking LIMIT 5')
                        sample_rows = cursor.fetchall()
                        logger.info(f"📋 Примеры записей: {sample_rows}")
                
                result = [dict(row) for row in rows]
                return result
                
        except Exception as e:
            logger.error(f"Ошибка получения активных отслеживаний: {e}")
            return []
    
    def update_crypto_price(self, user_id: int, crypto: str, price: float) -> bool:
        """Обновить цену криптовалюты для пользователя"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE crypto_tracking
                    SET last_price = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s AND crypto = %s AND is_active = TRUE
                ''', (price, user_id, crypto))
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Ошибка обновления цены для {crypto}: {e}")
            return False
