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

# スプレッドシート指定
SHEET_KEY = "13AyMMtGUUw3T_vsGGgygG9VywbuBppSTN2PqFv-Tawo"
spreadsheet = client.open_by_key(SHEET_KEY)
ws = spreadsheet.sheet1   # 必要に応じてタブ名を worksheet("シート1") に変更

st.title("📖 Health Diary - 閲覧・検索専用")

# ======================
# データ取得（キャッシュ）
# ======================
@st.cache_data(ttl=300)
def load_df():
    records = ws.get_all_records()
    return pd.DataFrame(records)

df = load_df()

# 欠けている列があっても揃える
expected_cols = ["id", "entry_date", "title", "content", "tag", "weather"]
for c in expected_cols:
    if c not in df.columns:
        df[c] = ""

# ======================
# 検索
# ======================
st.subheader("🔍 検索")

query = st.text_input("キーワード（複数はコンマ区切りで入力できます）")

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

# ページネーション（多い時用）
page_size = 50
page = st.number_input("ページ番号", min_value=1, value=1)
start = (page - 1) * page_size
end = start + page_size

st.write(f"全 {len(filtered)} 件中 {start+1} 〜 {min(end, len(filtered))} 件を表示")
st.dataframe(filtered.iloc[start:end], use_container_width=True)

# ======================
# 詳細ビュー（オプション）
# ======================
st.subheader("📄 詳細表示")
if not filtered.empty:
    idx = st.number_input("詳細を見たい行番号 (0開始)", min_value=0, max_value=len(filtered)-1, value=0)
    st.write(filtered.iloc[idx])

