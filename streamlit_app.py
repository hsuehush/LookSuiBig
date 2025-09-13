import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import google.generativeai as genai
from PIL import Image
import json
from datetime import datetime
import random
import time
from pathlib import Path
import base64

# 提示：為了使用 SQL 查詢功能，您可能需要安裝一個額外的套件。
# 請在您的終端機中執行： pip install pandasql

# --- 頁面配置 (請務必放在所有 st 指令之前) ---
st.set_page_config(
    page_title="LookSuiBig",
    page_icon="images/eye_logo_transparent.png",
    layout="wide"
)

# 寫一個輔助函數來讀取圖片並轉換為 Base64，方便複用
def get_image_as_base64(path_str):
    path = Path(path_str)
    if not path.is_file():
        # 如果檔案不存在，可以回傳 None 或錯誤訊息
        return None
    with open(path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

# --- 自訂 CSS 美化 (與之前相同) ---
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

# --- Gemini API 設定 (與之前相同) ---
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
except (FileNotFoundError, KeyError):
    st.warning("尚未設定 Gemini API 金鑰。AI 功能將無法使用。")
    model = None

# --- AI 函數 (與之前相同) ---
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
    elif context_view == '資金流向追蹤':
        if data_df is not None and not data_df.empty:
            data_context = data_df.to_csv(index=False)
            context_prompt = f"""
            使用者正在查看 Top 1 鯨魚的資金流向追蹤圖表。請根據以下的數據 CSV，回答他的問題或提供見解，例如分析哪個協議是該鯨魚最主要的資金去向。

            --- 圖表數據 ---
            {data_context}
            --- 數據結束 ---
            """

    elif context_view == '投資組合分析':
        if data_df is not None and not data_df.empty:
            data_context = data_df.to_csv(index=False)
            context_prompt = f"""
            使用者正在查看 Top 1 鯨魚的資產投資組合分佈。請根據以下的數據 CSV，回答他的問題或提供見解，例如分析該鯨魚的資產主要集中在哪種類型的投資，以及哪個協議佔比最高。

            --- 投資組合數據 ---
            {data_context}
            --- 數據結束 ---
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

# --- 數據載入 (與之前相同) ---
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

# NEW: 新增生成資金流向模擬數據的函數
@st.cache_data
def generate_fund_flow_data():
    """生成 SUI 資金流向的模擬數據"""
    data = [
        {'source': 'Top 1 Whale Wallet', 'target': 'Binance CEX', 'value': 1200000, 'label': '轉至交易所'},
        {'source': 'Top 1 Whale Wallet', 'target': 'Scallop Finance', 'value': 850000, 'label': 'DeFi 質押'},
        {'source': 'Top 1 Whale Wallet', 'target': 'Cetus Exchange', 'value': 650000, 'label': '提供流動性'},
        {'source': 'Top 1 Whale Wallet', 'target': 'Other Wallets', 'value': 300000, 'label': '內部轉帳'},
        {'source': 'Binance CEX', 'target': 'Top 1 Whale Wallet', 'value': 400000, 'label': '從交易所提幣'},
        {'source': 'Scallop Finance', 'target': 'Top 1 Whale Wallet', 'value': 150000, 'label': '領取質押獎勵'},
    ]
    return pd.DataFrame(data)

# 新增生成投資組合模擬數據的函數
@st.cache_data
def generate_portfolio_data():
    """生成單一地址的投資組合模擬數據"""
    data = {
        'category': [
            '錢包餘額', '錢包餘額', '已質押資產', '已質押資產', '借貸市場存款', '流動性池代幣'
        ],
        'protocol': [
            'SUI', 'USDC', 'Scallop Finance', 'Cetus Exchange', 'Navi Protocol', 'Cetus (SUI-USDC)'
        ],
        'asset': [
            'SUI', 'USDC', 'SUI', 'CETUS', 'USDC', 'SUI-USDC-LP'
        ],
        'value_usd': [
            5000000, 1500000, 3500000, 500000, 2000000, 1200000
        ]
    }
    return pd.DataFrame(data)

# --- 狀態管理 ---
def init_session_state():
    if 'page' not in st.session_state:
        st.session_state.page = '主頁'
    if 'selected_whale' not in st.session_state:
        st.session_state.selected_whale = None
    if 'selected_project' not in st.session_state:
        st.session_state.selected_project = None
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'detail_view' not in st.session_state:
        st.session_state.detail_view = '圖表分析'
    if 'show_ai_assistant' not in st.session_state:
        st.session_state.show_ai_assistant = True

    if 'user' not in st.session_state:
        st.session_state.user = {
            "logged_in": False,
            "name": "訪客",
            "saved_queries": []
        }

# --- 導航函數 ---
def navigate_to(page_name, whale_address=None, project_name=None):
    st.session_state.page = page_name
    st.session_state.selected_whale = whale_address
    st.session_state.selected_project = project_name
    st.session_state.messages = []
    st.session_state.detail_view = '圖表分析'
    st.session_state.show_ai_assistant = True

# --- 渲染函數 (UI 模組化) ---
def render_header():
    # 獲取 Base64 編碼後的圖片
    img_base64 = get_image_as_base64("images/eye_logo_transparent.png")
    
    # 使用 f-string 組合出完整的 <img> HTML 標籤
    # 加上一些 style 來控制圖片大小和對齊方式
    img_html = f'<img src="data:image/png;base64,{img_base64}" style="height: 40px; margin-right: 10px; vertical-align: middle;">'
    
    st.markdown(f"""
    <div class="app-header">
        <h1>{img_html}LookSuiBig 鯨魚儀表板</h1>
        <p>一個追蹤 SUI 生態中頂級鯨魚活動的分析工具</p>
    </div>
    """, unsafe_allow_html=True)

# MODIFIED: 全新的側邊欄，整合了所有導覽和用戶中心
def render_sidebar():
    with st.sidebar:
        st.title("導覽中心")
        st.markdown("---")

        with st.expander("🐳 鯨魚監控", expanded=True):
            if st.button("SUI 鯨魚列表", use_container_width=True):
                navigate_to('主頁')
                st.rerun()
            if st.button("穩定幣鯨魚列表", use_container_width=True):
                navigate_to('穩定幣鯨魚')
                st.rerun()

        with st.expander("📊 項目監控", expanded=True):
            if st.button("Scallop", use_container_width=True):
                navigate_to('項目監控', project_name='Scallop')
                st.rerun()
            st.caption("...(待補完)")

        if st.session_state.user['logged_in']:
            if st.button("👤 個人檔案", use_container_width=True):
                navigate_to('個人檔案')
                st.rerun()

        st.markdown("---")
        st.title("👤 用戶中心")
        
        if st.session_state.user['logged_in']:
            st.success(f"歡迎回來, {st.session_state.user['name']}!")
            if st.button("登出", use_container_width=True):
                st.session_state.user = {"logged_in": False, "name": "訪客", "saved_queries": []}
                navigate_to('主頁')
                st.toast("您已成功登出！")
                st.rerun()
        else:
            st.info("登入以使用個人化功能。")
            with st.form("login_form"):
                email = st.text_input("電子郵件 (模擬)", "sui.master@example.com")
                if st.form_submit_button("登入", use_container_width=True, type="primary"):
                    st.session_state.user['logged_in'] = True
                    st.session_state.user['name'] = email.split('@')[0]
                    st.session_state.user['saved_queries'] = []
                    st.toast("登入成功！", icon="🎉")
                    st.rerun()

def render_main_page(top10_whales, top1_transactions):
    # ... 函數內容與之前相同 ...
    st.header("SUI 持有量 Top 10 鯨魚")
    st.write("點擊鯨魚卡片旁的「查看詳情」按鈕，分析其每日 SUI 持有量變化。")
    if top10_whales is not None:
        for index, row in top10_whales.iterrows():
            with st.container(border=True):
                whale_address = row.iloc[0]
                total_sui = float(row.iloc[1])
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

# MODIFIED: 在詳細資訊頁加入資金流向追蹤功能
def render_detail_page(top1_balance, top1_transactions):
    main_col, ai_col = st.columns([2, 1])
    with main_col:
        with st.container(border=True):
            st.header("📈 Top 1 鯨魚交易分析")
            st.markdown(f"**地址**: `{st.session_state.selected_whale}`")
            
            # MODIFIED: 調整欄位以容納新按鈕
            btn_col1, btn_col2, btn_col3, btn_col4, btn_col5 = st.columns([1, 1.2, 1.2, 1.5, 1.5])
            with btn_col1:
                if st.button("← 返回", use_container_width=True): # 簡化按鈕文字
                    navigate_to('主頁')
            with btn_col2:
                btn_type = "primary" if st.session_state.detail_view == '圖表分析' else "secondary"
                if st.button("📊 圖表分析", use_container_width=True, type=btn_type):
                    st.session_state.detail_view = '圖表分析'
                    st.rerun()
            with btn_col3:
                btn_type = "primary" if st.session_state.detail_view == 'SQL查詢' else "secondary"
                if st.button("🔍 SQL 查詢", use_container_width=True, type=btn_type):
                    st.session_state.detail_view = 'SQL查詢'
                    st.rerun()
            with btn_col4:
                btn_type = "primary" if st.session_state.detail_view == '資金流向追蹤' else "secondary"
                if st.button("🌊 資金流向", use_container_width=True, type=btn_type): # 簡化按鈕文字
                    st.session_state.detail_view = '資金流向追蹤'
                    st.rerun()
            # NEW: 新增投資組合分析按鈕
            with btn_col5:
                btn_type = "primary" if st.session_state.detail_view == '投資組合分析' else "secondary"
                if st.button("💰 投資組合", use_container_width=True, type=btn_type): # 簡化按鈕文字
                    st.session_state.detail_view = '投資組合分析'
                    st.rerun()

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
                
                # MODIFIED: 將按鈕放在同一行，並加入儲存功能
                btn1_col, btn2_col, _ = st.columns([1, 1, 3])
                
                with btn1_col:
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
                
                with btn2_col:
                    if st.session_state.user['logged_in']:
                        if st.button("💾 儲存查詢", use_container_width=True):
                            if query.strip():
                                if any(q['query'] == query for q in st.session_state.user['saved_queries']):
                                    st.toast("此查詢已儲存。")
                                else:
                                    new_query_obj = {
                                        "id": f"query_{int(time.time() * 1000)}",
                                        "query": query,
                                        "notes": ""
                                    }
                                    st.session_state.user['saved_queries'].append(new_query_obj)
                                    st.success("查詢已成功儲存！")
                                    st.balloons()
                            else:
                                st.warning("查詢內容不能為空。")
                    else:
                        st.button("💾 儲存查詢", use_container_width=True, disabled=True, help="請先登入才能儲存")
            
            elif st.session_state.detail_view == '資金流向追蹤':
                st.subheader("🌊 資金流向分析 (最近 7 天模擬數據)")
                
                flow_df = generate_fund_flow_data()
                
                # 建立 Sankey 圖
                all_nodes = pd.concat([flow_df['source'], flow_df['target']]).unique()
                node_map = {node: i for i, node in enumerate(all_nodes)}
        
                fig = go.Figure(data=[go.Sankey(
                    textfont=dict(
                        color="black",  # 使用純黑色以獲得高對比度
                        size=14         # 加大字體尺寸
                    ),
                    node=dict(
                        pad=15,
                        thickness=15,
                        line=dict(color="black", width=0.3),
                        label=all_nodes,
                    ),
                    link=dict(
                        source=[node_map[s] for s in flow_df['source']],
                        target=[node_map[t] for t in flow_df['target']],
                        value=flow_df['value'],
                        label=flow_df['label']
                    ))])
                
                fig.update_layout(title_text="Top 1 鯨魚錢包資金流動圖", font_size=12)
                st.plotly_chart(fig, use_container_width=True)
                
                st.markdown("---")
                st.subheader("資金轉移明細")
                st.dataframe(flow_df, use_container_width=True, hide_index=True)

            elif st.session_state.detail_view == '投資組合分析':
                st.subheader("💰 資產分佈儀表板 (模擬數據)")
                
                portfolio_df = generate_portfolio_data()
                
                # 使用 Sunburst 圖表視覺化
                fig = px.sunburst(
                    portfolio_df,
                    path=['category', 'protocol'],
                    values='value_usd',
                    title='鯨魚資產分佈旭日圖 (按美元價值)',
                    hover_data=['asset']
                )
                fig.update_traces(textinfo="label+percent parent")
                st.plotly_chart(fig, use_container_width=True)
                
                st.markdown("---")
                st.subheader("資產分佈明細")
                st.dataframe(
                    portfolio_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "value_usd": st.column_config.NumberColumn(
                            "美元價值 (USD)",
                            format="$ %.2f"
                        ),
                        "category": "資產類型",
                        "protocol": "協議/主要資產",
                        "asset": "具體資產"
                    }
                )

    # AI 助理部分保持不變
    with ai_col:
        if st.session_state.show_ai_assistant:
            with st.container(border=True):
                if st.button("隱藏助理 →", use_container_width=True):
                    st.session_state.show_ai_assistant = False
                    st.rerun()

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
                            # 根據當前視圖選擇傳遞給 AI 的數據
                            if current_view == '圖表分析':
                                data_for_ai = top1_balance
                            elif current_view == 'SQL查詢':
                                data_for_ai = top1_transactions
                            elif current_view == '資金流向追蹤':
                                data_for_ai = generate_fund_flow_data()
                            elif current_view == '投資組合分析':
                                data_for_ai = generate_portfolio_data()
                            else:
                                data_for_ai = None
                            
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

# NEW: 全新的個人檔案頁面渲染函數
def render_profile_page():
    st.header(f"👤 {st.session_state.user['name']} 的個人檔案")

    st.subheader("📝 新增查詢")
    with st.form("new_query_form", clear_on_submit=True):
        new_query_text = st.text_area("SQL 查詢語句")
        new_notes_text = st.text_area("備註 (選填)")
        if st.form_submit_button("新增", type="primary"):
            if new_query_text.strip():
                new_query_obj = {
                    "id": f"query_{int(time.time() * 1000)}",
                    "query": new_query_text,
                    "notes": new_notes_text
                }
                st.session_state.user['saved_queries'].insert(0, new_query_obj)
                st.success("查詢已新增！")
                st.rerun()
            else:
                st.warning("查詢語句不能為空。")

    st.markdown("---")
    st.subheader("💾 已儲存的 SQL 查詢")

    if not st.session_state.user['saved_queries']:
        st.info("您尚未儲存任何查詢。")
        return

    # 反向遍歷以在刪除時避免 index 錯誤
    for i in range(len(st.session_state.user['saved_queries']) - 1, -1, -1):
        saved_query = st.session_state.user['saved_queries'][i]
        with st.container(border=True):
            
            # 使用 expander 讓介面更整潔
            with st.expander(f"查詢 #{i+1}", expanded=True):
                # 編輯查詢語句
                edited_query = st.text_area(
                    "**SQL 查詢**",
                    value=saved_query['query'],
                    key=f"query_{saved_query['id']}",
                    height=150
                )
                
                # 編輯備註
                edited_notes = st.text_area(
                    "**備註**",
                    value=saved_query['notes'],
                    key=f"notes_{saved_query['id']}",
                    placeholder="為這個查詢新增一些筆記..."
                )

                btn_col1, btn_col2, _ = st.columns([1, 1, 4])
                
                # 儲存變更按鈕
                if btn_col1.button("儲存變更", key=f"save_{saved_query['id']}", use_container_width=True):
                    st.session_state.user['saved_queries'][i]['query'] = edited_query
                    st.session_state.user['saved_queries'][i]['notes'] = edited_notes
                    st.toast(f"查詢 #{i+1} 已更新！", icon="✅")
                    st.rerun()
                
                # 刪除查詢按鈕
                if btn_col2.button("🗑️ 刪除", key=f"delete_{saved_query['id']}", use_container_width=True, type="secondary"):
                    st.session_state.user['saved_queries'].pop(i)
                    st.toast(f"查詢 #{i+1} 已刪除。")
                    st.rerun()

# NEW: 為項目監控新增的佔位頁面
def render_project_page():
    project_name = st.session_state.get('selected_project', '未知項目')
    st.header(f"📊 {project_name} 項目監控")
    st.info("此功能正在開發中，敬請期待！")
    st.markdown("""
    未來這裡將會顯示：
    - **總鎖倉價值 (TVL)**
    - **年回報率 (APR / APY)**
    - **項目基本介紹**
    - **與該項目互動的巨鯨列表**
    """)

def main():
    init_session_state()
    render_sidebar()
    render_header()
    
    top10_whales, top1_balance, whales_usdt, top1_transactions = load_data()
    
    st.markdown("---")

    page = st.session_state.page
    if page == '主頁':
        # MODIFIED: 如果有選擇的鯨魚，則跳轉到詳細頁面，否則顯示列表
        if st.session_state.selected_whale:
             render_detail_page(top1_balance, top1_transactions)
        else:
             render_main_page(top10_whales, top1_transactions)
    elif page == '詳細資訊':
        render_detail_page(top1_balance, top1_transactions)
    elif page == '穩定幣鯨魚':
        render_stablecoin_page(whales_usdt)
    elif page == '個人檔案':
        if st.session_state.user['logged_in']:
            render_profile_page()
        else:
            st.warning("請先登入以查看您的個人檔案。")
            render_main_page(top10_whales, top1_transactions)
    elif page == '項目監控':
        render_project_page()
    else:
        render_main_page(top10_whales, top1_transactions)

if __name__ == "__main__":
    main()

