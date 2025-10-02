import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from time import time

# ====== 設定 ======
SHEET_KEY = "13AyMMtGUUw3T_vsGGgygG9VywbuBppSTN2PqFv-Tawo"  # あなたのシートID

# ====== 認証 ======
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
client = gspread.authorize(creds)
ss = client.open_by_key(SHEET_KEY)

st.title("📖 Health Diary - 閲覧・検索・修正（診断つき）")

# ====== タブ選択 ======
worksheets = ss.worksheets()
tab_names = [w.title for w in worksheets]
selected_tab = st.selectbox("操作するタブ（ワークシート）を選んでください", tab_names)
ws = ss.worksheet(selected_tab)

with st.expander("🔧 デバッグ情報"):
    st.write("サービスアカウント:", getattr(creds, "service_account_email", "(unknown)"))
    st.write("スプレッドシート名:", ss.title)
    st.write("現在のタブ:", ws.title)
    if st.button("▶ 書き込みテスト（F2に一時値を書いて読み戻し）"):
        tok = f"write-test-{int(time())}"
        ws.update_acell("F2", tok)
        back = ws.acell("F2").value
        st.success(f"書き込みOK: {tok} / 読み戻し: {back}")

# ====== データ取得（キャッシュ付） ======
@st.cache_data(ttl=300)
def load_df(tab_name: str) -> pd.DataFrame:
    w = ss.worksheet(tab_name)
    recs = w.get_all_records()  # 1行目ヘッダ前提
    df_ = pd.DataFrame(recs)
    # 欠け列を補完
    for c in ["id", "entry_date", "title", "content", "tag", "weather"]:
        if c not in df_.columns:
            df_[c] = ""
    return df_

# 初回ロード
df = load_df(selected_tab)

# 🔄 強制再読込
if st.button("🔄 再読込（キャッシュクリア）"):
    st.cache_data.clear()
    try:
        st.rerun()
    except Exception:
        st.experimental_rerun()

# ====== 検索（カンマ区切り AND） ======
st.subheader("🔍 検索")
q = st.text_input("キーワード（複数はコンマ区切り。例: 運動,晴れ,ejection fraction）")
if q:
    terms = [t.strip() for t in q.split(",") if t.strip()]
    view = df.copy()
    for t in terms:
        view = view[
            view["title"].str.contains(t, case=False, na=False) |
            view["content"].str.contains(t, case=False, na=False) |
            view["tag"].str.contains(t, case=False, na=False) |
            view["weather"].str.contains(t, case=False, na=False)
        ]
else:
    view = df

st.write(f"件数: {len(view)}")
st.dataframe(view, use_container_width=True)

# ====== 修正（entry_date指定） ======
st.subheader("✏️ 修正（entry_date 指定）")
target_date = st.text_input("修正したい日付 (YYYY-MM-DD)")

def gs_row_from_date(the_date: str) -> int | None:
    """entry_date から Google Sheets の行番号（A1の行）を返す。ヘッダ分 +2 """
    if df.empty:
        return None
    s = df.copy()
    s["entry_date"] = s["entry_date"].astype(str)
    hits = s.index[s["entry_date"] == str(the_date)].tolist()
    return (hits[0] + 2) if hits else None  # 0始まりindex→+1、さらにヘッダで+1

if st.button("行を読み込み"):
    row_index = gs_row_from_date(target_date)
    if not row_index:
        st.warning("指定日付の行が見つかりませんでした。")
    else:
        current = ws.row_values(row_index)
        current += [""] * max(0, 6 - len(current))
        st.info(f"👉 Google Sheets 行番号: {row_index} / 現在値: {current[:6]}")

        with st.form("edit_form"):
            entry_date = st.text_input("日付", current[1])
            title      = st.text_input("タイトル", current[2])
            content    = st.text_area("内容", current[3], height=160)
            tag        = st.text_input("タグ", current[4])
            weather    = st.text_input("天気", current[5])

            submitted = st.form_submit_button("保存")
            if submitted:
                # 範囲一括更新（B〜F列）… 改行/長文に強い
                ws.update(
                    f"B{row_index}:F{row_index}",
                    [[entry_date, title, content, tag, weather]],
                    value_input_option="USER_ENTERED",
                )

                # すぐにAPIで直接読み戻して反映チェック
                after = ws.row_values(row_index)
                after += [""] * max(0, 6 - len(after))
                st.success("更新しました。直後の読み戻し内容を表示します👇")
                st.write("🟡 更新後の行（API直読）:", after[:6])

                # 表示も更新（キャッシュクリア→再取得）
                st.cache_data.clear()
                df2 = load_df(selected_tab)
                st.write("🟢 DataFrame再読込の該当行：")
                st.dataframe(df2[df2["entry_date"].astype(str) == str(entry_date)])
