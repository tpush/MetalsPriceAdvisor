print("ФРОНТЕНД (grafik.py): Файл grafik.py НАЧАЛ ВЫПОЛНЯТЬСЯ.")
import asyncio
from pyscript import document
from pyodide.ffi import to_js, create_proxy
import json
import time
import traceback
from datetime import datetime
import js

# Локальный кэш для данных, полученных из main.py
grafik_local_cache = {}

# Попытка импортировать display_error_in_historical_table из tabl2.py (если он там еще нужен для чего-то, кроме основного кэша)
# и all_historical_data_cache (хотя мы его напрямую использовать не будем, но импорт может быть нужен для PyScript)
try:
    from tabl2 import display_error_in_historical_table, all_historical_data_cache as tabl2_cache_ref # Импортируем для разрешения зависимостей, но использовать будем grafik_local_cache
except ImportError:
    print("ОШИБКА ИМПОРТА (grafik.py): Не удалось импортировать из tabl2.py. Часть функционала может не работать.")
    def display_error_in_historical_table(message):
        print(f"FALLBACK DISPLAY ERROR (grafik.py): {message}")
    tabl2_cache_ref = None # Заглушка

# Глобальная переменная для хранения экземпляра графика, чтобы его можно было обновлять или уничтожать
current_chart = None
# historical_data_is_ready = False # Убираем флаг

# def mark_historical_data_as_ready(): # Убираем функцию
#     global historical_data_is_ready
#     historical_data_is_ready = True
#     print("ФРОНТЕНД (grafik.py): Получен сигнал - исторические данные готовы.")

def set_external_historical_data(data):
    global grafik_local_cache
    grafik_local_cache = data
    print(f"ФРОНТЕНД (grafik.py): Внешние исторические данные установлены. Ключи: {list(grafik_local_cache.keys()) if grafik_local_cache else 'Кэш пуст'}")

def display_chart_error(message):
    # Попробуем найти существующий элемент или создать его, если это необходимо
    error_display_container = document.querySelector("#chart-error-container") # Используем контейнер
    if not error_display_container:
        # Если контейнера нет, можно создать его или просто логировать ошибку
        print(f"ФРОНТЕНД (grafik.py): Контейнер для ошибок графика #chart-error-container не найден. Ошибка: {message}")
        # В качестве альтернативы, можно создать этот элемент динамически, но это усложнит код.
        # Пока что, если контейнера нет, ошибка будет только в консоли.
        # Для простоты, предполагаем, что контейнер есть в HTML.
        # Если хотите, чтобы он создавался динамически, дайте знать.
        return
    
    error_display_container.innerHTML = f'<p style="color: red; text-align: center;">{message}</p>'
    print(f"ФРОНТЕНД (grafik.py): Отображена ошибка графика: {message}")

# Функция для преобразования даты из "ДД.ММ.ГГГГ" в объект Python datetime
def parse_custom_date(date_str):
    if not date_str or date_str == "N/A":
        return None
    try:
        return datetime.strptime(date_str, "%d.%m.%Y")
    except ValueError:
        print(f"Ошибка парсинга даты (grafik.py): {date_str}")
        return None

# Функция для преобразования даты из "YYYY-MM-DD" (из input) в объект Python datetime
def parse_input_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        print(f"Ошибка парсинга даты из поля ввода (grafik.py): {date_str}")
        return None

# Удаляем create_test_chart и handle_update_chart_button_click_TEST

