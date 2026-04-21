import os
import json
import time
from datetime import datetime, timedelta
from fredapi import Fred

def get_optimized_macro_data():
    # 1. 환경 설정 및 API 키 확인
    api_key = os.environ.get('FRED_API_KEY')
    if not api_key:
        print("❌ FRED_API_KEY가 설정되지 않았습니다. GitHub Secrets를 확인하세요.")
        return

    fred = Fred(api_key=api_key)
    today = datetime.now()

    # 2. 카테고리별 핵심 지표 정의 (ID 수정 및 최적화 완료)
    target_metrics = {
        # --- 통화정책 및 유동성 ---
        "FEDFUNDS": "미국 기준금리", 
        "RRPONTSYD": "역레포(RRP) 잔고", 
        "WALCL": "연준 총자산", 
        "WTREGEN": "재무부 일반계정(TGA)", 
        "BOGMBASE": "본원통화", 
        "WM1NS": "M1 통화량",
        "M2SL": "M2 통화량", 
        "TOTRESNS": "전체 지급준비금",
        "WSHOMCB": "연준 보유 MBS", 
        "TREAST": "연준 보유 국채", 
        "CURRCIR": "화폐 유통량", 
        "IORB": "지급준비금 이자", 
        "WLCFLPCL": "연준 대출: 유동성 지원", 
        "WLCFLP": "연준 대출: 할인창구", 
        "H41RESPP9": "BTFP(은행 지원 프로그램)",
        "WSHONCL": "연준 보유 기타 자산",
        "DFF": "연방기금 실효금리",
        "WLRRAL": "연준 부채: 역레포 합계", 
        
        # --- 금리 및 채권 시장 ---
        "T10Y2Y": "장단기 금리차 (10-2)", 
        "DGS10": "10년물 국채 금리", 
        "DGS2": "2년물 국채 금리",
        "DGS30": "30년물 국채 금리", 
        "DFII10": "10년물 실질금리(TIPS)", 
        "T10YIE": "10년 기대인플레이션(BEI)",
        "BAMLH0A0HYM2": "하이일드 스프레드", 
        "TEDRATE": "TED 스프레드", 
        "AAA": "AAA 우량 회사채 금리",
        "BAA": "Baa 비우량 회사채 금리", 
        "DGS1": "1년물 국채 금리", 
        "DGS5": "5년물 국채 금리",
        "DGS20": "20년물 국채 금리", 
        "T10Y3M": "10년-3개월 금리차", 
        "DTWEXBGS": "달러 인덱스",
        "SOFR": "SOFR 금리", 
        "AAA10Y": "AAA-10년물 스프레드",
        "BAA10Y": "Baa-10년물 스프레드", 
        "T5YIE": "5년 기대인플레이션",
        
        # --- 물가 및 인플레이션 (Internal Server Error 대비 재설정) ---
        "CPIAUCSL": "CPI (헤드라인)", 
        "CPILFESL": "Core CPI (근원)", 
        "PCEPI": "PCE 물가지수",
        "PCEPILFE": "Core PCE (근원)", 
        "PPIACO": "생산자물가지수(PPI)", 
        "CPIENGSL": "CPI: 에너지",
        "CPIFABSL": "CPI: 식음료", 
        "CUSR0000SAS": "CPI: 서비스", 
        "WPSFD49107": "PPI: 최종 수요 상세", # WPSFD4 대체
        "GASREGW": "가솔린 소매 가격", 
        "CPIHOSSL": "CPI: 주거비", 
        "STICKCPIM157SFRBATL": "Sticky CPI", 
        "MEDCPIM157SFRBCLE": "중위 CPI",
        
        # --- 고용 및 노동 시장 ---
        "PAYEMS": "비농업 고용자 수", 
        "UNRATE": "실업률", 
        "ICSA": "신규 실업수당 청구",
        "CCSA": "연속 실업수당 청구", 
        "JTSJOL": "JOLTs 구인 건수", 
        "CES0500000003": "평균 시간당 임금",
        "CIVPART": "경제활동 참가율", 
        "EMRATIO": "고용률", 
        "U6RATE": "체감 실업률(U6)",
        "ADPCHMS": "ADP 민간 고용 변화", # ADPWNUSNS 대체
        "JTSQUR": "이직률", 
        "LNS14000025": "25-54세 실업률",
        "MANEMP": "제조업 고용자 수",
        
        # --- 실물 경제성장 및 생산 ---
        "GDP": "명목 GDP", 
        "GDPC1": "실질 GDP", 
        "INDPRO": "산업 생산 지수", 
        "TCU": "설비 가동률",
        "RETAILIRSA": "실질 소매 판매", 
        "PCE": "개인 소비 지출", 
        "DGORDER": "내구재 신규 주문",
        "HSN1F": "신규 주택 판매", 
        "HOUST": "주택 착공 건수", 
        "CSUSHPISA": "케이스-실러 주택지수(SA)", # CSUSHPINSA 대체
        "IPMAN": "제조업 생산 지수", 
        "GDI": "국내 총소득 (GDI)",
        "TOTALSA": "자동차 판매량", 
        "ALTSALES": "경트럭 판매량",
        "EXPGSC1": "실질 수출", 
        "IMPGSC1": "실질 수입", 
        "BUSINV": "기업 재고", 
        "RSXFS": "소매 판매 (자동차 제외)", # RETAILSM14411S 대체
        
        # --- 경기 심리 및 위험 지표 ---
        "UMCSENT": "미시간대 소비자심리", 
        "VIXCLS": "VIX (공포 지수)", 
        "STLFSI3": "금융스트레스 지수",
        "NFCI": "금융여건 지수", 
        "IEABC": "경제정책 불확실성", 
        "BA0010101Q000S": "신규 사업 신청", # BUSAPPWNSUS 대체
        "USEPUINDXD": "뉴스 불확실성", 
        "GFDEGDQ188S": "GDP 대비 정부부채"
    }

    final_output = []

    # 3. 데이터 수집 루프
    for i, (series_id, name) in enumerate(target_metrics.items()):
        try:
            # 주기에 따른 수집 기간 설정
            info = fred.get_series_info(series_id)
            freq = info.get('frequency_short', 'M').upper()
            
            if freq in ['D', 'W']: years = 1
            elif freq == 'M': years = 5
            else: years = 10
            
            start_date = (today - timedelta(days=365 * years)).strftime('%Y-%m-%d')
            
            # 데이터 호출 (일시적 서버 에러 대비 재시도 로직 추가 가능)
            data = fred.get_series(series_id, observation_start=start_date)
            
            history = [
                {"date": str(d.date()), "value": float(v)} 
                for d, v in data.items() if not str(v).lower() == 'nan'
            ]
            
            if history:
                final_output.append({
                    "id": series_id,
                    "name": name,
                    "frequency": freq,
                    "period_years": years,
                    "currentValue": history[-1]["value"],
                    "data": history
                })
                print(f"[{i+1}/{len(target_metrics)}] ✅ {series_id} ({freq}): {years}년치 완료")
            
            # FRED 서버 부하 방지를 위해 지연 시간 증가 (0.5 -> 0.8)
            time.sleep(0.8)
            
        except Exception as e:
            print(f"[{i+1}/{len(target_metrics)}] ❌ {series_id} 오류: {e}")
            # 서버 에러(500) 시 잠시 더 대기
            time.sleep(2)

    # 4. JSON 파일 저장
    with open('macro_optimized.json', 'w', encoding='utf-8') as f:
        json.dump(final_output, f, ensure_ascii=False, indent=2)
    
    print(f"\n🎉 모든 작업 완료! 수집 성공: {len(final_output)}/{len(target_metrics)}")

if __name__ == "__main__":
    get_optimized_macro_data()
