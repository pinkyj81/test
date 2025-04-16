import streamlit as st
import pandas as pd
import pymssql
import altair as alt
from datetime import datetime

# MSSQL 연결 함수
def get_connection():
    return pymssql.connect(
        server='ms1901.gabiadb.com',
        user='pinkyj81',
        password='zoskek38!!',
        database='yujincast'
    )

# 조건 검색 함수
def load_filtered_data(start_date, end_date, product):
    conn = get_connection()
    query = """
        SELECT * 
        FROM yujincast.dbo.M3_2025_TD
        WHERE [Date] BETWEEN %s AND %s
        AND ([Product] = %s OR %s = '')
    """
    df = pd.read_sql(query, conn, params=[start_date, end_date, product, product])
    conn.close()
    return df

# 앱 제목
st.title("📊 Prc1별 TD 상태 조회")

# 조건 입력 UI
col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
with col1:
    start_date = st.date_input("시작 날짜", datetime(2025, 1, 1))
with col2:
    end_date = st.date_input("종료 날짜", datetime(2025, 12, 31))
with col3:
    product = st.text_input("Product (전체는 비워두세요)")
with col4:
    search_button = st.button("🔍 검색")

# 조건 검색 실행
if search_button:
    df = load_filtered_data(start_date, end_date, product)

    if df.empty:
        st.warning("조회된 데이터가 없습니다.")
    else:
        st.success(f"총 {len(df)}건이 조회되었습니다.")
        st.dataframe(df, use_container_width=True)

        df['Date'] = pd.to_datetime(df['Date'])

        chart_data = df.groupby(['Date', 'Prc1']).size().reset_index(name='Count')

        chart = alt.Chart(chart_data).mark_bar().encode(
            x=alt.X('Date:T', title='날짜'),
            y=alt.Y('Count:Q', title='개수'),
            color='Prc1:N',
            tooltip=['Date', 'Prc1', 'Count']
        ).properties(
            height=400,
            title='📅 날짜별 Prc1 발생 건수'
        )

        st.altair_chart(chart, use_container_width=True)

# 엑셀 업로드로 DB에 데이터 추가
st.header("📂 엑셀 업로드로 데이터 추가")

uploaded_file = st.file_uploader("엑셀 파일 업로드 (.xlsx)", type=["xlsx"])

if uploaded_file:
    try:
        df_excel = pd.read_excel(uploaded_file, engine='openpyxl')

        # NaN 컬럼 제거 및 컬럼명 문자열화
        df_excel = df_excel.loc[:, ~df_excel.columns.isna()]
        df_excel.columns = [str(col).strip() for col in df_excel.columns]

        required_columns = ['Date', 'Time', 'Prc1', 'Prc2', 'State', 'Value', 'Note1', 'Product']

        if all(col in df_excel.columns for col in required_columns):
            st.success("✅ 업로드된 엑셀 미리보기:")
            st.dataframe(df_excel, use_container_width=True)

            remove_duplicates = st.checkbox("⚠️ 중복 (Date + Time + Prc1) 제거", value=True)

            if remove_duplicates:
                before = len(df_excel)
                df_excel = df_excel.drop_duplicates(subset=['Date', 'Time', 'Prc1'])
                after = len(df_excel)
                st.info(f"중복 제거: {before - after}건 삭제됨 (총 {after}건 남음)")

            if st.button("📝 DB에 추가"):
                try:
                    conn = get_connection()
                    cursor = conn.cursor()

                    inserted_count = 0
                    for _, row in df_excel.iterrows():
                        # NaN 값은 None으로 치환
                        values = [row.get(col) if pd.notna(row.get(col)) else None for col in required_columns]

                        cursor.execute("""
                            INSERT INTO yujincast.dbo.M3_2025_TD
                            ([Date], [Time], [Prc1], [Prc2], [State], [Value], [Note1], [Product])
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """, values)
                        inserted_count += 1

                    conn.commit()
                    conn.close()
                    st.success(f"🎉 {inserted_count}건의 데이터가 성공적으로 추가되었습니다.")

                except Exception as e:
                    st.error(f"❌ DB 저장 중 오류: {e}")

        else:
            st.error(f"❌ 엑셀에 필수 컬럼이 없습니다: {required_columns}")

    except Exception as e:
        st.error(f"❌ 엑셀 처리 중 오류 발생: {e}")