async def handle_update_chart_button_click(event=None):
    print("ФРОНТЕНД (grafik.py): Нажата кнопка 'Показать график' (ID: #update-chart-button)")
    global current_chart, grafik_local_cache

    metal_select_element = document.querySelector("#chart-metal-select")
    date_start_input = document.querySelector("#chart-date-start")
    date_end_input = document.querySelector("#chart-date-end")

    if not (metal_select_element and date_start_input and date_end_input):
        display_chart_error("Не удалось найти элементы управления фильтрами графика.")
        return

    selected_metal = metal_select_element.value
    date_start_str = date_start_input.value
    date_end_str = date_end_input.value
    
    print(f"ФРОНТЕНД (grafik.py): Параметры для графика: Металл={selected_metal}, Старт={date_start_str}, Конец={date_end_str}")

    if not grafik_local_cache:
        display_chart_error("Исторические данные для графика еще не загружены или пусты. Попробуйте обновить страницу или подождать.")
        print("ФРОНТЕНД (grafik.py): grafik_local_cache пуст.")
        return

    metal_historical_data = grafik_local_cache.get(selected_metal)
    
    if not metal_historical_data:
        display_chart_error(f"Нет исторических данных для металла '{selected_metal}'.")
        print(f"ФРОНТЕНД (grafik.py): Нет данных для металла '{selected_metal}' в кэше.")
        return

    date_start_obj = parse_input_date(date_start_str)
    date_end_obj = parse_input_date(date_end_str)

    filtered_entries = []
    for entry in metal_historical_data:
        entry_date_str = entry.get("date")
        entry_price_str = entry.get("price")
        entry_date_obj = parse_custom_date(entry_date_str)

        if entry_date_obj and entry_price_str is not None and entry_price_str != "N/A":
            valid_entry = True
            if date_start_obj and entry_date_obj < date_start_obj:
                valid_entry = False
            if date_end_obj and entry_date_obj > date_end_obj:
                valid_entry = False
            
            if valid_entry:
                try:
                    # Убедимся, что цена - это строка перед заменой, затем float
                    price_str_cleaned = str(entry_price_str).replace(',', '.')
                    price = float(price_str_cleaned)
                    filtered_entries.append({"date": entry_date_obj, "price": price, "date_str": entry_date_str})
                except ValueError:
                    print(f"ФРОНТЕНД (grafik.py): Пропуск записи для графика: не удалось преобразовать цену '{entry_price_str}' в число для даты {entry_date_str}")
    
    if not filtered_entries:
        display_chart_error(f"Нет данных для графика для металла '{selected_metal}' в указанном диапазоне дат.")
        print(f"ФРОНТЕНД (grafik.py): Нет отфильтрованных записей для '{selected_metal}' с {date_start_str} по {date_end_str}.")
        # Очистим график, если он был, и данных нет
        if current_chart:
            try:
                current_chart.destroy()
                current_chart = None
                print("ФРОНТЕНД (grafik.py): График очищен, так как нет данных для отображения.")
            except Exception as e_destroy:
                print(f"ФРОНТЕНД (grafik.py): Ошибка при уничтожении графика (нет данных): {e_destroy}")
        # Можно также очистить canvas, если это необходимо, но destroy обычно достаточно
        canvas_el_js = js.document.getElementById('metalsPriceChart')
        if canvas_el_js:
             ctx = canvas_el_js.getContext('2d')
             ctx.clearRect(0, 0, canvas_el_js.width, canvas_el_js.height)
        return

    filtered_entries.sort(key=lambda x: x["date"])

    labels = [entry["date_str"] for entry in filtered_entries]
    data_points = [entry["price"] for entry in filtered_entries]

    chart_data_config = {
        'type': 'line',
        'data': {
            'labels': to_js(labels), # Преобразуем Python list в JS Array
            'datasets': [{
                'label': f'Цена на {selected_metal} (руб./грамм)',
                'data': to_js(data_points), # Преобразуем Python list в JS Array
                'fill': False,
                'borderColor': 'rgb(75, 192, 192)',
                'tension': 0.1
            }]
        },
        'options': {
            'responsive': True,
            'maintainAspectRatio': False,
            'scales': {
                'x': { # Настройки для оси X (даты)
                    'title': {
                        'display': True,
                        'text': 'Дата'
                    }
                },
                'y': { # Настройки для оси Y (цены)
                    'beginAtZero': False, # Обычно цены на металлы не начинаются с нуля
                    'title': {
                        'display': True,
                        'text': 'Цена (руб./грамм)'
                    }
                }
            },
            'plugins': {
                'legend': {
                    'position': 'top',
                },
                'title': {
                    'display': True,
                    'text': f'Динамика цен на {selected_metal}'
                }
            }
        }
    }

    try:
        canvas_el_js = js.document.getElementById('metalsPriceChart')
        if not canvas_el_js:
            display_chart_error("Элемент canvas 'metalsPriceChart' не найден для создания графика.")
            return

        ctx = canvas_el_js.getContext('2d')
        if not ctx:
            display_chart_error("Не удалось получить 2D контекст для графика.")
            return

        if current_chart:
            try:
                current_chart.destroy()
                print("ФРОНТЕНД (grafik.py): Старый график уничтожен перед созданием нового.")
            except Exception as e_destroy:
                print(f"ФРОНТЕНД (grafik.py): Ошибка при уничтожении старого графика: {e_destroy}")
        
        # Используем dict_converter=js.Object.fromEntries для лучшей совместимости с Chart.js 4.x
        js_chart_data_config = to_js(chart_data_config, dict_converter=js.Object.fromEntries)
        
        current_chart = js.Chart.new(ctx, js_chart_data_config)
        print(f"ФРОНТЕНД (grafik.py): График для '{selected_metal}' создан/обновлен.")
        # Очистим сообщение об ошибке, если график успешно построен
        error_display_container = document.querySelector("#chart-error-container")
        if error_display_container:
            error_display_container.innerHTML = ""


    except Exception as e:
        error_msg_critical = f"КРИТИЧЕСКАЯ ОШИБКА Python при создании/обновлении графика: {e}"
        print(error_msg_critical)
        traceback.print_exc()
        display_chart_error(f"Критическая ошибка Python при построении графика: {e}")

