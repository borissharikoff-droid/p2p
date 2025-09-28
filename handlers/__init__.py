#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Пакет обработчиков для Telegram бота
"""

from .rate_handler import RateHandler
from .wallet_handler import WalletHandler
from .inline_handler import InlineHandler

__all__ = ['RateHandler', 'WalletHandler', 'InlineHandler']
