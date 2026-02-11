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
# ---------------- Telegram Handlers ----------------
# ... (前面的 start, clear, show_history, handle_message 保持不變) ...
'''
def main():
    # 1. 建立 Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # 2. 註冊處理器
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("clear", clear))
    application.add_handler(CommandHandler("history", show_history))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # 3. 啟動機器人 (Polling 模式)
    logger.info("機器人已啟動 (Polling)...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
'''
# ---------------- Webhook Setup ----------------
def main():
    # 1. 建立 Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # 2. 註冊處理器
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("clear", clear))
    application.add_handler(CommandHandler("history", show_history))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # 3. 取得 Railway 環境變數
    # Railway 會自動給予 PORT，預設通常是 8080
    PORT = int(os.environ.get("PORT", 8080))
    
    # 取得 Railway 分配給你的公網網址 (例如: your-bot.up.railway.app)
    # 如果你在 Railway 沒看到這個變數，請手動在 Railway 介面設定一個自定義域名或檢查 Public Domain
    DOMAIN = os.environ.get("RAILWAY_PUBLIC_DOMAIN")

    if DOMAIN:
        logger.info(f"啟動 Webhook 模式，監聽 Port: {PORT}, Domain: {DOMAIN}")
        
        # 啟動 Webhook
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TELEGRAM_TOKEN,       # Webhook 的後綴，用 token 增加安全性
            webhook_url=f"https://{DOMAIN}/{TELEGRAM_TOKEN}",
            allowed_updates=Update.ALL_TYPES
        )
    else:
        # 如果沒偵測到網址，自動退回 Polling 模式 (方便本地測試)
        logger.warning("未偵測到 RAILWAY_PUBLIC_DOMAIN，改用 Polling 模式...")
        application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
