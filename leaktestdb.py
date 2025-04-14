import streamlit as st
import pandas as pd
import pymssql
import altair as alt
from datetime import date

# 1. MSSQL 연결 함수
def get_connection():
    return pymssql.connect(
        server='ms1901.gabiadb.com',
        user='pinkyj81',
        password='zoskek38!!',
        database='yujincast'
    )

# 2. 데이터 불러오기
@st.cache_data
def load_data():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM yujincast.dbo.MergedTable", conn)
    conn.close()
    return df

# 3. Streamlit 앱 시작
st.title("Prc1별 TD 상태 조회")

df = load_data()

if {'Date', 'State', 'Prc1'}.issubset(df.columns):
    df['Date'] = pd.to_datetime(df['Date'])
    df_td = df[df['State'] == '(TD)']

    # 4. 날짜 범위 기본값 설정
    min_date = df_td['Date'].min().date()
    max_date = df_td['Date'].max().date()

    # 5. 날짜 + 버튼을 한 줄로 배치
    with st.form("search_form"):
        col1, col2 = st.columns([4, 1])  # 비율 조정 가능

        with col1:
            start_date, end_date = st.date_input(
                "조회 기간",
                [min_date, max_date],
                label_visibility="collapsed"
            )

        with col2:
            st.write("")  # 간격 맞추기용
            submitted = st.form_submit_button("🔍 검색")

    # 6. 검색 버튼 눌렀을 때만 실행
    if submitted:
        df_range = df_td[
            (df_td['Date'].dt.date >= start_date) &
            (df_td['Date'].dt.date <= end_date)
        ]

        # 7. 필터링된 데이터프레임 표시
        st.subheader(f"📋 TD 데이터 ({start_date} ~ {end_date})")
        st.dataframe(df_range)

        # 8. 날짜 + Prc1 그룹화
        grouped = df_range.groupby([df_range['Date'].dt.date, 'Prc1']).size().reset_index(name='Count')
        grouped.columns = ['Date', 'Prc1', 'Count']

        # 9. 색상 설정
        color_scale = alt.Scale(
            domain=[10, 20, 30, 40],
            range=['red', 'yellow', 'green', 'blue']
        )

        # 10. Altair 그래프
        chart = alt.Chart(grouped).mark_bar().encode(
            x=alt.X('Date:T', title='날짜', axis=alt.Axis(format='%Y-%m-%d')),
            y=alt.Y('Count:Q', title='TD 수량'),
            color=alt.Color('Prc1:O', scale=color_scale, title='Prc1'),
            xOffset='Prc1:O',
            tooltip=['Date', 'Prc1', 'Count']
        ).properties(
            width=700,
            height=400,
            title="선택한 기간의 Prc1별 TD 상태"
        )

        st.altair_chart(chart, use_container_width=True)
else:
    st.warning("데이터에 'Date', 'State', 'Prc1' 컬럼이 없습니다.")
