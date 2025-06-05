# Metal Forecast API

Прогноз курса золота, серебра, платины и палладия на 3 дня вперёд по последним 60 значениям.

---

## Запуск локально

1. Установка зависимости:

pip install -r requirements.txt

2. Запуск сервера

uvicorn metal_forecast_api:app --reload

3. API будет доступен по адресу:
http://localhost:8000/docs