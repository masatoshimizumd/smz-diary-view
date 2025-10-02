# ----------------------------------------
# app2.py
# Health Diary App (ローカルテスト版)
# Google Sheets: id, entry_date, title, content, tag, weather
# ----------------------------------------

import streamlit as st
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

# ======================
# 1) Google Sheets 認証
# ======================
scope = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/drive"]

# --- Google Sheets 認証 (Secrets版) ---
creds_dict = st.secrets["gcp_service_account"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(creds_dict), scope)
client = gspread.authorize(creds)

sheet = client.open_by_key("1RCNgsyViZNOmhWrTAm3xM7mLkj_mAuXjp4cVEfmUuqI").sheet1


# ======================
# 2) データ読み込み関数
# ======================
@st.cache_data
def load_data():
    data = sheet.get_all_records()
    return pd.DataFrame(data)

df = load_data()

st.title("📖 Diary-view app")

# ======================
# 3) 新規入力フォーム
# ======================
st.subheader("📝 新規エントリー追加")

with st.form("new_entry"):
    entry_date = st.date_input("日付")
    title = st.text_input("タイトル")
    content = st.text_area("本文")
    tag = st.text_input("タグ")
    weather = st.text_input("天気")
    submitted = st.form_submit_button("追加")

    if submitted:
        # id はシートの次の行番号-1 として自動付与
        next_id = len(df) + 1
        sheet.append_row([next_id, str(entry_date), title, content, tag, weather])
        st.success("✅ 追加しました！")
        st.cache_data.clear()
        st.rerun()

# ======================
# 4) 検索機能
# ======================
st.subheader("🔍 検索")

keyword = st.text_input("キーワード検索（タイトル・本文・タグから）")

if keyword:
    mask = (
        df["title"].str.contains(keyword, case=False, na=False) |
        df["content"].str.contains(keyword, case=False, na=False) |
        df["tag"].str.contains(keyword, case=False, na=False)
    )
    result = df[mask]
    st.write(result)

# ======================
# 5) 修正機能（全カラム対応）
# ======================
st.subheader("✏️ 修正")

row_id = st.number_input("修正したい行番号 (2〜)", min_value=2, step=1)

if row_id <= len(df) + 1:
    try:
        # 各列の値を取得
        old_entry_date = sheet.cell(row_id, 2).value
        old_title = sheet.cell(row_id, 3).value
        old_content = sheet.cell(row_id, 4).value
        old_tag = sheet.cell(row_id, 5).value
        old_weather = sheet.cell(row_id, 6).value

        # 修正フォーム
        new_entry_date = st.text_input("日付", old_entry_date)
        new_title = st.text_input("タイトル修正", old_title)
        new_content = st.text_area("本文修正", old_content)
        new_tag = st.text_input("タグ修正", old_tag)
        new_weather = st.text_input("天気修正", old_weather)

        if st.button("保存"):
            sheet.update_cell(row_id, 2, new_entry_date)
            sheet.update_cell(row_id, 3, new_title)
            sheet.update_cell(row_id, 4, new_content)
            sheet.update_cell(row_id, 5, new_tag)
            sheet.update_cell(row_id, 6, new_weather)

            st.success(f"✅ {row_id} 行目を更新しました！")
            st.cache_data.clear()
            st.rerun()
    except Exception as e:
        st.error(f"エラー: {e}")

# ======================
# 6) 最新データ一覧
# ======================
st.subheader("📂 直近100件表示")
st.write(df.tail(100))

