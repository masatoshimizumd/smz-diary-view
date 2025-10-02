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
SHEET_KEY = "13AyMMtGUUw3T_vsGGgygG9VywbuBppSTN2PqFv-Tawo"
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

query = st.text_input("キーワード（複数はコンマ区切りで入力してください）")

if query:
    # コンマ区切りで分割 → 前後の空白を除去
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

target_date = st.text_input("修正したい日付を入力 (YYYY-MM-DD)")

if st.button("行を読み込み"):
    # データフレームの日付を文字列化（比較がズレないように）
    df["entry_date"] = df["entry_date"].astype(str)

    if target_date in df["entry_date"].values:
        # 行番号を取得（Google Sheets は1始まりなので +2 する）
        row_index = df.index[df["entry_date"] == str(target_date)][0] + 2
        row_values = sheet.row_values(row_index)

        # 👉 デバッグ出力（確認用）
        st.write("🔍 row_index:", row_index)
        st.write("🔍 row_values:", row_values)

        with st.form("edit_form"):
            entry_date = st.text_input("日付", row_values[1])
            title = st.text_input("タイトル", row_values[2])
            content = st.text_area("内容", row_values[3])
            tag = st.text_input("タグ", row_values[4])
            weather = st.text_input("天気", row_values[5])

            submitted = st.form_submit_button("保存")
            if submitted:
                # まずはここはコメントアウトして確認だけ
                # sheet.update_cell(row_index, 2, entry_date)
                # sheet.update_cell(row_index, 3, title)
                # sheet.update_cell(row_index, 4, content)
                # sheet.update_cell(row_index, 5, tag)
                # sheet.update_cell(row_index, 6, weather)

                st.success(f"{entry_date} のデータを更新しました！（まだデバッグ中）")
    else:
        st.warning("指定した日付が見つかりませんでした。")



