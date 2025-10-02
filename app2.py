import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

# ======================
# Google Sheets 認証
# ======================
scope = ["https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive"]

creds_dict = st.secrets["gcp_service_account"]
creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
client = gspread.authorize(creds)

# シート指定
SHEET_KEY = "13AyMMtGUUw3T_vsGGgygG9VywbuBppSTN2PqFv-Tawo"
ws = client.open_by_key(SHEET_KEY).sheet1

st.title("📖 Health Diary - 閲覧・検索・修正")

# ======================
# データ取得（キャッシュ付き）
# ======================
@st.cache_data(ttl=300)
def load_df():
    records = ws.get_all_records()
    return pd.DataFrame(records)

df = load_df()

# ======================
# 検索
# ======================
st.subheader("🔍 検索")

query = st.text_input("キーワード（複数はコンマ区切りで入力してください）")

if query:
    keywords = [q.strip() for q in query.split(",") if q.strip()]
    filtered = df.copy()
    for kw in keywords:
        filtered = filtered[
            filtered["title"].str.contains(kw, case=False, na=False) |
            filtered["content"].str.contains(kw, case=False, na=False) |
            filtered["tag"].str.contains(kw, case=False, na=False) |
            filtered["weather"].str.contains(kw, case=False, na=False)
        ]
else:
    filtered = df

# ページネーション
page_size = 50
page = st.number_input("ページ番号", min_value=1, value=1)
start, end = (page - 1) * page_size, (page - 1) * page_size + page_size
st.write(f"全 {len(filtered)} 件中 {start+1} 〜 {min(end, len(filtered))} 件を表示")
st.dataframe(filtered.iloc[start:end], use_container_width=True)

# ======================
# 修正フォーム
# ======================
st.subheader("✏️ 修正")

target_date = st.text_input("修正したい日付 (YYYY-MM-DD)")

if st.button("行を読み込み"):
    df["entry_date"] = df["entry_date"].astype(str)

    if target_date in df["entry_date"].values:
        # DataFrame index → Google Sheets row (必ず +2)
        row_index = df.index[df["entry_date"] == str(target_date)][0] + 2
        row_values = ws.row_values(row_index)

        st.write("👉 Google Sheets 上の行番号:", row_index)
        st.write("👉 現在の行の値:", row_values)

        with st.form("edit_form"):
            entry_date = st.text_input("日付", row_values[1])
            title = st.text_input("タイトル", row_values[2])
            content = st.text_area("内容", row_values[3])
            tag = st.text_input("タグ", row_values[4])
            weather = st.text_input("天気", row_values[5])

            submitted = st.form_submit_button("保存")
            if submitted:
                # セル単位更新（確実に反映）
                ws.update_cell(row_index, 2, entry_date)   # entry_date
                ws.update_cell(row_index, 3, title)        # title
                ws.update_cell(row_index, 4, content)      # content
                ws.update_cell(row_index, 5, tag)          # tag
                ws.update_cell(row_index, 6, weather)      # weather

                st.success(f"{entry_date} のデータを更新しました！")

                # キャッシュクリア & 再読み込み
                st.cache_data.clear()
                df = load_df()
                st.dataframe(df[df["entry_date"] == entry_date])
    else:
        st.warning("指定した日付が見つかりませんでした。")
