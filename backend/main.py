import http.server
import socketserver
import os
import json
import time
from threading import Lock
import re
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

PORT = 8000
WEB_DIR = os.path.join(os.path.dirname(__file__), '../frontend')
CBR_URL = 'https://www.cbr.ru/scripts/xml_metall.asp'

# Базовая структура данных о металлах
metals_cache = [
    {"name": "Золото", "price": "N/A", "unit": "руб./грамм", "date": "N/A"},
    {"name": "Серебро", "price": "N/A", "unit": "руб./грамм", "date": "N/A"},
    {"name": "Платина", "price": "N/A", "unit": "руб./грамм", "date": "N/A"},
    {"name": "Палладий", "price": "N/A", "unit": "руб./грамм", "date": "N/A"}
]

historical_metals_data_cache = {}
last_successful_update_time = 0
metals_data_lock = Lock()
parsing_error_message = None

def fetch_and_update_metal_prices():
    global metals_cache, historical_metals_data_cache, last_successful_update_time, parsing_error_message
    
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        
        params = {
            'date_req1': start_date.strftime('%d/%m/%Y'),
            'date_req2': end_date.strftime('%d/%m/%Y')
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(CBR_URL, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'xml')
        
        temp_historical_data = {
            "Золото": [], "Серебро": [], "Платина": [], "Палладий": []
        }
        
        metal_codes = {
            '1': "Золото",
            '2': "Серебро",
            '3': "Платина",
            '4': "Палладий"
        }
        
        latest_prices = {name: {"price": "N/A", "date": "N/A"} for name in metal_codes.values()}
        
        for record in soup.find_all('Record'):
            try:
                date = record['Date']
                code = record['Code']
                if code not in metal_codes:
                    continue
                    
                metal_name = metal_codes[code]
                buy_price = float(record.find('Buy').text.replace(',', '.'))
                
                temp_historical_data[metal_name].append({
                    "date": date,
                    "price": str(buy_price)
                })
                
                record_date = datetime.strptime(date, '%d.%m.%Y')
                latest_date = datetime.strptime(latest_prices[metal_name]["date"], '%d.%m.%Y') if latest_prices[metal_name]["date"] != "N/A" else datetime.min
                
                if record_date > latest_date:
                    latest_prices[metal_name] = {
                        "price": str(buy_price),
                        "date": date
                    }
                    
            except Exception as e:
                continue
        
        with metals_data_lock:
            for metal_entry in metals_cache:
                name = metal_entry["name"]
                if name in latest_prices:
                    metal_entry["price"] = latest_prices[name]["price"]
                    metal_entry["date"] = latest_prices[name]["date"]
            
            historical_metals_data_cache = temp_historical_data
            last_successful_update_time = time.time()
            parsing_error_message = None
            
    except requests.exceptions.RequestException as e:
        parsing_error_message = f"Ошибка сети при запросе к ЦБ РФ: {e}"
    except Exception as e:
        parsing_error_message = f"Произошла ошибка при парсинге данных ЦБ РФ: {e}"

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def do_GET(self):
        if self.path == '/api/hello':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {"message": "Hello from Python Backend!"}
            self.wfile.write(json.dumps(response).encode('utf-8'))
            return
            
        elif self.path == '/api/metals':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            with metals_data_lock:
                response_data = {
                    "data": metals_cache,
                    "error": parsing_error_message,
                    "last_successful_data_update": last_successful_update_time
                }
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
            return
            
        elif self.path == '/api/historical_metals':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            with metals_data_lock:
                response_data_hist = {
                    "data": historical_metals_data_cache,
                    "error": parsing_error_message,
                    "last_successful_data_update": last_successful_update_time
                }
            self.wfile.write(json.dumps(response_data_hist).encode('utf-8'))
            return
            
        elif self.path.startswith('/api/forecast/'):
            metal_code = self.path.split('/')[-1]
            metal_mapping = {
                'Au': ('gold', 'Золото'),
                'Ag': ('silver', 'Серебро'),
                'Pt': ('platinum', 'Платина'),
                'Pd': ('palladium', 'Палладий')
            }
            
            if metal_code not in metal_mapping:
                self.send_error(400, "Неверный код металла")
                return

            metal_name_en, metal_name_ru = metal_mapping[metal_code]
            
            with metals_data_lock:
                if metal_name_ru not in historical_metals_data_cache:
                    self.send_error(404, "Данные для металла не найдены")
                    return
                
                historical_data = historical_metals_data_cache[metal_name_ru]
                if not historical_data:
                    self.send_error(404, "Исторические данные отсутствуют")
                    return

            try:
                sorted_data = sorted(
                    historical_data,
                    key=lambda x: datetime.strptime(x['date'], '%d.%m.%Y')
                )
                
                one_month_ago = datetime.now() - timedelta(days=30)
                filtered_data = [
                    entry for entry in sorted_data
                    if datetime.strptime(entry['date'], '%d.%m.%Y') >= one_month_ago
                ]
                
                if len(filtered_data) < 5:
                    self.send_error(400, "Недостаточно данных за последний месяц")
                    return

                prices_for_ai = [float(entry['price']) for entry in sorted_data[-60:]]
                
                try:
                    response = requests.post(
                        'http://localhost:8001/forecast',
                        json={
                            'metal': metal_name_en,
                            'prices': ','.join(map(str, prices_for_ai))
                        }
                    )
                    response.raise_for_status()
                    forecast_data = response.json()

                    current_price = float(filtered_data[-1]['price'])
                    prices_month = [float(entry['price']) for entry in filtered_data]
                    ema_7 = sum(prices_month[-7:]) / 7 if len(prices_month) >= 7 else current_price
                    ema_21 = sum(prices_month[-21:]) / 21 if len(prices_month) >= 21 else current_price
                    ema_diff = ema_7 - ema_21
                    
                    # Анализируем прогноз цены
                    forecast_prices = forecast_data["forecast"][:7]
                    price_trend = forecast_prices[-1] - current_price
                    
                    # Определяем рекомендацию на основе обоих факторов
                    ema_signal = "BUY" if ema_diff > 0 else "SELL"
                    forecast_signal = "BUY" if price_trend > 0 else "SELL"
                    
                    # Если оба сигнала совпадают, высокая уверенность
                    # Если противоречат друг другу, низкая уверенность
                    if ema_signal == forecast_signal:
                        action = ema_signal
                        # Рассчитываем уверенность на основе обоих факторов
                        ema_strength = min(abs(ema_diff) / current_price * 100, 100) / 100
                        forecast_strength = min(abs(price_trend) / current_price * 100, 100) / 100
                        confidence = (ema_strength + forecast_strength) / 2
                    else:
                        # При противоречивых сигналах доверяем больше прогнозу
                        action = forecast_signal
                        # Уверенность ниже, так как сигналы противоречат друг другу
                        confidence = min(abs(price_trend) / current_price * 100, 100) / 200

                    response_data = {
                        "current_price": current_price,
                        "historical_data": filtered_data,
                        "forecast_prices": forecast_prices,
                        "recommendation": {
                            "action": action,
                            "confidence": confidence
                        },
                        "indicators": {
                            "ema_7": ema_7,
                            "ema_21": ema_21,
                            "ema_diff": ema_diff
                        }
                    }

                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps(response_data).encode('utf-8'))
                    return

                except requests.exceptions.RequestException as e:
                    self.send_error(500, f"Ошибка при запросе к ИИ сервису: {str(e)}")
                    return
                    
            except Exception as e:
                self.send_error(500, f"Ошибка при обработке данных: {str(e)}")
                return
                
        return super().do_GET()

fetch_and_update_metal_prices()

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    httpd.serve_forever() 