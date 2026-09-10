import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime, timedelta, timezone

# =========================================================
# 1. 과목 및 설정 (매주 이 부분만 수정하세요)
# =========================================================
SUBJECT_NAME = "은퇴와상속설계 퀴즈"   # 화면에 보이는 제목
CURRENT_WEEK = "3주차"               # 매주 여기만 바꾸면 됩니다
ADMIN_PASSWORD = "3383"               # 교수용 비밀번호
TABLE = "retire_quiz_results"         # 수파베이스 테이블 ★변경 금지★

# ---------------------------------------------------------
# 퀴즈 데이터
#   "q" : 학생에게 보이는 문제
#   "a" : 정답 (공백과 영문 대소문자는 자동으로 무시됩니다)
#         복수정답을 모두 적어야 하는 문제는 "가치,효용"처럼 쉼표로 구분
#   ※ 문항 수는 자유롭게 늘리고 줄일 수 있습니다 (최대 10개).
# ---------------------------------------------------------
QUIZ_DATA = [
    {"q": "1. 자산을 그대로 보유하면서, 그 자산에서 얻을 수 있는 소득을 계산해 기존 소득에 더하는 방법은?", "a": "포괄소득화"},
    {"q": "2. 세일러의 (__________)는, 사람은 돈에 꼬리표를 붙여 서로 다른 계좌처럼 취급한다고 설명한다.", "a": "심적회계"},
    {"q": "3. 이슈 5-B는 플랫폼의 주인-(________) 문제는 사라지지 않고 코드 안으로 숨는다고 주장한다.", "a": "대리인"},
    {"q": "4. 주된 일자리에서 가교직업을 갖는 부분은퇴 단계를 거쳐 (_____)은퇴 단계에 도달하는 경우가 많아지고 있다.", "a": "완전"},
    {"q": "5. (________)는 자신의 인생을 돌아보고 가족 친구 등 사회적 관계에 대해 다시 생각하는 은퇴생활 단계이다.", "a": "회상기"},
    {"q": "6. 점점 늘어나는 평균수명을 고려하면 은퇴준비는 젊은 시기부터 시작해야 하는 (________) 과업에 해당한다.", "a": "초장기"},
    {"q": "7. 은퇴설계에서 금리와 (______)는 필요자금 산정과 관리 및 생활비 산출에 영향을 미치게 된다.", "a": "물가"},
]



NUM_QUESTIONS = len(QUIZ_DATA)
# =========================================================


st.set_page_config(page_title=f"{SUBJECT_NAME}", layout="wide")


@st.cache_resource
def init_connection() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


try:
    supabase = init_connection()
except Exception:
    st.error("수파베이스 연결 설정(Secrets)이 필요합니다.")
    st.stop()

if "submitted_on_this_device" not in st.session_state:
    st.session_state.submitted_on_this_device = False

st.title(f"📊 {SUBJECT_NAME}")
st.caption(CURRENT_WEEK)

tab1, tab2, tab3 = st.tabs(["✍️ 퀴즈 제출", "🖥️ 제출자 명단 확인", "🔐 성적 분석(교수용)"])


