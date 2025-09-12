import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai
import json
from datetime import datetime
import random
# 提示：為了使用 SQL 查詢功能，您可能需要安裝一個額外的套件。
# 請在您的終端機中執行： pip install pandasql

# --- 頁面配置 (請務必放在所有 st 指令之前) ---
st.set_page_config(
    page_title="LookSuiBig - SUI 鯨魚儀表板",
    page_icon="🐳",
    layout="wide"
)

# --- 自訂 CSS 美化 (全新淺色主題) ---
st.markdown("""
<style>
/* 頂部導覽列樣式 */
.app-header {
    background-color: #ffffff; /* 使用乾淨的白色背景 */
    padding: 1rem 1.5rem;
    border-radius: 10px;
    margin-bottom: 20px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.04); /* 更柔和的陰影 */
    border: 1px solid #dee2e6; /* 淺灰色邊框 */
}
.app-header h1 {
    color: #212529; /* 深灰色主標題 */
    margin-bottom: 0.25rem;
}
.app-header p {
    color: #6c757d; /* 較淺的副標題顏色 */
    margin: 0;
}

/* 卡片容器樣式 */
[data-testid="stVerticalBlockBorderWrapper"] {
    background-color: #ffffff;
    border: 1px solid #dee2e6;
    border-radius: 10px;
    padding: 20px;
    margin-bottom: 15px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.04);
    transition: box-shadow 0.3s ease-in-out, border-color 0.3s ease-in-out;
}

[data-testid="stVerticalBlockBorderWrapper"]:hover {
    box-shadow: 0 8px 12px rgba(0, 0, 0, 0.06); /* 滑鼠懸停時陰影加深 */
    border-color: #007bff; /* 邊框變為主題色 */
}

/* 讓 Markdown 中的程式碼區塊更好看 */
code {
    background-color: #e9ecef; /* 淺灰色背景 */
    color: #495057; /* 深灰色文字 */
    padding: .2em .4em;
    margin: 0;
    font-size: 85%;
    border-radius: 6px;
}
</style>
""", unsafe_allow_html=True)

# --- Gemini API 設定 ---
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
except (FileNotFoundError, KeyError):
    st.warning("尚未設定 Gemini API 金鑰。AI 功能將無法使用。")
    model = None

# --- AI 函數 (全新升級版) ---
def get_gemini_response(prompt, data_df, context_view):
    """根據使用者當前的視圖，提供對應的 AI 協助。"""
    if not model:
        return "AI 模型未設定，請檢查您的 API 金鑰。"

    base_prompt = """
    你是一位專業、友善的加密貨幣數據分析助理。你的職責是根據使用者當前的操作頁面，提供對應的幫助。
    """
    
    context_prompt = ""
    # 根據視圖提供不同的上下文和指示
    if context_view == '圖表分析':
        if data_df is not None and not data_df.empty:
            data_context = data_df.to_csv(index=False)
            context_prompt = f"""
            使用者正在查看 SUI 鯨魚的每日持有量變化圖表。請根據以下的數據 CSV，回答他的問題，並提供簡潔、專業的見解。

            --- 圖表數據 ---
            {data_context}
            --- 數據結束 ---
            """
    elif context_view == 'SQL查詢':
        if data_df is not None and not data_df.empty:
            data_context = ", ".join(data_df.columns)
            context_prompt = f"""
            使用者正在 SQL 查詢工作區，希望能查詢名為 `top1_transactions` 的表格。
            - 如果使用者想知道如何查詢，請幫他生成一段符合需求的 SQL 程式碼。
            - 如果使用者詢問欄位意義，請根據欄位名稱進行解釋 (例如 `transaction_digest` 是交易哈希值)。
            - **絕對不要**自己執行查詢，僅提供 SQL 程式碼或解釋。

            可用的欄位如下:
            `{data_context}`
            """

    full_prompt = f"""
    {base_prompt}
    {context_prompt}

    使用者的問題是：
    "{prompt}"

    請用繁體中文回答。
    """
    
    try:
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        return f"呼叫 Gemini API 時發生錯誤：{e}"


