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

st.title("📖 Health Diary - 閲覧・検索・修正（タブ指定対応版）")

# ======================
# 利用可能なタブ一覧を表示
# ======================
worksheets = spreadsheet.worksheets()
tab_names = [w.title for w in worksheets]

selected_tab = st.selectbox("操作するタブを選んでください:", tab_names)
ws = spreadsheet.worksheet(selected_tab)

st.info(f"👉 現在操作中のタブ: {ws.title}")

# ======================
# データ取得
# ======================
@st.cache_data(ttl=300)
def load_df(tab_name):
    ws_tmp = spreadsheet.worksheet(tab_name)
    records = ws_tmp.get_all_records()
    return pd.DataFrame(records)

df = load_df(selected_tab)

# 欄が無い場合でも安全に列を揃える
expected_cols = ["id", "entry_date", "title", "content", "tag", "weather"]
for c in expected_cols:
    if c not in df.columns:
        df[c] = ""

# ======================
# 検索
# ======================
st.subheader("🔍 検索")

query = st.text_input("キーワード（複数はコンマ区切りで入力）")

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

st.dataframe(filtered, use_container_width=True)

# ======================
# 修正
# ======================
st.subheader("✏️ 修正")

target_date = st.text_input("修正したい日付 (YYYY-MM-DD)")

if st.button("行を読み込み"):
    df["entry_date"] = df["entry_date"].astype(str)

    if target_date in df["entry_date"].values:
        row_index = df.index[df["entry_date"] == str(target_date)][0] + 2
        row_values = ws.row_values(row_index)
        row_values += [""] * max(0, 6 - len(row_values))  # 足りない列は空埋め

        st.write("👉 Google Sheets 上の行番号:", row_index)
        st.write("👉 現在の行の値:", row_values[:6])

        with st.form("edit_form"):
            entry_date = st.text_input("日付", row_values[1])
            title = st.text_input("タイトル", row_values[2])
            content = st.text_area("内容", row_values[3], height=150)
            tag = st.text_input("タグ", row_values[4])
            weather = st.text_input("天気", row_values[5])

            submitted = st.form_submit_button("保存")
            if submitted:
                try:
                    # セル単位で更新（確実）
                    ws.update_cell(row_index, 2, entry_date)
                    ws.update_cell(row_index, 3, title)
                    ws.update_cell(row_index, 4, content)
                    ws.update_cell(row_index, 5, tag)
                    ws.update_cell(row_index, 6, weather)

                    st.success(f"{entry_date} のデータを更新しました ✅")

                    st.cache_data.clear()
                    df = load_df(selected_tab)
                    st.dataframe(df[df["entry_date"] == entry_date])

                except Exception as e:
                    st.error(f"更新エラー: {e}")
    else:
        st.warning("指定した日付が見つかりませんでした。")
