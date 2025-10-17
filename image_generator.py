#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор изображений с курсами валют с fallback на Pillow
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
        Генерирует изображение с курсами валют в стиле обменника
        
        Args:
            buy_rate: Курс покупки
            sell_rate: Курс продажи  
            avg_rate: Средний курс
            
        Returns:
            Путь к созданному изображению или None при ошибке
        """
        # Сначала пробуем HTML/CSS метод
        try:
            return self._generate_with_html2image(buy_rate, sell_rate, avg_rate)
        except Exception as e:
            logger.warning(f"HTML2Image не работает: {e}, пробуем Pillow")
            try:
                return self._generate_with_pillow(buy_rate, sell_rate, avg_rate)
            except Exception as e2:
                logger.error(f"Оба метода не работают: {e2}")
                return None
    
    def _generate_with_html2image(self, buy_rate: float, sell_rate: float, avg_rate: float) -> Optional[str]:
        """Генерация через HTML2Image"""
        # Получаем московское время
        moscow_tz = pytz.timezone('Europe/Moscow')
        moscow_time = datetime.now(moscow_tz)
        time_str = moscow_time.strftime('%H:%M • %d.%m.%Y')
        
        # Создаем HTML
        html_content = self._create_html(buy_rate, sell_rate, time_str)
        
        # Создаем CSS
        css_content = self._create_css()
        
        # Генерируем изображение
        from html2image import Html2Image
        hti = Html2Image()
        
        # Устанавливаем размер
        hti.screenshot(
            html_str=html_content,
            css_str=css_content,
            save_as='currency_rates.png',
            size=(self.width, self.height)
        )
        
        return 'currency_rates.png'
    
    def _generate_with_pillow(self, buy_rate: float, sell_rate: float, avg_rate: float) -> Optional[str]:
        """Генерация через Pillow (fallback)"""
        from PIL import Image, ImageDraw, ImageFont
        
        # Получаем московское время
        moscow_tz = pytz.timezone('Europe/Moscow')
        moscow_time = datetime.now(moscow_tz)
        time_str = moscow_time.strftime('%H:%M • %d.%m.%Y')
        
        # Создаем изображение с градиентным фоном
        img = Image.new('RGB', (self.width, self.height), color='#3b82f6')
        draw = ImageDraw.Draw(img)
        
        # Создаем градиентный фон
        for y in range(self.height):
            # Простой градиент от синего к более темному синему
            ratio = y / self.height
            r = int(59 + (30 - 59) * ratio)
            g = int(130 + (100 - 130) * ratio)
            b = int(246 + (200 - 246) * ratio)
            color = (r, g, b)
            draw.line([(0, y), (self.width, y)], fill=color)
        
        # Добавляем DX паттерн
        self._add_dx_pattern(draw)
        
        # Пытаемся найти подходящий шрифт
        font_paths = [
            '/System/Library/Fonts/Arial.ttf',
            '/System/Library/Fonts/Helvetica.ttc',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'
        ]
        
        title_font = None
        rate_font = None
        small_font = None
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    title_font = ImageFont.truetype(font_path, 48)
                    rate_font = ImageFont.truetype(font_path, 50)
                    small_font = ImageFont.truetype(font_path, 18)
                    break
                except:
                    continue
        
        if not title_font:
            title_font = ImageFont.load_default()
            rate_font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        
        # Рисуем основную карточку
        card_width = 1200
        card_height = 400
        card_x = (self.width - card_width) // 2
        card_y = (self.height - card_height) // 2
        
        # Тень карточки
        shadow_offset = 10
        draw.rounded_rectangle(
            [card_x + shadow_offset, card_y + shadow_offset, 
             card_x + card_width + shadow_offset, card_y + card_height + shadow_offset],
            radius=25, fill='#00000040'
        )
        
        # Сама карточка
        draw.rounded_rectangle(
            [card_x, card_y, card_x + card_width, card_y + card_height],
            radius=25, fill='#ffffff'
        )
        
        # Заголовок
        title_text = "USDT/RUB • Актуальные курсы"
        title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = card_x + (card_width - title_width) // 2
        title_y = card_y + 40
        draw.text((title_x, title_y), title_text, fill='#1e3a8a', font=title_font)
        
        # Курсы
        buy_text = f"Покупка"
        buy_value = f"{buy_rate:.2f}₽"
        sell_text = f"Продажа"
        sell_value = f"{sell_rate:.2f}₽"
        
        # Позиционируем курсы
        y_offset = title_y + 100
        left_margin = card_x + 60
        right_margin = card_x + card_width - 60
        
        # Покупка
        draw.text((left_margin, y_offset), buy_text, fill='#000000', font=rate_font)
        buy_bbox = draw.textbbox((0, 0), buy_value, font=rate_font)
        buy_value_width = buy_bbox[2] - buy_bbox[0]
        draw.text((right_margin - buy_value_width, y_offset), buy_value, fill='#000000', font=rate_font)
        
        # Разделитель
        divider_y = y_offset + 60
        draw.line([(left_margin, divider_y), (right_margin, divider_y)], fill='#e5e7eb', width=1)
        
        # Продажа
        sell_y = divider_y + 20
        draw.text((left_margin, sell_y), sell_text, fill='#000000', font=rate_font)
        sell_bbox = draw.textbbox((0, 0), sell_value, font=rate_font)
        sell_value_width = sell_bbox[2] - sell_bbox[0]
        draw.text((right_margin - sell_value_width, sell_y), sell_value, fill='#000000', font=rate_font)
        
        # Карточка времени
        time_card_width = 400
        time_card_height = 60
        time_card_x = (self.width - time_card_width) // 2
        time_card_y = card_y + card_height + 30
        
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
        time_bbox = draw.textbbox((0, 0), time_text, font=small_font)
        time_width = time_bbox[2] - time_bbox[0]
        time_x = time_card_x + (time_card_width - time_width) // 2
        time_y = time_card_y + (time_card_height - (time_bbox[3] - time_bbox[1])) // 2
        draw.text((time_x, time_y), time_text, fill='#000000', font=small_font)
        
        # Сохраняем изображение
        filename = 'currency_rates.png'
        img.save(filename)
        return filename
    
    def _add_dx_pattern(self, draw):
        """Добавляет DX паттерн на фон"""
        # Простой DX паттерн
        for x in range(0, self.width, 80):
            for y in range(0, self.height, 80):
                # Рисуем полупрозрачные линии для создания паттерна
                if (x // 80 + y // 80) % 2 == 0:
                    draw.line([(x, y), (x + 40, y + 40)], fill='#3b82f640', width=2)
                    draw.line([(x + 40, y), (x, y + 40)], fill='#3b82f640', width=2)
    
    def _create_html(self, buy_rate: float, sell_rate: float, time_str: str) -> str:
        """Создает HTML для изображения"""
        return f"""
        <!DOCTYPE html>
        <html lang="ru">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Курсы валют</title>
        </head>
        <body>
            <div class="container">
                <div class="main-card">
                    <div class="rate-row">
                        <span class="rate-label">Покупка</span>
                        <span class="rate-value">{buy_rate:.2f}₽</span>
                    </div>
                    <div class="divider"></div>
                    <div class="rate-row">
                        <span class="rate-label">Продажа</span>
                        <span class="rate-value">{sell_rate:.2f}₽</span>
                    </div>
                </div>
                
                <div class="time-card">
                    <span class="time-text">Обновлено: {time_str}</span>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _create_css(self) -> str:
        """Создает CSS для изображения"""
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            width: 1600px;
            height: 1000px;
            background: #3b82f6;
            background-image: 
                repeating-linear-gradient(
                    45deg,
                    transparent,
                    transparent 40px,
                    rgba(59, 130, 246, 0.3) 40px,
                    rgba(59, 130, 246, 0.3) 80px
                );
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
        }
        
        body::before {
            content: 'DX';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-image: 
                repeating-linear-gradient(
                    0deg,
                    transparent,
                    transparent 80px,
                    rgba(59, 130, 246, 0.1) 80px,
                    rgba(59, 130, 246, 0.1) 160px
                ),
                repeating-linear-gradient(
                    90deg,
                    transparent,
                    transparent 80px,
                    rgba(59, 130, 246, 0.1) 80px,
                    rgba(59, 130, 246, 0.1) 160px
                );
            pointer-events: none;
        }
        
        .container {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 30px;
            z-index: 1;
        }
        
        .main-card {
            width: 1200px;
            height: 400px;
            background: white;
            border-radius: 25px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            padding: 60px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            gap: 40px;
        }
        
        .rate-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            height: 60px;
        }
        
        .rate-label {
            font-size: 50px;
            font-weight: bold;
            color: #000;
        }
        
        .rate-value {
            font-size: 50px;
            font-weight: bold;
            color: #000;
        }
        
        .divider {
            height: 1px;
            background: #e5e7eb;
            width: 100%;
        }
        
        .time-card {
            width: 400px;
            height: 60px;
            background: white;
            border-radius: 15px;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .time-text {
            font-size: 18px;
            color: #000;
            font-weight: 500;
        }
        """


# Создаем глобальный экземпляр
image_generator = CurrencyImageGenerator()