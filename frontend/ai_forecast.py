print("ФРОНТЕНД (ai_forecast.py): Файл ai_forecast.py НАЧАЛ ВЫПОЛНЯТЬСЯ.")

import asyncio
from pyscript import document, when
from pyodide.ffi import to_js, create_proxy
import pyodide.http
import json
import traceback
from datetime import datetime, timedelta
import js

# Глобальная переменная для хранения экземпляра графика прогноза
current_forecast_chart = None

def update_recommendation_box(action, confidence, ema_diff):
    """Обновляет блок рекомендации на основе полученных данных"""
    try:
        recommendation_action = document.querySelector("#recommendation-action")
        recommendation_confidence = document.querySelector("#recommendation-confidence")
        ema_info = document.querySelector("#ema-info")
        recommendation_box = document.querySelector(".recommendation-box")
        
        if recommendation_action:
            recommendation_action.textContent = action
        if recommendation_confidence:
            recommendation_confidence.textContent = f"{int(confidence * 100)}%"
        if ema_info:
            ema_info.textContent = f"EMA7 {'>' if ema_diff > 0 else '<'} EMA21 на {abs(ema_diff):.2f}"
        
        if recommendation_box:
            recommendation_box.classList.remove("BUY", "SELL")
            recommendation_box.classList.add(action)
            
    except Exception as e:
        print(f"Ошибка при обновлении блока рекомендации: {e}")

def update_price_display(price):
    """Обновляет отображение текущей цены"""
    try:
        price_element = document.querySelector("#current-price")
        if price_element:
            price_element.textContent = f"{price:.2f} руб"
    except Exception as e:
        print(f"Ошибка при обновлении цены: {e}")

async def get_forecast_data(metal_code):
    """Получает прогноз от бэкенда"""
    try:
        response = await pyodide.http.pyfetch(
            f"/api/forecast/{metal_code}",
            method="GET",
            headers={"Accept": "application/json"}
        )
        
        if response.status != 200:
            error_text = await response.text()
            raise Exception(f"Ошибка HTTP {response.status}: {error_text}")
        
        return await response.json()
        
    except Exception as e:
        print(f"Ошибка при получении прогноза: {e}")
        raise e

def create_forecast_chart(historical_data, forecast_data):
    """Создает график с историческими данными и прогнозом"""
    global current_forecast_chart
    
    try:
        # Подготовка данных для графика
        dates = [entry["date"] for entry in historical_data]
        prices = [float(entry["price"]) for entry in historical_data]
        
        # Добавляем прогнозные значения
        forecast_dates = [
            (datetime.strptime(dates[-1], "%d.%m.%Y") + timedelta(days=i+1)).strftime("%d.%m.%Y")
            for i in range(len(forecast_data))
        ]
        
        # Конфигурация графика
        chart_config = {
            'type': 'line',
            'data': {
                'labels': to_js(dates + forecast_dates),
                'datasets': [
                    {
                        'label': 'Исторические данные',
                        'data': to_js(prices + [None] * len(forecast_data)),
                        'borderColor': 'rgb(75, 192, 192)',
                        'fill': False
                    },
                    {
                        'label': 'Прогноз',
                        'data': to_js([None] * len(prices) + forecast_data),
                        'borderColor': 'rgb(255, 99, 132)',
                        'borderDash': [5, 5],
                        'fill': False
                    }
                ]
            },
            'options': {
                'responsive': True,
                'maintainAspectRatio': False,
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
                },
                'plugins': {
                    'title': {
                        'display': True,
                        'text': 'Исторические данные и прогноз'
                    }
                }
            }
        }

        # Получаем canvas и создаем график
        canvas = js.document.getElementById('ai-forecast-chart')
        if not canvas:
            raise Exception("Canvas для графика прогноза не найден")

        # Уничтожаем предыдущий график, если он существует
        if current_forecast_chart:
            current_forecast_chart.destroy()

        # Создаем новый график
        js_config = to_js(chart_config, dict_converter=js.Object.fromEntries)
        current_forecast_chart = js.Chart.new(canvas.getContext('2d'), js_config)
        
    except Exception as e:
        print(f"Ошибка при создании графика прогноза: {e}")
        traceback.print_exc()

async def handle_forecast_button_click(event=None):
    """Обработчик нажатия кнопки получения прогноза"""
    try:
        metal_select = document.querySelector("#forecast-metal-select")
        if not metal_select:
            raise Exception("Элемент выбора металла не найден")
            
        selected_metal = metal_select.value
        forecast_data = await get_forecast_data(selected_metal)
        
        if not isinstance(forecast_data, dict):
            try:
                if hasattr(forecast_data, 'to_py'):
                    forecast_data = forecast_data.to_py()
                elif isinstance(forecast_data, str):
                    forecast_data = json.loads(forecast_data)
            except Exception as e:
                raise Exception("Неверный формат данных прогноза")
        
        if "error" in forecast_data:
            raise Exception(forecast_data["error"])
            
        required_fields = ["recommendation", "current_price", "historical_data", "forecast_prices"]
        for field in required_fields:
            if field not in forecast_data:
                raise Exception(f"В ответе отсутствует обязательное поле: {field}")
            
        update_recommendation_box(
            forecast_data["recommendation"]["action"],
            forecast_data["recommendation"]["confidence"],
            forecast_data["indicators"]["ema_diff"]
        )
        
        update_price_display(forecast_data["current_price"])
        create_forecast_chart(
            forecast_data["historical_data"],
            forecast_data["forecast_prices"]
        )
        
    except Exception as e:
        print(f"Ошибка при получении прогноза: {e}")

def bind_event_handlers():
    try:
        button = document.querySelector("#get-forecast-btn")
        if button:
            def proxy_handler(_):
                asyncio.ensure_future(handle_forecast_button_click())
            
            handler = create_proxy(proxy_handler)
            button.addEventListener("click", handler)
        else:
            print("Кнопка прогноза не найдена")
    except Exception as e:
        print(f"Ошибка при привязке обработчика: {e}")

bind_event_handlers()

print("ФРОНТЕНД (ai_forecast.py): Файл ai_forecast.py загружен.") 