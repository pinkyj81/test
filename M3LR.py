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
st.title("📊 리크(TD) 공정별 상태 조회")

# 조건 입력 UI
col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
with col1:
    start_date = st.date_input("시작 날짜", datetime(2025, 1, 1))
with col2:
    end_date = st.date_input("종료 날짜", datetime(2025, 12, 31))
with col3:
    product = st.selectbox("Product 선택", options=["", "M3LR", "M3TR"], index=0)
with col4:
    search_button = st.button("🔍 검색")

# 조건 검색 실행
if search_button:
    df = load_filtered_data(start_date, end_date, product)

    if df.empty:
        st.warning("조회된 데이터가 없습니다.")
    else:
        st.success(f"총 {len(df)}건이 조회되었습니다.")

        # ✅ 날짜에서 시간 제거
        df['Date'] = pd.to_datetime(df['Date']).dt.date

        # 그래프용 데이터
        chart_data = df.groupby(['Date', 'Prc1']).size().reset_index(name='Count')
        chart_data['Date'] = pd.to_datetime(chart_data['Date']).dt.date

        chart = alt.Chart(chart_data).mark_bar().encode(
            x=alt.X('Date:T', title='날짜'),
            y=alt.Y('Count:Q', title='개수'),
            color='Prc1:N',
            tooltip=['Date', 'Prc1', 'Count']
        ).properties(
            height=400,
            title='📅 날짜별 공정별 발생 건수'
        )

        # 🔼 그래프 출력
        st.altair_chart(chart, use_container_width=True)

        # 🔹 Prc1별 요약 테이블 출력
        prc1_pivot = df[df['Prc1'].isin(['10', '20', '30', '40'])].copy()
        prc1_table = (
            prc1_pivot.groupby('Date')['Prc1']
            .value_counts()
            .unstack(fill_value=0)
            .reindex(columns=['10', '20', '30', '40'], fill_value=0)
            .reset_index()
        )
        prc1_table['Date'] = pd.to_datetime(prc1_table['Date']).dt.date

        st.markdown("###### 📋 공정별 건수 요약")    
        st.dataframe(prc1_table, use_container_width=True)

        # 🔽 전체 데이터 출력
        st.markdown("###### 📄 상세 데이터")
        st.dataframe(df, use_container_width=True)

# 엑셀 또는 CSV 업로드 영역
st.markdown("###### 📂 엑셀 또는 CSV 업로드로 데이터 추가")

uploaded_file = st.file_uploader("엑셀(.xlsx) 또는 CSV(.csv) 파일 업로드", type=["xlsx", "csv"])

if uploaded_file:
    try:
        if uploaded_file.name.endswith(".xlsx"):
            df_excel = pd.read_excel(uploaded_file, engine='openpyxl')
        else:
            df_excel = pd.read_csv(uploaded_file)

        df_excel = df_excel.loc[:, ~df_excel.columns.isna()]
        df_excel.columns = [str(col).strip() for col in df_excel.columns]

        st.title("✅ 전체 업로드된 데이터 미리보기")
        st.dataframe(df_excel, use_container_width=True)

        # 🔧 오류 수정된 부분: 실제 존재하는 컬럼만 default로 설정
        all_columns = df_excel.columns.tolist()
        default_columns = ['Date', 'Time', 'Prc1', 'Prc2', 'State', 'Value', 'Note1', 'Product']
        valid_defaults = [col for col in default_columns if col in all_columns]

        selected_columns = st.multiselect(
            "📌 업로드할 열 선택", 
            options=all_columns,
            default=valid_defaults
        )
        df_excel = df_excel[selected_columns]

        if 'State' in df_excel.columns:
            states = df_excel['State'].dropna().unique().tolist()
            selected_states = st.multiselect("(⚙️ 포함할 상태(State))", options=states, default=states)
            df_excel = df_excel[df_excel['State'] == '(TD)']

        st.markdown("#### 🔍 필터링된 데이터 미리보기")
        st.dataframe(df_excel, use_container_width=True)

        remove_duplicates = st.checkbox("⚠️ 중복 (Date + Time + Prc1) 제거", value=True)
        if remove_duplicates and all(col in df_excel.columns for col in ['Date', 'Time', 'Prc1']):
            before = len(df_excel)
            df_excel = df_excel.drop_duplicates(subset=['Date', 'Time', 'Prc1'])
            after = len(df_excel)
            st.info(f"중복 제거됨: {before - after}건 삭제됨 (총 {after}건 남음)")

        if st.button("📝 DB에 추가"):
            required_columns = ['Date', 'Time', 'Prc1', 'Prc2', 'State', 'Value', 'Note1', 'Product']

            if all(col in df_excel.columns for col in required_columns):
                try:
                    conn = get_connection()
                    cursor = conn.cursor()

                    values_to_insert = [
                        tuple(row[col] if pd.notna(row[col]) else None for col in required_columns)
                        for _, row in df_excel.iterrows()
                    ]

                    cursor.executemany("""
                        INSERT INTO yujincast.dbo.M3_2025_TD
                        ([Date], [Time], [Prc1], [Prc2], [State], [Value], [Note1], [Product])
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, values_to_insert)

                    conn.commit()
                    conn.close()
                    st.success(f"🎉 {len(values_to_insert)}건이 성공적으로 업로드되었습니다.")
                except Exception as e:
                    st.error(f"❌ DB 저장 중 오류: {e}")
            else:
                st.error(f"❌ 필수 컬럼이 누락되었습니다: {required_columns}")

    except Exception as e:
        st.error(f"❌ 파일 처리 중 오류 발생: {e}")
