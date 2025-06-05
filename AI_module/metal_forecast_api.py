import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import numpy as np
from tensorflow.keras.models import load_model
import joblib
import os
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Metal Forecast API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MODELS_DIR = 'models'
FORECAST_DAYS = 3
LOOKBACK_DAYS = 60
SUPPORTED_METALS = ['gold', 'silver', 'platinum', 'palladium']
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class ForecastRequest(BaseModel):
    metal: str
    prices: str


@app.post("/forecast")
def forecast(req: ForecastRequest):
    metal = req.metal.lower()
    if metal not in SUPPORTED_METALS:
        raise HTTPException(status_code=400, detail=f"Unsupported metal: {metal}")

    try:
        price_list = [float(p.strip().replace(",", ".")) for p in req.prices.split(",")]
    except ValueError:
        raise HTTPException(status_code=400, detail="All prices must be valid float numbers separated by commas")

    if len(price_list) != LOOKBACK_DAYS:
        raise HTTPException(status_code=400, detail=f"Exactly {LOOKBACK_DAYS} prices required")

    try:
        model_path = os.path.join(BASE_DIR, MODELS_DIR, f"{metal}_model.h5")
        scaler_path = os.path.join(BASE_DIR, MODELS_DIR, f"{metal}_scaler.pkl")
        model = load_model(model_path, compile=False)
        scaler = joblib.load(scaler_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading model/scaler for {metal}: {e}")

    input_array = np.array(price_list).reshape(-1, 1)
    scaled_input = scaler.transform(input_array)
    X = scaled_input.reshape((1, LOOKBACK_DAYS, 1))
    scaled_pred = model.predict(X)[0]
    prediction = scaler.inverse_transform(scaled_pred.reshape(-1, 1)).flatten()

    return {"forecast": [round(p, 2) for p in prediction.tolist()]}


@app.get("/")
def root():
    return {
        "message": "POST /forecast with {'metal': 'gold', 'prices': '1234.5,1236.1,...'}"
    }


if __name__ == "__main__":
    uvicorn.run("metal_forecast_api:app", host="0.0.0.0", port=8000, reload=True)