# --- 數據載入 ---
@st.cache_data
def load_data():
    try:
        top10_whales_df = pd.read_excel("data/top10_sui_whale.xlsx")
        top1_balance_df = pd.read_excel("data/top1_sui_final.xlsx", header=1)
        whales_usdt_df = pd.read_excel("data/whales_usdt.xlsx", header=1)
        top1_transactions_df = pd.read_excel("data/whale_sui_top1_sui_transactions.xlsx", header=1)
        return top10_whales_df, top1_balance_df, whales_usdt_df, top1_transactions_df
    except FileNotFoundError as e:
        st.error(f"錯誤：找不到必要的 Excel 檔案 - {e}。")
        return None, None, None, None
    except Exception as e:
        st.error(f"讀取 Excel 檔案時發生錯誤：{e}。")
        return None, None, None, None

# --- 輔助函數 (Demo 數據生成) ---
def generate_demo_transaction_details():
    """為 Demo 生成豐富且逼真的交易細節"""
    scenarios = [
        {"類型": "質押", "協議/對象": "Scallop Finance", "詳情": f"📥 存入 {random.randint(100, 500) * 1000:,.0f} SUI 作為抵押品"},
        {"類型": "交換", "協議/對象": "Cetus Exchange", "詳情": f"🔄 交換 {random.randint(50, 250) * 1000:,.0f} SUI 為 {random.randint(60, 300) * 1000:,.0f} USDC"},
        {"類型": "轉出", "協議/對象": "0x...deadbeef", "詳情": f"📤 轉出 {random.randint(500, 1000) * 1000:,.0f} SUI"},
        {"類型": "申領", "協議/對象": "Scallop Finance", "詳情": f"✅ 申領 {random.randint(1, 10) * 100:,.0f} SUI 獎勵"},
        {"類型": "轉入", "協議/對象": "Binance", "詳情": f"📥 轉入 {random.randint(300, 800) * 1000:,.0f} SUI"},
    ]
    return random.choice(scenarios)

# --- 狀態管理 ---
def init_session_state():
    if 'page' not in st.session_state:
        st.session_state.page = '主頁'
    if 'selected_whale' not in st.session_state:
        st.session_state.selected_whale = None
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    # 新的狀態管理
    if 'detail_view' not in st.session_state:
        st.session_state.detail_view = '圖表分析'
    if 'show_ai_assistant' not in st.session_state:
        st.session_state.show_ai_assistant = True

# --- 導航函數 ---
def navigate_to(page_name, whale_address=None):
    st.session_state.page = page_name
    st.session_state.selected_whale = whale_address
    st.session_state.messages = []
    st.session_state.detail_view = '圖表分析'
    st.session_state.show_ai_assistant = True

# --- 渲染函數 (UI 模組化) ---
def render_header():
    st.markdown("""
    <div class="app-header">
        <h1>🐳 LookSuiBig 鯨魚儀表板</h1>
        <p>一個追蹤 SUI 生態中頂級鯨魚活動的分析工具</p>
    </div>
    """, unsafe_allow_html=True)

