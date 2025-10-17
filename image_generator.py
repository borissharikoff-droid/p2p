#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор изображений для курсов валют
Использует базовую картинку и накладывает только цифры справа
"""

import os
import logging
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)

class CurrencyImageGenerator:
    """Генератор изображений курсов валют"""
    
    def __init__(self):
        self.base_template_path = 'base_template.png'
        
        # Загружаем шрифт
        self._load_font()
    
    def _load_font(self):
        """Загружает шрифт для отображения цифр"""
        try:
            font_path = '/System/Library/Fonts/Supplemental/Arial Unicode.ttf'
            if os.path.exists(font_path):
                self.rate_font = ImageFont.truetype(font_path, 32)
                self.time_font = ImageFont.truetype(font_path, 16)
                logger.info(f"Используется шрифт: {font_path}")
            else:
                raise FileNotFoundError(f"Шрифт не найден: {font_path}")
        except Exception as e:
            logger.warning(f"Не удалось загрузить шрифт: {e}. Используется шрифт по умолчанию.")
            self.rate_font = ImageFont.load_default(size=32)
            self.time_font = ImageFont.load_default(size=16)
    
    def generate_currency_card(self, buy_rate: float, sell_rate: float, avg_rate: float = None) -> str:
        """
        Генерирует карточку с курсами валют
        
        Args:
            buy_rate: Курс покупки
            sell_rate: Курс продажи
            avg_rate: Средний курс (не используется, но оставлен для совместимости)
            
        Returns:
            str: Путь к созданному файлу изображения
        """
        try:
            # Проверяем существование базового шаблона
            if not os.path.exists(self.base_template_path):
                logger.error(f"Базовый шаблон не найден: {self.base_template_path}")
                return None
            
            # Загружаем базовую картинку
            img = Image.open(self.base_template_path)
            draw = ImageDraw.Draw(img)
            
            # Получаем текущее время
            moscow_tz = pytz.timezone('Europe/Moscow')
            current_time = datetime.now(moscow_tz)
            time_str = current_time.strftime("%H:%M • %d.%m.%Y")
            
            # Форматируем курсы
            buy_text = f"{buy_rate:.2f}₽"
            sell_text = f"{sell_rate:.2f}₽"
            
            # Координаты для наложения цифр (рассчитаны для базовой картинки)
            # Позиции для курсов справа в карточке
            buy_x = 420  # X координата для курса покупки
            buy_y = 120  # Y координата для курса покупки
            
            sell_x = 420  # X координата для курса продажи  
            sell_y = 185  # Y координата для курса продажи
            
            # Позиция для времени в нижней карточке
            time_x = 200  # X координата для времени
            time_y = 320  # Y координата для времени
            
            # Получаем размеры текста для правильного позиционирования
            buy_bbox = draw.textbbox((0, 0), buy_text, font=self.rate_font)
            buy_width = buy_bbox[2] - buy_bbox[0]
            
            sell_bbox = draw.textbbox((0, 0), sell_text, font=self.rate_font)
            sell_width = sell_bbox[2] - sell_bbox[0]
            
            time_bbox = draw.textbbox((0, 0), time_str, font=self.time_font)
            time_width = time_bbox[2] - time_bbox[0]
            
            # Выравниваем по правому краю для курсов
            right_margin = 460  # Отступ от правого края
            buy_x = right_margin - buy_width
            sell_x = right_margin - sell_width
            
            # Центрируем время
            time_x = time_x + (200 - time_width) // 2
            
            # Накладываем только цифры поверх базовой картинки
            draw.text((buy_x, buy_y), buy_text, fill='#000000', font=self.rate_font)
            draw.text((sell_x, sell_y), sell_text, fill='#000000', font=self.rate_font)
            draw.text((time_x, time_y), time_str, fill='#000000', font=self.time_font)
            
            # Сохраняем изображение
            filename = 'currency_rates.png'
            img.save(filename)
            logger.info(f"Изображение сохранено: {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Ошибка при генерации изображения: {e}")
            return None

# Создаем глобальный экземпляр
image_generator = CurrencyImageGenerator()