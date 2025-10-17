#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор изображений с курсами валют - РАБОЧАЯ версия
"""

import os
from datetime import datetime
import pytz
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class CurrencyImageGenerator:
    """Генератор изображений с курсами валют"""
    
    def __init__(self):
        self.width = 1600
        self.height = 1000
        
    def generate_currency_card(self, buy_rate: float, sell_rate: float, avg_rate: float) -> Optional[str]:
        """
        Генерирует изображение с курсами валют
        
        Args:
            buy_rate: Курс покупки
            sell_rate: Курс продажи  
            avg_rate: Средний курс
            
        Returns:
            Путь к созданному изображению или None при ошибке
        """
        try:
            return self._generate_with_pillow(buy_rate, sell_rate, avg_rate)
        except Exception as e:
            logger.error(f"Ошибка генерации изображения: {e}")
            return None
    
    def _generate_with_pillow(self, buy_rate: float, sell_rate: float, avg_rate: float) -> Optional[str]:
        """Генерация через Pillow - точная копия дизайна пользователя"""
        from PIL import Image, ImageDraw, ImageFont
        
        # Получаем московское время
        moscow_tz = pytz.timezone('Europe/Moscow')
        moscow_time = datetime.now(moscow_tz)
        time_str = moscow_time.strftime('%H:%M %d.%m.%Y')
        
        # Создаем изображение с ярко-синим фоном как в примере
        img = Image.new('RGB', (self.width, self.height), color='#0066ff')  # Ярко-синий фон
        draw = ImageDraw.Draw(img)
        
        # Основная карточка (большая, белая)
        card_width = 1000
        card_height = 200
        card_x = (self.width - card_width) // 2
        card_y = (self.height - card_height) // 2 - 80  # Смещена вверх
        
        # Тень основной карточки
        shadow_offset = 8
        draw.rounded_rectangle(
            [card_x + shadow_offset, card_y + shadow_offset, 
             card_x + card_width + shadow_offset, card_y + card_height + shadow_offset],
            radius=20, fill='#00000040'  # Более заметная тень
        )
        
        # Сама основная карточка - белая
        draw.rounded_rectangle(
            [card_x, card_y, card_x + card_width, card_y + card_height],
            radius=20, fill='#ffffff'
        )
        
        # Заголовок "USDT/RUB" по центру вверху
        try:
            title_font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 24)
            rate_font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 32)
        except:
            title_font = ImageFont.load_default()
            rate_font = ImageFont.load_default()
        
        title_text = "USDT/RUB"
        title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = card_x + (card_width - title_width) // 2
        title_y = card_y + 20
        draw.text((title_x, title_y), title_text, fill='#000000', font=title_font)
        
        # Первая строка данных (Покупка)
        y_offset = card_y + 70
        left_margin = card_x + 40
        right_margin = card_x + card_width - 40
        
        # Текст слева (########)
        left_text = "########"
        draw.text((left_margin, y_offset), left_text, fill='#000000', font=rate_font)
        
        # Значение справа
        buy_value = f"{buy_rate:.2f}₽"
        buy_bbox = draw.textbbox((0, 0), buy_value, font=rate_font)
        buy_value_width = buy_bbox[2] - buy_bbox[0]
        draw.text((right_margin - buy_value_width, y_offset), buy_value, fill='#000000', font=rate_font)
        
        # Разделительная линия
        divider_y = y_offset + 50
        draw.line([(left_margin, divider_y), (right_margin, divider_y)], fill='#e0e0e0', width=1)
        
        # Вторая строка данных (Продажа)
        sell_y = divider_y + 15
        draw.text((left_margin, sell_y), left_text, fill='#000000', font=rate_font)
        
        sell_value = f"{sell_rate:.2f}₽"
        sell_bbox = draw.textbbox((0, 0), sell_value, font=rate_font)
        sell_value_width = sell_bbox[2] - sell_bbox[0]
        draw.text((right_margin - sell_value_width, sell_y), sell_value, fill='#000000', font=rate_font)
        
        # Нижняя карточка (время)
        time_card_width = 400
        time_card_height = 50
        time_card_x = (self.width - time_card_width) // 2
        time_card_y = card_y + card_height + 40  # Отступ от основной карточки
        
        # Тень карточки времени
        draw.rounded_rectangle(
            [time_card_x + 5, time_card_y + 5, 
             time_card_x + time_card_width + 5, time_card_y + time_card_height + 5],
            radius=15, fill='#00000040'
        )
        
        # Карточка времени
        draw.rounded_rectangle(
            [time_card_x, time_card_y, time_card_x + time_card_width, time_card_y + time_card_height],
            radius=15, fill='#ffffff'
        )
        
        # Время обновления по центру
        time_text = f"######## {time_str}"
        time_bbox = draw.textbbox((0, 0), time_text, font=rate_font)
        time_width = time_bbox[2] - time_bbox[0]
        time_x = time_card_x + (time_card_width - time_width) // 2
        time_y = time_card_y + (time_card_height - (time_bbox[3] - time_bbox[1])) // 2
        draw.text((time_x, time_y), time_text, fill='#000000', font=rate_font)
        
        # Сохраняем изображение
        filename = 'currency_rates.png'
        img.save(filename)
        return filename
    


# Создаем глобальный экземпляр
image_generator = CurrencyImageGenerator()