def render_main_page(top10_whales, top1_transactions):
    st.header("SUI 持有量 Top 10 鯨魚")
    st.write("點擊鯨魚卡片旁的「查看詳情」按鈕，分析其每日 SUI 持有量變化。")

    if top10_whales is not None and not top10_whales.empty:
        address_col = top10_whales.columns[0]
        balance_col = top10_whales.columns[1]
        for index, row in top10_whales.iterrows():
            with st.container(border=True):
                # ... (此處程式碼與前一版相同，故省略以保持簡潔)
                whale_address = row[address_col]
                try:
                    total_sui = float(row[balance_col])
                except (ValueError, TypeError):
                    total_sui = 0.0

                col_info, col_btn = st.columns([4, 1])
                with col_info:
                    st.markdown(f"#### **排名 {index + 1}**")
                    st.markdown(f"**地址**: `{whale_address}`")
                    st.metric(label="持有量 (SUI)", value=f"{total_sui:,.2f}")
                
                with col_btn:
                    st.write("")
                    st.write("")
                    if st.button("查看詳情", key=f"whale_{index}", use_container_width=True):
                        if index == 0:
                            navigate_to('詳細資訊', whale_address=whale_address)
                        else:
                            st.warning("目前僅提供 Top 1 鯨魚的詳細數據。")
                
                if index == 0 and top1_transactions is not None:
                    st.markdown("---")
                    st.markdown("##### 最近 5 筆交易活動 (Demo)")
                    top1_transactions['timestamp_ms'] = pd.to_numeric(top1_transactions['timestamp_ms'], errors='coerce')
                    latest_txs = top1_transactions.dropna(subset=['timestamp_ms']).sort_values('timestamp_ms', ascending=False).head(5)
                    display_txs = []
                    for _, tx_row in latest_txs.iterrows():
                        tx_time = datetime.fromtimestamp(tx_row['timestamp_ms'] / 1000).strftime('%Y-%m-%d %H:%M:%S')
                        gas_cost = (pd.to_numeric(tx_row.get('total_gas_cost', 0), errors='coerce') or 0) / 1e9
                        demo_details = generate_demo_transaction_details()
                        display_txs.append({
                            "時間": tx_time, "類型": demo_details["類型"], "協議/對象": demo_details["協議/對象"],
                            "詳情": demo_details["詳情"], "Gas費用 (SUI)": f"{gas_cost:.6f}"
                        })
                    if display_txs:
                        df_display = pd.DataFrame(display_txs)
                        st.dataframe(df_display, use_container_width=True, hide_index=True,
                            column_config={
                                "時間": st.column_config.TextColumn(width="medium"), "類型": st.column_config.TextColumn(width="small"),
                                "協議/對象": st.column_config.TextColumn(width="medium"), "詳情": st.column_config.TextColumn(width="large"),
                                "Gas費用 (SUI)": st.column_config.NumberColumn(format="%.6f", width="small"),
                            })
                elif index > 0:
                    st.info("暫無詳細交易資料")
    else:
        st.error("無法載入 `data/top10_sui_whale.xlsx`，請檢查檔案是否存在。")

