#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Обработчик кошельков пользователей
"""

import logging
import time
from typing import Optional, List, Dict, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import DatabaseManager
from exceptions import WalletError, ValidationError
from validators import validate_wallet_address, validate_wallet_label
from config import bot_config

logger = logging.getLogger(__name__)


class WalletHandler:
    """Обработчик кошельков пользователей"""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.waiting_wallet_add: Dict[int, bool] = {}
        self.waiting_wallet_rename: Dict[int, int] = {}
        self.waiting_wallet_readdress: Dict[int, int] = {}
    
    def get_network_type(self, address: str) -> str:
        """Определяет тип сети по адресу кошелька"""
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
    
    def parse_wallet_input(self, text: str, label_optional_only: bool = False) -> tuple[bool, Optional[str], Optional[str], Optional[str]]:
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
            
            # Валидация адреса
            validate_wallet_address(address)
            
            # Валидация названия
            if label:
                label = validate_wallet_label(label)
            
            return True, address, label, None
        except ValidationError as e:
            return False, None, None, str(e)
        except Exception:
            return False, None, None, "❌ Не удалось разобрать сообщение. Попробуйте снова."
    
    async def handle_wallets_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик меню кошельков"""
        query = update.callback_query
        user = update.effective_user
        start_time = time.time()
        
        try:
            wallets = self.db.list_wallets(user.id)
            
            # Всегда показываем одинаковый текст
            text = (
                "💼 <b>Кошельки USDT</b>\n\n"
                "Добавьте адрес кошелька для приёма платежей и создания чеков.\n\n"
                "<b>Добавление кошелька:</b>\n"
                "<code>USDT - &lt;адрес&gt; [Название]</code>\n\n"
                "<b>Пример:</b>\n"
                "<code>USDT - PY3cykOJTeZUEGPHwSZxe29EdyznOB8X7 Реклама</code>\n\n"
                "<b>Создание чека:</b>\n"
                "<code>@DoxP2P_bot 50000 usdt *название*</code>\n\n"
                "<blockquote>Название необязательно, но рекомендуется для различения кошельков</blockquote>"
            )
            
            if not wallets:
                keyboard = [[InlineKeyboardButton("➕ Добавить кошелёк", callback_data="wallet_add")],
                            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")]]
                return await query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))

            # Отрисуем список кошельков кнопками
            buttons = []
            for w in wallets:
                title = w['label'] if w['label'] else w['address']
                buttons.append([InlineKeyboardButton(title, callback_data=f"wallet_view_{w['id']}")])
            buttons.append([InlineKeyboardButton("➕ Добавить кошелёк", callback_data="wallet_add")])
            buttons.append([InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")])
            await query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(buttons))
            
            # Логируем команду
            response_time = time.time() - start_time
            self.db.log_command(user.id, 'wallets_menu', '', response_time)
            
        except Exception as e:
            logger.error(f"Ошибка в handle_wallets_menu: {e}")
            await query.edit_message_text("❌ Произошла ошибка. Попробуйте позже.")
    
    async def handle_wallet_view(self, update: Update, context: ContextTypes.DEFAULT_TYPE, wallet_id: int) -> None:
        """Обработчик просмотра кошелька"""
        query = update.callback_query
        user = update.effective_user
        
        try:
            wallets = self.db.list_wallets(user.id)
            w = next((x for x in wallets if x['id'] == wallet_id), None)
            if not w:
                return await self.handle_wallets_menu(update, context)
            
            title = w['label'] if w['label'] else w['address']
            network_type = self.get_network_type(w['address'])
            text = (
                f"💼 <b>{title} ({network_type})</b>\n\n"
                f"Адрес: <code>{w['address']}</code>"
            )
            keyboard = [
                [InlineKeyboardButton("✏️ Переименовать", callback_data=f"wallet_rename_{w['id']}")],
                [InlineKeyboardButton("🔁 Сменить адрес", callback_data=f"wallet_readdress_{w['id']}")],
                [InlineKeyboardButton("🗑️ Удалить", callback_data=f"wallet_delete_{w['id']}")],
                [InlineKeyboardButton("⬅️ Назад", callback_data="wallets_menu")]
            ]
            await query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as e:
            logger.error(f"Ошибка в handle_wallet_view: {e}")
            await query.edit_message_text("❌ Произошла ошибка. Попробуйте позже.")
    
    async def handle_wallet_add_init(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик инициализации добавления кошелька"""
        query = update.callback_query
        user = update.effective_user
        
        try:
            # Проверяем лимит кошельков
            wallets = self.db.list_wallets(user.id)
            if len(wallets) >= bot_config.max_wallets_per_user:
                await query.edit_message_text(
                    f"❌ Достигнут лимит кошельков ({bot_config.max_wallets_per_user})\n\n"
                    "Удалите один из существующих кошельков, чтобы добавить новый."
                )
                return
            
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
    
    async def handle_wallet_add_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик сообщения для добавления кошелька"""
        user = update.effective_user
        text = update.message.text.strip()
        
        try:
            # Парсим ввод пользователя
            ok, address, label, error = self.parse_wallet_input(text)
            if not ok:
                return await update.message.reply_text(error)
            
            # Проверяем дубликаты
            existing = self.db.list_wallets(user.id)
            if any(w['address'].lower() == address.lower() for w in existing):
                return await update.message.reply_text("⚠️ Такой кошелек уже добавлен\n\nПопробуйте другой адрес:")
            
            # Сохраняем кошелек
            saved = self.db.add_wallet(user.id, address, label)
            self.waiting_wallet_add.pop(user.id, None)
            
            if saved:
                # Показываем кнопки из /start после успешного добавления
                keyboard = [
                    [InlineKeyboardButton("💲 Текущий курс", callback_data="get_rate")],
                    [InlineKeyboardButton("📈 Топ обменников", callback_data="get_rates_list")],
                    [InlineKeyboardButton("📊 Отслеживание цен", callback_data="tracking_menu")],
                    [InlineKeyboardButton("💼 Кошельки USDT", callback_data="wallets_menu")],
                    [InlineKeyboardButton("🆘 Поддержка", url=bot_config.support_url)]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    f"✅ **Кошелек добавлен**\n\nАдрес: `{address}`\n\nНазвание: {label or '—'}",
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text("❌ Не удалось сохранить кошелек. Попробуйте позже.")
                
        except ValidationError as e:
            await update.message.reply_text(f"❌ {e}")
        except Exception as e:
            logger.error(f"Ошибка добавления кошелька: {e}")
            await update.message.reply_text("❌ Произошла ошибка при добавлении кошелька.")
    
    async def handle_wallet_delete_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE, wallet_id: int) -> None:
        """Обработчик подтверждения удаления кошелька"""
        query = update.callback_query
        
        try:
            keyboard = [
                [InlineKeyboardButton("✅ Да, удалить", callback_data=f"wallet_delete_yes_{wallet_id}")],
                [InlineKeyboardButton("⬅️ Назад", callback_data=f"wallet_view_{wallet_id}")]
            ]
            await query.edit_message_text(
                "🗑️ <b>Удаление кошелька</b>\n\nУдалить этот кошелек?",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            logger.error(f"Ошибка в handle_wallet_delete_confirm: {e}")
            await query.answer("Попробуйте еще раз", show_alert=False)
    
    async def handle_wallet_delete_yes(self, update: Update, context: ContextTypes.DEFAULT_TYPE, wallet_id: int) -> None:
        """Обработчик удаления кошелька"""
        query = update.callback_query
        user = update.effective_user
        
        try:
            logger.info(f"Попытка удаления кошелька {wallet_id} для пользователя {user.id}")
            
            # Удаляем кошелек из БД
            success = self.db.delete_wallet(user.id, wallet_id)
            logger.info(f"Результат удаления кошелька {wallet_id}: {success}")
            
            if success:
                # Показываем сообщение об успешном удалении с кнопками из /start
                keyboard = [
                    [InlineKeyboardButton("💲 Текущий курс", callback_data="get_rate")],
                    [InlineKeyboardButton("📈 Топ обменников", callback_data="get_rates_list")],
                    [InlineKeyboardButton("📊 Отслеживание цен", callback_data="tracking_menu")],
                    [InlineKeyboardButton("💼 Кошельки USDT", callback_data="wallets_menu")],
                    [InlineKeyboardButton("🆘 Поддержка", url=bot_config.support_url)]
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
    
    def is_waiting_wallet_input(self, user_id: int) -> bool:
        """Проверить, ожидает ли бот ввод кошелька от пользователя"""
        return (user_id in self.waiting_wallet_add or 
                user_id in self.waiting_wallet_rename or 
                user_id in self.waiting_wallet_readdress)
