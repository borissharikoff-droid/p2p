#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор изображений с курсами валют используя HTML/CSS
"""

import os
from datetime import datetime
import pytz
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class CurrencyImageGenerator:
    """Генератор изображений с курсами валют используя HTML/CSS"""
    
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
        try:
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
            
        except Exception as e:
            logger.error(f"Ошибка генерации изображения: {e}")
            return None
    
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