import requests
import json
from datetime import datetime

def collect_fear_greed():
    url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
    headers = {'User-Agent': 'Mozilla/5.0'} # 차단 방지용 헤더
    
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        
        # 필요한 기록 데이터 추출
        raw_points = data['fear_and_greed_historical']['data']
        
        processed_data = []
        for p in raw_points:
            # ms 단위를 s 단위로 변경하여 날짜 변환
            dt = datetime.fromtimestamp(p['x'] / 1000.0)
            processed_data.append({
                "date": dt.strftime('%Y-%m-%d'),
                "value": float(p['y'])
            })
            
        # 결과 저장
        with open('fear_greed.json', 'w', encoding='utf-8') as f:
            json.dump(processed_data, f, ensure_ascii=False, indent=2)
            
        print("✅ Fear & Greed 데이터 업데이트 완료")
        
    except Exception as e:
        print(f"❌ Fear & Greed 오류: {e}")

if __name__ == "__main__":
    collect_fear_greed()
