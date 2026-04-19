import requests
import json
from datetime import datetime

def collect_fear_greed():
    url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
    
    # 실제 브라우저처럼 보이도록 헤더를 더 상세히 설정합니다.
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Referer': 'https://www.cnn.com/markets/fear-and-greed'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        
        # 403, 404 등 에러가 발생하면 여기서 예외를 발생시킵니다.
        response.raise_for_status() 
        
        data = response.json()
        
        # 데이터 구조 확인
        if 'fear_and_greed_historical' not in data:
            print("❌ 데이터 구조가 변경되었습니다.")
            return

        raw_points = data['fear_and_greed_historical']['data']
        processed_data = []
        
        for p in raw_points:
            dt = datetime.fromtimestamp(p['x'] / 1000.0)
            processed_data.append({
                "date": dt.strftime('%Y-%m-%d'),
                "value": float(p['y'])
            })
            
        with open('fear_greed.json', 'w', encoding='utf-8') as f:
            json.dump(processed_data, f, ensure_ascii=False, indent=2)
            
        print(f"✅ Fear & Greed 업데이트 완료 ({len(processed_data)} points)")
        
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP 에러 발생: {e.response.status_code} - {e.response.reason}")
    except Exception as e:
        print(f"❌ Fear & Greed 오류: {e}")

if __name__ == "__main__":
    collect_fear_greed()
