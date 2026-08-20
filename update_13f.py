import json
import time
import requests
import os

from pathlib import Path
from datetime import datetime, timezone
from xml.etree import ElementTree as ET


# ============================================================
# CONFIG
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

MANAGERS_FILE = BASE_DIR / "managers.json"
OUTPUT_DIR = BASE_DIR / "data" / "13f"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MASTER_MAPPING_FILE = BASE_DIR / "master_mappings.json"

# SEC에서는 식별 가능한 User-Agent 사용을 권장
# 반드시 실제 앱 이름과 연락 가능한 이메일로 변경
HEADERS = {
    "User-Agent": os.environ["SEC_USER_AGENT"],
    "Accept-Encoding": "gzip, deflate",
}


# SEC 요청 간 최소 간격
REQUEST_DELAY = 0.2


# ============================================================
# MANAGERS
# ============================================================

def load_managers():
    """
    config/managers.json 로드

    Expected:
    {
        "managers": [
            {
                "id": "berkshire-hathaway",
                "name": "Berkshire Hathaway",
                "cik": "0001067983",
                "category": "Conglomerate",
                "enabled": true
            }
        ]
    }
    """

    if not MANAGERS_FILE.exists():
        raise FileNotFoundError(
            f"managers.json 파일을 찾을 수 없습니다: {MANAGERS_FILE}"
        )

    with open(
        MANAGERS_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        data = json.load(f)

    managers = data.get("managers", [])

    if not isinstance(managers, list):
        raise ValueError(
            "managers.json의 'managers'는 배열이어야 합니다."
        )

    return managers


def validate_managers(managers):
    """
    managers.json 기본 검증

    - 필수 필드 확인
    - ID 중복 확인
    - CIK 중복 확인
    """

    required_fields = [
        "id",
        "name",
        "cik"
    ]

    ids = {}
    ciks = {}

    print("\n🔎 managers.json 검증 중...")

    for manager in managers:

        name = manager.get(
            "name",
            "Unknown"
        )

        # ----------------------------------------------------
        # 필수 필드 확인
        # ----------------------------------------------------

        for field in required_fields:

            if not manager.get(field):

                raise ValueError(
                    f"필수 필드 누락: "
                    f"{name} → '{field}'"
                )

        # ----------------------------------------------------
        # ID 중복 확인
        # ----------------------------------------------------

        manager_id = manager["id"]

        if manager_id in ids:

            raise ValueError(
                f"중복된 manager id 발견: "
                f"{manager_id}\n"
                f"- {ids[manager_id]}\n"
                f"- {name}"
            )

        ids[manager_id] = name

        # ----------------------------------------------------
        # CIK 중복 확인
        # ----------------------------------------------------

        cik = str(manager["cik"])

        if cik not in ciks:
            ciks[cik] = []

        ciks[cik].append(name)

    duplicates = {
        cik: names
        for cik, names in ciks.items()
        if len(names) > 1
    }

    if duplicates:

        print("\n⚠️ 중복 CIK 발견")

        for cik, names in duplicates.items():

            print(
                f"CIK {cik}: "
                + ", ".join(names)
            )

        print(
            "⚠️ 동일한 CIK는 동일한 SEC Filing을 "
            "가리킬 가능성이 있습니다.\n"
        )

    print(
        f"✅ 총 {len(managers)}개 manager 확인 완료"
    )


# ============================================================
# SEC REQUEST
# ============================================================

def sec_get(url):
    """
    SEC API / SEC Archive 공통 요청
    """

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    # SEC 요청 속도 관리
    time.sleep(REQUEST_DELAY)

    return response


# ============================================================
# GET LATEST 13F
# ============================================================

def get_latest_13f(cik):
    """
    해당 CIK의 최신 13F-HR 또는 13F-HR/A 조회
    """

    cik_padded = str(
        int(cik)
    ).zfill(10)

    url = (
        "https://data.sec.gov/submissions/"
        f"CIK{cik_padded}.json"
    )

    data = sec_get(url).json()

    recent = (
        data
        .get("filings", {})
        .get("recent", {})
    )

    forms = recent.get(
        "form",
        []
    )

    accessions = recent.get(
        "accessionNumber",
        []
    )

    filing_dates = recent.get(
        "filingDate",
        []
    )

    report_dates = recent.get(
        "reportDate",
        []
    )

    # SEC recent 데이터는 최신 Filing부터 정렬
    for i, form in enumerate(forms):

        clean_form = (
            form
            .strip()
            .upper()
        )

        if clean_form in [
            "13F-HR",
            "13F-HR/A"
        ]:

            return {
                "form": clean_form,
                "accessionNumber": accessions[i],
                "filingDate": filing_dates[i],
                "reportDate": report_dates[i]
            }

    return None


# ============================================================
# EXISTING DATA
# ============================================================

def get_output_file(manager_id):
    """
    manager id를 기반으로 저장 파일 경로 생성
    """

    return (
        OUTPUT_DIR
        / f"{manager_id}.json"
    )


def load_existing_data(manager_id):
    """
    기존 저장 JSON 로드
    """

    file_path = get_output_file(
        manager_id
    )

    if not file_path.exists():
        return None

    try:

        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except json.JSONDecodeError:

        print(
            f"⚠️ 기존 JSON 파일이 손상됨: "
            f"{file_path}"
        )

        # 손상된 파일이면 다시 생성
        return None


def is_already_latest(
    existing_data,
    latest_filing
):
    """
    기존 저장 데이터와 최신 SEC Filing 비교
    """

    if not existing_data:
        return False

    existing_accession = (
        existing_data
        .get("filing", {})
        .get("accessionNumber")
    )

    latest_accession = (
        latest_filing
        .get("accessionNumber")
    )

    return (
        existing_accession
        == latest_accession
    )


# ============================================================
# SEC FILING INDEX
# ============================================================

def get_filing_index(
    cik,
    accession_number
):
    """
    SEC Filing의 index.json 조회
    """

    cik_int = str(
        int(cik)
    )

    accession_clean = (
        accession_number
        .replace("-", "")
    )

    url = (
        "https://www.sec.gov/Archives/edgar/data/"
        f"{cik_int}/"
        f"{accession_clean}/"
        "index.json"
    )

    return sec_get(url).json()


# ============================================================
# FIND INFORMATION TABLE
# ============================================================

def find_information_table(index_json):
    """
    Filing 내부에서 13F Information Table XML 탐색
    """

    items = (
        index_json
        .get("directory", {})
        .get("item", [])
    )

    xml_files = []

    for item in items:

        name = (
            item
            .get("name", "")
        )

        name_lower = (
            name.lower()
        )

        if (
            name_lower.endswith(".xml")
            and "primary" not in name_lower
        ):

            xml_files.append(
                item
            )

    # --------------------------------------------------------
    # 우선순위
    #
    # infotable
    # informationtable
    # table
    # 기타 XML
    # --------------------------------------------------------

    keywords = [
        "infotable",
        "informationtable",
        "table"
    ]

    for keyword in keywords:

        for item in xml_files:

            name = (
                item
                .get("name", "")
                .lower()
            )

            if keyword in name:

                return item["name"]

    # XML 하나뿐이라면 fallback
    if xml_files:

        return xml_files[0]["name"]

    return None


# ============================================================
# DOWNLOAD XML
# ============================================================

def download_information_table(
    cik,
    accession_number,
    file_name
):
    """
    Information Table XML 다운로드
    """

    cik_int = str(
        int(cik)
    )

    accession_clean = (
        accession_number
        .replace("-", "")
    )

    url = (
        "https://www.sec.gov/Archives/edgar/data/"
        f"{cik_int}/"
        f"{accession_clean}/"
        f"{file_name}"
    )

    return sec_get(url).content


# ============================================================
# XML PARSER
# ============================================================

def clean_tag(tag):
    """
    XML namespace 제거

    예:
    {http://www.sec.gov/edgar/document/thirteenf/informationtable}infoTable
    ↓
    infoTable
    """

    if "}" in tag:

        tag = (
            tag
            .split("}")[-1]
        )

    if ":" in tag:

        tag = (
            tag
            .split(":")[-1]
        )

    return tag


def get_element_values(element):
    """
    하나의 infoTable 내부 데이터를
    dictionary로 변환
    """

    values = {}

    for child in element.iter():

        tag = clean_tag(
            child.tag
        )

        if child.text:

            text = (
                child.text
                .strip()
            )

            if text:

                values[tag] = text

    return values


def parse_number(value):
    """
    SEC XML 숫자 안전 변환
    """

    if value is None:
        return 0

    try:

        return float(
            str(value)
            .replace(",", "")
            .strip()
        )

    except (
        ValueError,
        TypeError
    ):

        return 0


def parse_13f(
    xml_data,
    master_mappings
):
    """
    13F Information Table XML 파싱

    master_mappings.json을 이용하여
    CUSIP → Ticker 매핑
    """

    root = ET.fromstring(
        xml_data
    )

    holdings = []

    mapped_count = 0
    unmapped_cusips = []

    for element in root.iter():

        if clean_tag(
            element.tag
        ) != "infoTable":

            continue

        values = get_element_values(
            element
        )

        issuer = (
            values.get(
                "nameOfIssuer",
                ""
            )
            .strip()
        )

        cusip = (
            values.get(
                "cusip",
                ""
            )
            .strip()
            .upper()
        )

        # --------------------------------------------------------
        # SEC 13F value
        # 단위: $1,000
        # --------------------------------------------------------

        value = (
            parse_number(
                values.get("value")
            )
            * 1000
        )

        shares = parse_number(
            values.get("sshPrnamt")
        )

        # issuer와 CUSIP 모두 없는 비정상 데이터 제외

        if not issuer and not cusip:

            continue

        # --------------------------------------------------------
        # CUSIP → Ticker Mapping
        # --------------------------------------------------------

        mapping = master_mappings.get(
            cusip,
            {}
        )

        ticker = mapping.get(
            "ticker"
        )

        # 매핑 성공

        if ticker:

            mapped_count += 1

        # 매핑 실패한 CUSIP 기록

        elif cusip:

            unmapped_cusips.append(
                {
                    "cusip": cusip,
                    "issuer": issuer
                }
            )

        # --------------------------------------------------------
        # Holding 생성
        # --------------------------------------------------------

        holding = {

            "issuer": issuer,

            "ticker": ticker,

            "cusip": cusip,

            "value": value,

            "shares": shares,

            "shareType": (
                values.get(
                    "sshPrnamtType"
                )
            ),

            "investmentDiscretion": (
                values.get(
                    "investmentDiscretion"
                )
            ),

            "putCall": (
                values.get(
                    "putCall"
                )
            )
        }

        holdings.append(
            holding
        )

    # --------------------------------------------------------
    # 가치 기준 내림차순 정렬
    # --------------------------------------------------------

    holdings.sort(
        key=lambda x: x["value"],
        reverse=True
    )

    # --------------------------------------------------------
    # Mapping 결과 출력
    # --------------------------------------------------------

    print(
        f"🏷️ Ticker 매핑: "
        f"{mapped_count}/{len(holdings)}"
    )

    if unmapped_cusips:

        print(
            f"⚠️ 미매핑 CUSIP: "
            f"{len(unmapped_cusips)}개"
        )

        # 너무 많이 출력되는 것을 방지
        for item in unmapped_cusips[:10]:

            print(
                f"   - "
                f"{item['cusip']} "
                f"({item['issuer']})"
            )

        if len(unmapped_cusips) > 10:

            print(
                f"   ... 외 "
                f"{len(unmapped_cusips) - 10}개"
            )

    return holdings

# ============================================================
# MASTER MAPPINGS
# ============================================================

def load_master_mappings():
    """
    master_mappings.json 로드

    구조:
    {
        "037833100": {
            "ticker": "AAPL",
            "name": "APPLE INC",
            "cik": "0000320193"
        }
    }
    """

    if not MASTER_MAPPING_FILE.exists():

        raise FileNotFoundError(
            "master_mappings.json 파일을 찾을 수 없습니다: "
            f"{MASTER_MAPPING_FILE}"
        )

    with open(
        MASTER_MAPPING_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        mappings = json.load(f)

    if not isinstance(
        mappings,
        dict
    ):
        raise ValueError(
            "master_mappings.json은 dictionary 구조여야 합니다."
        )

    print(
        f"📚 Master Mapping 로드 완료: "
        f"{len(mappings):,}개"
    )

    return mappings

# ============================================================
# SAVE DATA
# ============================================================

def save_manager_data(
    manager,
    filing,
    holdings
):
    """
    최종 JSON 생성 및 저장
    """

    total_value = sum(
        item["value"]
        for item in holdings
    )

    output = {
        "manager": {
            "id": manager["id"],
            "name": manager["name"],
            "cik": str(
                manager["cik"]
            ),
            "category": manager.get(
                "category",
                None
            )
        },

        "filing": {
            "form": filing.get(
                "form"
            ),
            "accessionNumber": filing.get(
                "accessionNumber"
            ),
            "filingDate": filing.get(
                "filingDate"
            ),
            "reportDate": filing.get(
                "reportDate"
            )
        },

        "dataUpdatedAt": (
            datetime
            .now(timezone.utc)
            .isoformat()
        ),

        "summary": {
            "totalHoldings": len(
                holdings
            ),

            "totalValue": total_value
        },

        "holdings": holdings
    }

    file_path = get_output_file(
        manager["id"]
    )

    with open(
        file_path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            output,
            f,
            ensure_ascii=False,
            indent=2
        )

    print(
        f"💾 저장 완료: "
        f"{file_path}"
    )


# ============================================================
# UPDATE ONE MANAGER
# ============================================================

def update_manager(
    manager,
    master_mappings
):

    manager_id = manager["id"]

    cik = manager["cik"]

    name = manager["name"]

    print(
        f"\n{'=' * 60}"
    )

    print(
        f"🔍 {name} 확인 중..."
    )

    latest_filing = get_latest_13f(
        cik
    )

    if not latest_filing:

        print(
            "⚠️ 13F-HR Filing 없음"
        )

        return False

    existing_data = load_existing_data(
        manager_id
    )

    if is_already_latest(
        existing_data,
        latest_filing
    ):

        print(
            "✅ 최신 데이터 유지 중"
        )

        return False

    print(
        "🆕 새로운 13F 발견"
    )

    index_json = get_filing_index(
        cik,
        latest_filing[
            "accessionNumber"
        ]
    )

    xml_file = find_information_table(
        index_json
    )

    if not xml_file:

        print(
            "❌ Information Table XML을 찾을 수 없음"
        )

        return False

    print(
        f"📄 XML 파일: "
        f"{xml_file}"
    )

    xml_data = (
        download_information_table(
            cik,
            latest_filing[
                "accessionNumber"
            ],
            xml_file
        )
    )

    # ★ master_mappings 전달

    holdings = parse_13f(
        xml_data,
        master_mappings
    )

    print(
        f"📊 파싱 완료: "
        f"{len(holdings)}개 보유 항목"
    )

    save_manager_data(
        manager,
        latest_filing,
        holdings
    )

    print(
        f"✅ {name} 업데이트 완료"
    )

    return True


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "\n🚀 SEC 13F 데이터 업데이트 시작"
    )

    print(
        f"📁 Repository: "
        f"{BASE_DIR}"
    )

    # --------------------------------------------------------
    # 1. managers.json 로드
    # --------------------------------------------------------

    managers = load_managers()

    master_mappings = load_master_mappings()

    # --------------------------------------------------------
    # 2. 기본 검증
    # --------------------------------------------------------

    validate_managers(
        managers
    )

    # --------------------------------------------------------
    # 3. enabled manager만 추출
    # --------------------------------------------------------

    enabled_managers = [

        manager

        for manager in managers

        if manager.get(
            "enabled",
            True
        )

    ]

    print(
        f"\n📋 실행 대상: "
        f"{len(enabled_managers)}개"
    )

    # --------------------------------------------------------
    # 4. 업데이트
    # --------------------------------------------------------

    updated_count = 0

    failed_count = 0

    skipped_count = 0

    for manager in enabled_managers:

        try:

            updated = update_manager(
                manager,
                master_mappings
            )

            if updated:

                updated_count += 1

            else:

                skipped_count += 1

        except requests.HTTPError as e:
    
            failed_count += 1

            response = e.response

            status_code = (
                response.status_code
                if response
                else "Unknown"
            )

            print(
                f"❌ HTTP 오류: "
                f"{manager['name']}"
            )

            print(
                f"Status: "
                f"{status_code}"
            )

        except Exception as e:

            failed_count += 1

            print(
                f"❌ 업데이트 실패: "
                f"{manager['name']}"
            )

            print(
                f"Error: "
                f"{e}"
            )

    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    print(
        f"\n{'=' * 60}"
    )

    print(
        "🎉 SEC 13F 업데이트 완료"
    )

    print(
        f"🆕 업데이트: "
        f"{updated_count}"
    )

    print(
        f"⏭️ 변경 없음: "
        f"{skipped_count}"
    )

    print(
        f"❌ 실패: "
        f"{failed_count}"
    )

    print(
        f"{'=' * 60}\n"
    )


if __name__ == "__main__":

    main()
