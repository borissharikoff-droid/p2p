#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Менеджер кэширования для оптимизации работы с курсами
"""

import json
import os
import time
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from exceptions import CacheError

logger = logging.getLogger(__name__)


class CacheManager:
    """Менеджер кэширования для курсов валют"""
    
    def __init__(self, cache_dir: str = "cache", cache_duration: int = 60):
        """
        Инициализация менеджера кэша
        
        Args:
            cache_dir: Директория для хранения кэша
            cache_duration: Время жизни кэша в секундах (по умолчанию 60 сек)
        """
        self.cache_dir = cache_dir
        self.cache_duration = cache_duration
        self.cache_file = os.path.join(cache_dir, "rates_cache.json")
        
        # Создаем директорию кэша если её нет
        os.makedirs(cache_dir, exist_ok=True)
    
    def get_cached_rates(self) -> Optional[Any]:
        """Получить курсы из кэша (поддержка legacy списка и нового dict с buy/sell)"""
        try:
            if not os.path.exists(self.cache_file):
                return None
            
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # Проверяем, не истек ли кэш
            cache_time = datetime.fromisoformat(cache_data.get('timestamp', ''))
            age_seconds = (datetime.now() - cache_time).total_seconds()
            
            if age_seconds > self.cache_duration:
                logger.info(f"Кэш истек (возраст: {age_seconds:.1f}с), требуется обновление")
                return None
            
            logger.info(f"Используем данные из кэша (возраст: {age_seconds:.1f}с)")
            return cache_data.get('data')
            
        except Exception as e:
            logger.error(f"Ошибка чтения кэша: {e}")
            raise CacheError(f"Не удалось прочитать кэш: {e}")
    
    def set_cached_rates(self, rates_data: Any) -> bool:
        """Сохранить курсы в кэш (любой сериализуемый формат)"""
        try:
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'data': rates_data
            }
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            logger.info("Данные сохранены в кэш")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка сохранения кэша: {e}")
            raise CacheError(f"Не удалось сохранить кэш: {e}")
    
    def clear_cache(self) -> bool:
        """Очистить кэш"""
        try:
            if os.path.exists(self.cache_file):
                os.remove(self.cache_file)
                logger.info("Кэш очищен")
            return True
        except Exception as e:
            logger.error(f"Ошибка очистки кэша: {e}")
            return False
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Получить информацию о кэше"""
        try:
            if not os.path.exists(self.cache_file):
                return {
                    'exists': False,
                    'size': 0,
                    'age_seconds': 0
                }
            
            # Размер файла
            file_size = os.path.getsize(self.cache_file)
            
            # Возраст кэша
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            cache_time = datetime.fromisoformat(cache_data.get('timestamp', ''))
            age_seconds = (datetime.now() - cache_time).total_seconds()
            
            return {
                'exists': True,
                'size': file_size,
                'age_seconds': age_seconds,
                'is_expired': age_seconds > self.cache_duration
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения информации о кэше: {e}")
            return {
                'exists': False,
                'size': 0,
                'age_seconds': 0
            }
    
    def cleanup_old_cache_files(self, max_age_hours: int = 24) -> int:
        """Очистка старых файлов кэша"""
        try:
            if not os.path.exists(self.cache_dir):
                return 0
            
            current_time = time.time()
            deleted_count = 0
            
            for filename in os.listdir(self.cache_dir):
                file_path = os.path.join(self.cache_dir, filename)
                
                if os.path.isfile(file_path):
                    file_age_hours = (current_time - os.path.getmtime(file_path)) / 3600
                    
                    if file_age_hours > max_age_hours:
                        os.remove(file_path)
                        deleted_count += 1
                        logger.info(f"Удален старый файл кэша: {filename}")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Ошибка очистки старых файлов кэша: {e}")
            raise CacheError(f"Не удалось очистить старые файлы кэша: {e}")
