#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trusted Currency Rate - Telegram бот для получения курсов обмена USDT в рубли
Рефакторенная версия с улучшенной архитектурой
"""

import logging
import asyncio
import time
import os
import uuid
import threading
import http.server
import socketserver
from typing import Optional, Dict, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, InlineQueryHandler, MessageHandler, ContextTypes, filters
from aiohttp import web
import pytz
from datetime import datetime

# Импорты наших модулей
from config import bot_config, db_config, cache_config, server_config
from database import DatabaseManager
from cache_manager import CacheManager
from handlers import RateHandler, WalletHandler, InlineHandler
from handlers.crypto_tracking_handler import CryptoTrackingHandler
from exceptions import BotError, BestChangeError, DatabaseError, CacheError, WalletError, ValidationError

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def get_moscow_time() -> datetime:
    """Получить текущее московское время"""
    moscow_tz = pytz.timezone('Europe/Moscow')
    return datetime.now(moscow_tz)


class TrustedCurrencyRateBot:
    """Trusted Currency Rate - Telegram бот для получения курсов USDT"""
    
    def __init__(self):
        # Инициализация компонентов
        self.db = DatabaseManager(db_config.path)
        self.cache = CacheManager(cache_config.directory, cache_config.duration)
        
        # Инициализация обработчиков
        self.rate_handler = RateHandler(self.db, self.cache)
        self.wallet_handler = WalletHandler(self.db)
        self.inline_handler = InlineHandler(self.db, self.rate_handler)
        self.crypto_tracking_handler = CryptoTrackingHandler(self.db)
        
        # Состояние бота
        self.application: Optional[Application] = None
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
                [InlineKeyboardButton("📊 Отслеживание курса", callback_data="tracking_menu")],
                [InlineKeyboardButton("💼 USDT кошелек", callback_data="wallets_menu")],
                [InlineKeyboardButton("🆘 Поддержка", url=bot_config.support_url)]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(welcome_message, parse_mode='HTML', reply_markup=reply_markup)
            
            # Логируем команду
            response_time = time.time() - start_time
            self.db.log_command(user.id, '/start', update.message.text, response_time)
                
        except DatabaseError as e:
            logger.error(f"Ошибка базы данных в start_command: {e}")
            await update.message.reply_text("❌ Ошибка базы данных. Попробуйте позже.")
        except Exception as e:
            logger.error(f"Ошибка в start_command: {e}")
            await update.message.reply_text("❌ Произошла ошибка. Попробуйте позже.")
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик нажатий на кнопки"""
        query = update.callback_query
        await query.answer()
        
        user = update.effective_user
        start_time = time.time()
        
        # Логируем все callback'и
        logger.info(f"Получен callback: {query.data} от пользователя {user.id}")
        
        try:
            if query.data == "get_rate":
                await self.rate_handler.handle_get_rate(update, context)
            elif query.data == "get_rates_list":
                await self.rate_handler.handle_get_rates_list(update, context)
            elif query.data == "wallets_menu":
                await self.wallet_handler.handle_wallets_menu(update, context)
            elif query.data == "tracking_menu":
                await self.crypto_tracking_handler.handle_tracking_menu(update, context)
            elif query.data.startswith("wallet_view_"):
                wallet_id = int(query.data.split("_")[-1])
                await self.wallet_handler.handle_wallet_view(update, context, wallet_id)
            elif query.data == "wallet_add":
                await self.wallet_handler.handle_wallet_add_init(update, context)
            elif query.data.startswith("wallet_rename_"):
                wallet_id = int(query.data.split("_")[-1])
                await self.handle_wallet_rename_init(update, context, wallet_id)
            elif query.data.startswith("wallet_readdress_"):
                wallet_id = int(query.data.split("_")[-1])
                await self.handle_wallet_readdress_init(update, context, wallet_id)
            elif query.data.startswith("wallet_delete_yes_"):
                wallet_id = int(query.data.split("_")[-1])
                logger.info(f"Обработка wallet_delete_yes для кошелька {wallet_id}")
                await self.wallet_handler.handle_wallet_delete_yes(update, context, wallet_id)
            elif query.data.startswith("wallet_delete_"):
                wallet_id = int(query.data.split("_")[-1])
                await self.wallet_handler.handle_wallet_delete_confirm(update, context, wallet_id)
            elif query.data == "wallet_delete_no":
                await self.wallet_handler.handle_wallets_menu(update, context)
            elif query.data == "back_to_menu":
                await self.handle_back_to_menu(update, context)
            elif query.data.startswith("tracking_"):
                await self.handle_tracking_callback(update, context)
                
        except BotError as e:
            logger.error(f"Ошибка бота в button_callback: {e}")
            await query.edit_message_text("❌ Произошла ошибка. Попробуйте позже.")
        except Exception as e:
            logger.error(f"Неожиданная ошибка в button_callback: {e}")
            await query.edit_message_text("❌ Произошла ошибка. Попробуйте позже.")
    
    async def message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработка входящих текстов для сценариев кошельков"""
        if not update.message or not update.effective_user:
            return
        
        user = update.effective_user
        text = update.message.text.strip()
        
        try:
            # Проверяем, ожидает ли бот ввод кошелька
            if self.wallet_handler.is_waiting_wallet_input(user.id):
                await self.wallet_handler.handle_wallet_add_message(update, context)
                return
            
            # Проверяем, ожидает ли бот ввод порога для отслеживания
            if self.crypto_tracking_handler.is_waiting_threshold_input(user.id):
                await self.crypto_tracking_handler.handle_tracking_threshold_message(update, context)
                return
            
            # Проверяем, ожидает ли бот поисковый запрос
            if self.crypto_tracking_handler.is_waiting_search_input(user.id):
                await self.crypto_tracking_handler.handle_tracking_search_message(update, context)
                return
            
            # Обработка других текстовых сообщений
            await update.message.reply_text(
                "💡 Используйте кнопки меню или команды для взаимодействия с ботом.\n"
                "Нажмите /start для открытия главного меню."
            )
            
        except ValidationError as e:
            await update.message.reply_text(f"❌ {e}")
        except WalletError as e:
            logger.error(f"Ошибка кошелька: {e}")
            await update.message.reply_text("❌ Ошибка работы с кошельком. Попробуйте позже.")
        except Exception as e:
            logger.error(f"Ошибка в message_handler: {e}")
            await update.message.reply_text("❌ Произошла ошибка. Попробуйте позже.")
    
    async def inline_query_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик inline запросов"""
        try:
            await self.inline_handler.handle_inline_query(update, context)
        except BotError as e:
            logger.error(f"Ошибка бота в inline_query_handler: {e}")
            await update.inline_query.answer([], cache_time=1)
        except Exception as e:
            logger.error(f"Неожиданная ошибка в inline_query_handler: {e}")
            await update.inline_query.answer([], cache_time=1)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
