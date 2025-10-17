#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Валидаторы для данных бота
"""

import re
from typing import Optional
from exceptions import ValidationError


def validate_wallet_address(address: str) -> bool:
    """
    Валидация адреса USDT кошелька для всех поддерживаемых сетей
    
    Args:
        address: Адрес кошелька для проверки
        
    Returns:
        True если адрес валидный
        
    Raises:
        ValidationError: Если адрес невалидный
    """
    if not address or not isinstance(address, str):
        raise ValidationError("Адрес кошелька не может быть пустым")
    
    # TRC20 (Tron) - начинается с T, длина 34
    trc20_pattern = r'^T[A-Za-z1-9]{33}$'
    
    # ERC20 (Ethereum) - начинается с 0x, длина 42
    erc20_pattern = r'^0x[a-fA-F0-9]{40}$'
    
    # BEP20 (BSC) - начинается с 0x, длина 42 (как ERC20)
    bep20_pattern = r'^0x[a-fA-F0-9]{40}$'
    
    # Polygon (MATIC) - начинается с 0x, длина 42
    polygon_pattern = r'^0x[a-fA-F0-9]{40}$'
    
    # Arbitrum - начинается с 0x, длина 42
    arbitrum_pattern = r'^0x[a-fA-F0-9]{40}$'
    
    # Optimism - начинается с 0x, длина 42
    optimism_pattern = r'^0x[a-fA-F0-9]{40}$'
    
    # Avalanche (C-Chain) - начинается с 0x, длина 42
    avalanche_pattern = r'^0x[a-fA-F0-9]{40}$'
    
    # TON - начинается с UQ, длина 48
    ton_pattern = r'^UQ[A-Za-z0-9+/]{46}$'
    
    # Более гибкая проверка для других форматов
    flexible_pattern = r'^[A-Za-z0-9]{26,50}$'
    
    if re.match(trc20_pattern, address):
        return True
    elif re.match(erc20_pattern, address):
        return True
    elif re.match(bep20_pattern, address):
        return True
    elif re.match(polygon_pattern, address):
        return True
    elif re.match(arbitrum_pattern, address):
        return True
    elif re.match(optimism_pattern, address):
        return True
    elif re.match(avalanche_pattern, address):
        return True
    elif re.match(ton_pattern, address):
        return True
    elif re.match(flexible_pattern, address) and not address.startswith('0x'):
        return True
    else:
        raise ValidationError(
            f"Неверный формат адреса кошелька: {address}. "
            "Поддерживаются TRC20, ERC20, BEP20, Polygon, Arbitrum, Optimism, Avalanche, TON форматы"
        )


def validate_amount(amount: str) -> float:
    """
    Валидация суммы для конвертации
    
    Args:
        amount: Строка с суммой
        
    Returns:
        Валидная сумма как float
        
    Raises:
        ValidationError: Если сумма невалидная
    """
    if not amount or not isinstance(amount, str):
        raise ValidationError("Сумма не может быть пустой")
    
    try:
        # Заменяем запятую на точку для русской локали
        clean_amount = amount.replace(',', '.').strip()
        value = float(clean_amount)
        
        if value <= 0:
            raise ValidationError("Сумма должна быть больше 0")
        
        if value > 10000000:  # Максимальная сумма
            raise ValidationError("Сумма слишком большая (максимум 10,000,000)")
        
        return value
        
    except ValueError:
        raise ValidationError(f"Неверный формат суммы: {amount}")


def validate_wallet_label(label: Optional[str]) -> Optional[str]:
    """
    Валидация названия кошелька
    
    Args:
        label: Название кошелька
        
    Returns:
        Валидное название или None
        
    Raises:
        ValidationError: Если название невалидное
    """
    if not label:
        return None
    
    if not isinstance(label, str):
        raise ValidationError("Название кошелька должно быть строкой")
    
    # Очищаем от лишних пробелов
    clean_label = label.strip()
    
    if len(clean_label) > 64:
        raise ValidationError("Название кошелька слишком длинное (максимум 64 символа)")
    
    # Проверяем на недопустимые символы
    if re.search(r'[<>"\']', clean_label):
        raise ValidationError("Название кошелька содержит недопустимые символы")
    
    return clean_label if clean_label else None


def validate_crypto_symbol(symbol: str) -> str:
    """
    Валидация символа криптовалюты
    
    Args:
        symbol: Символ криптовалюты
        
    Returns:
        Валидный символ в верхнем регистре
        
    Raises:
        ValidationError: Если символ невалидный
    """
    if not symbol or not isinstance(symbol, str):
        raise ValidationError("Символ криптовалюты не может быть пустым")
    
    clean_symbol = symbol.strip().upper()
    
    # Проверяем формат (только буквы и цифры, 2-10 символов)
    if not re.match(r'^[A-Z0-9]{2,10}$', clean_symbol):
        raise ValidationError(f"Неверный формат символа криптовалюты: {symbol}")
    
    # Проверяем только формат, поддержка проверяется в crypto_api.py
    # Здесь мы только валидируем формат символа
    
    return clean_symbol


def validate_threshold(threshold: float) -> float:
    """
    Валидация порога изменения цены
    
    Args:
        threshold: Порог в процентах
        
    Returns:
        Валидный порог
        
    Raises:
        ValidationError: Если порог невалидный
    """
    if not isinstance(threshold, (int, float)):
        raise ValidationError("Порог должен быть числом")
    
    if threshold < 1.0:
        raise ValidationError("Минимальный порог: 1%")
    
    if threshold > 50:
        raise ValidationError("Максимальный порог: 50%")
    
    return float(threshold)


def get_network_type(address: str) -> str:
    """
    Определяет тип сети USDT по адресу кошелька
    
    Args:
        address: Адрес кошелька
        
    Returns:
        Тип сети с эмодзи и названием
    """
    if not address or not isinstance(address, str):
        return "USDT"
    
    address = address.strip()
    
    # TRC20 (Tron) - начинается с T, длина 34
    if re.match(r'^T[A-Za-z1-9]{33}$', address):
        return "🟢 USDT TRC20"
    
    # TON - начинается с UQ, длина 48
    if re.match(r'^UQ[A-Za-z0-9+/]{46}$', address):
        return "🔵 USDT TON"
    
    # ERC20-совместимые сети (0x + 40 hex)
    if re.match(r'^0x[a-fA-F0-9]{40}$', address):
        # Для точного определения нужны дополнительные проверки
        # Пока возвращаем общий тип для всех EVM-совместимых сетей
        return "🟣 USDT EVM"
    
    # Другие форматы
    if re.match(r'^[A-Za-z0-9]{26,50}$', address) and not address.startswith('0x'):
        return "🟡 USDT"
    
    return "USDT"
