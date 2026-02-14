import random
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ===== 游戏存储 =====
games = {}
MAX_PLAYERS = 8


# ===== 工具函数 =====
def mention(user_id, name="玩家"):
    return f"<a href='tg://user?id={user_id}'>{name}</a>"


def get_game(chat_id):
    return games.get(chat_id)


# ===== 指令一：创建游戏 =====
async def startgame(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user

    if chat_id in games:
        await update.message.reply_text("⚠️ 已经有游戏在进行中")
        return

    games[chat_id] = {
        "host": user.id,
        "players": {user.id: user.first_name}
    }

    await update.message.reply_text(
        f"🎮 游戏创建成功！\n主持人：{user.first_name}\n其他人发送 /join 加入（最多8人）"
    )


# ===== 指令二：加入 =====
async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user

    game = get_game(chat_id)
    if not game:
        await update.message.reply_text("❌ 当前没有游戏，请先 /startgame")
        return

    if user.id in game["players"]:
        await update.message.reply_text("⚠️ 你已经在游戏中了")
        return

    if len(game["players"]) >= MAX_PLAYERS:
        await update.message.reply_text("🚫 人数已满（最多8人）")
        return

    game["players"][user.id] = user.first_name

    await update.message.reply_text(f"✅ {user.first_name} 加入游戏")


# ===== 指令三：开始摇骰 =====
async def roll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user

    game = get_game(chat_id)
    if not game:
        return

    if user.id != game["host"]:
        await update.message.reply_text("❌ 只有主持人可以开始本轮")
        return

    results = {}
    for uid in game["players"]:
        results[uid] = random.randint(0, 100)

    max_score = max(results.values())
    min_score = min(results.values())

    winners = [uid for uid, v in results.items() if v == max_score]
    losers = [uid for uid, v in results.items() if v == min_score]

    text = "🎲 本轮骰子结果\n\n"

    for uid, score in results.items():
        name = game["players"][uid]
        text += f"{mention(uid, name)} ：{score}\n"

    text += "\n🏆 胜利者：\n"
    for uid in winners:
        text += f"{mention(uid, game['players'][uid])}\n"

    text += "\n💀 失败者：\n"
    for uid in losers:
        text += f"{mention(uid, game['players'][uid])}\n"

    await update.message.reply_text(text, parse_mode="HTML")


# ===== 指令四：踢人 =====
async def kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    game = get_game(chat_id)

    if not game:
        return

    if user.id != game["host"]:
        await update.message.reply_text("❌ 只有主持人可以踢人")
        return

    if not context.args:
        await update.message.reply_text("用法：/kick 用户ID")
        return

    target_id = int(context.args[0])

    if target_id not in game["players"]:
        await update.message.reply_text("❌ 此人不在游戏中")
        return

    name = game["players"].pop(target_id)

    await update.message.reply_text(f"🚫 {name} 已被踢出游戏")


# ===== 指令五：离开 =====
async def leave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    game = get_game(chat_id)

    if not game:
        return

    if user.id not in game["players"]:
        return

    if user.id == game["host"]:
        await update.message.reply_text("❌ 主持人不能直接离开，请先转移主持人或结束游戏")
        return

    game["players"].pop(user.id)

    await update.message.reply_text(f"👋 {user.first_name} 已退出游戏")


# ===== 指令六：结束游戏 =====
async def end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user

    game = get_game(chat_id)
    if not game:
        return

    if user.id != game["host"]:
        return

    del games[chat_id]

    await update.message.reply_text("🛑 游戏已结束")


# ===== 指令七：转移主持人 =====
async def transfer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    game = get_game(chat_id)

    if not game:
        return

    if user.id != game["host"]:
        await update.message.reply_text("❌ 只有主持人可以转移主持人")
        return

    if not context.args:
        await update.message.reply_text("用法：/transfer 用户ID")
        return

    target_id = int(context.args[0])

    if target_id not in game["players"]:
        await update.message.reply_text("❌ 目标不在游戏中")
        return

    game["host"] = target_id

    await update.message.reply_text(f"👑 主持人已转移给 {game['players'][target_id]}")


# ===== 启动 =====
def main():
    import os

TOKEN = os.environ.get("8486507377:AAFJAiCWGYziwbfIvtyihkV3oMEzGdmU26Q")

app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("startgame", startgame))
    app.add_handler(CommandHandler("join", join))
    app.add_handler(CommandHandler("roll", roll))
    app.add_handler(CommandHandler("kick", kick))
    app.add_handler(CommandHandler("leave", leave))
    app.add_handler(CommandHandler("end", end))
    app.add_handler(CommandHandler("transfer", transfer))

    print("Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()
