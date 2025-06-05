# Этот файл предназначен для Python-кода на стороне клиента (если потребуется).
# Например, с использованием PyScript или Brython.

import asyncio
from pyscript import document, when
import pyodide.http
import json # Для разбора JSON ответа
import time # Для вывода времени в консоль (опционально)
import traceback # Добавим, так как он используется в display_error_in_table
import numbers
from datetime import datetime, timedelta

# Импортируем функции из tabl2.py
# Предполагается, что PyScript сможет найти этот файл в той же директории
# Если будут проблемы, возможно, потребуется более явное указание пути или другая конфигурация PyScript
# На данный момент PyScript обычно автоматически загружает соседние .py файлы, если они импортируются.
import tabl2
# import tabl1 # Закомментируем или удалим глобальный импорт

# Попытка импорта из grafik.py для проверки его загрузки и для вызова функции
try:
    from grafik import display_chart_error, set_external_historical_data
except ImportError as e:
    print(f"ФРОНТЕНД (main.py): Не удалось импортировать функции из grafik.py: {e}")
    def display_chart_error(message): pass # Заглушка
    def set_external_historical_data(data): pass # Заглушка

# Конфигурация
API_METALS_URL = '/api/metals' # URL нашего бэкенд API
UPDATE_INTERVAL_SECONDS = 300  # 5 минут в секундах
# API_HISTORICAL_METALS_URL и all_historical_data_cache теперь в tabl2.py

def display_error_in_table(message):
    table_body = document.querySelector("#metals-table tbody")
    if not table_body:
        print(f"ОШИБКА ФРОНТЕНДА: Элемент tbody таблицы 'metals-table' не найден для отображения ошибки: {message}")
        return
    table_body.innerHTML = f'<tr><td colspan="4" style="color: red; text-align: center;">{message}</td></tr>'
    print(f"ФРОНТЕНД: Отображена ошибка в таблице: {message}")

def populate_metal_table(metals_list):
    table_body = document.querySelector("#metals-table tbody")
    if not table_body:
        print("ОШИБКА ФРОНТЕНДА: Элемент tbody таблицы 'metals-table' не найден.")
        return

    table_body.innerHTML = "" # Очищаем предыдущие строки

    if not metals_list:
        display_error_in_table("Нет данных для отображения от API.")
        return

    new_rows_html = ""
    for i, metal in enumerate(metals_list):
        
        name_val = metal.get("name", "N/A")
        price_val = metal.get("price", "N/A")
        unit_val = metal.get("unit", "руб./грамм")
        date_val = metal.get("date", "N/A")
        
        # Формируем HTML для строки
        row_html = f"<tr><td>{name_val}</td><td>{price_val}</td><td>{unit_val}</td><td>{date_val}</td></tr>"
        new_rows_html += row_html
        
    table_body.innerHTML = new_rows_html

async def fetch_and_update_metals_data():
    print(f"ФРОНТЕНД (main.py): Попытка запроса данных с {API_METALS_URL} в {time.strftime('%H:%M:%S')}")
    try:
        response = await pyodide.http.pyfetch(API_METALS_URL)
        
        api_response_text = await response.string()
        # print(f"ФРОНТЕНД: Ответ от API получен: {api_response_text[:200]}...") # Логируем часть ответа
        api_data = json.loads(api_response_text)

        if response.status != 200:
            error_message = f"Ошибка HTTP: {response.status} при запросе к {API_METALS_URL}. Ответ: {api_data.get('error', api_response_text)}"
            print(error_message)
            display_error_in_table(error_message)
            return

        if api_data.get("error"):
            # Используем более информативное сообщение, если ошибка пришла от бэкенда
            error_message = f'Ошибка от API бэкенда: {api_data["error"]}'
            if api_data.get("last_successful_data_update", 0) == 0 and not api_data.get("data"):
                 error_message += " (Данные с ЦБ еще ни разу не были успешно загружены сервером)"
            print(error_message)
            display_error_in_table(error_message)
            # Если есть старые данные, но ошибка, можно их показать, но пока просто ошибка
            # if api_data.get("data"):
            #     populate_metal_table(api_data.get("data")) # Показать старые данные с сообщением об ошибке обновления
            return
        
        metals = api_data.get("data")
        if metals:
            populate_metal_table(metals)
            # last_updated_server_readable = time.ctime(api_data.get("last_successful_data_update", 0)) if api_data.get("last_successful_data_update") else "N/A"
            # print(f"ФРОНТЕНД: Данные успешно загружены. Последнее успешное обновление на сервере: {last_updated_server_readable}")
        else:
            display_error_in_table("API бэкенда вернуло ответ без данных и без явной ошибки.")
            print("ФРОНТЕНД (main.py): API бэкенда вернуло пустые данные без явной ошибки.")

    except Exception as e:
        error_message = f"Критическая ошибка в fetch_and_update_metals_data (main.py): {e}"
        print(error_message)
        display_error_in_table(error_message)
        traceback.print_exc() # Для более детальной отладки в консоли браузера

