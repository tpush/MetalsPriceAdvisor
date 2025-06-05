import asyncio
from pyscript import document
import pyodide.http
import json
import time
import traceback

# Конфигурация для таблицы актуальных цен
API_METALS_URL = '/api/metals'
UPDATE_INTERVAL_SECONDS = 300  # 5 минут в секундах

def display_error_in_table(message):
    table_body = document.querySelector("#metals-table tbody")
    if not table_body:
        print(f"ОШИБКА ФРОНТЕНДА (tabl1.py): Элемент tbody таблицы 'metals-table' не найден для отображения ошибки: {message}")
        return
    table_body.innerHTML = f'<tr><td colspan="4" style="color: red; text-align: center;">{message}</td></tr>'
    print(f"ФРОНТЕНД (tabl1.py): Отображена ошибка в таблице актуальных цен: {message}")

def populate_metal_table(metals_list):
    table_body = document.querySelector("#metals-table tbody")
    if not table_body:
        print("ОШИБКА ФРОНТЕНДА (tabl1.py): Элемент tbody таблицы 'metals-table' не найден.")
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
        
        row_html = f"<tr><td>{name_val}</td><td>{price_val}</td><td>{unit_val}</td><td>{date_val}</td></tr>"
        new_rows_html += row_html
        
    table_body.innerHTML = new_rows_html

async def fetch_and_update_actual_metals_data(): # Переименована для ясности
    print(f"ФРОНТЕНД (tabl1.py): Попытка запроса данных с {API_METALS_URL} в {time.strftime('%H:%M:%S')}")
    try:
        response = await pyodide.http.pyfetch(API_METALS_URL)
        api_response_text = await response.string()
        api_data = json.loads(api_response_text)

        if response.status != 200:
            error_message = f"Ошибка HTTP: {response.status} при запросе к {API_METALS_URL}. Ответ: {api_data.get('error', api_response_text)}"
            print(error_message)
            display_error_in_table(error_message)
            return

        if api_data.get("error"):
            error_message = f'Ошибка от API бэкенда: {api_data["error"]}'
            if api_data.get("last_successful_data_update", 0) == 0 and not api_data.get("data"):
                 error_message += " (Данные с ЦБ еще ни разу не были успешно загружены сервером)"
            print(error_message)
            display_error_in_table(error_message)
            return
        
        metals = api_data.get("data")
        if metals:
            populate_metal_table(metals)
        else:
            display_error_in_table("API бэкенда вернуло ответ без данных и без явной ошибки.")
            print("ФРОНТЕНД (tabl1.py): API бэкенда вернуло пустые данные без явной ошибки.")

    except Exception as e:
        error_message = f"Критическая ошибка в fetch_and_update_actual_metals_data (tabl1.py): {e}"
        print(error_message)
        display_error_in_table(error_message)
        traceback.print_exc()

print("ФРОНТЕНД (tabl1.py): Модуль tabl1.py загружен.") 