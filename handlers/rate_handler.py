#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Обработчик курсов валют
"""

import logging
import time
from typing import Optional, List, Dict, Any
from datetime import datetime
import pytz

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bestchange_parser import BestChangeParser
from database import DatabaseManager
from cache_manager import CacheManager
from exceptions import BestChangeError
from config import bot_config

logger = logging.getLogger(__name__)


def get_moscow_time() -> datetime:
    """Получить текущее московское время"""
    moscow_tz = pytz.timezone('Europe/Moscow')
    return datetime.now(moscow_tz)


class RateHandler:
    """Обработчик курсов валют"""
    
    def __init__(self, db: DatabaseManager):
        self.parser = BestChangeParser()
        self.db = db
        self.cache = CacheManager()
        self.current_rate: Optional[float] = None
    
    def get_current_rate(self) -> Optional[float]:
        """Получить текущий курс USDT"""
        try:
            # Сначала пытаемся получить из кэша
            cached_data = self.cache.get_cached_rates()
            
            if cached_data:
                rates = [ex['rate'] for ex in cached_data]
                self.current_rate = sum(rates) / len(rates)
                return self.current_rate
            
            # Если кэша нет, получаем свежие данные
            result = self.parser.run()
            if result.get("success") and result["data"]:
                rates = [ex['rate'] for ex in result["data"]]
                self.current_rate = sum(rates) / len(rates)
                # Сохраняем в кэш
                self.cache.set_cached_rates(result["data"])
                return self.current_rate
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка получения курса: {e}")
            raise BestChangeError(f"Не удалось получить курс: {e}")
    
    def convert_currency(self, amount: float, from_currency: str, to_currency: str) -> Optional[float]:
        """Конвертация валют"""
        try:
            rate = self.get_current_rate()
            if not rate:
                return None
            
            if from_currency == "RUB" and to_currency == "USDT":
                # Рубли в USDT
                return amount / rate
            elif from_currency == "USDT" and to_currency == "RUB":
                # USDT в рубли
                return amount * rate
            else:
                return None
                
        except Exception as e:
            logger.error(f"Ошибка конвертации: {e}")
            return None
    
    def can_user_request_rate(self, user_id: int) -> bool:
        """Проверить, может ли пользователь запросить курс (rate limiting)"""
        return self.db.can_user_request_rate(user_id, bot_config.rate_limit_cooldown)
    
    async def handle_get_rate(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик кнопки 'Получить курс' с rate limiting и кэшированием"""
        query = update.callback_query
        user = update.effective_user
        start_time = time.time()
        
        try:
            # Проверяем rate limiting
            if not self.can_user_request_rate(user.id):
                await query.edit_message_text(
                    f"⏳ Слишком частые запросы!\n"
                    f"Подождите {bot_config.rate_limit_cooldown} секунд перед следующим запросом курсов."
                )
                return
            
            await query.edit_message_text("🔄 Получаю актуальный курс USDT...")
            
            # Принудительно получаем свежие данные (игнорируем кэш при обновлении)
            result = self.parser.run()
            
            if not result.get("success"):
                # Если парсер не сработал, пробуем кэш как fallback
                cached_data = self.cache.get_cached_rates()
                if cached_data:
                    data = cached_data
                    is_cached = True
                    logger.info("Парсер недоступен, используем кэшированные данные")
                else:
                    error_msg = f"❌ Ошибка получения данных: {result.get('error', 'Неизвестная ошибка')}"
                    await query.edit_message_text(error_msg)
                    return
            else:
                data = result["data"]
                is_cached = False
                
                # Сохраняем в кэш
                if data:
                    self.cache.set_cached_rates(data)
            
            if data:
                # Берем обменник с наибольшим количеством отзывов (первый в отсортированном списке)
                best_exchanger = data[0]
                
                # Вычисляем средний курс по всем обменникам
                rates = [ex['rate'] for ex in data]
                avg_rate = sum(rates) / len(rates)
                
                # Логируем информацию о курсах для отладки
                logger.info(f"Парсинг курсов: найдено {len(data)} обменников")
                logger.info(f"Диапазон курсов: {min(rates):.4f} - {max(rates):.4f} RUB")
                logger.info(f"Средний курс: {avg_rate:.4f} RUB")
                logger.info(f"Топ-3 обменника: {[f'{ex[\"name\"]}: {ex[\"rate\"]:.4f}' for ex in data[:3]]}")
                
                # Формируем сообщение в указанном формате
                message = f"💱 USDT/RUB • Актуальные курсы\n"
                message += f"━━━━━━━━━━━━━━━━━\n"
                message += f"💰 Средний курс: {avg_rate:.2f}₽ за 1 USDT\n"
                message += f"📈 Курс продажи: {min(rates):.2f}₽ за 1 USDT\n"
                message += f"📉 Курс покупки: {max(rates):.2f}₽ за 1 USDT\n"
                message += f"━━━━━━━━━━━━━━━━━\n"
                message += f"🕘 Обновлено: {get_moscow_time().strftime('%H:%M • %d.%m.%Y')}"
                
                # Создаем клавиатуру с кнопками
                keyboard = [
                    [InlineKeyboardButton("♻️ Обновить курс", callback_data="get_rate")],
                    [InlineKeyboardButton("📈 Топ обменников", callback_data="get_rates_list")],
                    [InlineKeyboardButton("📊 Отслеживание цен", callback_data="tracking_menu")],
                    [InlineKeyboardButton("💼 Кошельки USDT", callback_data="wallets_menu")],
                    [InlineKeyboardButton("🆘 Поддержка", url=bot_config.support_url)]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(message, parse_mode='HTML', reply_markup=reply_markup)
                
                # Логируем запрос курса в БД
                exchange_data = {
                    'avg_rate': avg_rate
                }
                self.db.log_exchange_request(user.id, exchange_data)
                
            else:
                await query.edit_message_text("❌ Не найдено данных об обменниках")
            
            # Логируем команду
            response_time = time.time() - start_time
            self.db.log_command(user.id, 'get_rate', '', response_time)
                
        except BestChangeError as e:
            logger.error(f"Ошибка BestChange: {e}")
            await query.edit_message_text("❌ Ошибка получения курсов. Попробуйте позже.")
        except Exception as e:
            logger.error(f"Ошибка в handle_get_rate: {e}")
            await query.edit_message_text("❌ Произошла ошибка при получении курсов. Попробуйте позже.")
    
    async def handle_get_rates_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик кнопки 'Список лучших курсов' с кэшированием"""
        query = update.callback_query
        user = update.effective_user
        start_time = time.time()
        
        try:
            await query.edit_message_text("🔄 Получаю список лучших курсов...")
            
            # Сначала пытаемся получить данные из кэша
            cached_data = self.cache.get_cached_rates()
            
            if cached_data:
                # Используем кэшированные данные
                data = cached_data
                logger.info("Используем кэшированные данные для списка курсов")
            else:
                # Получаем свежие данные от парсера
                result = self.parser.run()
                
                if not result.get("success"):
                    error_msg = f"❌ Ошибка получения данных: {result.get('error', 'Неизвестная ошибка')}"
                    await query.edit_message_text(error_msg)
                    return
                
                data = result["data"]
                
                # Сохраняем в кэш
                if data:
                    self.cache.set_cached_rates(data)
            
            if data:
                # Берем топ-5 обменников
                top_exchangers = data[:5]
                
                # Формируем сообщение
                message = "💱 USDT/RUB • Топ-5 обменников\n"
                message += "━━━━━━━━━━━━━━━━━━━\n"
                
                # Эмодзи для позиций
                position_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
                
                for i, exchanger in enumerate(top_exchangers):
                    position_emoji = position_emojis[i]
                    
                    # Создаем ссылку на обменник (используем BestChange ссылки)
                    exchanger_link = exchanger.get('exchanger_link', f"https://www.bestchange.com/click.php?id={exchanger.get('id', 1000)}&from=10&to=91&city=1")
                    exchanger_name = exchanger['exchanger_name']
                    
                    # Вычисляем курсы покупки и продажи (примерные значения)
                    sell_rate = exchanger['rate']
                    buy_rate = sell_rate * 0.96  # Примерно на 4% ниже
                    
                    message += f"{position_emoji} <a href='{exchanger_link}'>{exchanger_name}</a>\n"
                    message += f"📈 Продажа: {sell_rate:.2f}₽ • 📉 Покупка: {buy_rate:.2f}₽ • ⭐️ {exchanger['reviews_count']} отзывов\n\n"
                
                # Добавляем время обновления
                message += f"🕘 Обновлено: {get_moscow_time().strftime('%H:%M:%S')}"
                
                # Создаем клавиатуру с кнопками
                keyboard = [
                    [InlineKeyboardButton("💲 Текущий курс", callback_data="get_rate")],
                    [InlineKeyboardButton("📊 Отслеживание цен", callback_data="tracking_menu")],
                    [InlineKeyboardButton("💼 Кошельки USDT", callback_data="wallets_menu")],
                    [InlineKeyboardButton("🆘 Поддержка", url=bot_config.support_url)]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(message, parse_mode='HTML', reply_markup=reply_markup, disable_web_page_preview=True)
                
                # Логируем запрос курса в БД
                rates = [ex['rate'] for ex in data]
                exchange_data = {
                    'avg_rate': sum(rates) / len(rates)
                }
                self.db.log_exchange_request(user.id, exchange_data)
                
            else:
                await query.edit_message_text("❌ Не найдено данных об обменниках")
            
            # Логируем команду
            response_time = time.time() - start_time
            self.db.log_command(user.id, 'get_rates_list', '', response_time)
                
        except BestChangeError as e:
            logger.error(f"Ошибка BestChange в списке курсов: {e}")
            await query.edit_message_text("❌ Ошибка получения списка курсов. Попробуйте позже.")
        except Exception as e:
            logger.error(f"Ошибка в handle_get_rates_list: {e}")
            await query.edit_message_text("❌ Произошла ошибка при получении списка курсов. Попробуйте позже.")