async def main_loop():
    print(f"ФРОНТЕНД (main.py): Запуск основного цикла.")
    
    # Импортируем tabl1 здесь, прямо перед использованием
    import tabl1
    print(f"ФРОНТЕНД (main.py): tabl1 импортирован внутри main_loop: {type(tabl1)}")

    # Однократная загрузка исторических данных при старте из tabl2.py
    historical_data_loaded_successfully = await tabl2.fetch_historical_data_once()
    await asyncio.sleep(0.1) 
    
    # Передаем загруженные исторические данные в модуль grafik
    if historical_data_loaded_successfully and tabl2.all_historical_data_cache:
        import grafik
        grafik.set_external_historical_data(tabl2.all_historical_data_cache)
        grafik.bind_chart_event_handlers()
    
    # Первоначальная загрузка актуальных цен
    print("ФРОНТЕНД (main.py): Первоначальная загрузка актуальных цен из tabl1...")
    await tabl1.fetch_and_update_actual_metals_data()

    # Основной цикл для обновления актуальных цен из tabl1.py
    while True:
        await tabl1.fetch_and_update_actual_metals_data() 
        print(f"ФРОНТЕНД (main.py): Ожидание {tabl1.UPDATE_INTERVAL_SECONDS} секунд до следующего обновления актуальных цен... ({time.strftime('%H:%M:%S')})")
        await asyncio.sleep(tabl1.UPDATE_INTERVAL_SECONDS)

print("ФРОНТЕНД (main.py): PyScript (main.py) загружен. Запуск основного цикла...")
asyncio.ensure_future(main_loop())

from pyscript import display

async def fetch_last_60_prices(metal_ru):
    # Map Russian to English for API
    metal_map = {
        'Золото': 'gold',
        'Серебро': 'silver',
        'Платина': 'platinum',
        'Палладий': 'palladium',
    }
    metal = metal_map.get(metal_ru, 'gold')
    # Fetch historical data from backend
    try:
        resp = await pyodide.http.pyfetch('/api/historical_metals')
        data = await resp.json()
        hist = data.get('data', {})
        metal_hist = hist.get(metal_ru, [])
        # Sort by date ascending
        metal_hist_sorted = sorted(metal_hist, key=lambda x: x['date'])
        last_60 = metal_hist_sorted[-60:] if len(metal_hist_sorted) >= 60 else metal_hist_sorted
        prices = [float(x['price']) for x in last_60 if x['price'] != 'N/A']
        if len(prices) < 60:
            return None, None  # Not enough data
        dates = [x['date'] for x in last_60]
        return prices, dates
    except Exception as e:
        print(f"Ошибка при получении исторических данных: {e}")
        return None, None

async def get_ai_forecast(metal, prices):
    url = 'http://localhost:8001/forecast'
    payload = {
        'metal': metal,
        'prices': ','.join(str(p) for p in prices)
    }
    try:
        resp = await pyodide.http.pyfetch(url, method='POST', headers={'Content-Type': 'application/json'}, body=json.dumps(payload))
        data = await resp.json()
        return data.get('forecast', [])
    except Exception as e:
        print(f"Ошибка AI API: {e}")
        return None

def calculate_ema(prices, period):
    ema = []
    k = 2 / (period + 1)
    for i, price in enumerate(prices):
        if i == 0:
            ema.append(price)
        else:
            ema.append(price * k + ema[-1] * (1 - k))
    return ema

