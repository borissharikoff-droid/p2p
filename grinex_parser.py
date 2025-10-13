#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Парсер курсов USDT/A7A5 с биржи Grinex
Берёт цену продажи и покупки, считает среднее + 0.30
"""

import requests
import json
import logging
from datetime import datetime
from typing import Dict, Optional, Union
from exceptions import BestChangeError

logger = logging.getLogger(__name__)


class GrinexParser:
    """Парсер для биржи Grinex USDT/A7A5"""
    
    def __init__(self):
        self.base_url = "https://grinex.io"
        self.trading_url = "https://grinex.io/trading/usdta7a5"
        self.api_url = "https://grinex.io/api/v1/public/ticker/usdta7a5"
        self.session = requests.Session()
        
        # Заголовки для имитации браузера
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://grinex.io/trading/usdta7a5',
        }
        self.session.headers.update(self.headers)
    
    def get_ticker_data(self) -> Optional[Dict]:
        """Получает данные тикера USDT/A7A5 через веб-скрапинг"""
        try:
            logger.info(f"Загружаем страницу торгов: {self.trading_url}")
            response = self.session.get(self.trading_url, timeout=30)
            response.raise_for_status()
            
            # Ищем bid/ask цены в HTML
            from bs4 import BeautifulSoup
            import re
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Ищем элементы с ценами (обычно в div с классами типа price, bid, ask)
            bid_price = None
            ask_price = None
            
            # Попробуем найти цены в различных элементах
            price_elements = soup.find_all(['span', 'div', 'td'], class_=re.compile(r'(price|bid|ask|buy|sell)', re.I))
            
            for element in price_elements:
                text = element.get_text(strip=True)
                # Ищем числа с точкой (цены)
                price_match = re.search(r'(\d+\.?\d*)', text)
                if price_match:
                    price = float(price_match.group(1))
                    if 1 < price < 1000:  # Разумный диапазон цен
                        if 'bid' in element.get('class', []) or 'buy' in element.get('class', []):
                            bid_price = price
                        elif 'ask' in element.get('class', []) or 'sell' in element.get('class', []):
                            ask_price = price
            
            # Если не нашли по классам, попробуем найти любые цены на странице
            if not bid_price or not ask_price:
                all_text = soup.get_text()
                prices = re.findall(r'(\d+\.?\d{2,4})', all_text)
                prices = [float(p) for p in prices if 1 < float(p) < 1000]
                if len(prices) >= 2:
                    prices.sort()
                    bid_price = prices[0]  # Меньшая цена = bid
                    ask_price = prices[-1]  # Большая цена = ask
            
            if not bid_price or not ask_price:
                raise BestChangeError("Не удалось найти цены bid/ask на странице")
            
            data = {
                'bid': bid_price,
                'ask': ask_price
            }
            
            logger.info(f"Получены данные тикера: {data}")
            return data
            
        except requests.RequestException as e:
            logger.error(f"Ошибка при загрузке страницы: {e}")
            raise BestChangeError(f"Не удалось загрузить данные с Grinex: {e}")
        except Exception as e:
            logger.error(f"Ошибка парсинга страницы: {e}")
            raise BestChangeError(f"Не удалось извлечь цены с Grinex: {e}")
    
    def parse_rates(self, ticker_data: Dict) -> Dict[str, float]:
        """Парсит курсы покупки и продажи из данных тикера"""
        try:
            # Извлекаем цены покупки и продажи
            bid_price = float(ticker_data.get('bid', 0))  # Цена покупки (bid)
            ask_price = float(ticker_data.get('ask', 0))  # Цена продажи (ask)
            
            if bid_price <= 0 or ask_price <= 0:
                raise BestChangeError("Некорректные цены в данных тикера")
            
            logger.info(f"Цена покупки (bid): {bid_price}, Цена продажи (ask): {ask_price}")
            
            # Считаем среднее
            mid_price = (bid_price + ask_price) / 2
            logger.info(f"Средняя цена: {mid_price}")
            
            # Добавляем 0.30
            final_rate = round(mid_price + 0.30, 2)
            logger.info(f"Итоговый курс (+0.30): {final_rate}")
            
            return {
                'bid_price': bid_price,
                'ask_price': ask_price,
                'mid_price': mid_price,
                'final_rate': final_rate,
                'timestamp': datetime.now().isoformat()
            }
            
        except (ValueError, KeyError) as e:
            logger.error(f"Ошибка парсинга данных тикера: {e}")
            raise BestChangeError(f"Не удалось извлечь курсы из данных: {e}")
    
    def run(self) -> Dict[str, Union[bool, str, Dict, float]]:
        """Основной метод для получения курса USDT/A7A5"""
        logger.info("Запуск парсера Grinex USDT/A7A5...")
        
        try:
            # Получаем данные тикера
            ticker_data = self.get_ticker_data()
            if not ticker_data:
                raise BestChangeError("Не удалось получить данные тикера")
            
            # Парсим курсы
            rates = self.parse_rates(ticker_data)
            
            # Формируем результат в формате, совместимом с BestChange
            return {
                "success": True,
                "data": {
                    "buy": [{
                        'exchanger_name': 'Grinex',
                        'rate': rates['bid_price'],
                        'reserve': 0,
                        'reviews_count': 0,
                        'exchanger_link': self.trading_url,
                        'parsed_at': rates['timestamp']
                    }],
                    "sell": [{
                        'exchanger_name': 'Grinex',
                        'rate': rates['ask_price'],
                        'reserve': 0,
                        'reviews_count': 0,
                        'exchanger_link': self.trading_url,
                        'parsed_at': rates['timestamp']
                    }]
                },
                "metrics": {
                    "avg_buy_rate": rates['bid_price'],
                    "avg_sell_rate": rates['ask_price'],
                    "mid_rate": rates['mid_price'],
                    "final_rate": rates['final_rate']
                },
                "total_buy_exchangers": 1,
                "total_sell_exchangers": 1,
                "grinex_data": rates
            }
            
        except BestChangeError:
            raise
        except Exception as e:
            logger.error(f"Неожиданная ошибка парсера Grinex: {e}")
            raise BestChangeError(f"Неожиданная ошибка парсера: {e}")


def main():
    """Главная функция для тестирования"""
    parser = GrinexParser()
    result = parser.run()
    
    if result.get("success"):
        grinex_data = result.get("grinex_data", {})
        print(f"Цена покупки (bid): {grinex_data.get('bid_price', 0)}")
        print(f"Цена продажи (ask): {grinex_data.get('ask_price', 0)}")
        print(f"Средняя цена: {grinex_data.get('mid_price', 0)}")
        print(f"Итоговый курс (+0.30): {grinex_data.get('final_rate', 0)}")
    else:
        print(f"Ошибка: {result.get('error', 'Неизвестная ошибка')}")


if __name__ == "__main__":
    main()
