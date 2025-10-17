#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор изображений для курсов валют
Использует статичный шаблон и накладывает только цифры
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
        self.width = 600
        self.height = 400
        self.template_path = 'currency_template.png'
        
        # Координаты для наложения текста (рассчитаны для шаблона)
        self.buy_rate_position = (420, 120)  # Позиция для курса покупки
        self.sell_rate_position = (420, 185)  # Позиция для курса продажи
        self.time_position = (200, 320)  # Позиция для времени
        
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
            # Проверяем существование шаблона
            if not os.path.exists(self.template_path):
                logger.error(f"Шаблон не найден: {self.template_path}")
                return None
            
            # Загружаем шаблон
            img = Image.open(self.template_path)
            draw = ImageDraw.Draw(img)
            
            # Получаем текущее время
            moscow_tz = pytz.timezone('Europe/Moscow')
            current_time = datetime.now(moscow_tz)
            time_str = current_time.strftime("%H:%M • %d.%m.%Y")
            
            # Форматируем курсы
            buy_text = f"{buy_rate:.2f}₽"
            sell_text = f"{sell_rate:.2f}₽"
            
            # Получаем размеры текста для центрирования
            buy_bbox = draw.textbbox((0, 0), buy_text, font=self.rate_font)
            buy_width = buy_bbox[2] - buy_bbox[0]
            
            sell_bbox = draw.textbbox((0, 0), sell_text, font=self.rate_font)
            sell_width = sell_bbox[2] - sell_bbox[0]
            
            time_bbox = draw.textbbox((0, 0), time_str, font=self.time_font)
            time_width = time_bbox[2] - time_bbox[0]
            
            # Вычисляем позиции для выравнивания по правому краю
            right_margin = 460  # Отступ от правого края карточки
            
            buy_x = right_margin - buy_width
            sell_x = right_margin - sell_width
            time_x = self.time_position[0] + (200 - time_width) // 2  # Центрируем время
            
            # Накладываем текст поверх шаблона
            draw.text((buy_x, self.buy_rate_position[1]), buy_text, fill='#000000', font=self.rate_font)
            draw.text((sell_x, self.sell_rate_position[1]), sell_text, fill='#000000', font=self.rate_font)
            draw.text((time_x, self.time_position[1]), time_str, fill='#000000', font=self.time_font)
            
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