import discord
import os
import sys
import asyncio
from discord.ext import commands
from datetime import datetime, timedelta, timezone

# 環境変数の読み込み
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# コマンドライン引数で自動モード判定
IS_AUTO_MODE = "--auto" in sys.argv

# タイムゾーン設定（JST）
JST = timezone(timedelta(hours=9))

# 対象チャンネルID（✅ リアクション付きメッセージ投稿チャンネル）
TARGET_CHANNEL_ID = 1398794128103309485
# リマインド送信先チャンネル
REMIND_CHANNEL_ID = 1398794128103309485
# 未リアクション者リスト投稿チャンネル
REPORT_CHANNEL_ID = 1398781319722565722

# 期生ロール名のキーワード
GEN_ROLE_KEYWORD = "期生"
# 除外するニックネームのキーワード
EXCLUDE_NICKNAME_KEYWORD = "管理用"

# 手動操作を許可するユーザーIDセット（必要に応じて変更）
ALLOWED_USERS = {1306911908929998899, 1039126356451131452}

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.reactions = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ ログイン成功: {bot.user.name}")
    if IS_AUTO_MODE:
        # 自動モードなら処理して即終了
        await run_reminder()
        await bot.close()
    else:
        # 手動モードなら常駐してコマンド待機
        print("🤖 手動モードで起動中。コマンドを待機しています。")

async def run_reminder():
    guild = bot.guilds[0]
    target_channel = guild.get_channel(TARGET_CHANNEL_ID)
    remind_channel = guild.get_channel(REMIND_CHANNEL_ID)
    report_channel = guild.get_channel(REPORT_CHANNEL_ID)

    now = datetime.now(JST)
    window = now - timedelta(weeks=2)
    delay = timedelta(minutes=3 if not IS_AUTO_MODE else 3 * 24 * 60)  # 手動は3分、自動は3日

    messages = []
    async for message in target_channel.history(limit=None, after=window):
        created_at_jst = message.created_at.astimezone(JST)
        if created_at_jst + delay > now:
            continue
        if any(reaction.emoji == "✅" for reaction in message.reactions):
            messages.append(message)

    if not messages:
        await report_channel.send("🔔 対象メッセージがありません。")
        return

    target_members = [
        m for m in guild.members
        if any(GEN_ROLE_KEYWORD in r.name for r in m.roles)
        and EXCLUDE_NICKNAME_KEYWORD not in (m.display_name or "")
        and not m.bot
    ]

    if not target_members:
        await report_channel.send("👥 対象ロールのメンバーが見つかりませんでした。")
        return

    reminded_users = set()

    for message in messages:
        for member in target_members:
            has_reacted = False
            for reaction in message.reactions:
                if reaction.emoji != "✅":
                    continue
                users = [user async for user in reaction.users()]
                if member in users:
                    has_reacted = True
                    break
            if not has_reacted:
                reminded_users.add(member)

    if not reminded_users:
        await report_channel.send("🎉 全員リアクション済みです！")
        return

    mentions = "\n".join(member.mention for member in reminded_users)
    await remind_channel.send(f"📣 リマインド送信対象:\n{mentions}")
    await report_channel.send(f"📝 未リアクション者一覧:\n{mentions}")

@bot.command()
async def remind(ctx):
    if ctx.author.id not in ALLOWED_USERS:
        await ctx.send("🚫 あなたにはこのコマンドを実行する権限がありません。")
        return
    await ctx.send("🔁 リマインド処理を開始します。")
    await run_reminder()
    await ctx.send("✅ リマインド完了。")

@bot.command()
async def shutdown(ctx):
    if ctx.author.id not in ALLOWED_USERS:
        await ctx.send("🚫 あなたにはこのコマンドを実行する権限がありません。")
        return
    await ctx.send("👋 Botをシャットダウンします。")
    await bot.close()

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("❌ DISCORD_TOKEN が設定されていません。")
        sys.exit(1)

    if IS_AUTO_MODE:
        asyncio.run(bot.start(DISCORD_TOKEN))
    else:
        bot.run(DISCORD_TOKEN)
