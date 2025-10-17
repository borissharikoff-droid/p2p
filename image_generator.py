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
            
            # Добавляем паттерн с символами рубля
            self._add_ruble_pattern(draw)
            
            # Создаем белую карточку
            card_x = (self.width - self.card_width) // 2
            card_y = (self.height - self.card_height) // 2
            
            # Рисуем карточку с тенью
            self._draw_card_with_shadow(draw, card_x, card_y)
            
            # Добавляем содержимое карточки в стиле обменника
            self._add_exchange_interface(draw, card_x, card_y, avg_rate)
            
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
    
    def _add_exchange_interface(self, draw: ImageDraw.Draw, x: int, y: int, avg_rate: float):
        """Добавляет интерфейс обменника на карточку точно как на примере"""
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
            currency_font = None
            amount_font = None
            small_font = None
            
            for font_path in font_paths:
                try:
                    if currency_font is None:
                        currency_font = ImageFont.truetype(font_path, 60)
                    if amount_font is None:
                        amount_font = ImageFont.truetype(font_path, 55)
                    if small_font is None:
                        small_font = ImageFont.truetype(font_path, 30)
                    break
                except:
                    continue
            
            # Если не удалось загрузить шрифты, используем стандартные
            if currency_font is None:
                currency_font = ImageFont.load_default()
            if amount_font is None:
                amount_font = ImageFont.load_default()
            if small_font is None:
                small_font = ImageFont.load_default()
            
            # Рассчитываем суммы для отображения (как на примере)
            rub_amount = 20000  # 20,000 рублей
            usdt_amount = rub_amount / avg_rate  # Конвертируем в USDT
            
            # Верхняя строка - RUB
            rub_y = y + 100
            
            # Иконка рубля (серый круг) - больше размер
            icon_size = 80
            icon_x = x + 80
            icon_y = rub_y - 15
            draw.ellipse([icon_x, icon_y, icon_x + icon_size, icon_y + icon_size], fill='#6b7280')
            
            # Символ рубля в иконке
            rub_symbol_bbox = draw.textbbox((0, 0), "₽", font=currency_font)
            rub_symbol_width = rub_symbol_bbox[2] - rub_symbol_bbox[0]
            rub_symbol_height = rub_symbol_bbox[3] - rub_symbol_bbox[1]
            draw.text((icon_x + (icon_size - rub_symbol_width) // 2, 
                      icon_y + (icon_size - rub_symbol_height) // 2), 
                     "₽", fill='white', font=currency_font)
            
            # Текст "RUB" - жирный
            draw.text((icon_x + icon_size + 30, rub_y), "RUB", fill='black', font=currency_font)
            
            # Сумма в рублях - выровнена по правому краю
            rub_text = f"{rub_amount:,}".replace(",", " ")
            amount_bbox = draw.textbbox((0, 0), rub_text, font=amount_font)
            amount_width = amount_bbox[2] - amount_bbox[0]
            amount_x = x + self.card_width - amount_width - 80
            draw.text((amount_x, rub_y), rub_text, fill='black', font=amount_font)
            
            # Разделительная линия - тонкая серая
            line_y = y + 200
            draw.line([(x + 60, line_y), (x + self.card_width - 60, line_y)], fill='#e5e7eb', width=1)
            
            # Иконка обмена в центре линии - светлая синяя
            exchange_icon_size = 50
            exchange_icon_x = x + self.card_width // 2 - exchange_icon_size // 2
            exchange_icon_y = line_y - exchange_icon_size // 2
            draw.ellipse([exchange_icon_x, exchange_icon_y, 
                         exchange_icon_x + exchange_icon_size, exchange_icon_y + exchange_icon_size], 
                        fill='#60a5fa')  # Светло-синий как на примере
            
            # Стрелки в иконке обмена
            arrow_bbox = draw.textbbox((0, 0), "↕", font=small_font)
            arrow_width = arrow_bbox[2] - arrow_bbox[0]
            arrow_height = arrow_bbox[3] - arrow_bbox[1]
            draw.text((exchange_icon_x + (exchange_icon_size - arrow_width) // 2,
                      exchange_icon_y + (exchange_icon_size - arrow_height) // 2),
                     "↕", fill='white', font=small_font)
            
            # Нижняя строка - USDT
            usdt_y = y + 300
            
            # Иконка доллара (серый круг)
            usdt_icon_x = x + 80
            usdt_icon_y = usdt_y - 15
            draw.ellipse([usdt_icon_x, usdt_icon_y, usdt_icon_x + icon_size, usdt_icon_y + icon_size], fill='#6b7280')
            
            # Символ доллара в иконке
            usd_symbol_bbox = draw.textbbox((0, 0), "$", font=currency_font)
            usd_symbol_width = usd_symbol_bbox[2] - usd_symbol_bbox[0]
            usd_symbol_height = usd_symbol_bbox[3] - usd_symbol_bbox[1]
            draw.text((usdt_icon_x + (icon_size - usd_symbol_width) // 2,
                      usdt_icon_y + (icon_size - usd_symbol_height) // 2),
                     "$", fill='white', font=currency_font)
            
            # Текст "USDT" - жирный
            draw.text((usdt_icon_x + icon_size + 30, usdt_y), "USDT", fill='black', font=currency_font)
            
            # Сумма в USDT - выровнена по правому краю
            usdt_text = f"{usdt_amount:.2f}"
            usdt_amount_bbox = draw.textbbox((0, 0), usdt_text, font=amount_font)
            usdt_amount_width = usdt_amount_bbox[2] - usdt_amount_bbox[0]
            usdt_amount_x = x + self.card_width - usdt_amount_width - 80
            draw.text((usdt_amount_x, usdt_y), usdt_text, fill='black', font=amount_font)
            
        except Exception as e:
            logger.error(f"Ошибка добавления интерфейса обменника: {e}")


# Создаем глобальный экземпляр
image_generator = CurrencyImageGenerator()
