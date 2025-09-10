import pandas as pd
import os

def get_top_10_whales(file_path):
    """
    從指定的 Excel 檔案中讀取數據，並回傳持有量最大的前 10 名鯨魚。

    Args:
        file_path (str): Excel 檔案的路徑。

    Returns:
        pandas.DataFrame: 一個包含前 10 名鯨魚數據的 DataFrame，
                          如果檔案不存在或格式錯誤則回傳 None。
    """
    try:
        # 讀取 Excel 檔案。根據您的 CSV 預覽，第一行是描述，所以我們將第二行作為標題。
        df = pd.read_excel(file_path, header=1)

        # 假設欄位名稱為 'owner_address' 和 'total_sui'
        # 如果您的欄位名稱不同，請在此處修改
        address_col = 'owner_address'
        balance_col = 'total_sui'

        # 檢查欄位是否存在，如果不存在，則嘗試使用前兩欄
        if address_col not in df.columns or balance_col not in df.columns:
            if len(df.columns) >= 2:
                print(f"警告：找不到 '{address_col}' 或 '{balance_col}' 欄位，將使用前兩欄。")
                # 重新命名欄位以便後續處理
                df.columns = [address_col, balance_col] + df.columns[2:].tolist()
            else:
                print("錯誤：Excel 檔案的欄位不足。")
                return None
        
        # --- 【關鍵修復】---
        # 在排序前，強制將餘額欄位轉換為數字格式。
        # errors='coerce' 會將任何無法轉換的文字（例如標題）變成無效值 (NaN)。
        df[balance_col] = pd.to_numeric(df[balance_col], errors='coerce')

        # 移除包含無效值的資料列，確保數據乾淨。
        df.dropna(subset=[balance_col], inplace=True)

        # 根據 'total_sui' 欄位進行降序排序
        sorted_df = df.sort_values(by=balance_col, ascending=False)

        # 選取前 10 筆紀錄
        top_10 = sorted_df.head(10)

        return top_10

    except FileNotFoundError:
        print(f"錯誤：找不到檔案 '{file_path}'。請確認檔案路徑是否正確。")
        return None
    except Exception as e:
        print(f"讀取或處理檔案時發生錯誤：{e}")
        return None

# --- 主程式執行區 ---
if __name__ == "__main__":
    # 定義您的輸入和輸出檔案路徑
    input_file = "data/whale_sui.xlsx"
    output_file = "data/top10_sui_whale.xlsx"
    
    # 呼叫函數來取得前 10 大鯨魚
    top_whales_df = get_top_10_whales(input_file)
    
    # 如果成功取得數據，就將結果印出來並儲存成新檔案
    if top_whales_df is not None:
        print("--- SUI 持有量 Top 10 鯨魚 ---")
        print(top_whales_df.to_string(index=False))

        try:
            # 確保 data 資料夾存在
            output_dir = os.path.dirname(output_file)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            # 將 DataFrame 另存為新的 Excel 檔案
            # index=False 表示不要將 DataFrame 的索引寫入 Excel 中
            top_whales_df.to_excel(output_file, index=False)
            
            print(f"\n成功！已將前 10 大鯨魚數據另存為 '{output_file}'")

        except Exception as e:
            print(f"\n儲存檔案時發生錯誤：{e}")

