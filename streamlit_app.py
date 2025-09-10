import streamlit as st
import pandas as pd
import plotly.express as px
# 引入 Google Gemini API 套件
import google.generativeai as genai

# --- 頁面配置 (請務必放在所有 st 指令之前) ---
st.set_page_config(page_title="LookSuiBig", layout="wide")

# --- Gemini API 設定 ---
# 提示：為了安全，請使用 Streamlit 的 secrets management 來儲存您的 API 金鑰
# 在您的專案中建立一個 .streamlit/secrets.toml 檔案，並寫入：
# GEMINI_API_KEY = "您的API金鑰"
try:
    # 從 secrets 中讀取 API 金鑰
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')
except (FileNotFoundError, KeyError):
    # 如果找不到 secrets，則顯示提示訊息
    st.warning("尚未設定 Gemini API 金鑰。AI 功能將無法使用。請在 `.streamlit/secrets.toml` 中設定您的金鑰。")
    model = None

# --- AI 函數 ---
def get_gemini_response(prompt, data_df):
    """
    處理與 Gemini API 的互動。
    它會將 DataFrame 轉換為 CSV 格式作為上下文，連同用戶的提問一起發送給 AI。
    """
    if not model:
        return "AI 模型未設定，請檢查您的 API 金鑰。"
    try:
        # 將數據轉換為 CSV 字串，讓 AI 能夠理解
        data_context = data_df.to_csv(index=False)
        
        # 建立一個更豐富的提示，包含上下文數據和用戶問題
        full_prompt = f"""
        你是一位專業的加密貨幣數據分析師。
        請根據以下的 SUI 鯨魚每日交易數據 CSV：

        --- 數據開始 ---
        {data_context}
        --- 數據結束 ---

        請根據上述數據，回答以下問題：
        "{prompt}"

        請用繁體中文回答，並提供簡潔、專業的見解。
        """
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        return f"呼叫 Gemini API 時發生錯誤：{e}"


# --- 數據載入 ---
@st.cache_data
def load_data():
    """
    從本地端讀取所有 Excel 檔案並回傳 DataFrame。
    """
    try:
        top10_whales_df = pd.read_excel("data/top10_sui_whale.xlsx")
        top1_balance_df = pd.read_excel("data/top1_sui_final.xlsx", header=1)
        whales_usdt_df = pd.read_excel("data/whales_usdt.xlsx", header=1)
        return top10_whales_df, top1_balance_df, whales_usdt_df
    except FileNotFoundError as e:
        st.error(f"錯誤：找不到必要的 Excel 檔案 - {e}。請確認 'data' 資料夾中包含 'top10_sui_whale.xlsx', 'top1_sui_final.xlsx', 和 'whales_usdt.xlsx'。")
        return None, None, None
    except Exception as e:
        st.error(f"讀取 Excel 檔案時發生錯誤：{e}。請檢查檔案格式是否正確。")
        return None, None, None


# 載入所有資料
top10_whales, top1_balance, whales_usdt = load_data()

# --- 狀態管理 ---
if 'page' not in st.session_state:
    st.session_state.page = '主頁'
if 'selected_whale' not in st.session_state:
    st.session_state.selected_whale = None
# 新增 AI 聊天介面的狀態
if 'show_ai_chat' not in st.session_state:
    st.session_state.show_ai_chat = False
if 'messages' not in st.session_state:
    st.session_state.messages = []

# --- 頁面導航函數 ---
def navigate_to(page_name, whale_address=None):
    st.session_state.page = page_name
    st.session_state.selected_whale = whale_address
    # 導航時重設 AI 聊天狀態
    st.session_state.show_ai_chat = False
    st.session_state.messages = []

# --- UI 介面渲染 ---
st.title("🐳 LookSuiBig 鯨魚儀表板")

# 建立分頁按鈕
col1, col2 = st.columns(2)
with col1:
    if st.button("SUI 鯨魚分析", use_container_width=True, type="primary" if st.session_state.page != '穩定幣鯨魚' else "secondary"):
        navigate_to('主頁')
with col2:
    if st.button("穩定幣鯨魚列表", use_container_width=True, type="primary" if st.session_state.page == '穩定幣鯨魚' else "secondary"):
        navigate_to('穩定幣鯨魚')

st.markdown("---")

# --- 頁面邏輯 ---

# 主頁：顯示 Top 10 SUI 鯨魚列表
if st.session_state.page == '主頁':
    st.header("SUI 持有量 Top 10 鯨魚")
    st.write("點擊鯨魚旁的「查看詳情」按鈕，分析其每日 SUI 持有量變化。")

    if top10_whales is not None and not top10_whales.empty:
        address_col = top10_whales.columns[0]
        balance_col = top10_whales.columns[1]

        for index, row in top10_whales.iterrows():
            whale_address = row[address_col]
            try:
                total_sui = float(row[balance_col])
            except (ValueError, TypeError):
                total_sui = 0.0

            col_addr, col_btn = st.columns([4, 1])
            with col_addr:
                st.markdown(f"**排名 {index + 1}**: `{whale_address}` - **持有量**: {total_sui:,.2f} SUI")
            with col_btn:
                if st.button(f"查看詳情", key=f"whale_{index}", use_container_width=True):
                    if index == 0:
                        navigate_to('詳細資訊', whale_address=whale_address)
                    else:
                        st.warning(f"目前僅提供 Top 1 鯨魚的詳細數據，您點擊的是排名 {index + 1} 的鯨魚。")
    else:
        st.error("無法載入 `data/top10_sui_whale.xlsx`，請檢查檔案是否存在。")

