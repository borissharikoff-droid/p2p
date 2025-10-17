#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор изображений с курсами валют - ТОЧНАЯ копия второго скрина
"""

import os
from datetime import datetime
import pytz
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class CurrencyImageGenerator:
    """Генератор изображений с курсами валют - точная копия второго скрина"""
    
    def __init__(self):
        self.width = 1600
        self.height = 1000
        
    def generate_currency_card(self, buy_rate: float, sell_rate: float, avg_rate: float) -> Optional[str]:
        """
        Генерирует изображение с курсами валют ИДЕНТИЧНО как на втором скрине
        
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
        """Генерация через Pillow - ТОЧНАЯ копия второго скрина"""
        from PIL import Image, ImageDraw, ImageFont
        
        # Получаем московское время
        moscow_tz = pytz.timezone('Europe/Moscow')
        moscow_time = datetime.now(moscow_tz)
        time_str = moscow_time.strftime('%H:%M • %d.%m.%Y')
        
        # Создаем изображение с точным синим фоном
        img = Image.new('RGB', (self.width, self.height), color='#3b82f6')
        draw = ImageDraw.Draw(img)
        
        # Добавляем DX паттерн - точно как на втором скрине
        self._add_dx_pattern(draw)
        
        # Ищем шрифт с поддержкой кириллицы
        font_paths = [
            '/System/Library/Fonts/Arial.ttf',
            '/System/Library/Fonts/Helvetica.ttc', 
            '/System/Library/Fonts/SF-Pro-Display-Regular.otf',
            '/System/Library/Fonts/SF-Pro-Text-Regular.otf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
            '/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf'
        ]
        
        # Размеры шрифтов точно как на втором скрине
        rate_font = None
        time_font = None
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    rate_font = ImageFont.truetype(font_path, 50)   # Большие курсы
                    time_font = ImageFont.truetype(font_path, 18)   # Время
                    break
                except:
                    continue
        
        if not rate_font:
            # Fallback на системный шрифт
            rate_font = ImageFont.load_default()
            time_font = ImageFont.load_default()
        
        # Основная карточка - точно как на втором скрине
        card_width = 1200
        card_height = 300
        card_x = (self.width - card_width) // 2
        card_y = (self.height - card_height) // 2 - 50  # Чуть выше центра
        
        # Тень карточки
        shadow_offset = 8
        draw.rounded_rectangle(
            [card_x + shadow_offset, card_y + shadow_offset, 
             card_x + card_width + shadow_offset, card_y + card_height + shadow_offset],
            radius=25, fill='#00000030'
        )
        
        # Сама карточка - белая
        draw.rounded_rectangle(
            [card_x, card_y, card_x + card_width, card_y + card_height],
            radius=25, fill='#ffffff'
        )
        
        # Курсы - точно как на втором скрине
        y_offset = card_y + 80
        
        # Покупка
        buy_text = "Покупка"
        buy_value = f"{buy_rate:.2f}₽"
        
        # Продажа  
        sell_text = "Продажа"
        sell_value = f"{sell_rate:.2f}₽"
        
        left_margin = card_x + 60
        right_margin = card_x + card_width - 60
        
        # Рисуем покупку
        draw.text((left_margin, y_offset), buy_text, fill='#000000', font=rate_font)
        buy_bbox = draw.textbbox((0, 0), buy_value, font=rate_font)
        buy_value_width = buy_bbox[2] - buy_bbox[0]
        draw.text((right_margin - buy_value_width, y_offset), buy_value, fill='#000000', font=rate_font)
        
        # Разделитель между курсами
        divider_y = y_offset + 80
        draw.line([(left_margin, divider_y), (right_margin, divider_y)], fill='#e5e7eb', width=1)
        
        # Рисуем продажу
        sell_y = divider_y + 20
        draw.text((left_margin, sell_y), sell_text, fill='#000000', font=rate_font)
        sell_bbox = draw.textbbox((0, 0), sell_value, font=rate_font)
        sell_value_width = sell_bbox[2] - sell_bbox[0]
        draw.text((right_margin - sell_value_width, sell_y), sell_value, fill='#000000', font=rate_font)
        
        # Карточка времени - точно как на втором скрине (маленькая, справа)
        time_card_width = 350
        time_card_height = 50
        time_card_x = card_x + card_width - time_card_width - 20  # Справа от основной карточки
        time_card_y = card_y + card_height + 20
        
        # Тень карточки времени
        draw.rounded_rectangle(
            [time_card_x + 5, time_card_y + 5, 
             time_card_x + time_card_width + 5, time_card_y + time_card_height + 5],
            radius=15, fill='#00000020'
        )
        
        # Карточка времени
        draw.rounded_rectangle(
            [time_card_x, time_card_y, time_card_x + time_card_width, time_card_y + time_card_height],
            radius=15, fill='#ffffff'
        )
        
        # Время обновления
        time_text = f"Обновлено: {time_str}"
        time_bbox = draw.textbbox((0, 0), time_text, font=time_font)
        time_width = time_bbox[2] - time_bbox[0]
        time_x = time_card_x + (time_card_width - time_width) // 2
        time_y = time_card_y + (time_card_height - (time_bbox[3] - time_bbox[1])) // 2
        draw.text((time_x, time_y), time_text, fill='#000000', font=time_font)
        
        # Стрелка вниз в правом верхнем углу - точно как на втором скрине
        arrow_x = self.width - 50
        arrow_y = 30
        self._draw_arrow_down(draw, arrow_x, arrow_y)
        
        # Сохраняем изображение
        filename = 'currency_rates.png'
        img.save(filename)
        return filename
    
    def _add_dx_pattern(self, draw):
        """Добавляет DX паттерн - точно как на втором скрине"""
        # DX паттерн в пиксельном стиле
        pattern_size = 80
        for x in range(0, self.width, pattern_size):
            for y in range(0, self.height, pattern_size):
                # Рисуем "DX" символы
                center_x = x + pattern_size // 2
                center_y = y + pattern_size // 2
                
                # D
                draw.line([(center_x - 15, center_y - 15), (center_x - 15, center_y + 15)], fill='#3b82f640', width=3)
                draw.line([(center_x - 15, center_y - 15), (center_x - 5, center_y - 15)], fill='#3b82f640', width=3)
                draw.line([(center_x - 15, center_y + 15), (center_x - 5, center_y + 15)], fill='#3b82f640', width=3)
                draw.line([(center_x - 5, center_y - 15), (center_x - 5, center_y)], fill='#3b82f640', width=3)
                draw.line([(center_x - 5, center_y + 15), (center_x - 5, center_y)], fill='#3b82f640', width=3)
                
                # X
                draw.line([(center_x + 5, center_y - 15), (center_x + 15, center_y + 15)], fill='#3b82f640', width=3)
                draw.line([(center_x + 15, center_y - 15), (center_x + 5, center_y + 15)], fill='#3b82f640', width=3)
    
    def _draw_arrow_down(self, draw, x, y):
        """Рисует стрелку вниз в правом верхнем углу"""
        # Белая стрелка вниз
        arrow_size = 20
        points = [
            (x, y),
            (x - arrow_size//2, y + arrow_size),
            (x + arrow_size//2, y + arrow_size)
        ]
        draw.polygon(points, fill='#ffffff')


# Создаем глобальный экземпляр
image_generator = CurrencyImageGenerator()