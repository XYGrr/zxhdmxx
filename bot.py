import os
import random
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode

# 日志
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# 存储每个群组的游戏状态
# 结构：{ chat_id: {'host': user_id, 'players': [user_id], 'rolls': {user_id: score} } }
games = {}

def get_mention(user):
    """返回可点击的提及文本"""
    if user.username:
        return f"@{user.username}"
    else:
        return f"[{user.full_name}](tg://user?id={user.id})"

# -------------------- 指令处理 --------------------
async def host(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user

    if chat_id in games and games[chat_id].get('host'):
        await update.message.reply_text("本群已有主持人，无法重复创建。")
        return

    games[chat_id] = {
        'host': user.id,
        'players': [user.id],
        'rolls': {}
    }
    await update.message.reply_text(
        f"游戏创建成功！主持人：{get_mention(user)}\n"
        f"其他玩家可使用 /join 加入游戏（最多8人）。"
    )

async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user

    if chat_id not in games:
        await update.message.reply_text("当前没有游戏，请先由主持人使用 /host 创建。")
        return

    game = games[chat_id]
    if user.id in game['players']:
        await update.message.reply_text("你已经在游戏中。")
        return
    if len(game['players']) >= 8:
        await update.message.reply_text("游戏人数已满（最多8人）。")
        return

    game['players'].append(user.id)
    await update.message.reply_text(f"{get_mention(user)} 加入游戏！当前人数：{len(game['players'])}/8")

async def roll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user

    if chat_id not in games:
        await update.message.reply_text("当前没有游戏。")
        return
    game = games[chat_id]
    if user.id != game['host']:
        await update.message.reply_text("只有主持人可以使用 /roll。")
        return
    if not game['players']:
        await update.message.reply_text("游戏中没有玩家。")
        return

    # 为每个玩家摇数
    rolls = {}
    for pid in game['players']:
        rolls[pid] = random.randint(0, 100)
    game['rolls'] = rolls

    # 生成结果文本
    msg_lines = ["摇数结果："]
    for pid, score in rolls.items():
        member = await context.bot.get_chat_member(chat_id, pid)
        msg_lines.append(f"{get_mention(member.user)} : {score}")

    max_score = max(rolls.values())
    min_score = min(rolls.values())
    winners = [pid for pid, s in rolls.items() if s == max_score]
    losers = [pid for pid, s in rolls.items() if s == min_score]

    msg_lines.append("")
    if winners:
        line = "胜利者："
        for pid in winners:
            member = await context.bot.get_chat_member(chat_id, pid)
            line += f"{get_mention(member.user)} "
        msg_lines.append(line)
    if losers:
        line = "失败者："
        for pid in losers:
            member = await context.bot.get_chat_member(chat_id, pid)
            line += f"{get_mention(member.user)} "
        msg_lines.append(line)

    await update.message.reply_text("\n".join(msg_lines), parse_mode=ParseMode.MARKDOWN)

async def remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user

    if chat_id not in games:
        await update.message.reply_text("当前没有游戏。")
        return
    game = games[chat_id]
    if user.id != game['host']:
        await update.message.reply_text("只有主持人可以使用 /remove。")
        return

    # 必须通过回复消息来移除
    if not update.message.reply_to_message:
        await update.message.reply_text("请回复要移除的用户的消息。")
        return

    target = update.message.reply_to_message.from_user
    if target.id == game['host']:
        await update.message.reply_text("不能移除主持人，请先转移身份。")
        return
    if target.id in game['players']:
        game['players'].remove(target.id)
        # 同时清除该玩家的摇数记录
        game['rolls'].pop(target.id, None)
        await update.message.reply_text(f"已移除 {get_mention(target)}。")
    else:
        await update.message.reply_text("该玩家不在游戏中。")

async def leave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user

    if chat_id not in games:
        await update.message.reply_text("当前没有游戏。")
        return
    game = games[chat_id]
    if user.id == game['host']:
        await update.message.reply_text("主持人不能自行离开，请先使用 /transfer 转移身份或使用 /end 结束游戏。")
        return
    if user.id in game['players']:
        game['players'].remove(user.id)
        game['rolls'].pop(user.id, None)
        await update.message.reply_text(f"{get_mention(user)} 已离开游戏。")
    else:
        await update.message.reply_text("你不在游戏中。")

async def end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user

    if chat_id not in games:
        await update.message.reply_text("当前没有游戏。")
        return
    game = games[chat_id]
    if user.id != game['host']:
        await update.message.reply_text("只有主持人可以使用 /end。")
        return

    del games[chat_id]
    await update.message.reply_text("游戏已结束。")

async def transfer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user

    if chat_id not in games:
        await update.message.reply_text("当前没有游戏。")
        return
    game = games[chat_id]
    if user.id != game['host']:
        await update.message.reply_text("只有主持人可以转移身份。")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("请回复要成为新主持人的用户的消息。")
        return

    new_host = update.message.reply_to_message.from_user
    if new_host.id == game['host']:
        await update.message.reply_text("不能转移给自己。")
        return
    if new_host.id not in game['players']:
        await update.message.reply_text("新主持人必须在游戏中。")
        return

    game['host'] = new_host.id
    await update.message.reply_text(f"主持人已转移给 {get_mention(new_host)}。")

# -------------------- 错误处理 --------------------
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Exception while handling an update:", exc_info=context.error)

# -------------------- 主函数 --------------------
def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        logger.error("请设置环境变量 BOT_TOKEN")
        return

    # 创建应用
    app = Application.builder().token(token).build()

    # 注册命令
    app.add_handler(CommandHandler("host", host))
    app.add_handler(CommandHandler("join", join))
    app.add_handler(CommandHandler("roll", roll))
    app.add_handler(CommandHandler("remove", remove))
    app.add_handler(CommandHandler("leave", leave))
    app.add_handler(CommandHandler("end", end))
    app.add_handler(CommandHandler("transfer", transfer))
    app.add_error_handler(error_handler)

    # 判断运行模式（Railway 会自动提供 PORT 环境变量）
    port = os.environ.get("PORT")
    if port:
        # Webhook 模式（推荐用于 Railway）
        webhook_url = os.environ.get("WEBHOOK_URL")
        if not webhook_url:
            # 尝试从 Railway 环境变量获取公共域名
            railway_domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN") or os.environ.get("RAILWAY_STATIC_URL")
            if railway_domain:
                webhook_url = f"https://{railway_domain}"
            else:
                logger.error("请设置环境变量 WEBHOOK_URL 或确保 Railway 提供了公共域名。")
                return

        # 最终 webhook 地址为：基础URL + /token
        full_webhook_url = f"{webhook_url}/{token}"
        app.run_webhook(
            listen="0.0.0.0",
            port=int(port),
            url_path=token,
            webhook_url=full_webhook_url
        )
    else:
        # 本地测试使用 polling
        app.run_polling()

if __name__ == "__main__":
    main()
