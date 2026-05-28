import streamlit as st
from google import genai
from datetime import datetime, timedelta
import asyncio
import requests
import re
import random
import csv

# api 키 불러오기
neis_key = st.secrets.get("NEIS_API_KEY")
google_key = st.secrets.get("GOOGLE_API_KEY")

client = genai.Client(
	api_key=google_key
)

# 색상 저장
tier0 = "background-color: #ff0000; color: #ffffff; padding: 2px 6px; border-radius: 4px;"
tier1 = "background-color: #948d5d; color: #ffffff; padding: 2px 6px; border-radius: 4px; text-shadow: 0 0 2px #ffea00, 0 0 4px #ffea00, 0 0 6px #ffea00;"
tier2 = "background-color: #757575; color: #ffffff; padding: 2px 6px; border-radius: 4px; text-shadow: 0 0 2px #e6e8e8, 0 0 4px #e6e8e8, 0 0 6px #e6e8e8;"
tier3 = "background-color: #6b5f4a; color: #ffffff; padding: 2px 6px; border-radius: 4px; text-shadow: 0 0 2px #edcf98, 0 0 4px #edcf98, 0 0 6px #edcf98;"


# 화면에 그릴 것
st.title("AI 급식 조회")
st.subheader("AI가 맛있는 급식순으로 등급을 매깁니다.")

st.success("AI가 신도고등학교의 급식에서 맛있는 걸 찾아드립니다! 개인별 맞춤 설정도 가능.")
st.warning("AI(구글 제미나이)가 상황에 따라 잘 작동하지 않거나 api 요청이 실패할 수도 있습니다.")

selected_date = st.date_input("조회할 날짜를 선택하세요 (선택한 날짜의 주(Week)의 급식을 불러옵니다.)", value=datetime.now())
day_of_week = selected_date.weekday()
monday = selected_date - timedelta(days=day_of_week) # 선택한 주의 월요일을 저장하는 변수

like = st.text_input("좋아하는 음식 또는 종류를 입력하면 순위가 올라갑니다. (필수 아님)")
allergy_list = st.multiselect(
	label="알레르기가 있는 것들을 모두 선택하세요.",
	options=[
		"1. 난류 🥚",
		"2. 우유 🥛",
		"3. 메밀 🌾",
		"4. 땅콩 🥜",
		"5. 대두 🫛",
		"6. 밀 🌾",
		"7. 고등어 🐟",
		"8. 게 🦀",
		"9. 새우 🦐",
		"10. 돼지고기 🐖",
		"11. 복숭아 🍑",
		"12. 토마토 🍅",
		"13. 아황산류 🧪",
		"14. 호두 🥜",
		"15. 닭고기 🐓",
		"16. 쇠고기 🐂",
		"17. 오징어 🦑",
		"18. 조개류(굴,전복,홍합 포함) 🦪",
		"19. 잣 🥜"
	]
)

is_checked_ai = st.checkbox("**:rainbow[(매우 추천)]** AI가 급식 순위를 알려줍니다.", True)
is_checked_other = st.checkbox("⭐️ 우리 학교가 아닌 랜덤한 다른 학교 급식 보기 :gray[(12,492개의 학교 리스트에서 뽑습니다.)]")

btn_holder = st.empty()
school_name_holder = st.empty()
color_info_holder = st.empty()


