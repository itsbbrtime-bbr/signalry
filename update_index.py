import requests
import json
import os
from datetime import datetime, timedelta

# FRED API 설정
API_KEY = os.environ['FRED_API_KEY']
BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

# 수집할 지표 리스트 (ID: 이름)
SERIES_IDS = {
    "SP500": "S&P 500",
    "NASDAQCOM": "NASDAQ",
    "VIXCLS": "VIX",
    "DGS2": "US 2Y Yield",
    "DGS10": "US 10Y Yield",
    "DGS30": "US 30Y Yield",
    "GOLDAMGBD228NLBM": "Gold",
    "DCOILWTICO": "WTI Oil",
    "DCOILBRENTEU": "Brent Oil",
    "DTWEXBGS": "Dollar Index"
}

def fetch_fred_data(series_id, name):
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    
    params = {
        "series_id": series_id,
        "api_key": API_KEY,
        "file_type": "json",
        "observation_start": start_date,
        "observation_end": end_date,
        "sort_order": "asc"
    }
    
    response = requests.get(BASE_URL, params=params)
    if response.status_code == 200:
        observations = response.json().get("observations", [])
        # '.'으로 들어오는 결측치 제거 및 포맷팅
        data_points = []
        last_value = 0.0
        
        for obs in observations:
            try:
                val = float(obs["value"])
                data_points.append({"date": obs["date"], "value": val})
                last_value = val
            except ValueError:
                continue # 주말/공휴일 패스
                
        return {
            "id": series_id,
            "name": name,
            "currentValue": last_value,
            "data": data_points
        }
    return None

all_metrics = []
for s_id, s_name in SERIES_IDS.items():
    print(f"Fetching {s_name}...")
    result = fetch_fred_data(s_id, s_name)
    if result:
        all_metrics.append(result)

# JSON 파일로 저장
with open("macro_data.json", "w", encoding="utf-8") as f:
    json.dump(all_metrics, f, ensure_ascii=False, indent=4)

print("Successfully updated macro_data.json")
