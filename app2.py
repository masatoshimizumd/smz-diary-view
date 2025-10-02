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

# シート指定（必要なら "Sheet1" → 実際のシート名に変更してください）
SHEET_KEY = "13AyMMtGUUw3T_vsGGgygG9VywbuBppSTN2PqFv-Tawo"
sheet = client.open_by_key(SHEET_KEY).sheet1

st.title("📖 Health Diary - 閲覧・検索・修正")

# ======================
# データ取得（キャッシュ付き）
# ======================
@st.cache_data(ttl=300)
def load_data():
    records = sheet.get_all_records()
    return pd.DataFrame(records)

df = load_data()


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
start = (page - 1) * page_size
end = start + page_size

st.write(f"全 {len(filtered)} 件中 {start+1} 〜 {min(end, len(filtered))} 件を表示")
st.dataframe(filtered.iloc[start:end])


# ======================
# 修正フォーム（関数化）
# ======================
def edit_row(row_index, row_values):
    """指定行をフォームで編集して保存"""
    with st.form("edit_form"):
        entry_date = st.text_input("日付", row_values[1])
        title = st.text_input("タイトル", row_values[2])
        content = st.text_area("内容", row_values[3])
        tag = st.text_input("タグ", row_values[4])
        weather = st.text_input("天気", row_values[5])

        submitted = st.form_submit_button("保存")
        if submitted:
            # セル単位で更新（確実に反映される）
            sheet.update_cell(row_index, 2, entry_date)   # entry_date
            sheet.update_cell(row_index, 3, title)        # title
            sheet.update_cell(row_index, 4, content)      # content
            sheet.update_cell(row_index, 5, tag)          # tag
            sheet.update_cell(row_index, 6, weather)      # weather

            st.success(f"{entry_date} のデータを更新しました！")

            # 保存直後にキャッシュクリア & 再読み込み
            st.cache_data.clear()
            df = load_data()
            st.dataframe(df[df["entry_date"] == entry_date])  # 更新後の行を確認用に表示


# ======================
# 修正機能本体
# ======================
st.subheader("✏️ 修正")

target_date = st.text_input("修正したい日付を入力 (YYYY-MM-DD)")

if st.button("行を読み込み"):
    df["entry_date"] = df["entry_date"].astype(str)

    if target_date in df["entry_date"].values:
        row_index = df.index[df["entry_date"] == str(target_date)][0] + 2
        row_values = sheet.row_values(row_index)

        st.write("👉 行番号:", row_index)
        st.write("👉 行の内容:", row_values)

        edit_row(row_index, row_values)
    else:
        st.warning("指定した日付が見つかりませんでした。")
