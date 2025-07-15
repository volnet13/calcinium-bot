import os
import math
import re
from telegram import Update, BotCommand
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

BOT_TOKEN = os.environ["BOT_TOKEN"]

def safe_eval(expr):
    allowed_names = {
        k: v for k, v in math.__dict__.items() if not k.startswith("__")
    }
    allowed_names.update({"abs": abs, "round": round, "pow": pow})
    return eval(expr, {"__builtins__": {}}, allowed_names)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Welcome! Send me a math expression to calculate.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🧠 *Calcinium Help*\n"
        "- Send math expressions like `2+2*5`, `pow(2,4)`\n",
        parse_mode="Markdown"
    )


async def handle_expression(update: Update, context: ContextTypes.DEFAULT_TYPE):
    expr = update.message.text.strip()

    if not any(char.isdigit() for char in expr):
        return

    math_keywords = [
        r"\+", "-", r"\*", "/", r"\*\*", "%", r"\^", r"", r"", ",",
        "sin", "cos", "tan", "sqrt", "log", "exp", "abs", "round", "pow", "pi", "e"
    ]
    if not any(re.search(kw, expr.lower()) for kw in math_keywords):
        return

    try:
        result = safe_eval(expr)
        await update.message.reply_text(
            f"🔒 Expression: `{expr}`\n🔑 Result: `{result}`",
            parse_mode="Markdown"
        )
    except:
        return

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("help", "Help info"),
    ]
    await app.bot.set_my_commands(commands)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_expression))

    print("🤖 Calcinium is running...")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.get_event_loop().run_until_complete(main())
