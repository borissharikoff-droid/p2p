#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Конфигурация бота - централизованное управление настройками
"""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()


@dataclass
class BotConfig:
    """Конфигурация Telegram бота"""
    token: str
    cache_duration: int = 60
    rate_limit_cooldown: int = 30
    max_wallets_per_user: int = 10
    cleanup_interval: int = 3600
    price_check_interval: int = 300
    support_url: str = "https://t.me/doxpublisher"
    
    @classmethod
    def from_env(cls) -> 'BotConfig':
        """Создать конфигурацию из переменных окружения"""
        token = os.getenv('BOT_TOKEN')
        if not token:
            print("⚠️ BOT_TOKEN не найден в переменных окружения!")
            print("⚠️ Установите переменную BOT_TOKEN в Railway")
            raise ValueError("BOT_TOKEN не установлен! Установите переменную окружения BOT_TOKEN")
        
        return cls(
            token=token,
            cache_duration=int(os.getenv('CACHE_DURATION', 60)),
            rate_limit_cooldown=int(os.getenv('RATE_LIMIT_COOLDOWN', 30)),
            max_wallets_per_user=int(os.getenv('MAX_WALLETS_PER_USER', 10)),
            cleanup_interval=int(os.getenv('CLEANUP_INTERVAL', 3600)),
            price_check_interval=int(os.getenv('PRICE_CHECK_INTERVAL', 300)),
            support_url=os.getenv('SUPPORT_URL', "https://t.me/doxpublisher")
        )


@dataclass
class DatabaseConfig:
    """Конфигурация базы данных"""
    path: str = "bot_database.db"
    cleanup_days: int = 7
    
    @classmethod
    def from_env(cls) -> 'DatabaseConfig':
        """Создать конфигурацию БД из переменных окружения"""
        return cls(
            path=os.getenv('DATABASE_PATH', "bot_database.db"),
            cleanup_days=int(os.getenv('DATABASE_CLEANUP_DAYS', 7))
        )


@dataclass
class CacheConfig:
    """Конфигурация кэширования"""
    directory: str = "cache"
    duration: int = 60
    max_age_hours: int = 24
    
    @classmethod
    def from_env(cls) -> 'CacheConfig':
        """Создать конфигурацию кэша из переменных окружения"""
        return cls(
            directory=os.getenv('CACHE_DIRECTORY', "cache"),
            duration=int(os.getenv('CACHE_DURATION', 60)),
            max_age_hours=int(os.getenv('CACHE_MAX_AGE_HOURS', 24))
        )


@dataclass
class ServerConfig:
    """Конфигурация сервера для Railway"""
    port: int = 8080
    host: str = "0.0.0.0"
    
    @classmethod
    def from_env(cls) -> 'ServerConfig':
        """Создать конфигурацию сервера из переменных окружения"""
        return cls(
            port=int(os.getenv('PORT', 8080)),
            host=os.getenv('HOST', "0.0.0.0")
        )


# Глобальные экземпляры конфигурации
bot_config = BotConfig.from_env()
db_config = DatabaseConfig.from_env()
cache_config = CacheConfig.from_env()
server_config = ServerConfig.from_env()
