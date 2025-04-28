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

st.set_page_config(page_title="아이 루틴 체크", layout="wide")
st.title("오늘은 뭐 해야 해?")

# 1. 아이 선택 + 날짜 선택
conn = get_connection()
child_df = pd.read_sql("SELECT DISTINCT ChildName FROM RoutinePlan WHERE UseYN='Y'", conn)
children = child_df['ChildName'].tolist() if not child_df.empty else ["Emma", "Jay"]
conn.close()

child = st.selectbox("아이 이름을 선택하세요", children)
check_date = st.date_input("날짜를 선택하세요", value=date.today(), key="child_routine_date")

# 2. 해당 날짜 루틴 가져오기
conn = get_connection()
df_plan = pd.read_sql(
    """
    SELECT PlanID, Task
    FROM RoutinePlan
    WHERE UseYN='Y' AND ChildName=%s AND [Date]=%s
    ORDER BY Task
    """,
    conn,
    params=(child, check_date.strftime('%Y-%m-%d'))
)
# 이미 체크된 루틴 가져오기
df_log = pd.read_sql(
    """
    SELECT PlanID, Completed
    FROM RoutineLog
    WHERE ChildName=%s AND [Date]=%s
    """,
    conn,
    params=(child, check_date.strftime('%Y-%m-%d'))
)
conn.close()

# 체크박스로 루틴 표기
st.subheader(f"{check_date} To Do list")
checked_planids = []
if not df_plan.empty:
    done_planids = df_log[df_log['Completed'] == 1]['PlanID'].tolist()
    checkboxes = []
    for i, row in df_plan.iterrows():
        checked = row['PlanID'] in done_planids
        # 체크박스 표시
        cb = st.checkbox(row['Task'], value=checked, key=f"routine_cb_{row['PlanID']}")
        checkboxes.append(cb)
        if cb:
            checked_planids.append(row['PlanID'])
    # 저장 버튼
    if st.button("완료"):
        conn = get_connection()
        cursor = conn.cursor()
        for planid in df_plan['PlanID']:
            is_checked = planid in checked_planids
            # RoutineLog에 이미 존재하면 업데이트, 없으면 insert
            cursor.execute(
                "SELECT COUNT(*) FROM RoutineLog WHERE PlanID=%s AND ChildName=%s AND [Date]=%s",
                (planid, child, check_date.strftime('%Y-%m-%d'))
            )
            exists = cursor.fetchone()[0]
            if exists:
                cursor.execute(
                    "UPDATE RoutineLog SET Completed=%s WHERE PlanID=%s AND ChildName=%s AND [Date]=%s",
                    (1 if is_checked else 0, planid, child, check_date.strftime('%Y-%m-%d'))
                )
            else:
                cursor.execute(
                    "INSERT INTO RoutineLog (PlanID, ChildName, [Date], Completed) VALUES (%s, %s, %s, %s)",
                    (planid, child, check_date.strftime('%Y-%m-%d'), 1 if is_checked else 0)
                )
        conn.commit()
        conn.close()
        st.success("루틴 완료 체크가 저장되었습니다!")
        st.rerun()
else:
    st.info("이 날짜에 등록된 루틴이 없습니다.")

# 3. 하단에 아이별 달력 출력 (부모페이지와 동일)
st.header("My To Do List")

# 연/월 선택
cal_col1, cal_col2 = st.columns(2)
with cal_col1:
    year = st.number_input("연도", value=check_date.year, min_value=2020, max_value=2100, key="calendar_year")
with cal_col2:
    month = st.number_input("월", value=check_date.month, min_value=1, max_value=12, key="calendar_month")

def make_calendar_html(df_plan, df_log, year, month):
    cal = calendar.monthcalendar(year, month)
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
                plans = df_plan[df_plan['Date'] == day_str]
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
                # 하늘색: 모두 완료
                cell_class = "done" if (not plans.empty and all_done) else ""
                html += f'<td class="{cell_class}">' + '<br>'.join(cell_lines) + '</td>'
        html += '</tr>'
    html += '</table>'
    return html

# 달력 데이터 쿼리
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
    conn,
    params=(child, month_start.strftime('%Y-%m-%d'), month_end.strftime('%Y-%m-%d'))
)
df_log = pd.read_sql(
    """
    SELECT PlanID, ChildName, [Date], Completed
    FROM RoutineLog
    WHERE ChildName=%s AND [Date] BETWEEN %s AND %s
    """,
    conn,
    params=(child, month_start.strftime('%Y-%m-%d'), month_end.strftime('%Y-%m-%d'))
)
conn.close()

if not df_plan.empty:
    df_plan['Date'] = df_plan['Date'].astype(str)
    df_log['Date'] = df_log['Date'].astype(str)
    cal_html = make_calendar_html(df_plan, df_log, int(year), int(month))
    st.markdown(cal_html, unsafe_allow_html=True)
else:
    st.info("이달에는 등록된 루틴이 없습니다.")
