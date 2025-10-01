#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Обработчик inline запросов
"""

import logging
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
import pytz

from telegram import Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import ContextTypes

from database import DatabaseManager
from exceptions import ValidationError
from validators import validate_amount
from config import bot_config

logger = logging.getLogger(__name__)


def get_moscow_time() -> datetime:
    """Получить текущее московское время"""
    moscow_tz = pytz.timezone('Europe/Moscow')
    return datetime.now(moscow_tz)


class InlineHandler:
    """Обработчик inline запросов"""
    
    def __init__(self, db: DatabaseManager, rate_handler):
        self.db = db
        self.rate_handler = rate_handler
    
    def parse_inline_query(self, query: str) -> Dict[str, Any]:
        """Парсит inline запрос: сумма [валюта] [кошелек]"""
        try:
            parts = query.strip().split()
            if len(parts) < 1:
                return {'valid': False, 'error': 'Введите сумму для конвертации'}
            
            # Парсим сумму
            try:
                amount = validate_amount(parts[0])
            except ValidationError as e:
                return {'valid': False, 'error': str(e)}
            
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
    
    async def handle_inline_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
                            "💱 DOX // P2P\n\n"
                            "Введите сумму для конвертации валют:\n"
                            "• 8000 — показать все варианты\n"
                            "• 8000 usdt — конвертация USDT\n"
                            "• 8000 rub — конвертация рублей\n"
                            "• 8000 usdt кошелек — с выбором кошелька\n\n"
                            "Пример: @DoxP2P_bot 8000"
                        )
                    ),
                    InlineQueryResultArticle(
                        id=str(uuid.uuid4()),
                        title="💼 Создать чек с кошельком",
                        description="Пример: 10000 usdt мой_кошелек",
                        input_message_content=InputTextMessageContent(
                            "💼 Создание чека с кошельком\n\n"
                            "Формат: @DoxP2P_bot [сумма] usdt [название]\n\n"
                            "Примеры:\n"
                            "• @DoxP2P_bot 10000 usdt мой_кошелек\n"
                            "• @DoxP2P_bot 50000 usdt работа\n"
                            "• @DoxP2P_bot 15000 usdt (без названия)\n\n"
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
                            "• 1000 — конвертация рублей в USDT\n"
                            "• 50.5 — конвертация USDT в рубли\n\n"
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
                    rate = self.rate_handler.get_current_rate()
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
    
    async def create_dual_currency_suggestions(self, user_id: int, amount: float, rate: float) -> List[InlineQueryResultArticle]:
        """Создает предложения для обеих валют когда валюта не указана"""
        try:
            results = []
            
            # Конвертация USDT в рубли
            rub_amount = self.rate_handler.convert_currency(amount, "USDT", "RUB")
            # Вычисляем реальный курс продажи
            sell_rate = rub_amount / amount if amount > 0 else rate
            results.append(
                InlineQueryResultArticle(
                    id=f"usdt_to_rub_{amount}",
                    title=f"💵 {amount:,.2f} USDT = {rub_amount:,.2f}₽",
                    description="Конвертировать USDT в рубли",
                    input_message_content=InputTextMessageContent(
                        f"💵 Конвертация валют\n\n"
                        f"💰 Курс продажи: {sell_rate:.2f}₽ за 1 USDT\n"
                        f"💱 {amount:,.2f} USDT = {rub_amount:,.2f}₽\n\n"
                        f"🕘 Обновлено: {get_moscow_time().strftime('%H:%M %d.%m.%Y')}"
                    )
                )
            )
            
            # Конвертация рублей в USDT
            usdt_amount = self.rate_handler.convert_currency(amount, "RUB", "USDT")
            # Вычисляем реальный курс покупки
            buy_rate = amount / usdt_amount if usdt_amount > 0 else rate
            results.append(
                InlineQueryResultArticle(
                    id=f"rub_to_usdt_{amount}",
                    title=f"💰 {amount:,.2f}₽ = {usdt_amount:.4f} USDT",
                    description="Конвертировать рубли в USDT",
                    input_message_content=InputTextMessageContent(
                        f"💵 Конвертация валют\n\n"
                        f"💰 Курс покупки: {buy_rate:.2f}₽ за 1 USDT\n"
                        f"💱 {amount:,.2f}₽ = {usdt_amount:.4f} USDT\n\n"
                        f"🕘 Обновлено: {get_moscow_time().strftime('%H:%M %d.%m.%Y')}"
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
    
    def create_conversion_results(self, amount: float, currency: str, rate: float) -> List[InlineQueryResultArticle]:
        """Создает результаты для обычной конвертации без кошелька"""
        if currency == 'RUB':
            # Конвертируем рубли в USDT
            usdt_amount = self.rate_handler.convert_currency(amount, "RUB", "USDT")
            # Вычисляем реальный курс покупки
            buy_rate = amount / usdt_amount if usdt_amount > 0 else rate
            return [
                InlineQueryResultArticle(
                    id=str(uuid.uuid4()),
                    title=f"💰 {amount:,.2f}₽ = {usdt_amount:.4f} USDT",
                    description=f"Конвертировать {amount:,.2f} рублей в USDT",
                    input_message_content=InputTextMessageContent(
                        f"💵 Конвертация валют\n\n"
                        f"💰 Курс покупки: {buy_rate:.2f}₽ за 1 USDT\n"
                        f"💱 {amount:,.2f}₽ = {usdt_amount:.4f} USDT\n\n"
                        f"🕘 Обновлено: {get_moscow_time().strftime('%H:%M %d.%m.%Y')}"
                    )
                )
            ]
        else:
            # Конвертируем USDT в рубли
            rub_amount = self.rate_handler.convert_currency(amount, "USDT", "RUB")
            # Вычисляем реальный курс продажи
            sell_rate = rub_amount / amount if amount > 0 else rate
            return [
                InlineQueryResultArticle(
                    id=str(uuid.uuid4()),
                    title=f"💵 {amount:,.2f} USDT = {rub_amount:,.2f}₽",
                    description=f"Конвертировать {amount:,.2f} USDT в рубли",
                    input_message_content=InputTextMessageContent(
                        f"💵 Конвертация валют\n\n"
                        f"💰 Курс продажи: {sell_rate:.2f}₽ за 1 USDT\n"
                        f"💱 {amount:,.2f} USDT = {rub_amount:,.2f}₽\n\n"
                        f"🕘 Обновлено: {get_moscow_time().strftime('%H:%M %d.%m.%Y')}"
                    )
                )
            ]
    
    async def create_wallet_suggestions(self, user_id: int, amount: float, currency: str) -> List[InlineQueryResultArticle]:
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
            rate = self.rate_handler.get_current_rate()
            if not rate:
                rate = 83.0  # Fallback курс
            
            results = []
            
            # Создаем предложения для каждого кошелька
            for i, wallet in enumerate(wallets[:10]):  # Ограничиваем до 10 кошельков
                wallet_name = wallet['label'] if wallet['label'] else f"Кошелек {i+1}"
                
                if currency == 'RUB':
                    # Пользователь хочет получить рубли, отправитель отправляет USDT
                    usdt_to_send = self.rate_handler.convert_currency(amount, "RUB", "USDT")
                    title = f"💸 {amount:,.0f}₽ → {usdt_to_send:.2f} USDT"
                    description = f"💼 {wallet_name} • Получить {amount:,.0f}₽"
                else:
                    # Пользователь хочет получить USDT, отправитель отправляет рубли
                    rub_to_send = self.rate_handler.convert_currency(amount, "USDT", "RUB")
                    title = f"💸 {amount:,.0f} USDT → {rub_to_send:,.0f}₽"
                    description = f"💼 {wallet_name} • Получить {amount:,.0f} USDT"
                
                results.append(
                    InlineQueryResultArticle(
                        id=f"wallet_{wallet['id']}_{amount}_{currency}",
                        title=title,
                        description=description,
                        input_message_content=InputTextMessageContent(
                            f"💸 <b>Запрос на оплату</b>\n\n"
                            f"💰 Сумма к получению: {amount:,.2f}{'₽' if currency == 'RUB' else ' USDT'}\n"
                            + (f"💵 К отправке: {usdt_to_send:.4f} USDT\n" if currency == 'RUB' else f"💰 К отправке: {rub_to_send:,.2f}₽\n") +
                            f"📊 Курс: {rate:.2f}₽ за 1 USDT\n\n"
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
    
    async def create_payment_message(self, user_id: int, amount: float, currency: str, wallet_name: str, rate: float) -> List[InlineQueryResultArticle]:
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
                usdt_to_send = self.rate_handler.convert_currency(amount, "RUB", "USDT")
                message_text = (
                    f"💸 <b>Запрос на оплату</b>\n\n"
                    f"💰 Сумма к получению: {amount:,.2f}₽\n"
                    f"💵 К отправке: {usdt_to_send:.4f} USDT\n"
                    f"📊 Курс: {rate:.2f}₽ за 1 USDT\n\n"
                    f"📍 <b>Адрес для отправки:</b>\n"
                    f"<code>{wallet['address']}</code>\n\n"
                    f"⚠️ <b>Внимание:</b> Отправляйте только USDT TRC20 на указанный адрес!"
                )
                title = f"💸 {amount:,.2f}₽ → {usdt_to_send:.4f} USDT"
                description = f"Отправить {usdt_to_send:.4f} USDT на {wallet['label']}"
            else:
                # Пользователь хочет получить USDT, отправитель отправляет рубли
                rub_to_send = self.rate_handler.convert_currency(amount, "USDT", "RUB")
                message_text = (
                    f"💸 <b>Запрос на оплату</b>\n\n"
                    f"💵 Сумма к получению: {amount:,.2f} USDT\n"
                    f"💰 К отправке: {rub_to_send:,.2f}₽\n"
                    f"📊 Курс: {rate:.2f}₽ за 1 USDT\n\n"
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
