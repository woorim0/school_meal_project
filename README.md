# AI 급식 조회 앱
### 기본 작동 방식
나이스 api로 불러온 급식 정보를 구글 제미나이 api로 순위를 매기는 프로그램입니다. (학교 수행평가를 바탕으로 한 프로젝트)

기본적으로 **스트림릿**으로 작동합니다.

[스트림릿 공식 문서](https://docs.streamlit.io/)

---
### 급식 API 호출
```python
import requests

def get_school_meal(office_code, school_code, date):
	url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
	
	params = {
		"KEY": your_neis_key,
		"Type": "json",
		"pIndex": 1,
		"pSize": 10,
		"ATPT_OFCDC_SC_CODE": office_code,
		"SD_SCHUL_CODE": school_code,
		"MLSV_YMD": date
	}

	try:
		response = requests.get(url, params=params)
		response.raise_for_status()
		data = response.json()
		
		if "mealServiceDietInfo" in data:
			meals = data["mealServiceDietInfo"][1]["row"]
			results = [] # 급식 정보를 담을 리스트
			
			for meal in meals:
				# <br/> 태그 제거 및 메뉴 정리
				menu = meal["DDISH_NM"].replace("<br/>", "\n")
				# 식사 구분(중식 등)과 메뉴를 합쳐서 리스트에 추가, 칼로리 정보 추가, 기본 급식 데이터 추가
				meal_text = f"<{meal['MMEAL_SC_NM']}>\n{meal['CAL_INFO']}\n{menu}"
				results.append(meal_text)
			
			# 모든 식사 정보를 줄바꿈으로 연결하여 하나의 텍스트로 반환
			return "\n\n".join(results)
		else:
			return "해당하는 날짜에 급식이 제공되지 않습니다."
			
	except Exception as e:
		return f"오류가 발생했습니다: {e}"
```

```python
급식 호출 함수: get_school_meal(office_code, school_code, date)
```

매개변수 office_code, school_code는 [여기에서](https://open.neis.go.kr/portal/data/service/selectServicePage.do?page=1&rows=10&sortColumn=&sortDirection=&infId=OPEN17020190531110010104913&infSeq=1) 찾을 수 있습니다.

매개변수 date 형식은 "20260101" 이런 형식입니다. 중간에 특수기호 같은 것이 들어가면 호출 오류가 생깁니다.

이 함수를 실행하면 해당하는 날짜에 맞는 급식 정보를 불러옵니다. 하루 치 조식, 중식, 석식을 불러옵니다.

만약 불러오지 못하면 오류 문자열을 반환하고, 급식이 제공되지 않는 날짜의 경우 "해당하는 날짜에 급식이 제공되지 않습니다." 문자열을 반환합니다.

```python
meal_text = f"<{meal['MMEAL_SC_NM']}>\n{meal['CAL_INFO']}\n{menu}"
```

위의 코드가 급식 정보를 담고 있습니다.

필요에 따라 정보를 가공해서 사용하면 좋습니다.

함수가 잘 실행되면 조식, 중식, 석식 구분 기호가 맨 처음에 오며, 칼로리 정보도 포함됩니다. 맨 마지막에는 제일 중요한 급식정보가 들어갑니다.

---
### 비동기 프로그래밍

월, 화, 수, 목, 금요일의 급식 정보를 모두 불러오는 방법은 반복문으로 5번 불러오면 됩니다.

함수를 한번 실행할때마다 동기(Sync)방식으로 실행되므로 api 요청을 보낸 뒤 요청이 처리될때까지 다음 코드를 실행하지 않는 문제가 있습니다.

이를 해결하기 위해 비동기(Async)방식을 사용하는 방법이 있습니다.

비동기 방식이란 함수를 실행한 뒤 요청이 처리될때까지 기다리지 않고, 바로 다음 코드를 실행하는 방식입니다.

```python
# 비동기 방식으로 불러오기 위한 함수
async def get_school_meal_async(office_code, school_code, date):
	# 인자 순서가 def get_school_meal과 완벽히 1:1로 일치해야 에러가 나지 않습니다.
	return await asyncio.to_thread(
		get_school_meal, office_code, school_code, date
	)


# 여러 날짜의 요청을 하나의 비동기 세트로 묶어주는 핵심 함수
async def fetch_all_dates(office_code, school_code, date_list):
	# for문 안에서 실행하는 게 아니라, '예약 찌트'만 만듭니다. (괄호 뒤에 await를 안 붙이는 게 핵심!)
	tasks = [
		get_school_meal_async(office_code, school_code, date)
		for date in date_list
	]

	# gather가 예약된 모든 날짜의 API 요청을 서버에 '동시에' 탕! 쏩니다.
	results = await asyncio.gather(*tasks)
	return results
```

위 함수들은 get_school_meal 함수를 비동기 방식으로 돌리기 위한 코드입니다.

```python
all_meals_list = loop.run_until_complete(
    fetch_all_dates(
        OFFICE_CODE, SCHOOL_CODE, dates
    )
)
```

위 코드를 실행하면 all_meals_list에 급식 정보 리스트가 담깁니다.

그런데 알고보니 급식 api를 호출할 때 여러 날짜의 급식 정보를 불러오는 방법이 있었습니다.

```python
params = {
	"KEY": "YOUR_API_KEY",          # 본인의 나이스 API 키 (있다면)
	"Type": "json",
	"pIndex": 1,
	"pSize": 10,                    # 하루 2~3식 제공 학교 고려 (5일치면 최소 10~15 설정)
	"ATPT_OFCDC_SC_CODE": "T10",    # 교육청 코드 (예시)
	"SD_SCHUL_CODE": "9290083",     # 학교 코드 (예시)
	"MLSV_FROM_YMD": from_ymd,      # 시작 날짜 (예: 20260525)
	"MLSV_TO_YMD": to_ymd           # 종료 날짜 (예: 20260529)
}
```

```python
"MLSV_FROM_YMD": from_ymd,      # 시작 날짜 (예: 20260525)
"MLSV_TO_YMD": to_ymd           # 종료 날짜 (예: 20260529)
```

위 코드가 여러 개의 급식 정보를 한번에 불러오는 코드입니다.

비동기 방식 대신 이 방식을 사용하는 것이 더 좋습니다.

---
### 제미나이 호출
사용하는 AI 모델은 **'gemini-3.1-flash-lite'** 모델으로 무료인데도 api 사용량이 널널합니다. (하루 500회 호출 가능)

```python
from google import genai

client = genai.Client(
	api_key=your_api_key
)

response = client.models.generate_content(
    model="gemini-3.1-flash-lite",
    contents=your_prompt
) # AI 답변이 끝나야만 다음 코드가 실행됨

ai_answer = response.text
```

직접 사용해보니 같은 호출이여도 실행 속도가 다름 (최소 3초에서 최대 30초)

사용하기 전 google-genai 라이브러리 설치 필수
```
pip install google-genai
```

[구글 공식 문서](https://ai.google.dev/gemini-api/docs/api-key?hl=ko#provide-api-key-explicitly)

---
### 랜덤 학교 고르는 방법

학교 리스트 파일은 [여기에서](https://open.neis.go.kr/portal/data/service/selectServicePage.do?page=1&rows=10&sortColumn=&sortDirection=&infId=OPEN17020190531110010104913&infSeq=1) 얻을 수 있습니다.

```python
import random
import csv

# api 호출에 필요한 변수
OFFICE_CODE = "C10"     # 부산특별시교육청
SCHOOL_CODE = "7150114" # 신도고 학교 코드
SCHOOL_NAME = "신도고등학교"
SCHOOL_REGION = "부산"

@st.cache_data # 처음 한번만 로딩하는 코드 (스트림릿 내장)
def load_school_csv(file_path):
	extracted_schools = []
	with open(file_path, mode='r', encoding='cp949') as f: # cp949는 한글 깨짐 방지
		reader = csv.DictReader(f)
		for row in reader:
			extracted_schools.append({
				"office_code": row["시도교육청코드"],
				"school_code": row["표준학교코드"],
				"school_name": row["학교명"],
				"school_region": row["소재지명"]
			})
	return extracted_schools

all_schools = load_school_csv("school_list.csv")
```

위 코드는 school_list.csv 파일을 파이썬에서 읽는 함수입니다.

```python
if is_checked_other: # 랜덤 학교 급식 체크박스 켜진 상태일때만
	random_school = random.choice(all_schools)
	OFFICE_CODE = random_school["office_code"]
	SCHOOL_CODE = random_school["school_code"]
	SCHOOL_NAME = random_school["school_name"]
	SCHOOL_REGION = random_school["school_region"]
```

체크박스가 활성화되면 랜덤한 학교의 정보를 불러옵니다.

불러온 정보를 바탕으로 급식 api를 통해 급식 정보를 불러올 수 있습니다.

---
### 글자 네온 효과 입히는 방법
```python
st.markdown(f"""
<style>
    #{네온 효과 입힐 글자} span {{
        opacity: 1 !important;
        background-color: #6b5f4a !important;
        text-shadow:
            0 0 2px #edcf98,
            0 0 4px #edcf98,
            0 0 6px #edcf98;
    }}
</style>
""", unsafe_allow_html=True)
```

글자 뒤에 밝은 그림자를 여러개 만들어서 텍스트 네온 효과를 냅니다.