# 詳細資訊頁面：顯示 Top 1 鯨魚的分析圖表與 AI 聊天
elif st.session_state.page == '詳細資訊':
    st.header(f"Top 1 鯨魚交易分析")
    st.markdown(f"**地址**: `{st.session_state.selected_whale}`")

    # --- 按鈕區域 ---
    btn_col1, btn_col2, _ = st.columns([1.2, 1, 3])
    with btn_col1:
        if st.button("← 返回列表", use_container_width=True):
            navigate_to('主頁')

    with btn_col2:
        button_text = "🤖 詢問 AI" if not st.session_state.show_ai_chat else "📊 顯示所有圖表"
        button_type = "primary" if not st.session_state.show_ai_chat else "secondary"
        if st.button(button_text, use_container_width=True, type=button_type):
            st.session_state.show_ai_chat = not st.session_state.show_ai_chat
            if not st.session_state.show_ai_chat:
                 st.session_state.messages = []

    st.markdown("---")

    if top1_balance is not None and not top1_balance.empty:
        if 'net_sui_change' in top1_balance.columns and 'balance_at_end_of_day' in top1_balance.columns:
            df_sui = top1_balance.copy()
            df_sui['net_sui_change_sui'] = pd.to_numeric(df_sui['net_sui_change'], errors='coerce') / 1_000_000_000
            df_sui['balance_at_end_of_day_sui'] = pd.to_numeric(df_sui['balance_at_end_of_day'], errors='coerce') / 1_000_000_000
            
            # --- 條件式佈局 ---
            if st.session_state.show_ai_chat:
                # --- 左右分欄：左圖右 AI ---
                chart_col, ai_col = st.columns(2)

                with chart_col:
                    st.subheader("每日 SUI 總餘額變化 (單位: SUI)")
                    fig1 = px.line(
                        df_sui,
                        x='transaction_date',
                        y='balance_at_end_of_day_sui',
                        title='鯨魚 SUI 持有量歷史趨勢',
                        labels={'transaction_date': '日期', 'balance_at_end_of_day_sui': 'SUI 總餘額'}
                    )
                    st.plotly_chart(fig1, use_container_width=True)

                    st.subheader("每日 SUI 淨流入/流出 (單位: SUI)")
                    fig2 = px.bar(
                        df_sui,
                        x='transaction_date',
                        y='net_sui_change_sui',
                        title='鯨魚每日 SUI 淨變化',
                        labels={'transaction_date': '日期', 'net_sui_change_sui': 'SUI 淨變化量'}
                    )
                    st.plotly_chart(fig2, use_container_width=True)

                with ai_col:
                    st.subheader("🤖 AI 分析助理")
                    st.write("您可以根據左側的圖表數據，向 AI 提問。")

                    for message in st.session_state.messages:
                        with st.chat_message(message["role"]):
                            st.markdown(message["content"])

                    if prompt := st.chat_input("例如：分析一下持有量最高和最低點"):
                        st.session_state.messages.append({"role": "user", "content": prompt})
                        with st.chat_message("user"):
                            st.markdown(prompt)

                        with st.chat_message("assistant"):
                            with st.spinner("AI 正在分析數據..."):
                                response = get_gemini_response(prompt, df_sui[['transaction_date', 'balance_at_end_of_day_sui', 'net_sui_change_sui']])
                                st.markdown(response)
                        
                        st.session_state.messages.append({"role": "assistant", "content": response})

            else:
                # --- 預設佈局：顯示所有圖表 ---
                st.subheader("每日 SUI 總餘額變化 (單位: SUI)")
                fig1 = px.line(
                    df_sui,
                    x='transaction_date',
                    y='balance_at_end_of_day_sui',
                    title='鯨魚 SUI 持有量歷史趨勢',
                    labels={'transaction_date': '日期', 'balance_at_end_of_day_sui': 'SUI 總餘額'}
                )
                st.plotly_chart(fig1, use_container_width=True)

                st.subheader("每日 SUI 淨流入/流出 (單位: SUI)")
                fig2 = px.bar(
                    df_sui,
                    x='transaction_date',
                    y='net_sui_change_sui',
                    title='鯨魚每日 SUI 淨變化',
                    labels={'transaction_date': '日期', 'net_sui_change_sui': 'SUI 淨變化量'}
                )
                st.plotly_chart(fig2, use_container_width=True)
        else:
            st.error("`top1_sui_final.xlsx` 檔案中缺少必要的 `net_sui_change` 或 `balance_at_end_of_day` 欄位。")
    else:
        st.error("無法載入 `data/top1_sui_final.xlsx`，請檢查檔案是否存在。")

# 穩定幣鯨魚頁面
elif st.session_state.page == '穩定幣鯨魚':
    st.header("穩定幣鯨魚持有量列表")
    st.subheader("USDT 持有量")
    if whales_usdt is not None:
        st.dataframe(whales_usdt)
    else:
        st.info("USDT 數據未載入。")
