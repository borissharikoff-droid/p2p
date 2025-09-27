#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trusted Currency Rate - Telegram бот для получения курсов обмена USDT в рубли
"""

import logging
import asyncio
import time
import os
import uuid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, InlineQueryHandler, MessageHandler, ContextTypes, filters
from bestchange_parser import BestChangeParser
from database import DatabaseManager
from cache_manager import CacheManager
import json
from datetime import datetime
import asyncio
from dotenv import load_dotenv
from aiohttp import web
import threading
import http.server
import socketserver

# Загружаем переменные окружения
load_dotenv()


# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен бота из переменных окружения
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    print("⚠️ BOT_TOKEN не найден в переменных окружения!")
    print("⚠️ Установите переменную BOT_TOKEN в Railway")
    # Временно используем токен по умолчанию для тестирования
    BOT_TOKEN = "8441060447:AAHmRDWx-6ezerQOgBnzSPYGBRUXpamcXFg"
    print("⚠️ Используется токен по умолчанию для тестирования")


class TrustedCurrencyRateBot:
    """Trusted Currency Rate - Telegram бот для получения курсов USDT"""
    
    def __init__(self):
        self.parser = BestChangeParser()
        self.db = DatabaseManager()
        cache_duration = int(os.getenv('CACHE_DURATION', 60))
        self.cache = CacheManager(cache_duration=cache_duration)
        self.rate_limit_cooldown = int(os.getenv('RATE_LIMIT_COOLDOWN', 30))
        self.current_rate = None  # Текущий курс USDT
        self.waiting_wallet_add: dict[int, bool] = {}
        self.waiting_wallet_rename: dict[int, int] = {}
        self.waiting_wallet_readdress: dict[int, int] = {}
    
    def get_current_rate(self):
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
            return None
    
    def convert_currency(self, amount: float, from_currency: str, to_currency: str):
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
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        start_time = time.time()
        user = update.effective_user
        
        try:
            # Логируем пользователя в БД
            user_data = {
                'user_id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'language_code': user.language_code,
                'is_bot': user.is_bot,
                'is_premium': getattr(user, 'is_premium', False)
            }
            self.db.add_or_update_user(user_data)
            
            # Начинаем сессию
            self.db.start_session(user.id, user.username)
            
            # Приветственное сообщение
            welcome_message = "💱 <b>DOX // P2P</b>\n\nБот показывает реальный курс USDT анализируя общую ситуацию на биржах."
            
            # Создаем клавиатуру с кнопками
            keyboard = [
                [InlineKeyboardButton("💲 Получить курс", callback_data="get_rate")],
                [InlineKeyboardButton("📈 Список лучших курсов", callback_data="get_rates_list")],
                [InlineKeyboardButton("💼 USDT кошелек", callback_data="wallets_menu")],
                [InlineKeyboardButton("🆘 Поддержка", url="https://t.me/doxpublisher")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(welcome_message, parse_mode='HTML', reply_markup=reply_markup)
            
            # Логируем команду
            response_time = time.time() - start_time
            self.db.log_command(user.id, '/start', update.message.text, response_time)
                
        except Exception as e:
            logger.error(f"Ошибка в start_command: {e}")
            await update.message.reply_text("❌ Произошла ошибка. Попробуйте позже.")
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий на кнопки"""
        query = update.callback_query
        await query.answer()
        
        user = update.effective_user
        start_time = time.time()
        
        # Логируем все callback'и
        logger.info(f"Получен callback: {query.data} от пользователя {user.id}")
        
        try:
            if query.data == "get_rate":
                await self.handle_get_rate(query, user, start_time)
            elif query.data == "get_rates_list":
                await self.handle_get_rates_list(query, user, start_time)
            elif query.data == "wallets_menu":
                await self.handle_wallets_menu(query, user, start_time)
            elif query.data.startswith("wallet_view_"):
                wallet_id = int(query.data.split("_")[-1])
                await self.handle_wallet_view(query, user, wallet_id)
            elif query.data == "wallet_add":
                await self.handle_wallet_add_init(query, user)
            elif query.data.startswith("wallet_rename_"):
                wallet_id = int(query.data.split("_")[-1])
                await self.handle_wallet_rename_init(query, user, wallet_id)
            elif query.data.startswith("wallet_readdress_"):
                wallet_id = int(query.data.split("_")[-1])
                await self.handle_wallet_readdress_init(query, user, wallet_id)
            elif query.data.startswith("wallet_delete_yes_"):
                wallet_id = int(query.data.split("_")[-1])
                logger.info(f"Обработка wallet_delete_yes для кошелька {wallet_id}")
                await self.handle_wallet_delete_yes(query, user, wallet_id)
            elif query.data.startswith("wallet_delete_"):
                wallet_id = int(query.data.split("_")[-1])
                await self.handle_wallet_delete_confirm(query, user, wallet_id)
            elif query.data == "wallet_delete_no":
                await self.handle_wallets_menu(query, user, start_time)
            elif query.data == "back_to_menu":
                await self.handle_back_to_menu(query, user, start_time)
                
        except Exception as e:
            logger.error(f"Ошибка в button_callback: {e}")
            await query.edit_message_text("❌ Произошла ошибка. Попробуйте позже.")
    
    async def handle_get_rate(self, query, user, start_time):
        """Обработчик кнопки 'Получить курс' с rate limiting и кэшированием"""
        try:
            # Проверяем rate limiting
            if not self.db.can_user_request_rate(user.id, self.rate_limit_cooldown):
                await query.edit_message_text(
                    f"⏳ Слишком частые запросы!\n"
                    f"Подождите {self.rate_limit_cooldown} секунд перед следующим запросом курсов."
                )
                return
            
            await query.edit_message_text("🔄 Получаю актуальный курс USDT...")
            
            # Сначала пытаемся получить данные из кэша
            cached_data = self.cache.get_cached_rates()
            cache_info = self.cache.get_cache_info()
            
            if cached_data:
                # Используем кэшированные данные
                data = cached_data
                is_cached = True
                logger.info("Используем кэшированные данные курсов")
            else:
                # Получаем свежие данные от парсера
                result = self.parser.run()
                
                if not result.get("success"):
                    error_msg = f"❌ Ошибка получения данных: {result.get('error', 'Неизвестная ошибка')}"
                    await query.edit_message_text(error_msg)
                    return
                
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
                
                # Формируем сообщение в указанном формате
                message = f"💱 USDT/RUB • Актуальные курсы\n"
                message += f"━━━━━━━━━━━━━━━━━━━━\n"
                message += f"💰 Средний курс: {avg_rate:.2f}₽ за 1 USDT\n"
                message += f"📈 Курс продажи: {best_exchanger['rate']:.2f}₽ за 1 USDT\n"
                message += f"📉 Курс покупки: {min(rates):.2f}₽ за 1 USDT\n"
                message += f"━━━━━━━━━━━━━━━━━━━━\n"
                message += f"🕘 Обновлено: {datetime.now().strftime('%H:%M • %d.%m.%Y')}"
                
                # Создаем клавиатуру с кнопками
                keyboard = [
                    [InlineKeyboardButton("♻️ Обновить", callback_data="get_rate")],
                    [InlineKeyboardButton("📈 Список лучших курсов", callback_data="get_rates_list")],
                    [InlineKeyboardButton("💼 USDT кошелек", callback_data="wallets_menu")],
                    [InlineKeyboardButton("🆘 Поддержка", url="https://t.me/doxpublisher")]
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
                
        except Exception as e:
            logger.error(f"Ошибка в handle_get_rate: {e}")
            await query.edit_message_text("❌ Произошла ошибка при получении курсов. Попробуйте позже.")
    
    async def handle_get_rates_list(self, query, user, start_time):
        """Обработчик кнопки 'Список лучших курсов' с кэшированием"""
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
                message += f"🕘 Обновлено: {datetime.now().strftime('%H:%M:%S')}"
                
                # Создаем клавиатуру с кнопками
                keyboard = [
                    [InlineKeyboardButton("💲 Получить курс", callback_data="get_rate")],
                    [InlineKeyboardButton("💼 USDT кошелек", callback_data="wallets_menu")],
                    [InlineKeyboardButton("🆘 Поддержка", url="https://t.me/doxpublisher")]
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
                
        except Exception as e:
            logger.error(f"Ошибка в handle_get_rates_list: {e}")
            await query.edit_message_text("❌ Произошла ошибка при получении списка курсов. Попробуйте позже.")
    
    async def send_wallets_menu(self, query, user):
        """Отправляет новое сообщение со списком кошельков"""
        try:
            wallets = self.db.list_wallets(user.id)
            
            # Всегда показываем одинаковый текст
            text = (
                "💼 <b>USDT-кошельки</b>\n\n"
                "Добавьте адрес кошелька для приема платежей и создания чеков.\n\n"
                "<b>Добавление кошелька:</b>\n"
                "<code>USDT - &lt;адрес&gt; [Название]</code>\n\n"
                "<b>Пример:</b>\n"
                "<code>USDT - PY3cykOJTeZUEGPHwSZxe29EdyznOB8X7 Реклама</code>\n\n"
                "<b>Создание чека:</b>\n"
                "<code>@DoxP2P_bot 50000 usdt *название*</code>\n\n"
                "<blockquote>Название необязательно, но рекомендуется для различения кошельков</blockquote>"
            )
            
            if not wallets:
                keyboard = [[InlineKeyboardButton("➕ Добавить кошелек", callback_data="wallet_add")],
                            [InlineKeyboardButton("🏠 Назад", callback_data="back_to_menu")]]
                await query.message.reply_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
                return

            # Отрисуем список кошельков кнопками
            buttons = []
            for w in wallets:
                title = w['label'] if w['label'] else w['address']
                buttons.append([InlineKeyboardButton(title, callback_data=f"wallet_view_{w['id']}")])
            buttons.append([InlineKeyboardButton("➕ Добавить кошелек", callback_data="wallet_add")])
            buttons.append([InlineKeyboardButton("🏠 Назад", callback_data="back_to_menu")])
            await query.message.reply_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(buttons))
        except Exception as e:
            logger.error(f"Ошибка в send_wallets_menu: {e}")
            await query.message.reply_text("❌ Произошла ошибка. Попробуйте позже.")

    async def handle_wallets_menu(self, query, user, start_time):
        try:
            wallets = self.db.list_wallets(user.id)
            
            # Всегда показываем одинаковый текст
            text = (
                "💼 <b>USDT-кошельки</b>\n\n"
                "Добавьте адрес кошелька для приема платежей и создания чеков.\n\n"
                "<b>Добавление кошелька:</b>\n"
                "<code>USDT - &lt;адрес&gt; [Название]</code>\n\n"
                "<b>Пример:</b>\n"
                "<code>USDT - PY3cykOJTeZUEGPHwSZxe29EdyznOB8X7 Реклама</code>\n\n"
                "<b>Создание чека:</b>\n"
                "<code>@DoxP2P_bot 50000 usdt *название*</code>\n\n"
                "<blockquote>Название необязательно, но рекомендуется для различения кошельков</blockquote>"
            )
            
            if not wallets:
                keyboard = [[InlineKeyboardButton("➕ Добавить кошелек", callback_data="wallet_add")],
                            [InlineKeyboardButton("🏠 Назад", callback_data="back_to_menu")]]
                return await query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))

            # Отрисуем список кошельков кнопками
            buttons = []
            for w in wallets:
                title = w['label'] if w['label'] else w['address']
                buttons.append([InlineKeyboardButton(title, callback_data=f"wallet_view_{w['id']}")])
            buttons.append([InlineKeyboardButton("➕ Добавить кошелек", callback_data="wallet_add")])
            buttons.append([InlineKeyboardButton("🏠 Назад", callback_data="back_to_menu")])
            await query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(buttons))
        except Exception as e:
            logger.error(f"Ошибка в handle_wallets_menu: {e}")
            await query.edit_message_text("❌ Произошла ошибка. Попробуйте позже.")

    async def handle_wallet_view(self, query, user, wallet_id: int):
        try:
            wallets = self.db.list_wallets(user.id)
            w = next((x for x in wallets if x['id'] == wallet_id), None)
            if not w:
                return await self.handle_wallets_menu(query, user, time.time())
            title = w['label'] if w['label'] else w['address']
            network_type = self.get_network_type(w['address'])
            text = (
                f"💼 <b>{title} ({network_type})</b>\n\n"
                f"Адрес: <code>{w['address']}</code>"
            )
            keyboard = [
                [InlineKeyboardButton("✏️ Переименовать", callback_data=f"wallet_rename_{w['id']}")],
                [InlineKeyboardButton("🔁 Изменить адрес", callback_data=f"wallet_readdress_{w['id']}")],
                [InlineKeyboardButton("🗑️ Удалить", callback_data=f"wallet_delete_{w['id']}")],
                [InlineKeyboardButton("⬅️ Назад", callback_data="wallets_menu")]
            ]
            await query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as e:
            logger.error(f"Ошибка в handle_wallet_view: {e}")
            await query.edit_message_text("❌ Произошла ошибка. Попробуйте позже.")

    async def handle_wallet_add_init(self, query, user):
        try:
            text = (
                "➕ <b>Добавление USDT-кошелька</b>\n\n"
                "<b>Формат сообщения:</b>\n"
                "<code>USDT TRC20 - &lt;адрес&gt; [Название — опционально]</code>\n\n"
                "<b>Пример:</b>\n"
                "<code>USDT TRC20 - PY3cykOJTeZUEGPHwSZxe29EdyznOB8X7 Реклама</code>\n\n"
                "<blockquote>Если название не укажете — будет показан только адрес</blockquote>"
            )
            keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="wallets_menu")]]
            await query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
            self.waiting_wallet_add[user.id] = True
        except Exception as e:
            logger.error(f"Ошибка в handle_wallet_add_init: {e}")
            await query.edit_message_text("❌ Произошла ошибка. Попробуйте позже.")

    async def handle_wallet_rename_init(self, query, user, wallet_id: int):
        try:
            self.waiting_wallet_rename[user.id] = wallet_id
            keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data=f"wallet_view_{wallet_id}")]]
            await query.edit_message_text(
                "✏️ <b>Новое название</b>\n\nПришлите новое имя для кошелька или отправьте '-' чтобы убрать название.",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            logger.error(f"Ошибка в handle_wallet_rename_init: {e}")
            await query.edit_message_text("❌ Произошла ошибка. Попробуйте позже.")

    async def handle_wallet_readdress_init(self, query, user, wallet_id: int):
        try:
            self.waiting_wallet_readdress[user.id] = wallet_id
            # Получаем текущий адрес кошелька
            wallet = self.db.get_wallet(user.id, wallet_id)
            current_address = wallet['address'] if wallet else "неизвестен"
            
            keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data=f"wallet_view_{wallet_id}")]]
            await query.edit_message_text(
                f"🔁 <b>Новый адрес</b>\n\nАдрес: {current_address}\n\nПришлите новый адрес в формате:\nUSDT TRC20 - &lt;адрес&gt;\n\nПример:\nUSDT TRC20 - PY3cykOJTeZUEGPHwSZxe29EdyznOB8X7",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            logger.error(f"Ошибка в handle_wallet_readdress_init: {e}")
            await query.edit_message_text("❌ Произошла ошибка. Попробуйте позже.")

    async def handle_wallet_delete_confirm(self, query, user, wallet_id: int):
        try:
            keyboard = [
                [InlineKeyboardButton("✅ Да, удалить", callback_data=f"wallet_delete_yes_{wallet_id}")],
                [InlineKeyboardButton("⬅️ Назад", callback_data=f"wallet_view_{wallet_id}")]
            ]
            # Изменяем существующее сообщение
            await query.edit_message_text(
                "🗑️ <b>Удаление кошелька</b>\n\nУдалить этот кошелек?",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            logger.error(f"Ошибка в handle_wallet_delete_confirm: {e}")
            await query.answer("Попробуйте еще раз", show_alert=False)

    async def handle_wallet_delete_yes(self, query, user, wallet_id: int):
        try:
            logger.info(f"Попытка удаления кошелька {wallet_id} для пользователя {user.id}")
            
            # Удаляем кошелек из БД
            success = self.db.delete_wallet(user.id, wallet_id)
            logger.info(f"Результат удаления кошелька {wallet_id}: {success}")
            
            if success:
                # Показываем сообщение об успешном удалении с кнопками из /start
                keyboard = [
                    [InlineKeyboardButton("💲 Получить курс", callback_data="get_rate")],
                    [InlineKeyboardButton("📈 Список лучших курсов", callback_data="get_rates_list")],
                    [InlineKeyboardButton("💼 USDT кошелек", callback_data="wallets_menu")],
                    [InlineKeyboardButton("🆘 Поддержка", url="https://t.me/doxpublisher")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    "✅ Ваш кошелек успешно удален",
                    parse_mode='HTML',
                    reply_markup=reply_markup
                )
            else:
                await query.edit_message_text("❌ Не удалось удалить кошелек")
        except Exception as e:
            logger.error(f"Ошибка в handle_wallet_delete_yes: {e}")
            await query.edit_message_text("❌ Произошла ошибка. Попробуйте позже.")
    async def handle_back_to_menu(self, query, user, start_time):
        """Обработчик кнопки 'Назад в меню'"""
        try:
            # Приветственное сообщение
            welcome_message = "💱 <b>DOX // P2P</b>\n\nБот показывает реальный курс USDT анализируя общую ситуацию на биржах."
            
            # Создаем клавиатуру с кнопками
            keyboard = [
                [InlineKeyboardButton("💲 Получить курс", callback_data="get_rate")],
                [InlineKeyboardButton("📈 Список лучших курсов", callback_data="get_rates_list")],
                [InlineKeyboardButton("💼 USDT кошелек", callback_data="wallets_menu")],
                [InlineKeyboardButton("🆘 Поддержка", url="https://t.me/doxpublisher")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(welcome_message, parse_mode='HTML', reply_markup=reply_markup)
            
            # Логируем команду
            response_time = time.time() - start_time
            self.db.log_command(user.id, 'back_to_menu', '', response_time)
                
        except Exception as e:
            logger.error(f"Ошибка в handle_back_to_menu: {e}")
            await query.edit_message_text("❌ Произошла ошибка. Попробуйте позже.")
    
    async def inline_query_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик inline запросов"""
        try:
            query = update.inline_query.query.strip()
            user_id = update.inline_query.from_user.id
            
            if not query:
                # Если запрос пустой, показываем подсказки
                results = [
                    InlineQueryResultArticle(
                        id=str(uuid.uuid4()),
                        title="💡 Введите сумму для конвертации",
                        description="Например: 8000 или 500.50",
                        input_message_content=InputTextMessageContent(
                            "💱 Trusted Currency Rate\n\n"
                            "Введите сумму для конвертации валют:\n"
                            "• 8000 - показать все варианты\n"
                            "• 8000 usdt - конвертация USDT\n"
                            "• 8000 rub - конвертация рублей\n"
                            "• 8000 usdt кошелек - с выбором кошелька\n\n"
                            "Пример: @DoxP2P_bot 8000"
                        )
                    ),
                    InlineQueryResultArticle(
                        id=str(uuid.uuid4()),
                        title="💼 Создать чек с кошельком",
                        description="Пример: 10000 usdt мой_кошелек",
                        input_message_content=InputTextMessageContent(
                            "💼 Создание чека с кошельком\n\n"
                            "Формат: <code>@DoxP2P_bot [сумма] usdt [название]</code>\n\n"
                            "Примеры:\n"
                            "• <code>@DoxP2P_bot 10000 usdt мой_кошелек</code>\n"
                            "• <code>@DoxP2P_bot 50000 usdt работа</code>\n"
                            "• <code>@DoxP2P_bot 15000 usdt</code> (без названия)\n\n"
                            "💡 Название кошелька поможет различать разные кошельки"
                        )
                    ),
                    InlineQueryResultArticle(
                        id=str(uuid.uuid4()),
                        title="🔄 Быстрая конвертация",
                        description="Просто введите сумму",
                        input_message_content=InputTextMessageContent(
                            "🔄 Быстрая конвертация валют\n\n"
                            "Просто введите сумму:\n"
                            "• <code>1000</code> - конвертация рублей в USDT\n"
                            "• <code>50.5</code> - конвертация USDT в рубли\n\n"
                            "Бот автоматически определит валюту по размеру суммы:\n"
                            "• Большие числа (1000+) = рубли → USDT\n"
                            "• Малые числа (<100) = USDT → рубли"
                        )
                    )
                ]
            else:
                # Парсим запрос: сумма + валюта + кошелек
                parsed = self.parse_inline_query(query)
                
                if not parsed['valid']:
                    results = [
                        InlineQueryResultArticle(
                            id=str(uuid.uuid4()),
                            title="❌ Неверный формат",
                            description=parsed['error'],
                            input_message_content=InputTextMessageContent(
                                f"❌ {parsed['error']}\n\n"
                            "Правильный формат:\n"
                            "• 1000 (показать все варианты)\n"
                            "• 1000 usdt\n"
                            "• 500.50 rub\n"
                            "• 1000 usdt wallet1"
                            )
                        )
                    ]
                else:
                    amount = parsed['amount']
                    currency = parsed['currency']
                    wallet_name = parsed.get('wallet')
                    
                    # Получаем текущий курс
                    rate = self.get_current_rate()
                    if not rate:
                        results = [
                            InlineQueryResultArticle(
                                id=str(uuid.uuid4()),
                                title="❌ Ошибка получения курса",
                                description="Попробуйте позже",
                                input_message_content=InputTextMessageContent(
                                    "❌ Не удалось получить актуальный курс. Попробуйте позже."
                                )
                            )
                        ]
                    else:
                        # Если валюта не указана - показываем варианты для обеих валют + кошельки
                        if currency is None:
                            results = await self.create_dual_currency_suggestions(user_id, amount, rate)
                        # Если валюта указана, но кошелек не выбран - показываем и конвертацию, и кошельки
                        elif not wallet_name and currency in ['USDT', 'RUB']:
                            conversion_results = self.create_conversion_results(amount, currency, rate)
                            wallet_results = await self.create_wallet_suggestions(user_id, amount, currency)
                            results = conversion_results + wallet_results
                        # Если указан кошелек, создаем сообщение для отправителя
                        elif wallet_name:
                            results = await self.create_payment_message(user_id, amount, currency, wallet_name, rate)
                        # Обычная конвертация без кошелька
                        else:
                            results = self.create_conversion_results(amount, currency, rate)
            
            await update.inline_query.answer(results, cache_time=60)
            
        except Exception as e:
            logger.error(f"Ошибка в inline_query_handler: {e}")
            await update.inline_query.answer([], cache_time=1)

    async def message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка входящих текстов для сценариев кошельков"""
        if not update.message or not update.effective_user:
            return
        user = update.effective_user
        text = update.message.text.strip()

        # Добавление нового кошелька
        if self.waiting_wallet_add.get(user.id):
            # Ожидали формат: USDT TRC20 - <адрес> [Название]
            ok, address, label, error = self.parse_wallet_input(text)
            if not ok:
                return await update.message.reply_text(error)
            # Проверим дубликаты
            existing = self.db.list_wallets(user.id)
            if any(w['address'].lower() == address.lower() for w in existing):
                # НЕ сбрасываем состояние, чтобы пользователь мог попробовать снова
                return await update.message.reply_text("⚠️ Такой кошелек уже добавлен\n\nПопробуйте другой адрес:")
            saved = self.db.add_wallet(user.id, address, label)
            self.waiting_wallet_add.pop(user.id, None)
            if saved:
                # Показываем кнопки из /start после успешного добавления
                keyboard = [
                    [InlineKeyboardButton("💲 Получить курс", callback_data="get_rate")],
                    [InlineKeyboardButton("📈 Список лучших курсов", callback_data="get_rates_list")],
                    [InlineKeyboardButton("💼 USDT кошелек", callback_data="wallets_menu")],
                    [InlineKeyboardButton("🆘 Поддержка", url="https://t.me/doxpublisher")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    f"✅ Кошелек добавлен\nАдрес: {address}\nНазвание: {label or '—'}",
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text("❌ Не удалось сохранить кошелек. Попробуйте позже.")
            return

        # Переименование
        if user.id in self.waiting_wallet_rename:
            wallet_id = self.waiting_wallet_rename.pop(user.id)
            new_label = None if text == '-' else text[:64]
            if self.db.update_wallet(user.id, wallet_id, None, new_label):
                # Получаем актуальные данные кошелька для отображения
                wallets = self.db.list_wallets(user.id)
                wallet = next((w for w in wallets if w['id'] == wallet_id), None)
                if wallet:
                    title = wallet['label'] if wallet['label'] else wallet['address']
                    network_type = self.get_network_type(wallet['address'])
                    view_text = (
                        "✅ Название обновлено\n\n"
                        f"💼 <b>{title} ({network_type})</b>\n\n"
                        f"Адрес: <code>{wallet['address']}</code>"
                    )
                else:
                    # Фолбек, если не нашли кошелек (маловероятно)
                    view_text = "✅ Название обновлено"

                # Кнопки как в просмотре кошелька
                keyboard = [
                    [InlineKeyboardButton("✏️ Переименовать", callback_data=f"wallet_rename_{wallet_id}")],
                    [InlineKeyboardButton("🔁 Изменить адрес", callback_data=f"wallet_readdress_{wallet_id}")],
                    [InlineKeyboardButton("🗑️ Удалить", callback_data=f"wallet_delete_{wallet_id}")],
                    [InlineKeyboardButton("⬅️ Назад", callback_data="wallets_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                return await update.message.reply_text(view_text, parse_mode='HTML', reply_markup=reply_markup)
            return await update.message.reply_text("❌ Не удалось обновить название")

        # Смена адреса
        if user.id in self.waiting_wallet_readdress:
            wallet_id = self.waiting_wallet_readdress.pop(user.id)
            # Ожидаем: USDT TRC20 - <адрес>
            ok, address, _, error = self.parse_wallet_input(text, label_optional_only=True)
            if not ok:
                return await update.message.reply_text(error)
            
            # Получаем текущий адрес кошелька для проверки
            wallets = self.db.list_wallets(user.id)
            current_wallet = next((w for w in wallets if w['id'] == wallet_id), None)
            
            if current_wallet and current_wallet['address'].lower() == address.lower():
                # Адрес не изменился
                keyboard = [
                    [InlineKeyboardButton("✏️ Переименовать", callback_data=f"wallet_rename_{wallet_id}")],
                    [InlineKeyboardButton("🔁 Изменить адрес", callback_data=f"wallet_readdress_{wallet_id}")],
                    [InlineKeyboardButton("🗑️ Удалить", callback_data=f"wallet_delete_{wallet_id}")],
                    [InlineKeyboardButton("⬅️ Назад", callback_data="wallets_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                return await update.message.reply_text("⚠️ Адрес не поменялся", reply_markup=reply_markup)
            
            # Проверяем дубликаты среди других кошельков (исключая текущий)
            existing = self.db.list_wallets(user.id)
            if any(w['address'].lower() == address.lower() and w['id'] != wallet_id for w in existing):
                return await update.message.reply_text("⚠️ Такой адрес уже используется в другом кошельке\n\nПопробуйте другой адрес:")
            
            if self.db.update_wallet(user.id, wallet_id, address, None):
                # Получаем обновленные данные кошелька
                wallet = self.db.get_wallet(user.id, wallet_id)
                if wallet:
                    # Формируем карточку кошелька
                    network_type = self.get_network_type(wallet['address'])
                    text = f"✅ Адрес обновлен\n\n💼 {wallet['label']} ({network_type})\n\nАдрес: {wallet['address']}"
                    keyboard = [
                        [InlineKeyboardButton("✏️ Переименовать", callback_data=f"wallet_rename_{wallet_id}")],
                        [InlineKeyboardButton("🔁 Изменить адрес", callback_data=f"wallet_readdress_{wallet_id}")],
                        [InlineKeyboardButton("🗑️ Удалить", callback_data=f"wallet_delete_{wallet_id}")],
                        [InlineKeyboardButton("⬅️ Назад", callback_data="wallets_menu")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    return await update.message.reply_text(text, reply_markup=reply_markup)
            return await update.message.reply_text("❌ Не удалось обновить адрес")

    def parse_inline_query(self, query: str) -> dict:
        """Парсит inline запрос: сумма [валюта] [кошелек]"""
        try:
            parts = query.strip().split()
            if len(parts) < 1:
                return {'valid': False, 'error': 'Введите сумму для конвертации'}
            
            # Парсим сумму
            try:
                amount = float(parts[0].replace(',', '.'))
                if amount <= 0:
                    return {'valid': False, 'error': 'Сумма должна быть больше 0'}
            except ValueError:
                return {'valid': False, 'error': 'Неверный формат суммы'}
            
            # Если только сумма - показываем варианты для обеих валют
            if len(parts) == 1:
                return {
                    'valid': True,
                    'amount': amount,
                    'currency': None,  # None означает "показать оба варианта"
                    'wallet': None
                }
            
            # Парсим валюту (если указана)
            currency = parts[1].lower()
            if currency not in ['usdt', 'rub', 'руб', 'рублей']:
                return {'valid': False, 'error': 'Поддерживаются только USDT и RUB'}
            
            # Нормализуем валюту
            if currency in ['rub', 'руб', 'рублей']:
                currency = 'RUB'
            else:
                currency = 'USDT'
            
            # Парсим кошелек (опционально)
            wallet = None
            if len(parts) > 2:
                wallet = ' '.join(parts[2:])
            
            return {
                'valid': True,
                'amount': amount,
                'currency': currency,
                'wallet': wallet
            }
            
        except Exception as e:
            return {'valid': False, 'error': f'Ошибка парсинга: {str(e)}'}

    async def create_dual_currency_suggestions(self, user_id: int, amount: float, rate: float) -> list:
        """Создает предложения для обеих валют когда валюта не указана"""
        try:
            results = []
            
            # Конвертация USDT в рубли
            rub_amount = self.convert_currency(amount, "USDT", "RUB")
            results.append(
                InlineQueryResultArticle(
                    id=f"usdt_to_rub_{amount}",
                    title=f"💵 {amount:,.2f} USDT = {rub_amount:,.2f}₽",
                    description="Конвертировать USDT в рубли",
                    input_message_content=InputTextMessageContent(
                        f"💵 Конвертация валют\n\n"
                        f"💰 Средний курс: {rate:.2f}₽ за 1$\n"
                        f"💱 {amount:,.2f} USDT = {rub_amount:,.2f}₽\n\n"
                        f"🕘 Обновлено: {datetime.now().strftime('%H:%M %d.%m.%Y')}"
                    )
                )
            )
            
            # Конвертация рублей в USDT
            usdt_amount = self.convert_currency(amount, "RUB", "USDT")
            results.append(
                InlineQueryResultArticle(
                    id=f"rub_to_usdt_{amount}",
                    title=f"💰 {amount:,.2f}₽ = {usdt_amount:.4f} USDT",
                    description="Конвертировать рубли в USDT",
                    input_message_content=InputTextMessageContent(
                        f"💵 Конвертация валют\n\n"
                        f"💰 Средний курс: {rate:.2f}₽ за 1$\n"
                        f"💱 {amount:,.2f}₽ = {usdt_amount:.4f} USDT\n\n"
                        f"🕘 Обновлено: {datetime.now().strftime('%H:%M %d.%m.%Y')}"
                    )
                )
            )
            
            # Добавляем предложения кошельков для обеих валют
            wallet_results_usdt = await self.create_wallet_suggestions(user_id, amount, "USDT")
            wallet_results_rub = await self.create_wallet_suggestions(user_id, amount, "RUB")
            
            # Ограничиваем количество кошельков до 3 для каждой валюты
            results.extend(wallet_results_usdt[:3])
            results.extend(wallet_results_rub[:3])
            
            return results
            
        except Exception as e:
            logger.error(f"Ошибка создания предложений для обеих валют: {e}")
            return [
                InlineQueryResultArticle(
                    id=str(uuid.uuid4()),
                    title="❌ Ошибка создания предложений",
                    description="Попробуйте позже",
                    input_message_content=InputTextMessageContent(
                        "❌ Произошла ошибка при создании предложений. Попробуйте позже."
                    )
                )
            ]

    def create_conversion_results(self, amount: float, currency: str, rate: float) -> list:
        """Создает результаты для обычной конвертации без кошелька"""
        if currency == 'RUB':
            # Конвертируем рубли в USDT
            usdt_amount = self.convert_currency(amount, "RUB", "USDT")
            return [
                InlineQueryResultArticle(
                    id=str(uuid.uuid4()),
                    title=f"💰 {amount:,.2f}₽ = {usdt_amount:.4f} USDT",
                    description=f"Конвертировать {amount:,.2f} рублей в USDT",
                    input_message_content=InputTextMessageContent(
                        f"💵 Конвертация валют\n\n"
                        f"💰 Средний курс: {rate:.2f}₽ за 1$\n"
                        f"💱 {amount:,.2f}₽ = {usdt_amount:.4f} USDT\n\n"
                        f"🕘 Обновлено: {datetime.now().strftime('%H:%M %d.%m.%Y')}"
                    )
                )
            ]
        else:
            # Конвертируем USDT в рубли
            rub_amount = self.convert_currency(amount, "USDT", "RUB")
            return [
                InlineQueryResultArticle(
                    id=str(uuid.uuid4()),
                    title=f"💵 {amount:,.2f} USDT = {rub_amount:,.2f}₽",
                    description=f"Конвертировать {amount:,.2f} USDT в рубли",
                    input_message_content=InputTextMessageContent(
                        f"💵 Конвертация валют\n\n"
                        f"💰 Средний курс: {rate:.2f}₽ за 1$\n"
                        f"💱 {amount:,.2f} USDT = {rub_amount:,.2f}₽\n\n"
                        f"🕘 Обновлено: {datetime.now().strftime('%H:%M %d.%m.%Y')}"
                    )
                )
            ]

    async def create_wallet_suggestions(self, user_id: int, amount: float, currency: str) -> list:
        """Создает предложения кошельков для выбора"""
        try:
            # Получаем список кошельков пользователя
            wallets = self.db.list_wallets(user_id)
            
            if not wallets:
                return [
                    InlineQueryResultArticle(
                        id=str(uuid.uuid4()),
                        title="❌ Нет кошельков",
                        description="Сначала добавьте кошелек через бота",
                        input_message_content=InputTextMessageContent(
                            "❌ У вас нет добавленных кошельков!\n\n"
                            "Добавьте кошелек через команду /start → 💼 USDT кошелек"
                        )
                    )
                ]
            
            # Получаем текущий курс для предварительного расчета
            rate = self.get_current_rate()
            if not rate:
                rate = 83.0  # Fallback курс
            
            results = []
            
            # Создаем предложения для каждого кошелька
            for i, wallet in enumerate(wallets[:10]):  # Ограничиваем до 10 кошельков
                wallet_name = wallet['label'] if wallet['label'] else f"Кошелек {i+1}"
                
                if currency == 'RUB':
                    # Пользователь хочет получить рубли, отправитель отправляет USDT
                    usdt_to_send = self.convert_currency(amount, "RUB", "USDT")
                    title = f"💸 {amount:,.0f}₽ → {usdt_to_send:.2f} USDT"
                    description = f"💼 {wallet_name} • Получить {amount:,.0f}₽"
                else:
                    # Пользователь хочет получить USDT, отправитель отправляет рубли
                    rub_to_send = self.convert_currency(amount, "USDT", "RUB")
                    title = f"💸 {amount:,.0f} USDT → {rub_to_send:,.0f}₽"
                    description = f"💼 {wallet_name} • Получить {amount:,.0f} USDT"
                
                # Создаем полный запрос с выбранным кошельком
                full_query = f"{amount} {currency.lower()} {wallet['label']}"
                
                results.append(
                    InlineQueryResultArticle(
                        id=f"wallet_{wallet['id']}_{amount}_{currency}",
                        title=title,
                        description=description,
                        input_message_content=InputTextMessageContent(
                            f"💸 <b>Запрос на оплату</b>\n\n"
                            f"💰 Сумма к получению: {amount:,.2f}{'₽' if currency == 'RUB' else ' USDT'}\n"
                            + (f"💵 К отправке: {usdt_to_send:.4f} USDT\n" if currency == 'RUB' else f"💰 К отправке: {rub_to_send:,.2f}₽\n") +
                            f"📊 Курс: {rate:.2f}₽ за 1$\n\n"
                            f"📍 <b>Адрес для отправки:</b>\n"
                            f"<code>{wallet['address']}</code>\n\n"
                            f"⚠️ <b>Внимание:</b> Отправляйте только USDT TRC20 на указанный адрес!",
                            parse_mode='HTML'
                        )
                    )
                )
            
            return results
            
        except Exception as e:
            logger.error(f"Ошибка создания предложений кошельков: {e}")
            return [
                InlineQueryResultArticle(
                    id=str(uuid.uuid4()),
                    title="❌ Ошибка загрузки кошельков",
                    description="Попробуйте позже",
                    input_message_content=InputTextMessageContent(
                        "❌ Произошла ошибка при загрузке кошельков. Попробуйте позже."
                    )
                )
            ]

    async def create_payment_message(self, user_id: int, amount: float, currency: str, wallet_name: str, rate: float) -> list:
        """Создает сообщение для отправителя с деталями платежа"""
        try:
            # Находим кошелек по названию
            wallets = self.db.list_wallets(user_id)
            wallet = None
            
            for w in wallets:
                if w['label'].lower() == wallet_name.lower():
                    wallet = w
                    break
            
            if not wallet:
                return [
                    InlineQueryResultArticle(
                        id=str(uuid.uuid4()),
                        title="❌ Кошелек не найден",
                        description=f"Кошелек '{wallet_name}' не найден",
                        input_message_content=InputTextMessageContent(
                            f"❌ Кошелек '{wallet_name}' не найден!\n\n"
                            "Доступные кошельки:\n" + 
                            "\n".join([f"• {w['label']}" for w in wallets[:5]])
                        )
                    )
                ]
            
            # Создаем сообщение для отправителя
            if currency == 'RUB':
                # Пользователь хочет получить рубли, отправитель отправляет USDT
                usdt_to_send = self.convert_currency(amount, "RUB", "USDT")
                message_text = (
                    f"💸 <b>Запрос на оплату</b>\n\n"
                    f"💰 Сумма к получению: {amount:,.2f}₽\n"
                    f"💵 К отправке: {usdt_to_send:.4f} USDT\n"
                    f"📊 Курс: {rate:.2f}₽ за 1$\n\n"
                    f"📍 <b>Адрес для отправки:</b>\n"
                    f"<code>{wallet['address']}</code>\n\n"
                    f"⚠️ <b>Внимание:</b> Отправляйте только USDT TRC20 на указанный адрес!"
                )
                title = f"💸 {amount:,.2f}₽ → {usdt_to_send:.4f} USDT"
                description = f"Отправить {usdt_to_send:.4f} USDT на {wallet['label']}"
            else:
                # Пользователь хочет получить USDT, отправитель отправляет рубли
                rub_to_send = self.convert_currency(amount, "USDT", "RUB")
                message_text = (
                    f"💸 <b>Запрос на оплату</b>\n\n"
                    f"💵 Сумма к получению: {amount:,.2f} USDT\n"
                    f"💰 К отправке: {rub_to_send:,.2f}₽\n"
                    f"📊 Курс: {rate:.2f}₽ за 1$\n\n"
                    f"📍 <b>Адрес для отправки:</b>\n"
                    f"<code>{wallet['address']}</code>\n\n"
                    f"⚠️ <b>Внимание:</b> Отправляйте только USDT TRC20 на указанный адрес!"
                )
                title = f"💸 {amount:,.2f} USDT → {rub_to_send:,.2f}₽"
                description = f"Отправить {rub_to_send:,.2f}₽ за {amount:,.2f} USDT"
            
            return [
                InlineQueryResultArticle(
                    id=f"payment_{user_id}_{int(amount)}_{currency}",
                    title=title,
                    description=description,
                    input_message_content=InputTextMessageContent(
                        message_text,
                        parse_mode='HTML'
                    )
                )
            ]
            
        except Exception as e:
            logger.error(f"Ошибка создания сообщения платежа: {e}")
            return [
                InlineQueryResultArticle(
                    id=str(uuid.uuid4()),
                    title="❌ Ошибка создания платежа",
                    description="Попробуйте позже",
                    input_message_content=InputTextMessageContent(
                        "❌ Произошла ошибка при создании запроса на оплату. Попробуйте позже."
                    )
                )
            ]

    def get_network_type(self, address: str):
        """Определяет тип сети по адресу кошелька.
        Логика:
        - ERC20/BEP20: 0x-префикс и 42 символа
        - TRC20: адрес длиной 26-50 символов, не начинающийся с 0x
        Иначе: USDT (не удалось надёжно определить).
        """
        addr_lower = address.lower()

        # ERC20/BEP20 (Ethereum/BSC): адреса формата 0x + 40 hex
        if addr_lower.startswith('0x') and len(address) == 42:
            return "USDT ERC20"

        # TRC20 (Tron): классический случай — 'T' и длина 34
        if (address.startswith('T') or address.startswith('t')) and len(address) == 34:
            return "USDT TRC20"

        # TRC20: любой адрес длиной 26-50 символов, не начинающийся с 0x
        if 26 <= len(address) <= 50 and not addr_lower.startswith('0x'):
            return "USDT TRC20"

        return "USDT"

    def _is_base58_like(self, s: str) -> bool:
        """Проверяет, что строка похожа на base58-адрес (для Tron и др.)."""
        base58_chars = set("123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz")
        return all(ch in base58_chars for ch in s)
    
    def parse_wallet_input(self, text: str, label_optional_only: bool = False):
        """Парсер строки вида: USDT TRC20 - <адрес> [Название]"""
        try:
            # Проверяем различные форматы
            text_upper = text.upper()
            if text_upper.startswith('USDT TRC20 - '):
                body = text[15:].strip()  # Убираем "USDT TRC20 - "
            elif text_upper.startswith('USDT ERC20 - '):
                body = text[15:].strip()  # Убираем "USDT ERC20 - "
            elif text_upper.startswith('USDT BEP20 - '):
                body = text[15:].strip()  # Убираем "USDT BEP20 - "
            elif text_upper.startswith('USDT - '):
                body = text[8:].strip()   # Убираем "USDT - "
            else:
                return False, None, None, (
                    "❌ Неверный формат\n\nИспользуйте:\nUSDT TRC20 - <адрес> [Название — опционально]\n\n"
                    "Пример:\nUSDT TRC20 - PY3cykOJTeZUEGPHwSZxe29EdyznOB8X7 Реклама"
                )
            
            parts = body.split(maxsplit=1)
            address = parts[0]
            label = parts[1] if (len(parts) > 1 and not label_optional_only) else None
            
            # Валидация адреса (минимально: длина и символы base58/hex)
            if not (20 <= len(address) <= 120):
                return False, None, None, "❌ Похоже адрес некорректный (длина). Проверьте и отправьте снова."
            if not all(c.isalnum() for c in address):
                return False, None, None, "❌ Адрес должен содержать только буквы и цифры."
            return True, address, label, None
        except Exception:
            return False, None, None, "❌ Не удалось разобрать сообщение. Попробуйте снова."
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        start_time = time.time()
        user = update.effective_user
        
        try:
            help_text = """
💱 <b>Trusted Currency Rate</b>

<b>Доступные команды:</b>
/start - Главное меню с кнопками
/help - Показать это сообщение
/stats - Показать статистику использования

<b>Функции бота:</b>
• 💲 Получить курс - быстрый обзор курсов
• 📈 Список лучших курсов - топ-5 обменников
• 🆘 Поддержка - прямая связь с администратором

<b>Что показывает бот:</b>
• Средний курс по всем обменникам
• Курс продажи от самого надежного обменника
• Курс покупки (минимальный)
• Время последнего обновления
• Информацию о лучших обменниках

<b>Источник данных:</b> BestChange.ru
            """
            await update.message.reply_text(help_text, parse_mode='HTML')
            
            # Логируем команду
            response_time = time.time() - start_time
            self.db.log_command(user.id, '/help', update.message.text, response_time)
            
        except Exception as e:
            logger.error(f"Ошибка в help_command: {e}")
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /stats"""
        start_time = time.time()
        user = update.effective_user
        
        try:
            # Получаем статистику пользователя
            user_stats = self.db.get_user_stats(user.id)
            
            if user_stats:
                message = f"📊 <b>Ваша статистика:</b>\n\n"
                message += f"👤 Пользователь: {user_stats.get('first_name', 'Неизвестно')}\n"
                message += f"📅 Первый вход: {user_stats.get('first_contact_date', 'Неизвестно')}\n"
                message += f"🔄 Последняя активность: {user_stats.get('last_activity_date', 'Неизвестно')}\n"
                message += f"💬 Всего команд: {user_stats.get('total_commands', 0)}\n"
                message += f"💰 Запросов курсов: {user_stats.get('total_requests', 0)}\n"
                
                if user_stats.get('last_session_duration'):
                    message += f"⏱️ Последняя сессия: {user_stats['last_session_duration']:.1f} сек\n"
                
                if user_stats.get('avg_session_duration'):
                    message += f"📈 Средняя сессия: {user_stats['avg_session_duration']:.1f} сек\n"
                
                await update.message.reply_text(message, parse_mode='HTML')
            else:
                await update.message.reply_text("❌ Статистика не найдена. Попробуйте сначала использовать /start")
            
            # Логируем команду
            response_time = time.time() - start_time
            self.db.log_command(user.id, '/stats', update.message.text, response_time)
            
        except Exception as e:
            logger.error(f"Ошибка в stats_command: {e}")
            await update.message.reply_text("❌ Ошибка получения статистики")
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ошибок"""
        logger.error(f"Ошибка: {context.error}")
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ Произошла ошибка. Попробуйте позже."
            )


async def cleanup_task(bot):
    """Периодическая очистка старых данных"""
    while True:
        try:
            # Очищаем старые данные из БД (старше 7 дней)
            deleted_db = bot.db.cleanup_old_data(days_to_keep=7)
            
            # Очищаем старые файлы кэша (старше 24 часов)
            deleted_cache = bot.cache.cleanup_old_cache_files(max_age_hours=24)
            
            if deleted_db > 0 or deleted_cache > 0:
                logger.info(f"Очистка завершена: БД={deleted_db}, кэш={deleted_cache}")
            
            # Ждем 1 час до следующей очистки
            await asyncio.sleep(3600)
            
        except Exception as e:
            logger.error(f"Ошибка в задаче очистки: {e}")
            await asyncio.sleep(3600)


async def health_check(request):
    """Health check endpoint для Railway"""
    try:
        return web.json_response({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "service": "telegram-bot",
            "port": int(os.getenv('PORT', 8000)),
            "uptime": "running"
        })
    except Exception as e:
        return web.json_response({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }, status=500)


class HealthCheckHandler(http.server.BaseHTTPRequestHandler):
    """Простой HTTP обработчик для health check"""
    
    def do_GET(self):
        print(f"🔍 Получен запрос: {self.path}")
        if self.path in ['/health', '/']:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            response = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "service": "telegram-bot",
                "port": int(os.getenv('PORT', 8080)),
                "uptime": "running"
            }
            
            self.wfile.write(json.dumps(response).encode())
            print(f"✅ Отправлен ответ: {response}")
        else:
            self.send_response(404)
            self.end_headers()
            print(f"❌ 404 для пути: {self.path}")
    
    def log_message(self, format, *args):
        # Отключаем логирование запросов
        pass


def run_simple_web_server():
    """Запуск простого HTTP сервера для health check"""
    port = int(os.getenv('PORT', 8080))
    
    print(f"🌐 Запуск простого health check сервера на порту {port}")
    print(f"🌐 Health check доступен на: http://0.0.0.0:{port}/health")
    print(f"🌐 Переменная PORT: {os.getenv('PORT', 'не установлена')}")
    
    # Создаем сервер с возможностью переиспользования адреса
    class ReusableTCPServer(socketserver.TCPServer):
        allow_reuse_address = True
    
    try:
        with ReusableTCPServer(("0.0.0.0", port), HealthCheckHandler) as httpd:
            print(f"✅ Health check сервер запущен на порту {port}")
            print(f"✅ Сервер слушает на 0.0.0.0:{port}")
            httpd.serve_forever()
            
    except Exception as e:
        print(f"❌ Ошибка запуска простого сервера: {e}")
        print(f"❌ Тип ошибки: {type(e).__name__}")
        print(f"❌ Детали ошибки: {str(e)}")
        
        # Пробуем альтернативный порт
        try:
            alt_port = 8080
            print(f"🔄 Пробуем альтернативный порт {alt_port}")
            
            with ReusableTCPServer(("0.0.0.0", alt_port), HealthCheckHandler) as httpd:
                print(f"✅ Health check сервер запущен на порту {alt_port}")
                httpd.serve_forever()
        except Exception as e2:
            print(f"❌ Ошибка на альтернативном порту: {e2}")
            print(f"❌ Тип ошибки: {type(e2).__name__}")
            print(f"❌ Детали ошибки: {str(e2)}")


def run_web_server():
    """Запуск HTTP сервера для health check (aiohttp)"""
    app = web.Application()
    app.router.add_get('/health', health_check)
    app.router.add_get('/', health_check)  # Добавляем корневой путь
    
    port = int(os.getenv('PORT', 8080))
    try:
        print(f"🌐 Запуск aiohttp health check сервера на порту {port}")
        print(f"🌐 Health check доступен на: http://0.0.0.0:{port}/health")
        web.run_app(app, host='0.0.0.0', port=port, access_log=None)
    except Exception as e:
        print(f"❌ Ошибка запуска aiohttp сервера: {e}")
        # Fallback на простой сервер
        print("🔄 Переключаемся на простой HTTP сервер")
        run_simple_web_server()


def main():
    """Основная функция для запуска бота"""
    # Создаем экземпляр бота
    bot = TrustedCurrencyRateBot()
    
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", bot.start_command))
    application.add_handler(CommandHandler("help", bot.help_command))
    application.add_handler(CommandHandler("stats", bot.stats_command))
    
    # Добавляем обработчик callback'ов для кнопок
    application.add_handler(CallbackQueryHandler(bot.button_callback))
    
    # Добавляем обработчик inline запросов
    application.add_handler(InlineQueryHandler(bot.inline_query_handler))
    
    # Обработчик текстов для кошельков
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.message_handler))
    
    # Добавляем обработчик ошибок
    application.add_error_handler(bot.error_handler)
    
    # Запускаем задачу очистки в фоне (только если JobQueue доступен)
    if application.job_queue:
        application.job_queue.run_repeating(
            lambda context: asyncio.create_task(cleanup_task(bot)),
            interval=3600,  # Каждый час
            first=60  # Первый запуск через минуту
        )
        print("✅ Задача очистки запланирована")
    else:
        print("⚠️ JobQueue недоступен, задача очистки не запланирована")
    
    # Запускаем бота
    print("🤖 Запуск Trusted Currency Rate бота...")
    print("📱 Бот готов к работе!")
    print("💡 Отправьте /start боту для получения курсов USDT")
    print("🔄 Inline режим: @DoxP2P_bot [сумма] для конвертации")
    print("⚡ Оптимизирован для высокой нагрузки (500+ пользователей/день)")
    print("🔄 Кэширование: 60 сек, Rate limiting: 30 сек")
    
    # Запускаем HTTP сервер для health check в отдельном потоке
    port = int(os.getenv('PORT', 8080))
    print(f"🌐 Health check: http://localhost:{port}/health")
    print(f"🌐 Переменная PORT: {os.getenv('PORT', 'не установлена')}")
    print(f"🌐 Используемый порт: {port}")
    print(f"🌐 Все переменные окружения: {dict(os.environ)}")
    
    # Пробуем сначала простой HTTP сервер
    print("🚀 Запуск health check сервера...")
    web_thread = threading.Thread(target=run_simple_web_server, daemon=True)
    web_thread.start()
    
    # Небольшая задержка для запуска health check сервера
    print("⏳ Ожидание запуска health check сервера...")
    time.sleep(5)
    print("✅ Health check сервер должен быть запущен")
    
    # Проверяем, что сервер запустился
    try:
        import requests
        response = requests.get(f"http://localhost:{port}/health", timeout=2)
        print(f"✅ Health check работает: {response.status_code}")
    except Exception as e:
        print(f"⚠️ Health check не отвечает: {e}")
        print("🔄 Пробуем альтернативный порт...")
        try:
            response = requests.get(f"http://localhost:8080/health", timeout=2)
            print(f"✅ Health check работает на порту 8080: {response.status_code}")
        except Exception as e2:
            print(f"❌ Health check не работает ни на одном порту: {e2}")
    
    # Используем run_polling() вместо await
    application.run_polling()


if __name__ == "__main__":
    main()
