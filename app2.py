import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

SHEET_KEY = "13AyMMtGUUw3T_vsGGgygG9VywbuBppSTN2PqFv-Tawo"
scope = ["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]

creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
client = gspread.authorize(creds)
ws = client.open_by_key(SHEET_KEY).sheet1

# 書き込みテスト
ws.update_acell("F2", "write-test")
val = ws.acell("F2").value
st.write("👉 F2 cell value after update:", val)
