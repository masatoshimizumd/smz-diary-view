import streamlit as st
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

# ======================
# Google Sheets 認証
# ======================
scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
creds_dict = st.secrets["gcp_service_account"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(creds_dict), scope)
client = gspread.authorize(creds)

# シート指定
SHEET_KEY = "1RCNgsyViZNOmhWrTAm3xM7mLkj_mAuXjp4cVEfmUuqI"
sheet = client.open_by_key(SHEET_KEY).sheet1

st.title("📖 Health Diary - 閲覧・検索専用")

# ======================
# データ取得（キャッシュ付き）
# ======================
@st.cache_data(ttl=300)  # 5分キャッシュ
def load_data():
    records = sheet.get_all_records()
    return pd.DataFrame(records)

df = load_data()

# ======================
# 検索機能
# ======================
st.subheader("🔍 検索")

keyword = st.text_input("キーワード（タイトル・内容・タグ・天気を対象）")

if keyword:
    filtered = df[
        df["title"].str.contains(keyword, case=False, na=False) |
        df["content"].str.contains(keyword, case=False, na=False) |
        df["tag"].str.contains(keyword, case=False, na=False) |
        df["weather"].str.contains(keyword, case=False, na=False)
    ]
else:
    filtered = df

# ======================
# ページネーション
# ======================
page_size = 50
page = st.number_input("ページ番号", min_value=1, value=1)
start = (page-1)*page_size
end = start + page_size

st.write(f"全 {len(filtered)} 件中 {start+1} 〜 {min(end, len(filtered))} 件を表示")
st.dataframe(filtered.iloc[start:end])

# ======================
# 修正機能
# ======================
st.subheader("✏️ 修正")

row_number = st.number_input("修正する行番号（ヘッダー除く行数で指定）", min_value=2, step=1)

if st.button("行を読み込み"):
    row_values = sheet.row_values(row_number)
    if row_values:
        with st.form("edit_form"):
            entry_date = st.text_input("日付", row_values[1])
            title = st.text_input("タイトル", row_values[2])
            content = st.text_area("内容", row_values[3])
            tag = st.text_input("タグ", row_values[4])
            weather = st.text_input("天気", row_values[5])

            submitted = st.form_submit_button("保存")
            if submitted:
                sheet.update(f"A{row_number}:F{row_number}", [[row_values[0], entry_date, title, content, tag, weather]])
                st.success("更新しました！")