def bind_chart_event_handlers():
    try:
        button = document.querySelector("#update-chart-button")
        if button:
            def proxy_handler(_):
                asyncio.ensure_future(handle_update_chart_button_click())
            
            handler = create_proxy(proxy_handler)
            button.addEventListener("click", handler)
    except Exception as e:
        print(f"Ошибка при привязке обработчика для графика: {e}")

# Удаляем ненужные закомментированные импорты и функции, если они остались
# Убедимся, что tabl2_cache_ref больше не используется, так как мы используем grafik_local_cache
# Убираем from tabl2 import display_error_in_historical_table, all_historical_data_cache as tabl2_cache_ref
# Вместо этого, если display_chart_error должен обрабатывать ошибки из tabl2, то это нужно пересмотреть.
# Но пока что display_chart_error - это специфичная для графика функция.

print("ФРОНТЕНД (grafik.py): Файл grafik.py ЗАВЕРШИЛ ВЫПОЛНЕНИЕ НАЧАЛЬНОЙ ЗАГРУЗКИ.")

# Закомментированный код ниже более не нужен, так как логика встроена в handle_update_chart_button_click
# # metal_select = document.querySelector("#chart-metal-select")
# # date_start_input = document.querySelector("#chart-date-start")
# # date_end_input = document.querySelector("#chart-date-end")

# # selected_metal = metal_select.value
# # date_start_str = date_start_input.value
# # date_end_str = date_end_input.value
# # print(f"ФРОНТЕНД (grafik.py): Параметры для графика: Металл={selected_metal}, Старт={date_start_str}, Конец={date_end_str}")
# # 
# # grafik_local_cache = get_historical_data_cache_from_main() # или как вы там его получаете
# # print(f"DEBUG (grafik.py): Проверка grafik_local_cache: {\'Ключи: \' + str(list(grafik_local_cache.keys())) if grafik_local_cache else \'Кэш пуст или None\'}")

# # if not grafik_local_cache:
# #     display_chart_error("Локальный кэш исторических данных в grafik.py пуст. Невозможно построить график.")
# #     return

# # metal_historical_data = grafik_local_cache.get(selected_metal)
# # print(f"DEBUG (grafik.py): Данные для металла \'{selected_metal}\': {str(metal_historical_data[:2]) + \'...\' if metal_historical_data and len(metal_historical_data) > 2 else str(metal_historical_data) if metal_historical_data else \'Нет данных\'}")

# # if not metal_historical_data:
# #     display_chart_error(f"Нет исторических данных для металла \'{selected_metal}\'.")
# #     return

# # # Фильтрация данных по дате
# # date_start_obj = parse_input_date(date_start_str)
# # date_end_obj = parse_input_date(date_end_str)
# # print(f"DEBUG (grafik.py): Распарсенные даты: Старт={date_start_obj}, Конец={date_end_obj}")

# # filtered_entries = []
# # for entry in metal_historical_data:
# #     entry_date_str = entry.get("date")
# #     entry_price_str = entry.get("price")
# #     entry_date_obj = parse_custom_date(entry_date_str)

# #     if entry_date_obj and entry_price_str != "N/A":
# #         valid_entry = True
# #         if date_start_obj and entry_date_obj < date_start_obj:
# #             valid_entry = False
# #         if date_end_obj and entry_date_obj > date_end_obj:
# #             valid_entry = False
# #         
# #         if valid_entry:
# #             try:
# #                 price = float(entry_price_str.replace(\',\', \'.\')) 
# #                 filtered_entries.append({"date": entry_date_obj, "price": price, "date_str": entry_date_str})
# #             except ValueError:
# #                 print(f"Пропуск записи для графика: не удалось преобразовать цену \'{entry_price_str}\' в число для даты {entry_date_str}")
# # 
# # print(f"DEBUG (grafik.py): Количество отфильтрованных записей: {len(filtered_entries)}")
# # if filtered_entries:
# #     print(f"DEBUG (grafik.py): Первая отфильтрованная запись: {filtered_entries[0]}")

# # if not filtered_entries:
# #     display_chart_error(f"Нет данных для графика для металла \'{selected_metal}\' в указанном диапазоне дат.")
# #     return

# # filtered_entries.sort(key=lambda x: x["date"])

# # labels = [entry["date_str"] for entry in filtered_entries]
# # data_points = [entry["price"] for entry in filtered_entries]
# # print(f"DEBUG (grafik.py): Метки для графика (первые 5): {labels[:5]}")
# # print(f"DEBUG (grafik.py): Точки данных для графика (первые 5): {data_points[:5]}")

