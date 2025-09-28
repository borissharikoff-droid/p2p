#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Кастомные исключения для бота
"""


class BotError(Exception):
    """Базовое исключение для бота"""
    pass


class BestChangeError(BotError):
    """Ошибка парсинга BestChange"""
    pass


class DatabaseError(BotError):
    """Ошибка работы с базой данных"""
    pass


class CacheError(BotError):
    """Ошибка работы с кэшем"""
    pass


class WalletError(BotError):
    """Ошибка работы с кошельками"""
    pass


class RateLimitError(BotError):
    """Ошибка превышения лимита запросов"""
    pass


class ValidationError(BotError):
    """Ошибка валидации данных"""
    pass