# --- [TAB 1] 학생 제출 화면 ---
with tab1:
    st.header("답안지")

    if st.session_state.submitted_on_this_device:
        st.warning("⚠️ 이 기기에서 제출이 완료되었습니다. 응시는 더 이상 불가능합니다.")
    else:
        with st.form("quiz_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("이름", placeholder="이름")
            with col2:
                student_id = st.text_input("학번", placeholder="학번")

            st.divider()

            user_responses = []
            for i, item in enumerate(QUIZ_DATA):
                st.markdown(f"**{item['q']}**")
                ans = st.text_input(f"{i+1}번 답안", key=f"q{i}")
                user_responses.append(ans)

            submitted = st.form_submit_button(
                "답안 제출하고 확인받기 "
                "(기기당 답안 제출은 1회만 가능하니, 신중하게 검토하고 버튼 누르세요)"
            )

            if submitted:
                if not name or not student_id:
                    st.error("이름과 학번을 입력해 주세요.")
                else:
                    try:
                        existing = supabase.table(TABLE).select("id")\
                            .eq("주차", CURRENT_WEEK).eq("학번", student_id).execute()

                        if existing.data:
                            st.error(f"❌ {name} 학생은 이미 이번 주 답안을 제출했습니다.")
                        else:
                            kst = timezone(timedelta(hours=9))
                            now_time = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")

                            row_dict = {
                                "주차": CURRENT_WEEK,
                                "제출시간": now_time,
                                "이름": name,
                                "학번": student_id,
                            }

                            # 채점 (공백 제거 + 영문 소문자 변환 후 비교)
                            total_correct = 0
                            for i, item in enumerate(QUIZ_DATA, 1):
                                s_ans = set(item["a"].replace(" ", "").lower().split(","))
                                u_ans = set(user_responses[i-1].replace(" ", "").lower().split(","))

                                is_correct = (s_ans == u_ans)
                                if is_correct:
                                    total_correct += 1

                                row_dict[f"q{i}_답"] = user_responses[i-1]
                                row_dict[f"q{i}_결과"] = "O" if is_correct else "X"

                            row_dict["총점"] = total_correct

                            supabase.table(TABLE).insert(row_dict).execute()

                            st.session_state.submitted_on_this_device = True
                            st.success(f"{name} 학생, 제출 성공! ({total_correct}/{NUM_QUESTIONS})")
                            st.rerun()

                    except Exception:
                        # 과부하 등으로 실패해도 학생 화면이 멈추지 않도록 처리
                        st.warning("제출 처리 중 문제가 있었습니다. 잠시 후 다시 시도해주세요.")


# --- [TAB 2] 제출 명단 확인 ---
with tab2:
    st.subheader(f"📍 {CURRENT_WEEK} 제출 완료 명단")
    st.info("명단을 확인하려면 아래 버튼을 누르세요.")

    if st.button("🔄 명단 새로고침 (클릭)"):
        try:
            response = supabase.table(TABLE).select("*")\
                .eq("주차", CURRENT_WEEK).execute()
            today_list = pd.DataFrame(response.data)

            if not today_list.empty:
                st.write(f"현재 총 {len(today_list)}명 제출 완료")
                cols = st.columns(6)
                for i, row in enumerate(today_list.itertuples()):
                    cols[i % 6].success(f"✅ {row.이름}")
            else:
                st.write("아직 제출자가 없습니다.")
        except Exception:
            st.error("데이터를 불러오는 데 실패했습니다.")


# --- [TAB 3] 성적 분석 ---
with tab3:
    st.header("🔐 관리자 인증")
    admin_pw = st.text_input("비밀번호를 입력하세요", type="password")

    if admin_pw == ADMIN_PASSWORD:
        st.success("인증 성공")
        try:
            response = supabase.table(TABLE).select("*").execute()
            df = pd.DataFrame(response.data)

            if not df.empty:
                st.subheader("학생별 평균 정답률 (전체 주차)")
                stats = df.groupby(["학번", "이름"])["총점"].mean().reset_index()
                stats["정답률(%)"] = (stats["총점"] / NUM_QUESTIONS * 100).round(1)
                st.dataframe(stats.sort_values("총점", ascending=False),
                             use_container_width=True, hide_index=True)

                st.divider()

                st.subheader("주차별 응시 현황")
                by_week = df.groupby("주차").agg(
                    응시인원=("학번", "count"),
                    평균점수=("총점", "mean"),
                ).round(1).reset_index()
                st.dataframe(by_week, use_container_width=True, hide_index=True)

                st.divider()

                st.subheader(f"{CURRENT_WEEK} 문항별 정답률")
                cur = df[df["주차"] == CURRENT_WEEK]
                if cur.empty:
                    st.info("이번 주차 제출 데이터가 없습니다.")
                else:
                    rows = []
                    for i in range(1, NUM_QUESTIONS + 1):
                        col = f"q{i}_결과"
                        if col in cur.columns:
                            ok = (cur[col] == "O").sum()
                            rows.append({
                                "문항": f"{i}번",
                                "정답": int(ok),
                                "오답": int(len(cur) - ok),
                                "정답률(%)": round(ok / len(cur) * 100, 1),
                            })
                    if rows:
                        st.dataframe(pd.DataFrame(rows),
                                     use_container_width=True, hide_index=True)
                        st.caption("정답률이 낮은 문항은 수업에서 다시 짚어주시면 좋습니다.")

                st.divider()

                st.download_button(
                    "엑셀 데이터 다운로드",
                    data=df.to_csv(index=False).encode("utf-8-sig"),
                    file_name=f"{SUBJECT_NAME}_결과.csv",
                    mime="text/csv",
                )
            else:
                st.info("제출된 데이터가 없습니다.")
        except Exception:
            st.error("데이터를 불러오는 중 오류가 발생했습니다.")
    elif admin_pw:
        st.error("비밀번호 불일치")
