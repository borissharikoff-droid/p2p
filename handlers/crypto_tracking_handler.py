#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Обработчик отслеживания криптовалют
"""

import logging
import time
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import pytz

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import DatabaseManager
from exceptions import ValidationError, DatabaseError
from validators import validate_crypto_symbol, validate_threshold
from config import bot_config
from crypto_api import get_crypto_price, get_multiple_crypto_prices

logger = logging.getLogger(__name__)


def get_moscow_time() -> datetime:
    """Получить текущее московское время"""
    moscow_tz = pytz.timezone('Europe/Moscow')
    return datetime.now(moscow_tz)


class CryptoTrackingHandler:
    """Обработчик отслеживания криптовалют"""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.waiting_threshold_input: Dict[int, str] = {}  # user_id -> crypto
        
        # Список поддерживаемых криптовалют с эмодзи
        self.supported_cryptos = {
            'BTC': {'name': 'Bitcoin', 'emoji': '₿', 'color': '🟠'},
            'ETH': {'name': 'Ethereum', 'emoji': 'Ξ', 'color': '🔵'},
            'USDT': {'name': 'Tether', 'emoji': '₮', 'color': '🟢'},
            'BNB': {'name': 'Binance Coin', 'emoji': '🟡', 'color': '🟡'},
            'ADA': {'name': 'Cardano', 'emoji': '🔵', 'color': '🔵'},
            'SOL': {'name': 'Solana', 'emoji': '🟣', 'color': '🟣'},
            'XRP': {'name': 'Ripple', 'emoji': '💧', 'color': '💧'},
            'DOT': {'name': 'Polkadot', 'emoji': '🔴', 'color': '🔴'},
            'DOGE': {'name': 'Dogecoin', 'emoji': '🐕', 'color': '🐕'},
            'MATIC': {'name': 'Polygon', 'emoji': '🟣', 'color': '🟣'},
            'LTC': {'name': 'Litecoin', 'emoji': '⚡', 'color': '⚡'},
            'BCH': {'name': 'Bitcoin Cash', 'emoji': '💰', 'color': '💰'},
            'LINK': {'name': 'Chainlink', 'emoji': '🔗', 'color': '🔗'},
            'UNI': {'name': 'Uniswap', 'emoji': '🦄', 'color': '🦄'}
        }
    
    async def handle_tracking_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик главного меню отслеживания"""
        query = update.callback_query
        user = update.effective_user
        start_time = time.time()
        
        try:
            # Получаем текущие настройки пользователя
            user_trackings = self.db.get_tracking_settings(user.id)
            active_count = sum(1 for t in user_trackings if t.get('is_active', False))
            
            message = "📊 <b>Отслеживание криптовалют</b>\n\n"
            message += f"🔔 Активных отслеживаний: <b>{active_count}</b>\n\n"
            message += "<b>Как это работает:</b>\n"
            message += "• Выберите криптовалюту для отслеживания\n"
            message += "• Установите порог изменения цены (например, 5%)\n"
            message += "• Получайте уведомления при росте/падении\n\n"
            message += "<b>Формат уведомлений:</b>\n"
            message += "🟢 $BTC: 45,250 (+5.15%)\n"
            message += "🔴 $ETH: 2,850 (-3.20%)\n\n"
            message += "Выберите действие:"
            
            keyboard = [
                [InlineKeyboardButton("🪙 Выбрать криптовалюты", callback_data="tracking_select_crypto")],
                [InlineKeyboardButton("📋 Мои отслеживания", callback_data="tracking_my_list")],
                [InlineKeyboardButton("⚙️ Настройки", callback_data="tracking_settings")],
                [InlineKeyboardButton("🏠 Назад", callback_data="back_to_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(message, parse_mode='HTML', reply_markup=reply_markup)
            
            # Логируем команду
            response_time = time.time() - start_time
            self.db.log_command(user.id, 'tracking_menu', '', response_time)
            
        except DatabaseError as e:
            logger.error(f"Ошибка базы данных в tracking_menu: {e}")
            await query.edit_message_text("❌ Ошибка базы данных. Попробуйте позже.")
        except Exception as e:
            logger.error(f"Ошибка в tracking_menu: {e}")
            await query.edit_message_text("❌ Произошла ошибка. Попробуйте позже.")
    
    async def handle_tracking_select_crypto(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик выбора криптовалют для отслеживания"""
        query = update.callback_query
        user = update.effective_user
        start_time = time.time()
        
        try:
            # Получаем текущие настройки пользователя
            user_trackings = self.db.get_tracking_settings(user.id)
            tracked_cryptos = {t['crypto'] for t in user_trackings if t.get('is_active', True)}
            
            message = "🪙 <b>Выбор криптовалют для отслеживания</b>\n\n"
            message += "Выберите криптовалюты, за которыми хотите следить:\n\n"
            
            # Создаем кнопки для каждой криптовалюты
            keyboard = []
            for i in range(0, len(self.supported_cryptos), 2):
                row = []
                cryptos_list = list(self.supported_cryptos.items())
                for j in range(2):
                    if i + j < len(cryptos_list):
                        crypto, info = cryptos_list[i + j]
                        is_tracked = crypto in tracked_cryptos
                        button_text = f"{'✅' if is_tracked else '⬜'} {info['emoji']} {crypto}"
                        row.append(InlineKeyboardButton(button_text, callback_data=f"tracking_crypto_{crypto}"))
                keyboard.append(row)
            
            keyboard.append([InlineKeyboardButton("🏠 Назад", callback_data="tracking_menu")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(message, parse_mode='HTML', reply_markup=reply_markup)
            
            # Логируем команду
            response_time = time.time() - start_time
            self.db.log_command(user.id, 'tracking_select_crypto', '', response_time)
            
        except DatabaseError as e:
            logger.error(f"Ошибка базы данных в tracking_select_crypto: {e}")
            await query.edit_message_text("❌ Ошибка базы данных. Попробуйте позже.")
        except Exception as e:
            logger.error(f"Ошибка в tracking_select_crypto: {e}")
            await query.edit_message_text("❌ Произошла ошибка. Попробуйте позже.")
    
    async def handle_tracking_crypto_toggle(self, update: Update, context: ContextTypes.DEFAULT_TYPE, crypto: str) -> None:
        """Обработчик включения/выключения отслеживания криптовалюты"""
        query = update.callback_query
        user = update.effective_user
        
        try:
            # Валидируем символ криптовалюты
            crypto = validate_crypto_symbol(crypto)
            
            # Получаем текущие настройки
            user_trackings = self.db.get_tracking_settings(user.id)
            current_tracking = next((t for t in user_trackings if t['crypto'] == crypto), None)
            
            if current_tracking and current_tracking.get('is_active', False):
                # Отключаем отслеживание
                success = self.db.toggle_crypto_tracking(user.id, crypto)
                if success:
                    await query.answer(f"❌ Отслеживание {crypto} отключено")
                else:
                    await query.answer("❌ Ошибка отключения отслеживания")
            else:
                # Включаем отслеживание с порогом по умолчанию
                success = self.db.toggle_crypto_tracking(user.id, crypto)
                if success:
                    # Устанавливаем порог по умолчанию 5%
                    self.db.set_tracking_threshold(user.id, crypto, 5.0)
                    await query.answer(f"✅ Отслеживание {crypto} включено (порог: 5%)")
                else:
                    await query.answer("❌ Ошибка включения отслеживания")
            
            # Обновляем меню
            await self.handle_tracking_select_crypto(update, context)
            
        except ValidationError as e:
            await query.answer(f"❌ {e}")
        except DatabaseError as e:
            logger.error(f"Ошибка базы данных в tracking_crypto_toggle: {e}")
            await query.answer("❌ Ошибка базы данных")
        except Exception as e:
            logger.error(f"Ошибка в tracking_crypto_toggle: {e}")
            await query.answer("❌ Произошла ошибка")
    
    async def handle_tracking_my_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик списка моих отслеживаний"""
        query = update.callback_query
        user = update.effective_user
        start_time = time.time()
        
        try:
            # Получаем настройки пользователя
            user_trackings = self.db.get_tracking_settings(user.id)
            active_trackings = [t for t in user_trackings if t.get('is_active', False)]
            
            if not active_trackings:
                message = "📋 <b>Мои отслеживания</b>\n\n"
                message += "У вас нет активных отслеживаний.\n\n"
                message += "Нажмите \"Выбрать криптовалюты\" чтобы добавить отслеживание."
                
                keyboard = [
                    [InlineKeyboardButton("🪙 Выбрать криптовалюты", callback_data="tracking_select_crypto")],
                    [InlineKeyboardButton("🏠 Назад", callback_data="tracking_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(message, parse_mode='HTML', reply_markup=reply_markup)
                return
            
            message = "📋 <b>Мои отслеживания</b>\n\n"
            
            # Создаем кнопки для каждого отслеживания
            keyboard = []
            for tracking in active_trackings:
                crypto = tracking['crypto']
                threshold = tracking['threshold']
                last_price = tracking.get('last_price')
                
                if crypto in self.supported_cryptos:
                    info = self.supported_cryptos[crypto]
                    price_text = f"${last_price:,.2f}" if last_price else "—"
                    
                    button_text = f"{info['emoji']} {crypto} • {threshold}% • {price_text}"
                    keyboard.append([InlineKeyboardButton(button_text, callback_data=f"tracking_manage_{crypto}")])
            
            keyboard.append([InlineKeyboardButton("🏠 Назад", callback_data="tracking_menu")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(message, parse_mode='HTML', reply_markup=reply_markup)
            
            # Логируем команду
            response_time = time.time() - start_time
            self.db.log_command(user.id, 'tracking_my_list', '', response_time)
            
        except DatabaseError as e:
            logger.error(f"Ошибка базы данных в tracking_my_list: {e}")
            await query.edit_message_text("❌ Ошибка базы данных. Попробуйте позже.")
        except Exception as e:
            logger.error(f"Ошибка в tracking_my_list: {e}")
            await query.edit_message_text("❌ Произошла ошибка. Попробуйте позже.")
    
    async def handle_tracking_manage(self, update: Update, context: ContextTypes.DEFAULT_TYPE, crypto: str) -> None:
        """Обработчик управления конкретным отслеживанием"""
        query = update.callback_query
        user = update.effective_user
        
        try:
            # Валидируем символ криптовалюты
            crypto = validate_crypto_symbol(crypto)
            
            # Получаем настройки для этой криптовалюты
            user_trackings = self.db.get_tracking_settings(user.id)
            tracking = next((t for t in user_trackings if t['crypto'] == crypto), None)
            
            if not tracking:
                await query.answer("❌ Отслеживание не найдено")
                return
            
            if crypto in self.supported_cryptos:
                info = self.supported_cryptos[crypto]
                threshold = tracking['threshold']
                last_price = tracking.get('last_price')
                price_text = f"${last_price:,.2f}" if last_price else "—"
                
                message = f"⚙️ <b>Управление отслеживанием</b>\n\n"
                message += f"{info['emoji']} <b>{crypto} ({info['name']})</b>\n"
                message += f"📊 Текущая цена: <b>{price_text}</b>\n"
                message += f"🔔 Порог уведомлений: <b>{threshold}%</b>\n\n"
                message += "Выберите действие:"
                
                keyboard = [
                    [InlineKeyboardButton(f"📊 Изменить порог ({threshold}%)", callback_data=f"tracking_set_threshold_{crypto}")],
                    [InlineKeyboardButton("❌ Отключить отслеживание", callback_data=f"tracking_toggle_{crypto}")],
                    [InlineKeyboardButton("⬅️ Назад к списку", callback_data="tracking_my_list")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(message, parse_mode='HTML', reply_markup=reply_markup)
            
        except ValidationError as e:
            await query.answer(f"❌ {e}")
        except DatabaseError as e:
            logger.error(f"Ошибка базы данных в tracking_manage: {e}")
            await query.answer("❌ Ошибка базы данных")
        except Exception as e:
            logger.error(f"Ошибка в tracking_manage: {e}")
            await query.answer("❌ Произошла ошибка")
    
    async def handle_tracking_set_threshold(self, update: Update, context: ContextTypes.DEFAULT_TYPE, crypto: str) -> None:
        """Обработчик установки порога уведомлений"""
        query = update.callback_query
        user = update.effective_user
        
        try:
            # Валидируем символ криптовалюты
            crypto = validate_crypto_symbol(crypto)
            
            if crypto in self.supported_cryptos:
                info = self.supported_cryptos[crypto]
                
                message = f"📊 <b>Установка порога для {crypto}</b>\n\n"
                message += f"{info['emoji']} <b>{crypto} ({info['name']})</b>\n\n"
                message += "Введите порог изменения цены в процентах:\n\n"
                message += "<b>Примеры:</b>\n"
                message += "• <code>5</code> - уведомления при изменении на 5%\n"
                message += "• <code>2.5</code> - уведомления при изменении на 2.5%\n"
                message += "• <code>10</code> - уведомления при изменении на 10%\n\n"
                message += "Минимум: 1%, Максимум: 50%"
                
                keyboard = [
                    [InlineKeyboardButton("1%", callback_data=f"tracking_threshold_{crypto}_1")],
                    [InlineKeyboardButton("2.5%", callback_data=f"tracking_threshold_{crypto}_2.5")],
                    [InlineKeyboardButton("5%", callback_data=f"tracking_threshold_{crypto}_5")],
                    [InlineKeyboardButton("10%", callback_data=f"tracking_threshold_{crypto}_10")],
                    [InlineKeyboardButton("⬅️ Назад", callback_data=f"tracking_manage_{crypto}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(message, parse_mode='HTML', reply_markup=reply_markup)
                
                # Устанавливаем ожидание ввода порога
                self.waiting_threshold_input[user.id] = crypto
            
        except ValidationError as e:
            await query.answer(f"❌ {e}")
        except Exception as e:
            logger.error(f"Ошибка в tracking_set_threshold: {e}")
            await query.answer("❌ Произошла ошибка")
    
    async def handle_tracking_threshold_set(self, update: Update, context: ContextTypes.DEFAULT_TYPE, crypto: str, threshold: float) -> None:
        """Обработчик установки конкретного порога"""
        query = update.callback_query
        user = update.effective_user
        
        try:
            # Валидируем данные
            crypto = validate_crypto_symbol(crypto)
            threshold = validate_threshold(threshold)
            
            # Устанавливаем порог
            success = self.db.set_tracking_threshold(user.id, crypto, threshold)
            
            if success:
                await query.answer(f"✅ Порог для {crypto} установлен: {threshold}%")
                # Возвращаемся к управлению отслеживанием
                await self.handle_tracking_manage(update, context, crypto)
            else:
                await query.answer("❌ Ошибка установки порога")
            
        except ValidationError as e:
            await query.answer(f"❌ {e}")
        except DatabaseError as e:
            logger.error(f"Ошибка базы данных в tracking_threshold_set: {e}")
            await query.answer("❌ Ошибка базы данных")
        except Exception as e:
            logger.error(f"Ошибка в tracking_threshold_set: {e}")
            await query.answer("❌ Произошла ошибка")
    
    async def handle_tracking_threshold_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик текстового ввода порога"""
        if not update.message or not update.effective_user:
            return
        
        user = update.effective_user
        text = update.message.text.strip()
        
        try:
            # Проверяем, ожидает ли бот ввод порога
            if user.id not in self.waiting_threshold_input:
                return
            
            crypto = self.waiting_threshold_input[user.id]
            
            # Валидируем введенный порог
            threshold = validate_threshold(float(text))
            crypto = validate_crypto_symbol(crypto)
            
            # Устанавливаем порог
            success = self.db.set_tracking_threshold(user.id, crypto, threshold)
            
            if success:
                # Убираем из ожидания
                del self.waiting_threshold_input[user.id]
                
                # Показываем успешное сообщение
                if crypto in self.supported_cryptos:
                    info = self.supported_cryptos[crypto]
                    message = f"✅ <b>Порог установлен</b>\n\n"
                    message += f"{info['emoji']} <b>{crypto} ({info['name']})</b>\n"
                    message += f"🔔 Порог уведомлений: <b>{threshold}%</b>\n\n"
                    message += "Теперь вы будете получать уведомления при изменении цены на указанный процент."
                    
                    keyboard = [
                        [InlineKeyboardButton("📋 Мои отслеживания", callback_data="tracking_my_list")],
                        [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await update.message.reply_text(message, parse_mode='HTML', reply_markup=reply_markup)
                else:
                    await update.message.reply_text(f"✅ Порог для {crypto} установлен: {threshold}%")
            else:
                await update.message.reply_text("❌ Ошибка установки порога. Попробуйте еще раз.")
                
        except ValidationError as e:
            await update.message.reply_text(f"❌ {e}\n\nПопробуйте еще раз:")
        except ValueError:
            await update.message.reply_text("❌ Неверный формат числа. Введите число (например: 5 или 2.5)")
        except Exception as e:
            logger.error(f"Ошибка в tracking_threshold_message: {e}")
            await update.message.reply_text("❌ Произошла ошибка. Попробуйте еще раз.")
    
    def is_waiting_threshold_input(self, user_id: int) -> bool:
        """Проверить, ожидает ли бот ввод порога от пользователя"""
        return user_id in self.waiting_threshold_input
    
    async def send_price_notification(self, user_id: int, crypto: str, current_price: float, 
                                    previous_price: float, change_percent: float, threshold: float) -> None:
        """Отправить уведомление об изменении цены"""
        try:
            if crypto not in self.supported_cryptos:
                return
            
            info = self.supported_cryptos[crypto]
            
            # Определяем цвет и символ изменения
            if change_percent > 0:
                color = "🟢"
                change_symbol = "+"
            else:
                color = "🔴"
                change_symbol = ""
            
            # Форматируем сообщение
            message = f"{color}${crypto}: {current_price:,.2f} ({change_symbol}{change_percent:.2f}%)\n"
            message += f"📊 Порог: {threshold}% • {info['name']}"
            
            # Отправляем уведомление
            if self.application:
                await self.application.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode='HTML'
                )
                
                # Обновляем время последнего уведомления
                self.db.update_tracking_notification(user_id, crypto)
                
                logger.info(f"Отправлено уведомление пользователю {user_id}: {crypto} {change_percent:.2f}%")
            
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления: {e}")
    
    async def get_crypto_price(self, crypto: str) -> Optional[float]:
        """Получить текущую цену криптовалюты"""
        try:
            # Используем реальный API
            price = await get_crypto_price(crypto)
            
            if price:
                return price
            
            # Fallback к моковым данным если API недоступен
            logger.warning(f"API недоступен, используем моковые данные для {crypto}")
            mock_prices = {
                'BTC': 45000.0,
                'ETH': 2800.0,
                'USDT': 1.0,
                'BNB': 320.0,
                'ADA': 0.45,
                'SOL': 95.0,
                'XRP': 0.52,
                'DOT': 6.8,
                'DOGE': 0.08,
                'MATIC': 0.85,
                'LTC': 72.0,
                'BCH': 240.0,
                'LINK': 14.5,
                'UNI': 6.2
            }
            
            return mock_prices.get(crypto.upper())
            
        except Exception as e:
            logger.error(f"Ошибка получения цены {crypto}: {e}")
            return None
    
    async def check_price_alerts(self) -> None:
        """Проверить все активные отслеживания и отправить уведомления"""
        try:
            # Получаем все активные отслеживания
            active_trackings = self.db.get_active_trackings()
            
            if not active_trackings:
                return
            
            # Группируем по криптовалютам для оптимизации запросов
            cryptos_to_check = list(set(tracking['crypto'] for tracking in active_trackings))
            
            for crypto in cryptos_to_check:
                # Получаем текущую цену
                current_price = await self.get_crypto_price(crypto)
                
                if not current_price:
                    continue
                
                # Находим все отслеживания для этой криптовалюты
                crypto_trackings = [t for t in active_trackings if t['crypto'] == crypto]
                
                for tracking in crypto_trackings:
                    user_id = tracking['user_id']
                    threshold = tracking['threshold']
                    last_price = tracking['last_price']
                    last_notification = tracking['last_notification']
                    
                    # Если это первая цена или цена изменилась
                    if last_price is None:
                        # Сохраняем первую цену
                        self.db.update_tracking_price(user_id, crypto, current_price)
                        continue
                    
                    # Вычисляем изменение в процентах
                    change_percent = ((current_price - last_price) / last_price) * 100
                    
                    # Проверяем, превышен ли порог
                    if abs(change_percent) >= threshold:
                        # Проверяем, не отправляли ли уведомление недавно (защита от спама)
                        if self.should_send_notification(last_notification):
                            await self.send_price_notification(
                                user_id, crypto, current_price, last_price, change_percent, threshold
                            )
                    
                    # Обновляем последнюю цену
                    self.db.update_tracking_price(user_id, crypto, current_price)
                    
        except Exception as e:
            logger.error(f"Ошибка проверки уведомлений: {e}")
    
    def should_send_notification(self, last_notification: str) -> bool:
        """Проверить, можно ли отправлять уведомление (защита от спама)"""
        try:
            if not last_notification:
                return True
            
            # Парсим время последнего уведомления
            last_time = datetime.fromisoformat(last_notification)
            current_time = get_moscow_time()
            
            # Не отправляем уведомления чаще чем раз в 30 минут
            time_diff = (current_time - last_time).total_seconds()
            return time_diff >= 1800  # 30 минут
            
        except Exception:
            return True  # Если ошибка парсинга, разрешаем отправку