def update_ai_card(metal_en, metal_ru, last_price, forecast, dates, prices):
    # Update metal name and price
    name_span = document.querySelector('#ai-metal-name')
    name_span.textContent = metal_ru
    price_span = document.querySelector('#ai-metal-price')
    # Show only the first forecast value for all metals
    if forecast and isinstance(forecast, list) and len(forecast) > 0:
        predicted_price = forecast[0]
        price_span.textContent = f"{predicted_price} руб"
    else:
        price_span.textContent = f"— руб"
    # Recommendation logic using EMA7 and EMA21 (same for all metals)
    rec_div = document.querySelector('#ai-recommendation')
    if forecast and len(forecast) > 0 and prices and len(prices) >= 21:
        all_prices = prices + [forecast[0]]
        ema7 = calculate_ema(all_prices, 7)[-1]
        ema21 = calculate_ema(all_prices, 21)[-1]
        diff = round(abs(ema7 - ema21), 2)
        if ema7 > ema21:
            rec = 'BUY'
            color = 'BUY'
            msg = f'EMA7 > EMA21 на {diff}'
        elif ema7 < ema21:
            rec = 'SELL'
            color = 'SELL'
            msg = f'EMA7 < EMA21 на {diff}'
        else:
            rec = 'HOLD'
            color = 'HOLD'
            msg = 'Нет выраженного тренда'
        conf = '50%'  # Placeholder
        rec_html = f'<b>Рекомендация: {rec}</b><br>Уверенность: {conf}<br>{msg}'
        rec_div.className = f'recommendation {color}'
        rec_div.innerHTML = rec_html
    else:
        rec_div.className = 'recommendation'
        rec_div.innerHTML = '<b>Рекомендация: —</b><br>Уверенность: —<br>—'

    # Update chart
    from js import Chart
    ctx = document.querySelector('#ai-forecast-chart').getContext('2d')
    if hasattr(update_ai_card, 'chart') and update_ai_card.chart:
        update_ai_card.chart.destroy()
        update_ai_card.chart = None

    # Создаем массивы для исторических данных и прогноза
    historical_dates = dates[-30:] if dates else []  # Берем последний месяц
    historical_prices = prices[-30:] if prices else []  # Берем последний месяц
    
    # Создаем даты для прогноза (7 дней вперед)
    if historical_dates:
        last_date = datetime.strptime(historical_dates[-1], '%d.%m.%Y')
        forecast_dates = [(last_date + timedelta(days=i+1)).strftime('%d.%m.%Y') for i in range(len(forecast))]
    else:
        forecast_dates = []

    # Создаем данные для соединительной линии
    connection_dates = [historical_dates[-1], forecast_dates[0]] if historical_dates and forecast_dates else []
    connection_prices = [historical_prices[-1], forecast[0]] if historical_prices and forecast else []

    chart_data = {
        'type': 'line',
        'data': {
            'labels': to_js(historical_dates + forecast_dates),
            'datasets': [
                {
                    'label': 'Исторические данные',
                    'data': to_js(historical_prices + [None] * len(forecast)),
                    'borderColor': 'rgb(75, 192, 192)',
                    'tension': 0.1,
                    'fill': False
                },
                {
                    'label': 'Прогноз',
                    'data': to_js([None] * len(historical_prices) + forecast),
                    'borderColor': 'rgb(255, 99, 132)',
                    'tension': 0.1,
                    'fill': False,
                    'borderDash': [5, 5]
                },
                {
                    'label': '',  # Пустой label, чтобы не отображалось в легенде
                    'data': to_js([None] * (len(historical_dates) - 1) + connection_prices + [None] * (len(forecast) - 1)),
                    'borderColor': 'rgb(255, 165, 0)',  # Оранжевый цвет
                    'tension': 0,
                    'fill': False,
                    'borderWidth': 2,
                    'pointRadius': 0,  # Убираем точки
                    'showLine': True  # Показываем только линию
                }
            ]
        },
        'options': {
            'responsive': True,
            'maintainAspectRatio': False,
            'plugins': {
                'legend': {
                    'display': True,
                    'labels': {
                        'filter': lambda item, chart: item['text'] != ''  # Скрываем пустые метки
                    }
                },
                'title': {
                    'display': True,
                    'text': 'Исторические данные и прогноз'
                }
            },
            'scales': {
                'y': {
                    'beginAtZero': False,
                    'title': {
                        'display': True,
                        'text': 'Цена (руб./грамм)'
                    }
                },
                'x': {
                    'title': {
                        'display': True,
                        'text': 'Дата'
                    }
                }
            }
        }
    }

    js_chart_data = to_js(chart_data, dict_converter=js.Object.fromEntries)
    update_ai_card.chart = Chart.new(ctx, js_chart_data)

from pyscript import when

@when('click', '#ai-forecast-btn')
async def on_ai_forecast_btn_click(event=None):
    metal_select = document.querySelector('#ai-metal-select')
    metal_en = metal_select.value
    metal_ru_map = {'gold': 'Золото', 'silver': 'Серебро', 'platinum': 'Платина', 'palladium': 'Палладий'}
    metal_ru = metal_ru_map.get(metal_en, 'Золото')
    prices, dates = await fetch_last_60_prices(metal_ru)
    if not prices or not dates:
        rec_div = document.querySelector('#ai-recommendation')
        rec_div.className = 'recommendation'
        rec_div.innerHTML = '<b>Недостаточно данных для прогноза</b>'
        return
    forecast = await get_ai_forecast(metal_en, prices)
    last_price = prices[-1] if prices else '—'

    # Swap forecast for palladium and platinum
    if metal_en == 'palladium':
        other_prices, _ = await fetch_last_60_prices('Платина')
        other_forecast = await get_ai_forecast('platinum', other_prices)
        if other_forecast and isinstance(other_forecast, list) and len(other_forecast) > 0:
            forecast = other_forecast
    elif metal_en == 'platinum':
        other_prices, _ = await fetch_last_60_prices('Палладий')
        other_forecast = await get_ai_forecast('palladium', other_prices)
        if other_forecast and isinstance(other_forecast, list) and len(other_forecast) > 0:
            forecast = other_forecast

    # Bulletproof check: forecast must be a non-empty list of numbers
    if (
        not isinstance(forecast, list)
        or not forecast
        or any([isinstance(forecast, dict), forecast is None])
        or not all(isinstance(x, numbers.Number) for x in forecast)
    ):
        rec_div = document.querySelector('#ai-recommendation')
        rec_div.className = 'recommendation'
        rec_div.innerHTML = '<b>Рекомендация: —</b><br>Уверенность: —<br>—'
        # Clear the chart
        from js import Chart
        ctx = document.querySelector('#ai-forecast-chart').getContext('2d')
        if hasattr(update_ai_card, 'chart') and update_ai_card.chart:
            update_ai_card.chart.destroy()
            update_ai_card.chart = None
        return
    update_ai_card(metal_en, metal_ru, last_price, forecast, dates, prices) 