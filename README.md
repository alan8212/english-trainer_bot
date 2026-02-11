# English Tutor Telegram Bot

這是一個基於 **Google Gemini AI** 與 **python-telegram-bot** 框架開發的智慧英文家教機器人。它能夠自動修正用戶的英文文法、提供單字建議，並根據需求推薦英文新聞閱讀。

## 📋 功能特點

*   **文法修正**：自動重述正確句子，並解釋錯誤原因與提供例句。
*   **新聞推薦**：根據用戶指令，推薦英文新聞摘要與重點單字。
*   **對話記憶**：支援最近 10 輪的對話上下文記憶，讓教學更連貫。
*   **自動切換模式**：自動偵測環境變數，支援在 **Polling** 與 **Webhook** 模式間無縫切換。

## 🛠 必備環境

1.  **Python 3.10+**
2.  **Telegram Bot Token**：由 [@BotFather](https://t.me/BotFather) 取得。
3.  **Gemini API Key**：由 [Google AI Studio](https://aistudio.google.com/) 取得。

## ⚙️ 環境變數設定

請在 Railway 的 **Variables** 介面或本地 `.env` 檔案中設定以下變數：

| 變數名稱 | 說明 |
| :--- | :--- |
| `TELEGRAM_BOT_TOKEN` | 你的 Telegram 機器人 Token |
| `GEMINI_API_KEY` | 你的 Google Gemini API 金鑰 |

## 🚀 部署教學 (Railway)

### 1. 準備必要檔案
確保你的 Repository 包含以下檔案：
*   `bot.py`：主程式碼。
*   `requirements.txt`：必須包含 `python-telegram-bot[webhooks]`。
*   `Procfile`：內容為 `worker: python bot.py`。

### 2. 開啟 Webhook 支援
1.  進入 Railway 服務設定 (Settings)。
2.  在 **Networking** 區塊點擊 **Generate Domain**。
3.  產生網域後，程式會自動讀取 `RAILWAY_PUBLIC_DOMAIN` 並啟動 Webhook。

## 🎮 使用指令

*   `/start` - 啟動機器人。
*   `/clear` - 清除對話記憶。
*   `/history` - 顯示目前的對話紀錄摘要。
*   `直接輸入英文` - 機器人會針對你的句子進行教學與修正。

## 📦 依賴套件 (requirements.txt)

請確保你的 `requirements.txt` 內容如下，以避免 Webhook 啟動失敗：

```text
python-telegram-bot[webhooks]
google-generativeai
python-dotenv
