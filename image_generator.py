#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор изображений с курсами валют
"""

import os
from PIL import Image, ImageDraw, ImageFont
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class CurrencyImageGenerator:
    """Генератор изображений с курсами валют"""
    
    def __init__(self):
        self.width = 1080
        self.height = 1080
        self.card_width = 800
        self.card_height = 600
        self.card_margin = 40
        
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
            # Создаем изображение с градиентным фоном
            image = Image.new('RGB', (self.width, self.height), color='#1e3a8a')
            draw = ImageDraw.Draw(image)
            
            # Добавляем паттерн с символами рубля
            self._add_ruble_pattern(draw)
            
            # Создаем белую карточку
            card_x = (self.width - self.card_width) // 2
            card_y = (self.height - self.card_height) // 2
            
            # Рисуем карточку с тенью
            self._draw_card_with_shadow(draw, card_x, card_y)
            
            # Добавляем текст на карточку
            self._add_currency_text(draw, card_x, card_y, buy_rate, sell_rate, avg_rate)
            
            # Сохраняем изображение
            image_path = "currency_rates.png"
            image.save(image_path, "PNG")
            
            return image_path
            
        except Exception as e:
            logger.error(f"Ошибка генерации изображения: {e}")
            return None
    
    def _add_ruble_pattern(self, draw: ImageDraw.Draw):
        """Добавляет паттерн с символами рубля на фон"""
        try:
            # Пытаемся загрузить шрифт с поддержкой Unicode
            try:
                # Пробуем разные шрифты для поддержки русского текста
                font_paths = [
                    "/System/Library/Fonts/Arial.ttf",  # macOS
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
                    "C:/Windows/Fonts/arial.ttf",  # Windows
                    "arial.ttf"
                ]
                font = None
                for font_path in font_paths:
                    try:
                        font = ImageFont.truetype(font_path, 40)
                        break
                    except:
                        continue
                
                if font is None:
                    font = ImageFont.load_default()
                    
            except:
                font = ImageFont.load_default()
            
            # Добавляем полупрозрачные символы рубля
            for x in range(0, self.width, 80):
                for y in range(0, self.height, 80):
                    draw.text((x, y), "₽", fill=(59, 130, 246, 50), font=font)
                    
        except Exception as e:
            logger.warning(f"Не удалось добавить паттерн: {e}")
    
    def _draw_card_with_shadow(self, draw: ImageDraw.Draw, x: int, y: int):
        """Рисует карточку с тенью"""
        # Тень
        shadow_offset = 3
        draw.rounded_rectangle(
            [x + shadow_offset, y + shadow_offset, 
             x + self.card_width + shadow_offset, y + self.card_height + shadow_offset],
            radius=15,
            fill=(0, 0, 0, 30)
        )
        
        # Основная карточка
        draw.rounded_rectangle(
            [x, y, x + self.card_width, y + self.card_height],
            radius=15,
            fill='white'
        )
    
    def _add_currency_text(self, draw: ImageDraw.Draw, x: int, y: int, 
                          buy_rate: float, sell_rate: float, avg_rate: float):
        """Добавляет текст с курсами на карточку"""
        try:
            # Пытаемся загрузить шрифты с поддержкой Unicode
            font_paths = [
                "/System/Library/Fonts/Arial.ttf",  # macOS
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
                "C:/Windows/Fonts/arial.ttf",  # Windows
                "arial.ttf"
            ]
            
            # Загружаем шрифты разных размеров
            title_font = None
            rate_font = None
            small_font = None
            
            for font_path in font_paths:
                try:
                    if title_font is None:
                        title_font = ImageFont.truetype(font_path, 48)
                    if rate_font is None:
                        rate_font = ImageFont.truetype(font_path, 36)
                    if small_font is None:
                        small_font = ImageFont.truetype(font_path, 24)
                    break
                except:
                    continue
            
            # Если не удалось загрузить шрифты, используем стандартные
            if title_font is None:
                title_font = ImageFont.load_default()
            if rate_font is None:
                rate_font = ImageFont.load_default()
            if small_font is None:
                small_font = ImageFont.load_default()
            
            # Заголовок
            title = "USDT/RUB Курсы"
            title_bbox = draw.textbbox((0, 0), title, font=title_font)
            title_width = title_bbox[2] - title_bbox[0]
            title_x = x + (self.card_width - title_width) // 2
            draw.text((title_x, y + 40), title, fill='black', font=title_font)
            
            # Курс покупки
            buy_text = f"📈 Покупка: {buy_rate:.2f}₽"
            draw.text((x + 40, y + 120), buy_text, fill='black', font=rate_font)
            
            # Разделительная линия
            line_y = y + 220
            draw.line([(x + 40, line_y), (x + self.card_width - 40, line_y)], fill='#e5e7eb', width=2)
            
            # Иконка обмена в центре линии
            icon_x = x + self.card_width // 2 - 25
            icon_y = line_y - 25
            draw.ellipse([icon_x, icon_y, icon_x + 50, icon_y + 50], fill='#3b82f6')
            
            # Стрелки в иконке
            draw.text((icon_x + 15, icon_y + 10), "↕", fill='white', font=small_font)
            
            # Курс продажи
            sell_text = f"📉 Продажа: {sell_rate:.2f}₽"
            draw.text((x + 40, y + 280), sell_text, fill='black', font=rate_font)
            
            # Средний курс
            avg_text = f"⚖️ Средний: {avg_rate:.2f}₽"
            draw.text((x + 40, y + 340), avg_text, fill='black', font=rate_font)
            
        except Exception as e:
            logger.error(f"Ошибка добавления текста: {e}")


# Создаем глобальный экземпляр
image_generator = CurrencyImageGenerator()
