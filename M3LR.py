import streamlit as st
import pandas as pd
import pyodbc
import altair as alt
from datetime import datetime

# 1. MSSQL 연결 함수
def get_connection():
    return pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=ms1901.gabiadb.com;"
        "DATABASE=yujincast;"
        "UID=pinkyj81;"
        "PWD=zoskek38!!"
    )

# 2. 조건 검색 함수
def load_filtered_data(start_date, end_date, product):
    conn = get_connection()
    query = """
        SELECT * 
        FROM yujincast.dbo.M3_2025_TD
        WHERE [Date] BETWEEN ? AND ?
        AND ([Product] = ? OR ? = '')
    """
    df = pd.read_sql(query, conn, params=[start_date, end_date, product, product])
    conn.close()
    return df

# 3. 앱 제목
st.title("📊 Prc1별 TD 상태 조회")

# 4. 조건 입력 UI (가로 정렬)
col1, col2, col3, col4 = st.columns([2, 2, 2, 1])

with col1:
    start_date = st.date_input("시작 날짜", datetime(2025, 1, 1))
with col2:
    end_date = st.date_input("종료 날짜", datetime(2025, 12, 31))
with col3:
    product = st.text_input("Product (전체는 비워두세요)")
with col4:
    search_button = st.button("🔍 검색")

# 5. 검색 실행 시
if search_button:
    df = load_filtered_data(start_date, end_date, product)

    if df.empty:
        st.warning("조회된 데이터가 없습니다.")
    else:
        st.success(f"총 {len(df)}건이 조회되었습니다.")

        # ✅ 너비 맞춘 데이터프레임 출력
        st.dataframe(df, use_container_width=True)

        # ✅ 날짜 컬럼 타입 변환
        df['Date'] = pd.to_datetime(df['Date'])

        # ✅ 날짜 + Prc1별 막대그래프용 데이터 그룹핑
        chart_data = df.groupby(['Date', 'Prc1']).size().reset_index(name='Count')

        # ✅ Altair 막대그래프 생성
        chart = alt.Chart(chart_data).mark_bar().encode(
            x=alt.X('Date:T', title='날짜'),
            y=alt.Y('Count:Q', title='개수'),
            color='Prc1:N',
            tooltip=['Date', 'Prc1', 'Count']
        ).properties(
            height=400,
            title='📅 날짜별 Prc1 발생 건수'
        )

        # ✅ 그래프 출력 (너비 통일)
        st.altair_chart(chart, use_container_width=True)
        
        st.header("📂 엑셀 업로드로 데이터 추가")

uploaded_file = st.file_uploader("엑셀 파일 업로드 (.xlsx)", type=["xlsx"])

if uploaded_file:
    try:
        df_excel = pd.read_excel(uploaded_file)

        # 필수 컬럼
        required_columns = ['Date', 'Time', 'Prc1', 'Prc2', 'State', 'Value', 'Note1', 'Product']

        if all(col in df_excel.columns for col in required_columns):
            st.success("✅ 업로드된 엑셀 미리보기:")
            st.dataframe(df_excel, use_container_width=True)

            # 중복 제거 옵션
            remove_duplicates = st.checkbox("⚠️ 중복 (Date + Time + Prc1) 제거", value=True)

            if remove_duplicates:
                before = len(df_excel)
                df_excel = df_excel.drop_duplicates(subset=['Date', 'Time', 'Prc1'])
                after = len(df_excel)
                st.info(f"중복 제거: {before - after}건 삭제됨 (총 {after}건 남음)")

            # 업로드 실행 버튼
            if st.button("📝 DB에 추가"):
                try:
                    conn = get_connection()
                    cursor = conn.cursor()

                    inserted_count = 0
                    for _, row in df_excel.iterrows():
                        cursor.execute("""
                            INSERT INTO yujincast.dbo.M3_2025_TD
                            ([Date], [Time], [Prc1], [Prc2], [State], [Value], [Note1], [Product])
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, row['Date'], row['Time'], row['Prc1'], row['Prc2'],
                             row['State'], row['Value'], row['Note1'], row['Product'])
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

