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

from grinex_parser import GrinexParser
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
        self.parser = GrinexParser()
        self.db = db
        self.cache = CacheManager()
        self.current_rate: Optional[float] = None
    
    def get_current_rate(self) -> Optional[float]:
        """Получить текущий курс USDT"""
        try:
            # Вспомогательная функция: средний по топ-10 buy/sell +0.30
            def _compute_mid_plus_margin(data: Any) -> Optional[float]:
                if isinstance(data, list):
                    # Legacy: нет разделения, берем топ-10 и усредняем
                    base_rates = [ex['rate'] for ex in data[:10]]
                    if not base_rates:
                        return None
                    mid = sum(base_rates) / len(base_rates)
                    return round(mid + 0.30, 2)
                if isinstance(data, dict):
                    buy_top = [ex['rate'] for ex in data.get('buy', [])[:10]]
                    sell_top = [ex['rate'] for ex in data.get('sell', [])[:10]]
                    avg_buy = sum(buy_top) / len(buy_top) if buy_top else None
                    avg_sell = sum(sell_top) / len(sell_top) if sell_top else None
                    if avg_buy is not None and avg_sell is not None:
                        mid = (avg_buy + avg_sell) / 2
                    else:
                        mid = avg_buy if avg_buy is not None else (avg_sell if avg_sell is not None else None)
                    return round(mid + 0.30, 2) if mid is not None else None
                return None

            # Сначала пытаемся получить из кэша
            cached_data = self.cache.get_cached_rates()
            
            if cached_data:
                mid_plus = _compute_mid_plus_margin(cached_data)
                if mid_plus is not None:
                    self.current_rate = mid_plus
                    return mid_plus
            
            # Если кэша нет, получаем свежие данные
            result = self.parser.run()
            if result.get("success") and result["data"]:
                data = result["data"]
                mid_plus = _compute_mid_plus_margin(data)
                if mid_plus is not None:
                    self.cache.set_cached_rates(data)
                    self.current_rate = mid_plus
                    return mid_plus
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка получения курса: {e}")
            raise BestChangeError(f"Не удалось получить курс: {e}")
    
    def convert_currency(self, amount: float, from_currency: str, to_currency: str) -> Optional[float]:
        """Конвертация валют"""
        try:
            # Получаем данные из кэша для правильной конвертации
            cached_data = self.cache.get_cached_rates()
            if not cached_data:
                return None
            
            # Обрабатываем старый формат кэша (список)
            if isinstance(cached_data, list):
                # Если кэш в старом формате, используем средний курс
                if not cached_data:
                    return None
                rates = [ex['rate'] for ex in cached_data[:5]]
                avg_rate = sum(rates) / len(rates)
                
                if from_currency == "RUB" and to_currency == "USDT":
                    # Рубли в USDT - используем средний курс
                    return amount / avg_rate
                elif from_currency == "USDT" and to_currency == "RUB":
                    # USDT в рубли - используем средний курс
                    return amount * avg_rate
                else:
                    return None
            
            # Новый формат кэша (словарь с buy/sell)
            buy_data = cached_data.get('buy', [])
            sell_data = cached_data.get('sell', [])
            
            if from_currency == "RUB" and to_currency == "USDT":
                # Рубли в USDT - нужен курс ПОКУПКИ USDT
                if buy_data:
                    # Используем средний курс покупки из топ-5
                    buy_rates = [ex['rate'] for ex in buy_data[:5]]
                    avg_buy_rate = sum(buy_rates) / len(buy_rates)
                    return amount / avg_buy_rate
                elif sell_data:
                    # Если данных покупки нет, используем средний курс продажи как курс покупки
                    sell_rates = [ex['rate'] for ex in sell_data[:5]]
                    avg_sell_rate = sum(sell_rates) / len(sell_rates)
                    # Используем средний курс продажи как курс покупки
                    return amount / avg_sell_rate
                else:
                    return None
                    
            elif from_currency == "USDT" and to_currency == "RUB":
                # USDT в рубли - нужен курс ПРОДАЖИ USDT
                if sell_data:
                    # Используем средний курс продажи из топ-5
                    sell_rates = [ex['rate'] for ex in sell_data[:5]]
                    avg_sell_rate = sum(sell_rates) / len(sell_rates)
                    return amount * avg_sell_rate
                else:
                    return None
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
                    # Проверяем формат кэшированных данных
                    if isinstance(cached_data, list):
                        # Старый формат - простой список, конвертируем в новый
                        data = {'sell': cached_data, 'buy': []}
                        is_cached = True
                        logger.info("Парсер недоступен, используем кэшированные данные (старый формат)")
                    elif isinstance(cached_data, dict) and 'sell' in cached_data:
                        # Новый формат
                        data = cached_data
                        is_cached = True
                        logger.info("Парсер недоступен, используем кэшированные данные (новый формат)")
                    else:
                        logger.error(f"Неизвестный формат кэшированных данных: {type(cached_data)}")
                        data = None
                else:
                    data = None
                
                if not data:
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
                # Считаем по топ-10 buy/sell
                buy_top = [ex['rate'] for ex in data.get('buy', [])[:10]]
                sell_top = [ex['rate'] for ex in data.get('sell', [])[:10]]
                avg_buy_rate = (sum(buy_top) / len(buy_top)) if buy_top else None
                avg_sell_rate = (sum(sell_top) / len(sell_top)) if sell_top else None
                if avg_buy_rate is None and avg_sell_rate is None:
                    await query.edit_message_text("❌ Не найдено данных об обменниках")
                    response_time = time.time() - start_time
                    self.db.log_command(user.id, 'get_rate', '', response_time)
                    return
                mid = (avg_buy_rate + avg_sell_rate) / 2 if (avg_buy_rate is not None and avg_sell_rate is not None) else (avg_buy_rate if avg_buy_rate is not None else avg_sell_rate)
                rate_value = round(mid + 0.30, 2)
                # Подробное логирование для верификации результата
                logger.info(
                    f"Калькуляция курса (Grinex USDT/A7A5): avg_buy_top10={avg_buy_rate}, avg_sell_top10={avg_sell_rate}, mid={mid}, final(+0.30)={rate_value}"
                )
                # Формат ответа по требованию
                message = (
                    "💱 USDT/RUB • Актуальные курсы\n"
                    "━━━━━━━━━━━━━━━━━\n"
                    f"💰 Средний курс: {rate_value:.2f}₽ за 1 USDT\n"
                    "━━━━━━━━━━━━━━━━━\n"
                    f"🕘 Обновлено: {get_moscow_time().strftime('%H:%M • %d.%m.%Y')}"
                )
                # Вернем кнопки под сообщением
                keyboard = [
                    [InlineKeyboardButton("♻️ Обновить курс", callback_data="get_rate")],
                    [InlineKeyboardButton("📈 Топ обменников", callback_data="get_rates_list")],
                    [InlineKeyboardButton("📊 Отслеживание цен", callback_data="tracking_menu")],
                    [InlineKeyboardButton("💼 Кошельки USDT", callback_data="wallets_menu")],
                    [InlineKeyboardButton("🆘 Поддержка", url=bot_config.support_url)]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(message, reply_markup=reply_markup)
                # Логируем простое значение в БД
                exchange_data = {'mid_plus_0_30': rate_value}
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
            logger.error(f"Ошибка в handle_get_rate: {e}", exc_info=True)
            await query.edit_message_text("❌ Произошла ошибка при получении курсов. Попробуйте позже.")
    
    async def handle_get_rates_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик кнопки 'Список лучших курсов' с кэшированием"""
        query = update.callback_query
        user = update.effective_user
        start_time = time.time()
        
        try:
            await query.edit_message_text("🔄 Получаю список лучших курсов...")
            
            # Принудительно получаем свежие данные (игнорируем кэш)
            result = self.parser.run()
            
            if not result.get("success"):
                # Если парсер не сработал, пробуем кэш как fallback
                cached_data = self.cache.get_cached_rates()
                if cached_data:
                    # Проверяем формат кэшированных данных
                    if isinstance(cached_data, list):
                        # Старый формат - простой список, конвертируем в новый
                        data = {'sell': cached_data, 'buy': []}
                        logger.info("Парсер недоступен, используем кэшированные данные (старый формат)")
                    elif isinstance(cached_data, dict) and 'sell' in cached_data:
                        # Новый формат
                        data = cached_data
                        logger.info("Парсер недоступен, используем кэшированные данные (новый формат)")
                    else:
                        logger.error(f"Неизвестный формат кэшированных данных: {type(cached_data)}")
                        data = None
                else:
                    data = None
                
                if not data:
                    error_msg = f"❌ Ошибка получения данных: {result.get('error', 'Неизвестная ошибка')}"
                    await query.edit_message_text(error_msg)
                    return
            else:
                data = result["data"]
                
                # Сохраняем в кэш
                if data:
                    self.cache.set_cached_rates(data)
            
            if data:
                # Получаем данные продажи (USDT → RUB) для списка топ обменников
                sell_data = data.get('sell', [])
                
                # Логируем информацию для отладки
                logger.info(f"Список курсов: найдено {len(sell_data)} обменников")
                logger.info(f"Первый обменник: {sell_data[0] if sell_data else 'Нет данных'}")
                
                # Берем топ-5 обменников ПРОДАЖИ (USDT → RUB). Если buy доступен, покажем обе колонки отдельно
                top_exchangers = sell_data[:5]
                
                # Формируем сообщение
                message = "💱 USDT TRC20/T-Bank RUB • Топ-5 обменников\n"
                message += "━━━━━━━━━━━━━━━━━━━\n"
                
                # Эмодзи для позиций
                position_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
                
                for i, exchanger in enumerate(top_exchangers):
                    position_emoji = position_emojis[i]
                    
                    # Создаем ссылку на обменник (используем BestChange ссылки)
                    exchanger_link = exchanger.get('exchanger_link', f"https://www.bestchange.com/click.php?id={exchanger.get('id', 1000)}&from=10&to=91&city=1")
                    exchanger_name = exchanger.get('exchanger_name', exchanger.get('name', 'Неизвестный'))
                    
                    # На BestChange для страницы ПРОДАЖИ (USDT→RUB) rate — сколько RUB вы получите за 1 USDT (курс продажи)
                    sell_rate = exchanger['rate']
                    # Для корректности не выводим синтетический buy_rate. Покажем buy отдельно, если доступен ниже.
                    buy_rate = None
                    
                    message += f"{position_emoji} <a href='{exchanger_link}'>{exchanger_name}</a>\n"
                    message += f"📈 Продажа: {sell_rate:.2f}₽ • ⭐️ {exchanger['reviews_count']} отзывов\n\n"

                # Если есть buy-данные, добавим отдельный блок Топ-5 покупки (RUB→USDT)
                buy_data = data.get('buy', [])
                if buy_data:
                    message += "━━━━━━━━━━━━━━━━━━━\n"
                    message += "🟦 Топ-5 покупки (RUB→USDT)\n"
                    for j, exchanger in enumerate(buy_data[:5]):
                        position_emoji = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"][j]
                        exchanger_link = exchanger.get('exchanger_link', f"https://www.bestchange.com/click.php?id={exchanger.get('id', 1000)}&from=10&to=91&city=1")
                        exchanger_name = exchanger.get('exchanger_name', exchanger.get('name', 'Неизвестный'))
                        buy_rate = exchanger['rate']  # сколько RUB нужно отдать за 1 USDT (курс покупки)
                        message += f"{position_emoji} <a href='{exchanger_link}'>{exchanger_name}</a>\n"
                        message += f"📉 Покупка: {buy_rate:.2f}₽ • ⭐️ {exchanger.get('reviews_count', 0)} отзывов\n\n"
                
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
                rates = [ex['rate'] for ex in sell_data]
                exchange_data = {
                    'avg_rate': sum(rates) / len(rates) if rates else 0
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
            logger.error(f"Ошибка в handle_get_rates_list: {e}", exc_info=True)
            await query.edit_message_text("❌ Произошла ошибка при получении списка курсов. Попробуйте позже.")
