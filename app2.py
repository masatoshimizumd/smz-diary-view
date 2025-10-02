import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from time import time

# ========= 設定 =========
SHEET_KEY = "13AyMMtGUUw3T_vsGGgygG9VywbuBppSTN2PqFv-Tawo"  # ←閲覧/入力で使う同じシートID
TARGET_WS_NAME = None  # 特定のタブ名で開くなら "Sheet1" など。未指定なら sheet1 を開く

# ========= 認証 =========
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
client = gspread.authorize(creds)

# ワークシート取得
ss = client.open_by_key(SHEET_KEY)
ws = ss.worksheet(TARGET_WS_NAME) if TARGET_WS_NAME else ss.sheet1

st.title("📖 Health Diary – 閲覧・検索・修正（デバッグ付き）")

# ========= デバッグ情報 =========
with st.expander("🔧 Advanced / デバッグ"):
    st.write("サービスアカウント:", getattr(creds, "service_account_email", "(unknown)"))
    st.write("操作中のスプレッドシート:", ss.title)
    st.write("操作中のワークシート(タブ):", ws.title)

    # 書き込みテスト（F2 に一時トークンを書き、読み戻す）
    if st.button("▶ 書き込みテスト（F2 に一時値を書いて読み戻し）"):
        token = f"write-test-{int(time())}"
        try:
            ws.update_acell("F2", token)  # USER_ENTERED デフォルト
            back = ws.acell("F2").value
            st.success(f"書き込み成功: {token} / 読み戻し: {back}")
        except Exception as e:
            st.error(f"書き込みテスト失敗: {e}")

# ========= データ取得 =========
@st.cache_data(ttl=300)
def load_df():
    # get_all_records は1行目をヘッダとして辞書化、2行目が index=0 に相当
    recs = ws.get_all_records()
    return pd.DataFrame(recs)

df = load_df()

# 欄が無い（空シート）でも落ちないように
expected_cols = ["id", "entry_date", "title", "content", "tag", "weather"]
for c in expected_cols:
    if c not in df.columns:
        df[c] = ""

# ========= 検索（カンマ区切り AND 検索）=========
st.subheader("🔍 検索")
query = st.text_input("キーワード（複数はコンマ区切り。例: 運動,晴れ,ejection fraction）")
if query:
    terms = [q.strip() for q in query.split(",") if q.strip()]
    filtered = df.copy()
    for t in terms:
        filtered = filtered[
            filtered["title"].str.contains(t, case=False, na=False) |
            filtered["content"].str.contains(t, case=False, na=False) |
            filtered["tag"].str.contains(t, case=False, na=False) |
            filtered["weather"].str.contains(t, case=False, na=False)
        ]
else:
    filtered = df

# ページネーション
page_size = 50
page = st.number_input("ページ番号", min_value=1, value=1)
start, end = (page - 1) * page_size, (page - 1) * page_size + page_size
st.write(f"全 {len(filtered)} 件中 {start+1} 〜 {min(end, len(filtered))} 件を表示")
st.dataframe(filtered.iloc[start:end], use_container_width=True)

# ========= 修正（entry_date で特定）=========
st.subheader("✏️ 修正（entry_date 指定）")
target_date = st.text_input("修正したい日付 (YYYY-MM-DD)")

def gs_row_from_date(the_date: str) -> int | None:
    """entry_date から Google Sheets の行番号(A1基準)を返す。ヘッダ行ぶん +2 を足す。"""
    if df.empty:
        return None
    s = df.copy()
    s["entry_date"] = s["entry_date"].astype(str)
    hits = s.index[s["entry_date"] == str(the_date)].tolist()
    return (hits[0] + 2) if hits else None  # +1で0->1行目、さらにヘッダぶん +1

if st.button("行を読み込み"):
    row_index = gs_row_from_date(target_date)
    if not row_index:
        st.warning("指定日付の行が見つかりませんでした。")
    else:
        current = ws.row_values(row_index)
        # 列が6未満でも安全に埋める
        current += [""] * max(0, 6 - len(current))

        st.info(f"👉 行番号: {row_index} / 現在値: {current[:6]}")
        with st.form("edit_form"):
            entry_date = st.text_input("日付", current[1])
            title      = st.text_input("タイトル", current[2])
            content    = st.text_area("内容", current[3], height=150)
            tag        = st.text_input("タグ", current[4])
            weather    = st.text_input("天気", current[5])

            mode = st.radio("更新方式", ["セル単位更新（確実）", "行一括更新（高速）"], index=0)
            submitted = st.form_submit_button("保存")

            if submitted:
                try:
                    if mode == "セル単位更新（確実）":
                        # B〜F を安全にセル単位更新
                        ws.update_cell(row_index, 2, entry_date)
                        ws.update_cell(row_index, 3, title)
                        ws.update_cell(row_index, 4, content)
                        ws.update_cell(row_index, 5, tag)
                        ws.update_cell(row_index, 6, weather)
                    else:
                        # 行一括（B〜F にまとめて）。id(A列)は触らない
                        ws.update(
                            f"B{row_index}:F{row_index}",
                            [[entry_date, title, content, tag, weather]],
                            value_input_option="USER_ENTERED",
                        )

                    st.success("更新しました。シートを再読込して確認します。")
                    st.cache_data.clear()
                    df = load_df()
                    st.dataframe(df[df["entry_date"].astype(str) == str(entry_date)])

                except Exception as e:
                    st.error(f"更新時エラー: {e}")
                    with st.expander("トレースを見る"):
                        st.exception(e)
