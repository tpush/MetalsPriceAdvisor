import asyncio
from pyscript import document, when
import pyodide.http
import json
import time
import traceback

# Конфигурация
API_HISTORICAL_METALS_URL = '/api/historical_metals' # URL для исторических данных

# Глобальная переменная для хранения всех исторических данных, чтобы не запрашивать их каждый раз
all_historical_data_cache = {}

def display_error_in_historical_table(message):
    table_body = document.querySelector("#historical-metals-table tbody")
    if not table_body:
        print(f"ОШИБКА ФРОНТЕНДА (tabl2.py): Элемент tbody таблицы 'historical-metals-table' не найден для отображения ошибки: {message}")
        return
    table_body.innerHTML = f'<tr><td colspan="2" style="color: red; text-align: center;">{message}</td></tr>'

def populate_historical_metal_table(metal_history_list):
    table_body = document.querySelector("#historical-metals-table tbody")
    if not table_body:
        print("ОШИБКА ФРОНТЕНДА (tabl2.py): Элемент tbody таблицы 'historical-metals-table' не найден.")
        return

    table_body.innerHTML = "" # Очищаем предыдущие строки

    if not metal_history_list:
        table_body.innerHTML = '<tr><td colspan="2" style="text-align: center;">Нет исторических данных для выбранного металла.</td></tr>'
        return

    new_rows_html = ""
    for entry in metal_history_list:
        date_val = entry.get("date", "N/A")
        price_val = entry.get("price", "N/A")
        row_html = f"<tr><td>{date_val}</td><td>{price_val}</td></tr>"
        new_rows_html += row_html
        
    table_body.innerHTML = new_rows_html

async def fetch_historical_data_once():
    global all_historical_data_cache
    print(f"ФРОНТЕНД (tabl2.py): Попытка первичной загрузки исторических данных с {API_HISTORICAL_METALS_URL}")
    try:
        response = await pyodide.http.pyfetch(API_HISTORICAL_METALS_URL)
        api_response_text = await response.string()
        api_data = json.loads(api_response_text)

        if response.status != 200:
            error_message = f"Ошибка HTTP: {response.status} при запросе к {API_HISTORICAL_METALS_URL}. Ответ: {api_data.get('error', api_response_text)}"
            print(error_message)
            display_error_in_historical_table(error_message)
            return False # Указываем на неудачу

        if api_data.get("error"):
            error_message = f'Ошибка от API (исторические данные): {api_data["error"]}'
            print(error_message)
            display_error_in_historical_table(error_message)
            return False
        
        all_historical_data_cache = api_data.get("data")
        if all_historical_data_cache:
            print(f"ФРОНТЕНД (tabl2.py): Исторические данные успешно загружены и закэшированы.")
            # По умолчанию отобразим данные для первого металла в списке (если он есть)
            # Это делается для того, чтобы при первой загрузке страницы таблица не была пустой, если данные пришли
            metal_select_element = document.querySelector("#metal-select")
            date_select_element = document.querySelector("#date-select") # Нужен для передачи в update_historical_table_on_select
            
            if metal_select_element and date_select_element: 
                # Вызываем обновление с текущим значением селекта металла и даты
                # чтобы таблица заполнилась при первой загрузке, если данные пришли успешно
                # Передаем None как event, так как это не прямой вызов из события
                update_historical_table_on_select(event=None) 
            return True
        else:
            display_error_in_historical_table("API исторических данных вернуло ответ без данных.")
            print("ФРОНТЕНД (tabl2.py): API исторических данных вернуло пустые данные.")
            return False

    except Exception as e:
        error_message = f"Критическая ошибка в fetch_historical_data_once (tabl2.py): {e}"
        print(error_message)
        display_error_in_historical_table(error_message)
        traceback.print_exc()
        return False

@when("change", "#metal-select")
@when("change", "#date-select")
def update_historical_table_on_select(event):
    metal_select_element = document.querySelector("#metal-select")
    date_select_element = document.querySelector("#date-select")
    
    selected_metal = metal_select_element.value
    selected_date_raw = date_select_element.value

    selected_date_formatted = ""
    # Если дата не выбрана (пустая строка), то selected_date_formatted останется пустой,
    # и это будет означать, что фильтр по дате не применяется (показывать все даты для металла).
    if selected_date_raw:
        try:
            parts = selected_date_raw.split('-') # YYYY-MM-DD
            if len(parts) == 3:
                selected_date_formatted = f"{parts[2]}.{parts[1]}.{parts[0]}"
            else:
                print(f"ФРОНТЕНД (tabl2.py): Некорректный формат даты из поля ввода: {selected_date_raw}")
                display_error_in_historical_table(f"Выбрана некорректная дата: {selected_date_raw}")
                return
        except Exception as e:
            print(f"ФРОНТЕНД (tabl2.py): Ошибка преобразования даты '{selected_date_raw}': {e}")
            display_error_in_historical_table(f"Ошибка при обработке выбранной даты: {selected_date_raw}")
            return

    print(f"ФРОНТЕНД (tabl2.py): Обновление таблицы. Металл: {selected_metal}, Дата (исходная): {selected_date_raw}, Дата (формат.): {selected_date_formatted}")

    if not all_historical_data_cache:
        print("ФРОНТЕНД (tabl2.py): Исторические данные еще не загружены. Таблица не будет обновлена.")
        # Можно не выводить ошибку в таблицу, если это первоначальная загрузка и данные еще в пути
        # display_error_in_historical_table("Исторические данные не загружены. Попробуйте обновить страницу.")
        return

    metal_data = all_historical_data_cache.get(selected_metal)
    if metal_data:
        if selected_date_formatted:
            filtered_data = [entry for entry in metal_data if entry.get("date") == selected_date_formatted]
            if not filtered_data:
                 print(f"ФРОНТЕНД (tabl2.py): Нет данных для металла '{selected_metal}' на дату '{selected_date_formatted}'.")
                 populate_historical_metal_table([])
            else:
                populate_historical_metal_table(filtered_data)
        else:
            populate_historical_metal_table(metal_data)
    else:
        print(f"ФРОНТЕНД (tabl2.py): Нет исторических данных для металла '{selected_metal}'.")
        populate_historical_metal_table([])

print("ФРОНТЕНД (tabl2.py): Модуль tabl2.py загружен.") 