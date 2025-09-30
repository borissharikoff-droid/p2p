#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Парсер курсов обмена USDT в рубли с сайта BestChange
Сортирует обменники по количеству отзывов
"""

import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime
from typing import List, Dict, Optional, Union
from exceptions import BestChangeError


class BestChangeParser:
    """Парсер для сайта BestChange"""
    
    def __init__(self):
        self.base_url = "https://www.bestchange.com"
        self.target_url = "https://www.bestchange.com/tether-trc20-to-cash-ruble-in-msk.html"
        self.session = requests.Session()
        
        # Заголовки для имитации браузера
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        self.session.headers.update(self.headers)
    
    def get_page_content(self) -> str:
        """Получает содержимое страницы"""
        try:
            print(f"Загружаем страницу: {self.target_url}")
            response = self.session.get(self.target_url, timeout=30)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            # Проверяем, что страница загрузилась корректно
            if "USDT" not in response.text and "RUB" not in response.text:
                print("⚠️ Предупреждение: на странице не найдены ключевые слова USDT/RUB")
            
            print(f"Размер страницы: {len(response.text)} символов")
            return response.text
        except requests.RequestException as e:
            print(f"Ошибка при загрузке страницы: {e}")
            raise BestChangeError(f"Не удалось загрузить страницу: {e}")
    
    def parse_exchange_rates(self, html_content: str) -> List[Dict]:
        """Парсит курсы обмена из HTML"""
        soup = BeautifulSoup(html_content, 'lxml')
        exchange_data = []
        
        # Ищем таблицу с курсами обмена по структуре BestChange
        # Данные находятся в tbody с определенными классами
        tbody = soup.find('tbody')
        if not tbody:
            print("Таблица с курсами не найдена")
            return exchange_data
        
        # Ищем строки таблицы
        rows = tbody.find_all('tr')
        
        for row in rows:
            try:
                cells = row.find_all('td')
                if len(cells) < 6:  # Минимальное количество колонок (0-5)
                    continue
                
                # Извлекаем данные из ячеек по классам BestChange
                # Структура: [0] - иконка, [1] - обменник, [2] - лимиты, [3] - курс, [4] - резерв, [5] - отзывы
                
                # Название обменника (в div.ca)
                exchanger_cell = cells[1]
                exchanger_name_elem = exchanger_cell.find('div', class_='ca')
                if not exchanger_name_elem:
                    continue
                exchanger_name = exchanger_name_elem.get_text(strip=True)
                if not exchanger_name or len(exchanger_name) < 2:
                    continue
                
                # Курс обмена (в td.bi, ячейка 3)
                rate_cell = cells[3]
                rate_text = rate_cell.get_text(strip=True)
                
                # Отладочная информация
                print(f"Обменник: {exchanger_name}, Ячейка курса: '{rate_text}'")
                
                # Ищем число с точкой (курс) - более точный поиск
                rate_match = re.search(r'(\d+\.?\d*)', rate_text)
                if not rate_match:
                    print(f"Не найден курс в тексте: '{rate_text}'")
                    continue
                rate = float(rate_match.group(1))
                print(f"Извлеченный курс: {rate}")
                
                # Резерв (в td.ar, ячейка 4)
                reserve_cell = cells[4]
                reserve_text = reserve_cell.get_text(strip=True)
                reserve_match = re.search(r'(\d+(?:\s*\d+)*)', reserve_text.replace(' ', ''))
                reserve = 0
                if reserve_match:
                    reserve_str = reserve_match.group(1).replace(' ', '')
                    reserve = int(reserve_str) if reserve_str.isdigit() else 0
                
                # Количество отзывов (в td.rw, ячейка 5)
                reviews_cell = cells[5]
                reviews_text = reviews_cell.get_text(strip=True)
                reviews_count = 0
                reviews_match = re.search(r'(\d+)', reviews_text)
                if reviews_match:
                    reviews_count = int(reviews_match.group(1))
                
                # Ссылка на обменник
                exchanger_link = ""
                link_element = exchanger_cell.find('a')
                if link_element and link_element.get('href'):
                    href = link_element.get('href')
                    if href.startswith('/'):
                        exchanger_link = self.base_url + href
                    elif href.startswith('http'):
                        exchanger_link = href
                
                # Проверяем, что у нас есть все необходимые данные
                if rate > 0:  # Курс должен быть больше 0
                    exchange_data.append({
                        'exchanger_name': exchanger_name,
                        'rate': rate,
                        'reserve': reserve,
                        'reviews_count': reviews_count,
                        'exchanger_link': exchanger_link,
                        'parsed_at': datetime.now().isoformat()
                    })
                
            except (ValueError, AttributeError, IndexError) as e:
                print(f"Ошибка при парсинге строки: {e}")
                continue
        
        print(f"Найдено {len(exchange_data)} обменников")
        return exchange_data
    
    def sort_by_reviews(self, exchange_data: List[Dict]) -> List[Dict]:
        """Сортирует обменники по количеству отзывов (по убыванию)"""
        return sorted(exchange_data, key=lambda x: x['reviews_count'], reverse=True)
    
    def format_output(self, exchange_data: List[Dict]) -> str:
        """Форматирует вывод данных"""
        if not exchange_data:
            return "Данные об обменниках не найдены"
        
        output = []
        output.append("=" * 80)
        output.append("КУРСЫ ОБМЕНА USDT TRC20 → РУБЛИ (НАЛИЧНЫЕ)")
        output.append("=" * 80)
        output.append(f"Найдено обменников: {len(exchange_data)}")
        output.append(f"Время парсинга: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        output.append("")
        output.append("ОБМЕННИКИ (отсортированы по количеству отзывов):")
        output.append("-" * 80)
        
        for i, data in enumerate(exchange_data, 1):
            output.append(f"{i:2d}. {data['exchanger_name']}")
            output.append(f"    Курс: 1 USDT = {data['rate']:.4f} RUB")
            output.append(f"    Резерв: {data['reserve']:,} RUB")
            output.append(f"    Отзывы: {data['reviews_count']}")
            if data['exchanger_link']:
                output.append(f"    Ссылка: {data['exchanger_link']}")
            output.append("")
        
        return "\n".join(output)
    
    def save_to_json(self, exchange_data: List[Dict], filename: str = None) -> str:
        """Сохраняет данные в JSON файл"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"bestchange_rates_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(exchange_data, f, ensure_ascii=False, indent=2)
        
        return filename
    
    def run(self) -> Dict[str, Union[bool, str, List[Dict], int]]:
        """Основной метод для запуска парсера"""
        print("Запуск парсера BestChange...")
        
        try:
            # Получаем содержимое страницы
            html_content = self.get_page_content()
            
            # Парсим данные
            exchange_data = self.parse_exchange_rates(html_content)
            if not exchange_data:
                raise BestChangeError("Не удалось извлечь данные об обменниках")
            
            # Сортируем по количеству отзывов
            sorted_data = self.sort_by_reviews(exchange_data)
            
            # Форматируем вывод
            formatted_output = self.format_output(sorted_data)
            
            # Сохраняем в JSON
            json_filename = self.save_to_json(sorted_data)
            
            return {
                "success": True,
                "data": sorted_data,
                "formatted_output": formatted_output,
                "json_file": json_filename,
                "total_exchangers": len(sorted_data)
            }
        except BestChangeError:
            raise
        except Exception as e:
            raise BestChangeError(f"Неожиданная ошибка парсера: {e}")


def main():
    """Главная функция"""
    parser = BestChangeParser()
    result = parser.run()
    
    if result.get("success"):
        print(result["formatted_output"])
        print(f"\nДанные сохранены в файл: {result['json_file']}")
    else:
        print(f"Ошибка: {result.get('error', 'Неизвестная ошибка')}")


if __name__ == "__main__":
    main()
