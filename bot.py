import os
import logging
from datetime import datetime
from dotenv import load_dotenv

import google.generativeai as genai
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

load_dotenv()

# ---------------- 配置區 ----------------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
    raise ValueError("缺少 TELEGRAM_BOT_TOKEN 或 GEMINI_API_KEY，請檢查 .env")

# Gemini 配置
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')  # 或 'gemini-2.5-flash-lite' 如果可用

# 系統 Prompt（固定 Markdown，每呼叫必帶）
SYSTEM_PROMPT = """
## 角色設定
你是專業的英文家教老師，專門幫用戶（alan）修正文法、單字、句子流暢度。
- 回應風格：親切、鼓勵、正面為主，例如「很好！只是這裡可以改成...」
- 處理流程：1. 先重述正確版句子。2. 解釋錯誤原因（簡單清楚）。3. 提供 1–2 個類似例句。4. 建議改進方向。
- 如果用戶說「給我新聞」「推薦文章」或類似：推薦一篇簡單英文新聞/短文摘要（主題自選或依用戶興趣），附 3–5 個重點單字 + 中文解釋。
- 語言：主要用英文回應，必要時用中文輔助解釋複雜文法。
- 其他：保持回應簡潔、有趣，避免太長。記住用戶是台灣人，偶爾可融入輕鬆台灣用語風格。
"""

# 歷史儲存：{chat_id: [{"role": "user"|"model", "content": str}, ...]}
conversation_history = {}

MAX_HISTORY_ROUNDS = 10      # 最多保留 10 輪
MAX_INPUT_TOKENS = 8000      # 超過就截斷

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------------- Helper Functions ----------------
def get_history(chat_id: int):
    return conversation_history.get(chat_id, [])

def update_history(chat_id: int, role: str, content: str):
    if chat_id not in conversation_history:
        conversation_history[chat_id] = []
    conversation_history[chat_id].append({"role": role, "content": content})
    # 限制長度
    if len(conversation_history[chat_id]) > MAX_HISTORY_ROUNDS * 2:
        conversation_history[chat_id] = conversation_history[chat_id][-MAX_HISTORY_ROUNDS * 2 :]

def clear_history(chat_id: int):
    if chat_id in conversation_history:
        del conversation_history[chat_id]

def build_contents(chat_id: int, new_message: str):
    history = get_history(chat_id)
    contents = [{"role": "model", "parts": [SYSTEM_PROMPT]}]  # 系統 prompt 放最前

    for msg in history:
        role = "user" if msg["role"] == "user" else "model"
        contents.append({"role": role, "parts": [msg["content"]]})

    contents.append({"role": "user", "parts": [new_message]})
    return contents

# ---------------- Telegram Handlers ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "嗨！我是你的英文家教 Bot～\n"
        "直接傳英文句子給我修正文法/單字，或說「給我新聞」要推薦學習文章。\n"
        "指令：\n/clear - 清空對話歷史\n/history - 看目前記憶的對話"
    )

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    clear_history(chat_id)
    await update.message.reply_text("對話歷史已清空！我們從頭開始吧～")

async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    hist = get_history(chat_id)
    if not hist:
        await update.message.reply_text("目前沒有對話歷史。")
        return

    text = "目前記憶的對話（最近部分）：\n\n"
    for i, msg in enumerate(hist[-10:], 1):
        prefix = "你：" if msg["role"] == "user" else "我："
        text += f"{i}. {prefix} {msg['content'][:100]}...\n"
    await update.message.reply_text(text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_msg = update.message.text.strip()

    if not user_msg:
        return

    # 建構 contents
    contents = build_contents(chat_id, user_msg)

    try:
        # 呼叫 Gemini
        response = model.generate_content(contents)

        reply_text = response.text.strip()

        # 更新歷史
        update_history(chat_id, "user", user_msg)
        update_history(chat_id, "model", reply_text)

        await update.message.reply_text(reply_text)

    except Exception as e:
        logger.error(f"Gemini 錯誤: {e}")
        await update.message.reply_text("抱歉，出了點問題... 請再試一次！")

# ---------------- Webhook Setup ----------------
def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("clear", clear))
    application.add_handler(CommandHandler("history", show_history))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Railway 給的 PORT 環境變數（預設 8080）
    port = int(os.environ.get("PORT", 8080))

    # Webhook 路徑（Railway 會給 https://your-app.up.railway.app/）
    # 注意：最後要加上你的 token 作為 path 的一部分（安全）
    webhook_path = f"/{TELEGRAM_TOKEN}"

    # 設定 webhook（部署後再執行一次 set_webhook）
    # 你可以先本地跑 polling 測試，部署後再設 webhook
    # application.run_polling()  # ← 開發時用這個，本地測試

    # 部署時用 webhook
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=webhook_path,
        webhook_url=f"https://{os.environ.get('RAILWAY_PUBLIC_DOMAIN', 'your-app.up.railway.app')}{webhook_path}",
    )

if __name__ == "__main__":
    main()