# 학교 급식을 반환하는 함수
def get_school_meal(office_code, school_code, date):
	url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
	
	params = {
		"KEY": neis_key,
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


# 위에서 선택한 알레르기 리스트에서 숫자(번호)만 추출하여 세트(Set)로 만듭니다.
def get_allergy_matching_menus(allergy_refs, meal_text):
	# 예: ['1. 난류', '4. 땅콩', '6. 밀'] -> {'1', '4', '6'}
	my_allergy_numbers = set()
	for ref in allergy_refs:
		match = re.search(r"\d+", ref)
		if match:
			my_allergy_numbers.add(match.group())

	matched_menus = ""

	# 2. 급식 텍스트를 한 줄씩 읽으면서 검사합니다.
	lines = meal_text.strip().split("\n")
	for line in lines:
		line = line.strip()
		if not line:
			continue

		# [수정 포인트] 괄호 안에 '숫자'와 '점(.)'만 들어있는 패턴만 타겟팅하여 알레르기 번호를 추출합니다.
		# 이렇게 하면 (신), (말차) 같은 한글 괄호는 건드리지 않고 통과합니다.
		allergy_match = re.search(r"\([\d\s\.]+\)", line)

		allergy_in_menu = []
		menu_name = line  # 기본값은 원본 줄 전체

		if allergy_match:
			# 알레르기 괄호가 존재한다면, 그 안에서 숫자들을 다 뽑아냅니다.
			allergy_raw_inside = allergy_match.group()
			allergy_in_menu = re.findall(r"\d+", allergy_raw_inside)

			# [수정 포인트] 오직 숫자가 들어있던 그 알레르기 괄호 부분만 본문에서 쏙 지워줍니다.
			menu_name = line.replace(allergy_raw_inside, "").strip()

		# 공통 정제: 맨 뒤에 붙은 스트림릿 강조용 별표(*) 및 공백 제거
		menu_name = menu_name.rstrip("*").strip()

		# 칼로리 정보 정보나 공백 메뉴는 검사에서 제외합니다.
		if "Kcal" in menu_name or not menu_name or menu_name == "<조식>" or menu_name == "<중식>" or menu_name == "<석식>":
			continue

		# 3. 메뉴에 적힌 알레르기 번호 중 하나라도 내 알레르기 번호 세트에 포함되어 있는지 교집합 검사
		# 문자열 비교를 위해 세트로 변환하여 비교합니다.
		if set(allergy_in_menu) & my_allergy_numbers:
			# 일치하는 게 있다면 리스트에 추가 (메뉴 원본 줄이나 가공된 이름을 넣으시면 됩니다)
			safe_menu_name = re.sub(r'[^a-zA-Z0-9가-힣]', '_', menu_name)
			matched_menus += f"0.{safe_menu_name},\n"

	return matched_menus


# 급식표에서 알레르기 정보를 삭제하는 함수
def clean_meal_text(text):
	# 1. 알레르기 정보 제거: (숫자.숫자...) 형태를 찾아 빈 문자열로 바꿉니다.
	# [0-9.]+ 는 숫자와 마침표(.)가 하나 이상 반복되는 패턴을 의미합니다.
	text = re.sub(r'\([0-9.]+\)', '', text)
	
	# 2. '*' 문자 제거
	text = text.replace('*', '')
	
	# 3. 불필요한 공백 정리
	# 각 줄 끝에 남은 공백을 제거하고, 빈 줄이 너무 많아지지 않게 정리합니다.
	lines = [line.strip() for line in text.split('\n')]
	return '\n'.join(lines)


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

if is_checked_other: # 랜덤 학교 급식 체크박스 켜진 상태일때만
	random_school = random.choice(all_schools)
	OFFICE_CODE = random_school["office_code"]
	SCHOOL_CODE = random_school["school_code"]
	SCHOOL_NAME = random_school["school_name"]
	SCHOOL_REGION = random_school["school_region"]


days = ["월", "화", "수", "목", "금"]
cols = st.columns(5)
full_data = ""
full_allergy = ""

# 버튼을 누르면 급식 정보를 불러옴
if btn_holder.button("급식 조회"):
	school_name_holder.subheader(SCHOOL_REGION + " " + SCHOOL_NAME)

	with st.spinner("🍱 급식 정보 불러오는 중..."):
		loop = asyncio.new_event_loop()
		asyncio.set_event_loop(loop)

		dates = []

		for i in range(5):
			dates.append((monday + timedelta(days=i)).strftime("%Y%m%d")) # i만큼 날짜 뒤를 구함 형식은 YYYYmmdd이다.

		# 딱 한 번만 루프를 실행하여 전체 결과를 리스트로 받아옵니다.
		all_meals_list = loop.run_until_complete(
			fetch_all_dates(
				OFFICE_CODE, SCHOOL_CODE, dates
			)
		)

		for i in range(5):
			with cols[i]:
				newDate = dates[i]
				mealText = all_meals_list[i]
				st.subheader(days[i])

				date_obj = datetime.strptime(newDate, "%Y%m%d")
				formatted_date = date_obj.strftime("%m월 %d일")
				st.text(formatted_date)

				mealTextClean = clean_meal_text(mealText)
				words = mealTextClean.split('\n')
				for word in words:
					clean_word = word.strip()
					if clean_word:  # 빈 줄이 아닐 경우에만 출력
						if clean_word == "<조식>":
							st.text("")
							colorText = f'<span style="font-size: 20px; color: #fcba4e; font-weight: bold;">☀️ 조식</span>'
							st.markdown(colorText, unsafe_allow_html=True)
						elif clean_word == "<중식>":
							st.text("")
							colorText = f'<span style="font-size: 20px; color: #fcba4e; font-weight: bold;">☀️ 중식</span>'
							st.markdown(colorText, unsafe_allow_html=True)
						elif clean_word == "<석식>":
							st.text("")
							colorText = f'<span style="font-size: 20px; color: #fffc4d; font-weight: bold;">🌙 석식</span>'
							st.markdown(colorText, unsafe_allow_html=True)
						elif "Kcal" in clean_word:
							st.text(clean_word)
						else:
							if is_checked_ai:
								# ai 순위랑 색깔 가독성 높이기 위해 투명도 0.5
								colorText = f'<span style="opacity: 0.5; background-color: #4c555e; color: #ffffff; padding: 2px 6px; border-radius: 4px;">{clean_word}</span>'
							else:
								# ai 순위 없어서 투명도 100%
								colorText = f'<span style="opacity: 1; background-color: #4c555e; color: #ffffff; padding: 2px 6px; border-radius: 4px;">{clean_word}</span>'
							
							# 고유 아이디랑 출력 텍스트 같게 설정
							safe_id = re.sub(r'[^a-zA-Z0-9가-힣]', '_', clean_word) # 허용되지 않는 모든 특수기호 '_'로 치환
							st.markdown(f'<p id="{safe_id}">{colorText}</p>', unsafe_allow_html=True)

				full_data += mealTextClean + "\n\n"
				full_allergy += get_allergy_matching_menus(allergy_list, mealText)

	ai_answer = ""

	if is_checked_ai:
		color_info_holder.markdown(
			f'급식 순위 색상 참고: <span style="{tier0}">알레르기 색 (빨간색)</span> <span style="{tier1}">🥇1등 색 (금색)</span> <span style="{tier2}">🥈2등 색 (은색)</span> <span style="{tier3}">🥉3등 색 (동색)</span>',
			unsafe_allow_html=True
		)

		prompt = """
		총 n개의 식단에서 맛있는 음식 1,2,3등 매겨줘.
		평범한 메뉴를 제외하고 중식 1,2,3등 석식 1,2,3등 이런 식으로 각각의 식단마다 순위를 매겨야 함.
		n*3개만큼의 메뉴를 출력해야 함. 식단이 제공되지 않는 건 제외해야 함.
		음식 이름을 급식표에 있는 이름 그대로를 사용. +나 ,나 ()가 들어있어도 한 메뉴로 인식.
		기타 정보(칼로리)는 제외. 만약 음식 이름에 ,기호가 들어가면 +로 바꿔줘
		<제일 중요한 규칙> 출력 형식: (앞에 문자열 X) 순위숫자.음식번호1, 순위숫자.음식번호2, ..., (마지막에 꼭 ,붙이기)
		텍스트 서식 사용 금지, 각각의 식단 햇갈리면 안됨
		추가로 고기류, 간식류에 가중치를 조금 올리면 좋을 것 같음.
		"""

		Like = ""
		if like != "":
			Like = f"이 음식을 1위가 되도록 해줘: {like}"

		with st.spinner("🤖 AI가 급식 순위 매기는 중... (최대 1분 소요)"):
			response = client.models.generate_content(
				model="gemini-3.1-flash-lite",
				contents=full_data+prompt+Like
			)

		ai_answer = response.text


	# AI 답변 디버깅용으로 보기
	#st.text("디버깅용 AI 답변 보기\n\n" + ai_answer + "\n\n\n알레르기 정보 디버깅\n\n" + full_allergy)

	pattern = r"(\d+)\.(.*?)(?=,|\n|$)"
	matches = re.findall(pattern, ai_answer + "\n\n" + full_allergy) # AI 답변 + 알레르기

	for rank, menu_name in matches:
		# 추출된 텍스트 양끝의 불필요한 공백 제거(.strip())
		rank = rank.strip()
		menu_name = menu_name.strip()
		safe_id = re.sub(r'[^a-zA-Z0-9가-힣]', '_', menu_name)

		if rank == "0": # 알레르기 코드
			st.markdown(f"""
			<style>
				#{safe_id} span {{
					opacity: 1 !important;
					background-color: #ff0000 !important;
				}}
			</style>
			""", unsafe_allow_html=True)

		elif rank == "1":
			st.markdown(f"""
			<style>
				#{safe_id} span {{
					opacity: 1 !important;
					background-color: #948d5d !important;
					text-shadow:
						0 0 2px #ffea00,
						0 0 4px #ffea00,
						0 0 6px #ffea00;
				}}
			</style>
			""", unsafe_allow_html=True)
		elif rank == "2":
			st.markdown(f"""
			<style>
				#{safe_id} span {{
					opacity: 1 !important;
					background-color: #757575 !important;
					text-shadow:
						0 0 2px #e6e8e8,
						0 0 4px #e6e8e8,
						0 0 6px #e6e8e8;
				}}
			</style>
			""", unsafe_allow_html=True)
		elif rank == "3":
			st.markdown(f"""
			<style>
				#{safe_id} span {{
					opacity: 1 !important;
					background-color: #6b5f4a !important;
					text-shadow:
						0 0 2px #edcf98,
						0 0 4px #edcf98,
						0 0 6px #edcf98;
				}}
			</style>
			""", unsafe_allow_html=True)
