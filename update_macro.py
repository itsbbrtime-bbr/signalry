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

    # 2. 카테고리별 핵심 100개 지표 정의 (ID: 이름)
    target_metrics = {
        # --- 통화정책 및 유동성 (20) ---
        "FEDFUNDS": "미국 기준금리", "RRPONTSYD": "역레포(RRP) 잔고", "WALCL": "연준 총자산", 
        "WTREGEN": "재무부 일반계정(TGA)", "M2SL": "M2 통화량", "TOTRESNS": "전체 지급준비금",
        "WSHOMCB": "연준 보유 MBS", "TREAST": "연준 보유 국채", "CURRCIR": "화폐 유통량", 
        "IORB": "지준부리마", "BOGMBASE": "본원통화", "WLCFLL": "연준 대출: 유동성 지원",
        "WLCFLP": "연준 대출: 할인창구", "WLCFBT": "BTFP(은행 지원 프로그램)", "WSHONCL": "연준 보유 기타 자산",
        "REFRAT": "뉴욕 연준 재할인율", "WLRRAL": "연준 부채: 역레포 합계", "H41RESPP": "연준 보유 기타 유가증권",
        "WM1NS": "M1 통화량", "WRBWFRNS": "외국계 은행 지준금",
        # --- 금리 및 채권 시장 (20) ---
        "T10Y2Y": "장단기 금리차 (10-2)", "DGS10": "10년물 국채 금리", "DGS2": "2년물 국채 금리",
        "DGS30": "30년물 국채 금리", "DFII10": "10년물 실질금리(TIPS)", "T10YIE": "10년 기대인플레이션(BEI)",
        "BAMLH0A0HYM2": "하이일드 스프레드", "TEDRATE": "TED 스프레드", "AAA": "AAA 우량 회사채 금리",
        "BAA": "Baa 비우량 회사채 금리", "DGS1": "1년물 국채 금리", "DGS5": "5년물 국채 금리",
        "DGS20": "20년물 국채 금리", "T10Y3M": "10년-3개월 금리차", "DTWEXBGS": "달러 인덱스",
        "SOFR": "SOFR 금리", "BAMLHE00EHYI": "유로 하이일드 인덱스", "AAA10Y": "AAA-10년물 스프레드",
        "BAA10Y": "Baa-10년물 스프레드", "T5YIE": "5년 기대인플레이션",
        # --- 물가 및 인플레이션 (15) ---
        "CPIAUCSL": "CPI (헤드라인)", "CPILFESL": "Core CPI (근원)", "PCEPI": "PCE 물가지수",
        "PCEPILFE": "Core PCE (근원)", "PPIACO": "생산자물가지수(PPI)", "CPIENGSL": "CPI: 에너지",
        "CPIFABSL": "CPI: 식음료", "CUSR0000SAS": "CPI: 서비스", "CUSR0000SA0L1E": "CPI: 근원 상세",
        "WPSFD4": "PPI: 최종 수요", "GASREGW": "가솔린 소매 가격", "DPCRED3A066NBEA": "실질 PCE (내구재)",
        "CPIHOSSL": "CPI: 주거비", "STICKCPIM157SFRBATL": "Sticky CPI", "MEDCPIM157SFRBCLE": "중위 CPI",
        # --- 고용 및 노동 시장 (15) ---
        "PAYEMS": "비농업 고용자 수", "UNRATE": "실업률", "ICSA": "신규 실업수당 청구",
        "CCSA": "연속 실업수당 청구", "JTSJOL": "JOLTs 구인 건수", "CES0500000003": "평균 시간당 임금",
        "CIVPART": "경제활동 참가율", "EMRATIO": "고용률", "U6RATE": "체감 실업률(U6)",
        "ADPWNUSNS": "ADP 민간 고용", "JTSQUR": "이직률", "LNS14000025": "25-54세 실업률",
        "W270611000Q027SBEA": "개인 소득 합계", "LNS12032194": "파트타임 고용자 수", "MANEMP": "제조업 고용자 수",
        # --- 실물 경제성장 및 생산 (20) ---
        "GDP": "명목 GDP", "GDPC1": "실질 GDP", "INDPRO": "산업 생산 지수", "TCU": "설비 가동률",
        "RETAILIRSA": "실질 소매 판매", "PCE": "개인 소비 지출", "DGORDER": "내구재 신규 주문",
        "HSN1F": "신규 주택 판매", "HOUST": "주택 착공 건수", "CSUSHPINSA": "케이스-실러 주택지수",
        "NEWORDER": "ISM 제조업 신규주문 대용", "IPMAN": "제조업 생산 지수", "GDI": "국내 총소득 (GDI)",
        "A191RL1Q225SBEA": "GDP 성장률 (분기)", "TOTALSA": "자동차 판매량", "ALTSALES": "경트럭 판매량",
        "EXPGSC1": "실질 수출", "IMPGSC1": "실질 수입", "BUSINV": "기업 재고", "RETAILSM14411S": "이커머스 매출",
        # --- 경기 심리 및 위험 지표 (10) ---
        "UMCSENT": "미시간대 소비자심리", "VIXCLS": "VIX (공포 지수)", "STLFSI3": "금융스트레스 지수",
        "NFCI": "금융여건 지수", "IEABC": "경제정책 불확실성", "BUSAPPWNSUS": "신규 사업 신청",
        "USEPUINDXD": "뉴스 불확실성", "WM1NS": "가계 저축률", "GFDEGDQ188S": "GDP 대비 정부부채", "T10Y3M": "금리차 (10Y-3M)"
    }

    final_output = []

    # 3. 데이터 수집 루프
    for i, (series_id, name) in enumerate(target_metrics.items()):
        try:
            # 주기에 따른 수집 기간 설정 (지표 정보 조회)
            info = fred.get_series_info(series_id)
            freq = info.get('frequency_short', 'M').upper()
            
            if freq in ['D', 'W']: # 일간, 주간 -> 1년
                years = 1
            elif freq == 'M': # 월간 -> 5년
                years = 5
            else: # 분기 및 기타 -> 10년
                years = 10
            
            start_date = (today - timedelta(days=365 * years)).strftime('%Y-%m-%d')
            
            # 데이터 호출
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
                print(f"[{i+1}/100] ✅ {series_id} ({freq}): {years}년치 수집 완료")
            
            # API 제한(분당 120회) 방지를 위해 0.5초 휴식
            time.sleep(0.5)
            
        except Exception as e:
            print(f"[{i+1}/100] ❌ {series_id} 오류: {e}")

    # 4. JSON 파일 저장
    with open('macro_optimized.json', 'w', encoding='utf-8') as f:
        json.dump(final_output, f, ensure_ascii=False, indent=2)
    
    print(f"\n🎉 모든 작업이 완료되었습니다! 파일명: macro_optimized.json")

if __name__ == "__main__":
    get_optimized_macro_data()