def render_detail_page(top1_balance, top1_transactions):
    # --- 全新兩欄式佈局 ---
    main_col, ai_col = st.columns([2, 1])

    # --- 左側：主內容區 ---
    with main_col:
        with st.container(border=True):
            st.header("📈 Top 1 鯨魚交易分析")
            st.markdown(f"**地址**: `{st.session_state.selected_whale}`")

            # 導航與視圖切換按鈕
            btn_col1, btn_col2, btn_col3, _ = st.columns([1, 1.2, 1.2, 1.6])
            with btn_col1:
                if st.button("← 返回列表", use_container_width=True):
                    navigate_to('主頁')
            with btn_col2:
                btn_type = "primary" if st.session_state.detail_view == '圖表分析' else "secondary"
                if st.button("📊 圖表分析", use_container_width=True, type=btn_type):
                    st.session_state.detail_view = '圖表分析'
            with btn_col3:
                btn_type = "primary" if st.session_state.detail_view == 'SQL查詢' else "secondary"
                if st.button("🔍 SQL 查詢", use_container_width=True, type=btn_type):
                    st.session_state.detail_view = 'SQL查詢'
            
            # 根據選擇的視圖顯示內容
            if st.session_state.detail_view == '圖表分析':
                if top1_balance is not None and not top1_balance.empty:
                    df_sui = top1_balance.copy()
                    df_sui['net_sui_change_sui'] = pd.to_numeric(df_sui['net_sui_change'], errors='coerce') / 1_000_000_000
                    df_sui['balance_at_end_of_day_sui'] = pd.to_numeric(df_sui['balance_at_end_of_day'], errors='coerce') / 1_000_000_000
                    st.subheader("每日 SUI 總餘額變化 (單位: SUI)")
                    fig1 = px.line(df_sui, x='transaction_date', y='balance_at_end_of_day_sui', title='鯨魚 SUI 持有量歷史趨勢')
                    st.plotly_chart(fig1, use_container_width=True)
                    st.subheader("每日 SUI 淨流入/流出 (單位: SUI)")
                    fig2 = px.bar(df_sui, x='transaction_date', y='net_sui_change_sui', title='鯨魚每日 SUI 淨變化')
                    st.plotly_chart(fig2, use_container_width=True)
                else:
                    st.error("無法載入 `data/top1_sui_final.xlsx` 圖表數據。")

            elif st.session_state.detail_view == 'SQL查詢':
                st.subheader("📄 原始交易數據預覽 (前 10 筆)")
                if top1_transactions is not None and not top1_transactions.empty:
                    st.dataframe(top1_transactions.head(10), use_container_width=True)
                else:
                    st.warning("交易數據預覽無法載入。")
                st.markdown("---")
                st.subheader("🔍 SQL 查詢工作區")
                st.info("您可以使用標準 SQL 語法查詢上方名為 `top1_transactions` 的表格。")
                default_query = "SELECT \n    transaction_digest, timestamp_ms, sender, transaction_kind \nFROM \n    top1_transactions \nORDER BY \n    timestamp_ms DESC \nLIMIT 10;"
                query = st.text_area("輸入您的 SQL 查詢：", value=default_query, height=250, key="sql_query_input")
                if st.button("執行查詢", use_container_width=True, type="primary"):
                    if top1_transactions is not None:
                        try:
                            from pandasql import sqldf
                            result_df = sqldf(query, {'top1_transactions': top1_transactions})
                            st.subheader("✅ 查詢結果")
                            st.dataframe(result_df, use_container_width=True)
                        except Exception as e:
                            st.error(f"查詢時發生錯誤：\n{e}")
                    else:
                        st.error("交易數據尚未載入，無法執行查詢。")

    # --- 右側：AI 助理區 ---
    with ai_col:
        if st.session_state.show_ai_assistant:
            with st.container(border=True):
                if st.button("隱藏助理 →", use_container_width=True):
                    st.session_state.show_ai_assistant = False
                    st.rerun()
                
                # AI 聊天介面
                st.subheader("🤖 AI 分析助理")
                st.info("我可以幫您分析圖表、生成 SQL 或解釋交易。")
                for message in st.session_state.messages:
                    with st.chat_message(message["role"]):
                        st.markdown(message["content"])
                if prompt := st.chat_input("有什麼可以幫您的嗎？"):
                    st.session_state.messages.append({"role": "user", "content": prompt})
                    with st.chat_message("user"):
                        st.markdown(prompt)
                    with st.chat_message("assistant"):
                        with st.spinner("AI 正在思考中..."):
                            current_view = st.session_state.detail_view
                            data_for_ai = top1_balance if current_view == '圖表分析' else top1_transactions
                            response = get_gemini_response(prompt, data_for_ai, current_view)
                            st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
        else:
            if st.button("← 顯示 AI 助理", use_container_width=True):
                st.session_state.show_ai_assistant = True
                st.rerun()

def render_stablecoin_page(whales_usdt):
    st.header("💵 穩定幣鯨魚持有量列表")
    if whales_usdt is not None:
        st.dataframe(whales_usdt, use_container_width=True, hide_index=True)
    else:
        st.info("USDT 數據未載入。")

def main():
    render_header()
    init_session_state()
    top10_whales, top1_balance, whales_usdt, top1_transactions = load_data()
    selected_tab = st.radio( "選擇分析頁面", ["SUI 鯨魚分析", "穩定幣鯨魚列表"], key="main_tab", horizontal=True, label_visibility="collapsed")
    if selected_tab == "SUI 鯨魚分析" and st.session_state.page == '穩定幣鯨魚':
         navigate_to('主頁')
    elif selected_tab == "穩定幣鯨魚列表" and st.session_state.page != '穩定幣鯨魚':
         navigate_to('穩定幣鯨魚')
    st.markdown("---")
    if st.session_state.page == '主頁':
        render_main_page(top10_whales, top1_transactions)
    elif st.session_state.page == '詳細資訊':
        render_detail_page(top1_balance, top1_transactions)
    elif st.session_state.page == '穩定幣鯨魚':
        render_stablecoin_page(whales_usdt)

if __name__ == "__main__":
    main()