# # chart_data = {
# #     'type': 'line',
# #     'data': {
# #         'labels': to_js(labels),
# #         'datasets': [{
# #             'label': f'Цена на {selected_metal} (руб./грамм)',
# #             'data': to_js(data_points),
# #             'fill': False,
# #             'borderColor': 'rgb(75, 192, 192)',
# #             'tension': 0.1
# #         }]
# #     },
# #     'options': {
# # ... existing code ...

# # Ваш предыдущий код для работы с реальными данными пока закомментирован
# metal_select = document.querySelector("#chart-metal-select")
# date_start_input = document.querySelector("#chart-date-start")
# date_end_input = document.querySelector("#chart-date-end")

# selected_metal = metal_select.value
# date_start_str = date_start_input.value
# date_end_str = date_end_input.value
# print(f"ФРОНТЕНД (grafik.py): Параметры для графика: Металл={selected_metal}, Старт={date_start_str}, Конец={date_end_str}")
# 
# grafik_local_cache = get_historical_data_cache_from_main() # или как вы там его получаете
# print(f"DEBUG (grafik.py): Проверка grafik_local_cache: {'Ключи: ' + str(list(grafik_local_cache.keys())) if grafik_local_cache else 'Кэш пуст или None'}")

# if not grafik_local_cache:
#     display_chart_error("Локальный кэш исторических данных в grafik.py пуст. Невозможно построить график.")
#     return

# metal_historical_data = grafik_local_cache.get(selected_metal)
# print(f"DEBUG (grafik.py): Данные для металла '{selected_metal}': {str(metal_historical_data[:2]) + '...' if metal_historical_data and len(metal_historical_data) > 2 else str(metal_historical_data) if metal_historical_data else 'Нет данных'}")

# if not metal_historical_data:
#     display_chart_error(f"Нет исторических данных для металла '{selected_metal}'.")
#     return

# # Фильтрация данных по дате
# date_start_obj = parse_input_date(date_start_str)
# date_end_obj = parse_input_date(date_end_str)
# print(f"DEBUG (grafik.py): Распарсенные даты: Старт={date_start_obj}, Конец={date_end_obj}")

# filtered_entries = []
# for entry in metal_historical_data:
#     entry_date_str = entry.get("date")
#     entry_price_str = entry.get("price")
#     entry_date_obj = parse_custom_date(entry_date_str)

#     if entry_date_obj and entry_price_str != "N/A":
#         valid_entry = True
#         if date_start_obj and entry_date_obj < date_start_obj:
#             valid_entry = False
#         if date_end_obj and entry_date_obj > date_end_obj:
#             valid_entry = False
#         
#         if valid_entry:
#             try:
#                 price = float(entry_price_str.replace(',', '.')) 
#                 filtered_entries.append({"date": entry_date_obj, "price": price, "date_str": entry_date_str})
#             except ValueError:
#                 print(f"Пропуск записи для графика: не удалось преобразовать цену '{entry_price_str}' в число для даты {entry_date_str}")
# 
# print(f"DEBUG (grafik.py): Количество отфильтрованных записей: {len(filtered_entries)}")
# if filtered_entries:
#     print(f"DEBUG (grafik.py): Первая отфильтрованная запись: {filtered_entries[0]}")

# if not filtered_entries:
#     display_chart_error(f"Нет данных для графика для металла '{selected_metal}' в указанном диапазоне дат.")
#     return

# filtered_entries.sort(key=lambda x: x["date"])

# labels = [entry["date_str"] for entry in filtered_entries]
# data_points = [entry["price"] for entry in filtered_entries]
# print(f"DEBUG (grafik.py): Метки для графика (первые 5): {labels[:5]}")
# print(f"DEBUG (grafik.py): Точки данных для графика (первые 5): {data_points[:5]}")

# chart_data = {
#     'type': 'line',
#     'data': {
#         'labels': to_js(labels),
#         'datasets': [{
#             'label': f'Цена на {selected_metal} (руб./грамм)',
#             'data': to_js(data_points),
#             'fill': False,
#             'borderColor': 'rgb(75, 192, 192)',
#             'tension': 0.1
#         }]
#     },
#     'options': {
#         'responsive': True,
#         'maintainAspectRatio': True, 
#         'scales': {
#             'y': {
#                 'beginAtZero': False
#             }
#         }
#     }
# }

# ctx = document.getElementById('metalsPriceChart').getContext('2d')
# 
# if current_chart:
#     current_chart.destroy()

# current_chart = window.Chart.new(ctx, to_js(chart_data))
# print(f"ФРОНТЕНД (grafik.py): График для '{selected_metal}' обновлен/построен.")

print("ФРОНТЕНД (grafik.py): Модуль grafik.py загружен.") 