• 💼 USDT кошелек - управление кошельками
• 📊 Отслеживание курса - уведомления о изменениях
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
            
        except DatabaseError as e:
            logger.error(f"Ошибка базы данных в help_command: {e}")
        except Exception as e:
            logger.error(f"Ошибка в help_command: {e}")
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
            
        except DatabaseError as e:
            logger.error(f"Ошибка базы данных в stats_command: {e}")
            await update.message.reply_text("❌ Ошибка получения статистики")
        except Exception as e:
            logger.error(f"Ошибка в stats_command: {e}")
            await update.message.reply_text("❌ Ошибка получения статистики")
    
    async def handle_back_to_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик кнопки 'Назад в меню'"""
        query = update.callback_query
        user = update.effective_user
        start_time = time.time()
        
        try:
            # Приветственное сообщение
            welcome_message = "💱 <b>DOX // P2P</b>\n\nБот показывает реальный курс USDT анализируя общую ситуацию на биржах."
            
            # Создаем клавиатуру с кнопками
            keyboard = [
                [InlineKeyboardButton("💲 Получить курс", callback_data="get_rate")],
                [InlineKeyboardButton("📈 Список лучших курсов", callback_data="get_rates_list")],
                [InlineKeyboardButton("📊 Отслеживание курса", callback_data="tracking_menu")],
                [InlineKeyboardButton("💼 USDT кошелек", callback_data="wallets_menu")],
                [InlineKeyboardButton("🆘 Поддержка", url=bot_config.support_url)]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(welcome_message, parse_mode='HTML', reply_markup=reply_markup)
            
            # Логируем команду
            response_time = time.time() - start_time
            self.db.log_command(user.id, 'back_to_menu', '', response_time)
                
        except Exception as e:
            logger.error(f"Ошибка в handle_back_to_menu: {e}")
            await query.edit_message_text("❌ Произошла ошибка. Попробуйте позже.")
    
    # Удаляем заглушку, так как теперь есть полноценный обработчик
    
    async def handle_tracking_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик callback'ов для отслеживания"""
        query = update.callback_query
        user = update.effective_user
        
        try:
            if query.data == "tracking_select_crypto":
                await self.crypto_tracking_handler.handle_tracking_select_crypto(update, context)
            elif query.data == "tracking_my_list":
                await self.crypto_tracking_handler.handle_tracking_my_list(update, context)
            elif query.data == "tracking_settings":
                await self.crypto_tracking_handler.handle_tracking_settings(update, context)
            elif query.data.startswith("tracking_crypto_"):
                crypto = query.data.split("_")[-1]
                await self.crypto_tracking_handler.handle_tracking_crypto_toggle(update, context, crypto)
            elif query.data.startswith("tracking_manage_"):
                crypto = query.data.split("_")[-1]
                await self.crypto_tracking_handler.handle_tracking_manage(update, context, crypto)
            elif query.data.startswith("tracking_set_threshold_"):
                crypto = query.data.split("_")[-1]
                await self.crypto_tracking_handler.handle_tracking_set_threshold(update, context, crypto)
            elif query.data.startswith("tracking_threshold_"):
                parts = query.data.split("_")
                crypto = parts[2]
                threshold = float(parts[3])
                await self.crypto_tracking_handler.handle_tracking_threshold_set(update, context, crypto, threshold)
            elif query.data.startswith("tracking_toggle_"):
                crypto = query.data.split("_")[-1]
                await self.crypto_tracking_handler.handle_tracking_crypto_toggle(update, context, crypto)
            elif query.data.startswith("tracking_category_"):
                category = query.data.split("_")[-1]
                await self.crypto_tracking_handler.handle_tracking_category(update, context, category)
            elif query.data == "tracking_search":
                await self.crypto_tracking_handler.handle_tracking_search(update, context)
            elif query.data == "tracking_all":
                await self.crypto_tracking_handler.handle_tracking_all(update, context)
            else:
                await query.answer("Неизвестная команда")
        except Exception as e:
            logger.error(f"Ошибка в handle_tracking_callback: {e}")
            await query.answer("❌ Произошла ошибка")
    
    async def handle_wallet_rename_init(self, update: Update, context: ContextTypes.DEFAULT_TYPE, wallet_id: int) -> None:
        """Заглушка для переименования кошелька"""
        query = update.callback_query
        await query.answer("Функция в разработке")
    
    async def handle_wallet_readdress_init(self, update: Update, context: ContextTypes.DEFAULT_TYPE, wallet_id: int) -> None:
        """Заглушка для изменения адреса кошелька"""
        query = update.callback_query
        await query.answer("Функция в разработке")
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик ошибок"""
        logger.error(f"Ошибка: {context.error}")
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ Произошла ошибка. Попробуйте позже."
            )


async def cleanup_task(bot: TrustedCurrencyRateBot) -> None:
    """Периодическая очистка старых данных"""
    while True:
        try:
            # Очищаем старые данные из БД (старше 7 дней)
            deleted_db = bot.db.cleanup_old_data(days_to_keep=db_config.cleanup_days)
            
            # Очищаем старые файлы кэша (старше 24 часов)
            deleted_cache = bot.cache.cleanup_old_cache_files(max_age_hours=cache_config.max_age_hours)
            
            if deleted_db > 0 or deleted_cache > 0:
                logger.info(f"Очистка завершена: БД={deleted_db}, кэш={deleted_cache}")
            
            # Ждем до следующей очистки
            await asyncio.sleep(bot_config.cleanup_interval)
            
        except Exception as e:
            logger.error(f"Ошибка в задаче очистки: {e}")
            await asyncio.sleep(bot_config.cleanup_interval)


async def health_check(request) -> web.Response:
    """Health check endpoint для Railway"""
    try:
        return web.json_response({
            "status": "healthy",
            "timestamp": get_moscow_time().isoformat(),
            "service": "telegram-bot",
            "port": server_config.port,
            "uptime": "running"
        })
    except Exception as e:
        return web.json_response({
            "status": "error",
            "error": str(e),
            "timestamp": get_moscow_time().isoformat()
        }, status=500)


class HealthCheckHandler(http.server.BaseHTTPRequestHandler):
    """Простой HTTP обработчик для health check"""
    
    def do_GET(self) -> None:
        print(f"🔍 Получен запрос: {self.path}")
        if self.path in ['/health', '/']:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            response = {
                "status": "healthy",
                "timestamp": get_moscow_time().isoformat(),
                "service": "telegram-bot",
                "port": server_config.port,
                "uptime": "running"
            }
            
            import json
            self.wfile.write(json.dumps(response).encode())
            print(f"✅ Отправлен ответ: {response}")
        else:
            self.send_response(404)
            self.end_headers()
            print(f"❌ 404 для пути: {self.path}")
    
    def log_message(self, format, *args) -> None:
        # Отключаем логирование запросов
        pass


def run_simple_web_server() -> None:
    """Запуск простого HTTP сервера для health check"""
    port = server_config.port
    
    print(f"🌐 Запуск простого health check сервера на порту {port}")
    print(f"🌐 Health check доступен на: http://0.0.0.0:{port}/health")
    print(f"🌐 Переменная PORT: {os.getenv('PORT', 'не установлена')}")
    
    # Создаем сервер с возможностью переиспользования адреса
    class ReusableTCPServer(socketserver.TCPServer):
        allow_reuse_address = True
    
    try:
        with ReusableTCPServer((server_config.host, port), HealthCheckHandler) as httpd:
            print(f"✅ Health check сервер запущен на порту {port}")
            print(f"✅ Сервер слушает на {server_config.host}:{port}")
            httpd.serve_forever()
            
    except Exception as e:
        print(f"❌ Ошибка запуска простого сервера: {e}")
        print(f"❌ Тип ошибки: {type(e).__name__}")
        print(f"❌ Детали ошибки: {str(e)}")
        
        # Пробуем альтернативный порт
        try:
            alt_port = 8080
            print(f"🔄 Пробуем альтернативный порт {alt_port}")
            
            with ReusableTCPServer((server_config.host, alt_port), HealthCheckHandler) as httpd:
                print(f"✅ Health check сервер запущен на порту {alt_port}")
                httpd.serve_forever()
        except Exception as e2:
            print(f"❌ Ошибка на альтернативном порту: {e2}")


def main() -> None:
    """Основная функция для запуска бота"""
    # Создаем экземпляр бота
    bot = TrustedCurrencyRateBot()
    
    # Создаем приложение
    application = Application.builder().token(bot_config.token).build()
    
    # Устанавливаем ссылку на application в боте
    bot.application = application
    
    # Устанавливаем ссылку на application в обработчиках
    bot.crypto_tracking_handler.application = application
    
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
            interval=bot_config.cleanup_interval,
            first=60  # Первый запуск через минуту
        )
        print("✅ Задача очистки запланирована")
        
        # Запускаем задачу проверки цен для уведомлений
        async def check_prices_job(context):
            try:
                await bot.crypto_tracking_handler.check_price_alerts()
            except Exception as e:
                logger.error(f"Ошибка в задаче проверки цен: {e}")
        
        application.job_queue.run_repeating(
            check_prices_job,
            interval=bot_config.price_check_interval,
            first=120  # Первый запуск через 2 минуты
        )
        print("✅ Задача проверки цен запланирована")
    else:
        print("⚠️ JobQueue недоступен, задачи не запланированы")
    
    # Запускаем бота
    print("🤖 Запуск Trusted Currency Rate бота...")
    print("📱 Бот готов к работе!")
    print("💡 Отправьте /start боту для получения курсов USDT")
    print("🔄 Inline режим: @DoxP2P_bot [сумма] для конвертации")
    print("⚡ Оптимизирован для высокой нагрузки (500+ пользователей/день)")
    print(f"🔄 Кэширование: {cache_config.duration} сек, Rate limiting: {bot_config.rate_limit_cooldown} сек")
    
    # Запускаем HTTP сервер для health check в отдельном потоке
    print(f"🌐 Health check: http://localhost:{server_config.port}/health")
    print(f"🌐 Переменная PORT: {os.getenv('PORT', 'не установлена')}")
    print(f"🌐 Используемый порт: {server_config.port}")
    
    # Пробуем сначала простой HTTP сервер
    print("🚀 Запуск health check сервера...")
    web_thread = threading.Thread(target=run_simple_web_server, daemon=True)
    web_thread.start()
    
    # Небольшая задержка для запуска health check сервера
    print("⏳ Ожидание запуска health check сервера...")
    time.sleep(5)
    print("✅ Health check сервер должен быть запущен")
    
    # Используем run_polling() вместо await
    application.run_polling()


if __name__ == "__main__":
    main()
