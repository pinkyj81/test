import streamlit as st
import pandas as pd
import pymssql
from datetime import date, timedelta
import calendar

def get_connection():
    return pymssql.connect(
        server='ms1901.gabiadb.com',
        user='pinkyj81',
        password='zoskek38!!',
        database='yujincast'
    )

st.set_page_config(page_title="날짜별 루틴", layout="wide")
st.title("오늘의 계획")

children = ["emma", "Jay"]  # 초기 리스트, DB연동 가능

# 날짜별 루틴 입력
st.header("루틴 입력")
col1, col2, col3 = st.columns(3)
with col1:
    child = st.selectbox("아이 선택", children, key="add_child")
with col2:
    routine_date = st.date_input("루틴 날짜", value=date.today(), key="add_routine_date")
# 기존 루틴 콤보박스 + 직접 입력
conn = get_connection()
task_df = pd.read_sql(
    "SELECT DISTINCT Task FROM RoutinePlan WHERE ChildName=%s AND UseYN='Y' ORDER BY Task",
    conn, params=(child,)
)
conn.close()
existing_tasks = task_df['Task'].tolist() if not task_df.empty else []
task_options = existing_tasks + ["직접 입력"]
with col3:
    task_select = st.selectbox("기존 루틴 선택/입력", task_options, key="task_combo")
    if task_select == "직접 입력":
        task = st.text_input("새 루틴 직접 입력", key="new_task_input")
    else:
        task = task_select

add_btn = st.button("루틴 추가하기")
if add_btn and task.strip():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO RoutinePlan (ChildName, [Date], Task, UseYN) VALUES (%s, %s, %s, 'Y')",
        (child, routine_date.strftime('%Y-%m-%d'), task)
    )
    conn.commit()
    conn.close()
    st.success(f"{child}의 {routine_date} 루틴 '{task}' 추가 완료!")
    st.rerun()

# --- 달력(캘린더)만 보여주기 ---

st.header("루틴 확인하기")

# 아이 선택 (캘린더용)
conn = get_connection()
child_df = pd.read_sql("SELECT DISTINCT ChildName FROM RoutinePlan WHERE UseYN='Y'", conn)
children_for_calendar = child_df['ChildName'].tolist() if not child_df.empty else ["유현이", "서현이"]
conn.close()
child_for_calendar = st.selectbox("캘린더에 표시할 아이 선택", children_for_calendar, key="calendar_child")

# 연/월 선택
cal_col1, cal_col2 = st.columns(2)
with cal_col1:
    year = st.number_input("연도", value=date.today().year, min_value=2020, max_value=2100, key="calendar_year")
with cal_col2:
    month = st.number_input("월", value=date.today().month, min_value=1, max_value=12, key="calendar_month")

def make_calendar_html(df_plan, df_log, year, month):
    cal = calendar.monthcalendar(year, month)
    day_routines = {}
    for day in range(1, calendar.monthrange(year, month)[1]+1):
        day_str = f"{year}-{month:02d}-{day:02d}"
        routines = []
        plans = df_plan[df_plan['Date'] == day_str]
        for _, r in plans.iterrows():
            planid = r['PlanID']
            log = df_log[(df_log['PlanID'] == planid) & (df_log['Date'] == day_str)]
            status = "O" if (not log.empty and log.iloc[0]['Completed'] == 1) else "X"
            routines.append(status)
        day_routines[day] = routines

    # HTML 테이블
    html = """
    <style>
    td {vertical-align:top; font-size:15px; white-space:pre-line; min-width:80px;}
    .done {background-color: #e3f2fd !important;}
    </style>
    """
    html += '<table border="1" style="border-collapse:collapse; text-align:left;">'
    html += '<tr>' + ''.join(f'<th>{w}</th>' for w in ['일','월','화','수','목','금','토']) + '</tr>'
    for week in cal:
        html += '<tr>'
        for day in week:
            if day == 0:
                html += '<td></td>'
            else:
                day_str = f"{year}-{month:02d}-{day:02d}"
                # 해당 날짜의 루틴과 완료여부
                plans = df_plan[df_plan['Date'] == day_str]
                # 루틴 텍스트
                cell_lines = [f"<b>{day}</b>"]
                routines = []
                all_done = True if not plans.empty else False
                for _, r in plans.iterrows():
                    planid = r['PlanID']
                    log = df_log[(df_log['PlanID'] == planid) & (df_log['Date'] == day_str)]
                    done = (not log.empty and log.iloc[0]['Completed'] == 1)
                    if not done:
                        all_done = False
                    routines.append(f"{r['Task']} ({'O' if done else 'X'})")
                for routine_line in routines:
                    cell_lines.append(routine_line)
                # 셀 배경색 결정
                cell_class = "done" if (not plans.empty and all_done) else ""
                html += f'<td class="{cell_class}">' + '<br>'.join(cell_lines) + '</td>'
        html += '</tr>'
    html += '</table>'
    return html

# 해당 아이, 연/월 루틴+로그 불러오기
conn = get_connection()
month_start = date(int(year), int(month), 1)
last_day = calendar.monthrange(int(year), int(month))[1]
month_end = date(int(year), int(month), last_day)

df_plan = pd.read_sql(
    """
    SELECT PlanID, ChildName, [Date], Task
    FROM RoutinePlan
    WHERE UseYN='Y' AND ChildName=%s AND [Date] BETWEEN %s AND %s
    ORDER BY [Date], Task
    """,
    conn, params=(child_for_calendar, month_start.strftime('%Y-%m-%d'), month_end.strftime('%Y-%m-%d'))
)
df_log = pd.read_sql(
    """
    SELECT PlanID, ChildName, [Date], Completed
    FROM RoutineLog
    WHERE ChildName=%s AND [Date] BETWEEN %s AND %s
    """,
    conn, params=(child_for_calendar, month_start.strftime('%Y-%m-%d'), month_end.strftime('%Y-%m-%d'))
)
conn.close()

if not df_plan.empty:
    df_plan['Date'] = df_plan['Date'].astype(str)
    df_log['Date'] = df_log['Date'].astype(str)
    cal_html = make_calendar_html(df_plan, df_log, int(year), int(month))
    st.markdown(cal_html, unsafe_allow_html=True)
else:
    st.info("이달에는 등록된 루틴이 없습니다.")
