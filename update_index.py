import requests
import json
import os
from datetime import datetime, timedelta

# FRED API 설정
# GitHub Actions 환경변수에서 API 키를 가져옵니다.
API_KEY = os.environ.get('FRED_API_KEY')
BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

# 수집할 지표 리스트 (ID: (이름, 빈도))
# 주식, 채권, 원자재 모두 일별 데이터이므로 "Daily"로 설정합니다.
SERIES_IDS = {
    "SP500": ("S&P 500", "D"),
    "NASDAQCOM": ("NASDAQ", "D"),
    "NASDAQ100": ("NASDAQ-100", "D"),
    "VIXCLS": ("VIX", "D")
}

def fetch_fred_data(series_id, name, frequency):
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
    
    try:
        response = requests.get(BASE_URL, params=params)
        if response.status_code == 200:
            observations = response.json().get("observations", [])
            data_points = []
            last_value = 0.0
            
            for obs in observations:
                try:
                    # FRED는 값이 없는 주말/공휴일에 '.'을 반환합니다.
                    if obs["value"] == ".":
                        continue
                    
                    val = float(obs["value"])
                    data_points.append({"date": obs["date"], "value": val})
                    last_value = val
                except (ValueError, KeyError):
                    continue 
                    
            return {
                "id": series_id,
                "name": name,
                "frequency": frequency,   # Swift 모델의 'frequency'에 대응
                "currentValue": last_value, # Swift 모델의 'currentValue'에 대응
                "data": data_points        # Swift 모델의 'data'에 대응
            }
    except Exception as e:
        print(f"Error fetching {name}: {e}")
    return None

all_metrics = []
for s_id, (s_name, s_freq) in SERIES_IDS.items():
    print(f"Fetching {s_name}...")
    result = fetch_fred_data(s_id, s_name, s_freq)
    if result:
        all_metrics.append(result)

# 최종 JSON 파일 저장 (파일명은 필요에 따라 macro_data.json 등으로 변경 가능)
with open("index_data.json", "w", encoding="utf-8") as f:
    json.dump(all_metrics, f, ensure_ascii=False, indent=4)

print("Successfully updated macro_data.json")
