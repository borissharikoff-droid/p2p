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
        self.width = 1600
        self.height = 1000
        self.card_width = 1200
        self.card_height = 400
        self.card_margin = 200
        
    def generate_currency_card(self, buy_rate: float, sell_rate: float, avg_rate: float) -> Optional[str]:
        """
        Генерирует изображение с курсами валют в стиле обменника
        
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
            
            # Создаем градиентный фон
            self._create_gradient_background(draw)
            
            # Добавляем паттерн с символами рубля
            self._add_ruble_pattern(draw)
            
            # Создаем основную карточку с курсами
            card_x = (self.width - self.card_width) // 2
            card_y = (self.height - self.card_height) // 2 - 50
            
            # Рисуем основную карточку с тенью
            self._draw_card_with_shadow(draw, card_x, card_y)
            
            # Добавляем курсы покупки и продажи
            self._add_exchange_interface(draw, card_x, card_y, buy_rate, sell_rate)
            
            # Создаем карточку с временем обновления
            time_card_width = 400
            time_card_height = 60
            time_card_x = (self.width - time_card_width) // 2
            time_card_y = card_y + self.card_height + 30
            
            # Рисуем карточку времени с тенью
            self._draw_time_card(draw, time_card_x, time_card_y, time_card_width, time_card_height)
            
            # Добавляем время обновления
            self._add_update_time(draw, time_card_x, time_card_y, time_card_width, time_card_height)
            
            # Сохраняем изображение
            image_path = "currency_rates.png"
            image.save(image_path, "PNG")
            
            return image_path
            
        except Exception as e:
            logger.error(f"Ошибка генерации изображения: {e}")
            return None
    
    def _create_gradient_background(self, draw: ImageDraw.Draw):
        """Создает синий фон с паттерном DX"""
        try:
            # Создаем сплошной синий фон
            draw.rectangle([0, 0, self.width, self.height], fill='#3b82f6')
                
        except Exception as e:
            logger.warning(f"Не удалось создать фон: {e}")
    
    def _add_ruble_pattern(self, draw: ImageDraw.Draw):
        """Добавляет паттерн DX на фон"""
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
                        font = ImageFont.truetype(font_path, 30)
                        break
                    except:
                        continue
                
                if font is None:
                    font = ImageFont.load_default()
                    
            except:
                font = ImageFont.load_default()
            
            # Добавляем полупрозрачный паттерн DX
            for x in range(0, self.width, 80):
                for y in range(0, self.height, 80):
                    draw.text((x, y), "DX", fill=(59, 130, 246, 50), font=font)
                    
        except Exception as e:
            logger.warning(f"Не удалось добавить паттерн: {e}")
    
    def _draw_card_with_shadow(self, draw: ImageDraw.Draw, x: int, y: int):
        """Рисует карточку с тенью"""
        # Тень - более заметная
        shadow_offset = 8
        draw.rounded_rectangle(
            [x + shadow_offset, y + shadow_offset, 
             x + self.card_width + shadow_offset, y + self.card_height + shadow_offset],
            radius=25,
            fill=(0, 0, 0, 50)
        )
        
        # Основная карточка - более округлая
        draw.rounded_rectangle(
            [x, y, x + self.card_width, y + self.card_height],
            radius=25,
            fill='white'
        )
    
    def _add_exchange_interface(self, draw: ImageDraw.Draw, x: int, y: int, buy_rate: float, sell_rate: float):
        """Добавляет интерфейс с курсами покупки и продажи"""
        try:
            # Пытаемся загрузить шрифты с поддержкой Unicode
            font_paths = [
                "/System/Library/Fonts/Arial.ttf",  # macOS
                "/System/Library/Fonts/Helvetica.ttc",  # macOS
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",  # Linux
                "C:/Windows/Fonts/arial.ttf",  # Windows
                "C:/Windows/Fonts/calibri.ttf",  # Windows
                "arial.ttf"
            ]
            
            # Загружаем шрифты разных размеров
            main_font = None
            small_font = None
            
            for font_path in font_paths:
                try:
                    if main_font is None:
                        main_font = ImageFont.truetype(font_path, 50)
                    if small_font is None:
                        small_font = ImageFont.truetype(font_path, 20)
                    break
                except:
                    continue
            
            # Если не удалось загрузить шрифты, используем стандартные
            if main_font is None:
                main_font = ImageFont.load_default()
            if small_font is None:
                small_font = ImageFont.load_default()
            
            # Верхняя строка - Покупка
            buy_y = y + 80
            
            # Текст "Покупка" - жирный черный
            draw.text((x + 60, buy_y), "Покупка", fill='black', font=main_font)
            
            # Курс покупки - выровнен по правому краю
            buy_text = f"{buy_rate:.2f}₽"
            buy_bbox = draw.textbbox((0, 0), buy_text, font=main_font)
            buy_width = buy_bbox[2] - buy_bbox[0]
            buy_x = x + self.card_width - buy_width - 60
            draw.text((buy_x, buy_y), buy_text, fill='black', font=main_font)
            
            # Разделительная линия - тонкая серая
            line_y = y + 150
            draw.line([(x + 50, line_y), (x + self.card_width - 50, line_y)], fill='#e5e7eb', width=1)
            
            # Нижняя строка - Продажа
            sell_y = y + 200
            
            # Текст "Продажа" - жирный черный
            draw.text((x + 60, sell_y), "Продажа", fill='black', font=main_font)
            
            # Курс продажи - выровнен по правому краю
            sell_text = f"{sell_rate:.2f}₽"
            sell_bbox = draw.textbbox((0, 0), sell_text, font=main_font)
            sell_width = sell_bbox[2] - sell_bbox[0]
            sell_x = x + self.card_width - sell_width - 60
            draw.text((sell_x, sell_y), sell_text, fill='black', font=main_font)
            
        except Exception as e:
            logger.error(f"Ошибка добавления интерфейса курсов: {e}")
    
    def _draw_time_card(self, draw: ImageDraw.Draw, x: int, y: int, width: int, height: int):
        """Рисует карточку с временем обновления"""
        # Тень
        shadow_offset = 4
        draw.rounded_rectangle(
            [x + shadow_offset, y + shadow_offset, 
             x + width + shadow_offset, y + height + shadow_offset],
            radius=15,
            fill=(0, 0, 0, 30)
        )
        
        # Основная карточка
        draw.rounded_rectangle(
            [x, y, x + width, y + height],
            radius=15,
            fill='white'
        )
    
    def _add_update_time(self, draw: ImageDraw.Draw, x: int, y: int, width: int, height: int):
        """Добавляет время обновления на карточку"""
        try:
            from datetime import datetime
            import pytz
            
            # Получаем московское время
            moscow_tz = pytz.timezone('Europe/Moscow')
            moscow_time = datetime.now(moscow_tz)
            
            # Пытаемся загрузить шрифт
            font_paths = [
                "/System/Library/Fonts/Arial.ttf",  # macOS
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
                "C:/Windows/Fonts/arial.ttf",  # Windows
                "arial.ttf"
            ]
            
            font = None
            for font_path in font_paths:
                try:
                    font = ImageFont.truetype(font_path, 18)
                    break
                except:
                    continue
            
            if font is None:
                font = ImageFont.load_default()
            
            # Форматируем время
            time_text = f"Обновлено: {moscow_time.strftime('%H:%M • %d.%m.%Y')}"
            
            # Центрируем текст
            text_bbox = draw.textbbox((0, 0), time_text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            text_x = x + (width - text_width) // 2
            text_y = y + (height - text_height) // 2
            
            draw.text((text_x, text_y), time_text, fill='black', font=font)
            
        except Exception as e:
            logger.error(f"Ошибка добавления времени обновления: {e}")


# Создаем глобальный экземпляр
image_generator = CurrencyImageGenerator()
