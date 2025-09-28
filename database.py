#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль для работы с базой данных SQLite
"""

import sqlite3
import logging
from datetime import datetime
from typing import Optional, Dict, List, Tuple, Union, Any
import json
from exceptions import DatabaseError

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Менеджер базы данных для Telegram бота"""
    
    def __init__(self, db_path: str = "bot_database.db"):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self) -> sqlite3.Connection:
        """Получить соединение с базой данных"""
        return sqlite3.connect(self.db_path)
    
    def init_database(self):
        """Инициализация базы данных и создание таблиц"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Включаем WAL режим для лучшей производительности
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.execute("PRAGMA cache_size=10000")
                cursor.execute("PRAGMA temp_store=MEMORY")
                
                # Таблица пользователей (упрощенная)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        last_activity_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        total_requests INTEGER DEFAULT 0,
                        last_rate_request TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Таблица запросов курсов (упрощенная)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS exchange_requests (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        request_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        avg_rate REAL,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')

                # Таблица кошельков пользователя
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_wallets (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        address TEXT NOT NULL,
                        label TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')
                
                # Таблица лога команд
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS commands_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        command_name TEXT NOT NULL,
                        message_text TEXT,
                        response_time REAL DEFAULT 0,
                        command_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')
                
                # Таблица сессий пользователей
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        username TEXT,
                        session_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        session_end TIMESTAMP,
                        session_duration REAL,
                        commands_in_session INTEGER DEFAULT 0,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')
                
                # Таблица аналитики пользователей
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_analytics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        daily_requests INTEGER DEFAULT 0,
                        weekly_requests INTEGER DEFAULT 0,
                        monthly_requests INTEGER DEFAULT 0,
                        favorite_command TEXT,
                        last_session_duration REAL,
                        avg_session_duration REAL,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')
                
                # Таблица отслеживания курсов криптовалют
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS crypto_tracking (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        crypto TEXT NOT NULL,
                        threshold REAL DEFAULT 5.0,
                        is_active BOOLEAN DEFAULT 1,
                        last_price REAL,
                        last_notification TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id),
                        UNIQUE(user_id, crypto)
                    )
                ''')
                
                # Таблица истории цен криптовалют
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS crypto_price_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        crypto TEXT NOT NULL,
                        price REAL NOT NULL,
                        price_usd REAL,
                        price_rub REAL,
                        change_24h REAL,
                        volume_24h REAL,
                        market_cap REAL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Миграция: добавляем новые колонки если их нет
                try:
                    cursor.execute('ALTER TABLE users ADD COLUMN last_rate_request TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
                    logger.info("Добавлена колонка last_rate_request")
                except sqlite3.OperationalError:
                    pass  # Колонка уже существует
                
                try:
                    cursor.execute('ALTER TABLE users ADD COLUMN total_commands INTEGER DEFAULT 0')
                    logger.info("Добавлена колонка total_commands")
                except sqlite3.OperationalError:
                    pass  # Колонка уже существует
                
                # Миграция: добавляем колонку username в user_sessions если её нет
                try:
                    cursor.execute('ALTER TABLE user_sessions ADD COLUMN username TEXT')
                    logger.info("Добавлена колонка username в user_sessions")
                except sqlite3.OperationalError:
                    pass  # Колонка уже существует
                
                # Создаем индексы для быстрого поиска (только если колонки существуют)
                try:
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_activity ON users(last_activity_date)')
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_rate_request ON users(last_rate_request)')
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_exchange_requests_timestamp ON exchange_requests(request_timestamp)')
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_exchange_requests_user ON exchange_requests(user_id)')
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_crypto_tracking_user ON crypto_tracking(user_id)')
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_crypto_tracking_active ON crypto_tracking(is_active)')
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_crypto_price_history_crypto ON crypto_price_history(crypto)')
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_crypto_price_history_timestamp ON crypto_price_history(timestamp)')
                except sqlite3.OperationalError as e:
                    logger.warning(f"Не удалось создать некоторые индексы: {e}")
                
                conn.commit()
                logger.info("База данных инициализирована успешно")
                
        except Exception as e:
            logger.error(f"Ошибка инициализации базы данных: {e}")
            raise
    
    def add_or_update_user(self, user_data: Dict) -> bool:
        """Добавить или обновить пользователя (оптимизированная версия)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Используем INSERT OR REPLACE для атомарной операции
                cursor.execute('''
                    INSERT OR REPLACE INTO users 
                    (user_id, username, first_name, last_activity_date, last_rate_request)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP, NULL)
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
                    VALUES (?, ?, ?, ?)
                ''', (user_id, command_name, message_text, response_time))
                
                # Обновляем счетчик команд у пользователя
                cursor.execute('''
                    UPDATE users SET 
                        total_commands = total_commands + 1,
                        last_activity_date = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (user_id,))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Ошибка записи команды: {e}")
            return False
    
    def log_exchange_request(self, user_id: int, exchange_data: Dict) -> bool:
        """Записать запрос курса (оптимизированная версия)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Добавляем запись о запросе курса (только средний курс)
                cursor.execute('''
                    INSERT INTO exchange_requests 
                    (user_id, avg_rate)
                    VALUES (?, ?)
                ''', (user_id, exchange_data.get('avg_rate')))
                
                # Обновляем счетчик запросов и время последнего запроса
                cursor.execute('''
                    UPDATE users SET 
                        total_requests = total_requests + 1,
                        last_activity_date = CURRENT_TIMESTAMP,
                        last_rate_request = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (user_id,))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Ошибка записи запроса курса: {e}")
            return False
    
    def start_session(self, user_id: int, username: str = None) -> bool:
        """Начать сессию пользователя"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO user_sessions (user_id, username, session_start)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                ''', (user_id, username))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Ошибка начала сессии: {e}")
            return False
    
    def end_session(self, user_id: int) -> bool:
        """Завершить сессию пользователя"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Находим последнюю незавершенную сессию
                cursor.execute('''
                    SELECT id, session_start FROM user_sessions 
                    WHERE user_id = ? AND session_end IS NULL 
                    ORDER BY session_start DESC LIMIT 1
                ''', (user_id,))
                
                session = cursor.fetchone()
                if session:
                    session_id, session_start = session
                    
                    # Вычисляем продолжительность сессии
                    cursor.execute('''
                        SELECT (julianday('now') - julianday(?)) * 24 * 60 * 60
                    ''', (session_start,))
                    
                    duration = cursor.fetchone()[0]
                    
                    # Подсчитываем команды в сессии
                    cursor.execute('''
                        SELECT COUNT(*) FROM commands_log 
                        WHERE user_id = ? AND command_timestamp >= ?
                    ''', (user_id, session_start))
                    
                    commands_count = cursor.fetchone()[0]
                    
                    # Обновляем сессию
                    cursor.execute('''
                        UPDATE user_sessions SET 
                            session_end = CURRENT_TIMESTAMP,
                            session_duration = ?,
                            commands_in_session = ?
                        WHERE id = ?
                    ''', (duration, commands_count, session_id))
                    
                    # Обновляем аналитику
                    self.update_user_analytics(user_id, duration)
                    
                    conn.commit()
                    return True
                
                return False
                
        except Exception as e:
            logger.error(f"Ошибка завершения сессии: {e}")
            return False
    
    def update_user_analytics(self, user_id: int, session_duration: float):
        """Обновить аналитику пользователя"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Получаем текущую аналитику
                cursor.execute("SELECT * FROM user_analytics WHERE user_id = ?", (user_id,))
                analytics = cursor.fetchone()
                
                if analytics:
                    # Обновляем существующую запись
                    cursor.execute('''
                        UPDATE user_analytics SET 
                            last_session_duration = ?,
                            avg_session_duration = (avg_session_duration + ?) / 2,
                            last_updated = CURRENT_TIMESTAMP
                        WHERE user_id = ?
                    ''', (session_duration, session_duration, user_id))
                else:
                    # Создаем новую запись
                    cursor.execute('''
                        INSERT INTO user_analytics 
                        (user_id, last_session_duration, avg_session_duration)
                        VALUES (?, ?, ?)
                    ''', (user_id, session_duration, session_duration))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Ошибка обновления аналитики: {e}")
    
    def get_user_stats(self, user_id: int) -> Optional[Dict]:
        """Получить статистику пользователя"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Основная информация о пользователе
                cursor.execute('''
                    SELECT u.*, a.daily_requests, a.weekly_requests, a.monthly_requests,
                           a.favorite_command, a.last_session_duration, a.avg_session_duration
                    FROM users u
                    LEFT JOIN user_analytics a ON u.user_id = a.user_id
                    WHERE u.user_id = ?
                ''', (user_id,))
                
                user_data = cursor.fetchone()
                if user_data:
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, user_data))
                
                return None
                
        except Exception as e:
            logger.error(f"Ошибка получения статистики пользователя: {e}")
            return None
    
    def get_bot_statistics(self) -> Dict:
        """Получить общую статистику бота"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                stats = {}
                
                # Общее количество пользователей
                cursor.execute("SELECT COUNT(*) FROM users")
                stats['total_users'] = cursor.fetchone()[0]
                
                # Новые пользователи за сегодня
                cursor.execute('''
                    SELECT COUNT(*) FROM users 
                    WHERE DATE(first_contact_date) = DATE('now')
                ''')
                stats['new_users_today'] = cursor.fetchone()[0]
                
                # Активные пользователи за сегодня
                cursor.execute('''
                    SELECT COUNT(*) FROM users 
                    WHERE DATE(last_activity_date) = DATE('now')
                ''')
                stats['active_users_today'] = cursor.fetchone()[0]
                
                # Общее количество команд
                cursor.execute("SELECT COUNT(*) FROM commands_log")
                stats['total_commands'] = cursor.fetchone()[0]
                
                # Общее количество запросов курсов
                cursor.execute("SELECT COUNT(*) FROM exchange_requests")
                stats['total_exchange_requests'] = cursor.fetchone()[0]
                
                # Самая популярная команда
                cursor.execute('''
                    SELECT command_name, COUNT(*) as count 
                    FROM commands_log 
                    GROUP BY command_name 
                    ORDER BY count DESC 
                    LIMIT 1
                ''')
                popular_command = cursor.fetchone()
                if popular_command:
                    stats['most_popular_command'] = popular_command[0]
                    stats['most_popular_command_count'] = popular_command[1]
                
                return stats
                
        except Exception as e:
            logger.error(f"Ошибка получения статистики бота: {e}")
            return {}
    
    def can_user_request_rate(self, user_id: int, cooldown_seconds: int = 30) -> bool:
        """Проверить, может ли пользователь запросить курс (rate limiting)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT last_rate_request FROM users 
                    WHERE user_id = ?
                ''', (user_id,))
                
                result = cursor.fetchone()
                if not result:
                    return True
                
                last_request = result[0]
                if not last_request:
                    return True
                
                # Проверяем, прошло ли достаточно времени
                cursor.execute('''
                    SELECT (julianday('now') - julianday(?)) * 24 * 60 * 60
                ''', (last_request,))
                
                seconds_passed = cursor.fetchone()[0]
                return seconds_passed >= cooldown_seconds
                
        except Exception as e:
            logger.error(f"Ошибка проверки rate limiting: {e}")
            return True  # В случае ошибки разрешаем запрос
    
    def cleanup_old_data(self, days_to_keep: int = 7):
        """Очистка старых данных для экономии места"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Удаляем старые записи запросов курсов
                cursor.execute('''
                    DELETE FROM exchange_requests 
                    WHERE request_timestamp < datetime('now', '-{} days')
                '''.format(days_to_keep))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                if deleted_count > 0:
                    logger.info(f"Удалено {deleted_count} старых записей запросов курсов")
                
                return deleted_count
                
        except Exception as e:
            logger.error(f"Ошибка очистки старых данных: {e}")
            return 0
    
    def close(self):
        """Закрыть соединение с базой данных"""
        pass  # SQLite автоматически закрывает соединения

    # ------------------- WALLET CRUD -------------------
    def add_wallet(self, user_id: int, address: str, label: Optional[str]) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO user_wallets (user_id, address, label)
                    VALUES (?, ?, ?)
                ''', (user_id, address, label))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка добавления кошелька: {e}")
            return False

    def list_wallets(self, user_id: int) -> List[Dict]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, address, COALESCE(label, '') as label
                    FROM user_wallets
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                ''', (user_id,))
                rows = cursor.fetchall()
                return [
                    { 'id': r[0], 'address': r[1], 'label': r[2] }
                    for r in rows
                ]
        except Exception as e:
            logger.error(f"Ошибка получения списка кошельков: {e}")
            return []

    def update_wallet(self, user_id: int, wallet_id: int, new_address: Optional[str], new_label: Optional[str]) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if new_address is not None and new_label is not None:
                    cursor.execute('''
                        UPDATE user_wallets
                        SET address = ?, label = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ? AND user_id = ?
                    ''', (new_address, new_label, wallet_id, user_id))
                elif new_address is not None:
                    cursor.execute('''
                        UPDATE user_wallets
                        SET address = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ? AND user_id = ?
                    ''', (new_address, wallet_id, user_id))
                elif new_label is not None:
                    cursor.execute('''
                        UPDATE user_wallets
                        SET label = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ? AND user_id = ?
                    ''', (new_label, wallet_id, user_id))
                else:
                    return True
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка обновления кошелька: {e}")
            return False

    def get_wallet(self, user_id: int, wallet_id: int) -> Optional[Dict]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, address, COALESCE(label, '') as label
                    FROM user_wallets
                    WHERE id = ? AND user_id = ?
                ''', (wallet_id, user_id))
                row = cursor.fetchone()
                if row:
                    return {
                        'id': row[0],
                        'address': row[1], 
                        'label': row[2]
                    }
                return None
        except Exception as e:
            logger.error(f"Ошибка получения кошелька: {e}")
            return None

    def delete_wallet(self, user_id: int, wallet_id: int) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM user_wallets WHERE id = ? AND user_id = ?
                ''', (wallet_id, user_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка удаления кошелька: {e}")
            return False

    # ------------------- CRYPTO TRACKING METHODS -------------------
    
    def get_tracking_settings(self, user_id: int) -> List[Dict]:
        """Получить настройки отслеживания пользователя"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT crypto, threshold, is_active, last_price, last_notification
                    FROM crypto_tracking
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                ''', (user_id,))
                rows = cursor.fetchall()
                return [
                    {
                        'crypto': row[0],
                        'threshold': row[1],
                        'is_active': bool(row[2]),
                        'last_price': row[3],
                        'last_notification': row[4]
                    }
                    for row in rows
                ]
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
                    WHERE user_id = ? AND crypto = ?
                ''', (user_id, crypto))
                
                result = cursor.fetchone()
                
                if result:
                    # Переключаем существующую запись
                    new_status = not bool(result[0])
                    cursor.execute('''
                        UPDATE crypto_tracking
                        SET is_active = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = ? AND crypto = ?
                    ''', (new_status, user_id, crypto))
                else:
                    # Создаем новую запись
                    cursor.execute('''
                        INSERT INTO crypto_tracking (user_id, crypto, is_active)
                        VALUES (?, ?, 1)
                    ''', (user_id, crypto))
                    new_status = True
                
                conn.commit()
                return new_status
                
        except Exception as e:
            logger.error(f"Ошибка переключения отслеживания: {e}")
            return False
    
    def set_tracking_threshold(self, user_id: int, threshold: float) -> bool:
        """Установить порог для всех активных отслеживаний пользователя"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE crypto_tracking
                    SET threshold = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND is_active = 1
                ''', (threshold, user_id))
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Ошибка установки порога: {e}")
            return False
    
    def set_crypto_threshold(self, user_id: int, crypto: str, threshold: float) -> bool:
        """Установить порог для конкретной криптовалюты"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE crypto_tracking
                    SET threshold = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND crypto = ?
                ''', (threshold, user_id, crypto))
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Ошибка установки порога для {crypto}: {e}")
            return False
    
    def update_crypto_price(self, user_id: int, crypto: str, price: float) -> bool:
        """Обновить цену криптовалюты для пользователя"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE crypto_tracking
                    SET last_price = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND crypto = ? AND is_active = 1
                ''', (price, user_id, crypto))
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Ошибка обновления цены для {crypto}: {e}")
            return False
    
    def update_tracking_price(self, user_id: int, crypto: str, price: float) -> bool:
        """Обновить цену отслеживания (аналог update_crypto_price)"""
        return self.update_crypto_price(user_id, crypto, price)
    
    def toggle_all_tracking(self, user_id: int) -> bool:
        """Переключить все отслеживания пользователя"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Получаем текущий статус
                cursor.execute('''
                    SELECT COUNT(*) FROM crypto_tracking
                    WHERE user_id = ? AND is_active = 1
                ''', (user_id,))
                
                active_count = cursor.fetchone()[0]
                
                # Если есть активные - отключаем все, если нет - включаем все
                new_status = active_count == 0
                
                cursor.execute('''
                    UPDATE crypto_tracking
                    SET is_active = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (new_status, user_id))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Ошибка переключения всех отслеживаний: {e}")
            return False
    
    def add_crypto_price(self, crypto: str, price: float, price_usd: float = None, 
                        price_rub: float = None, change_24h: float = None, 
                        volume_24h: float = None, market_cap: float = None) -> bool:
        """Добавить цену криптовалюты в историю"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO crypto_price_history 
                    (crypto, price, price_usd, price_rub, change_24h, volume_24h, market_cap)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (crypto, price, price_usd, price_rub, change_24h, volume_24h, market_cap))
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Ошибка добавления цены криптовалюты: {e}")
            return False
    
    def get_latest_crypto_price(self, crypto: str) -> Optional[Dict]:
        """Получить последнюю цену криптовалюты"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT price, price_usd, price_rub, change_24h, volume_24h, market_cap, timestamp
                    FROM crypto_price_history
                    WHERE crypto = ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                ''', (crypto,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'price': row[0],
                        'price_usd': row[1],
                        'price_rub': row[2],
                        'change_24h': row[3],
                        'volume_24h': row[4],
                        'market_cap': row[5],
                        'timestamp': row[6]
                    }
                return None
                
        except Exception as e:
            logger.error(f"Ошибка получения цены криптовалюты: {e}")
            return None
    
    def get_active_trackings(self) -> List[Dict]:
        """Получить все активные отслеживания для проверки уведомлений"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT user_id, crypto, threshold, last_price, last_notification
                    FROM crypto_tracking
                    WHERE is_active = 1
                    ORDER BY user_id, crypto
                ''')
                
                rows = cursor.fetchall()
                return [
                    {
                        'user_id': row[0],
                        'crypto': row[1],
                        'threshold': row[2],
                        'last_price': row[3],
                        'last_notification': row[4]
                    }
                    for row in rows
                ]
                
        except Exception as e:
            logger.error(f"Ошибка получения активных отслеживаний: {e}")
            return []
    
    def update_tracking_price(self, user_id: int, crypto: str, price: float) -> bool:
        """Обновить последнюю цену для отслеживания"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE crypto_tracking
                    SET last_price = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND crypto = ?
                ''', (price, user_id, crypto))
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Ошибка обновления цены отслеживания: {e}")
            return False
    
    def update_tracking_notification(self, user_id: int, crypto: str) -> bool:
        """Обновить время последнего уведомления"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE crypto_tracking
                    SET last_notification = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND crypto = ?
                ''', (user_id, crypto))
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Ошибка обновления времени уведомления: {e}")
            return False