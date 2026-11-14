import discord
import os
import sys
from discord.ext import commands
from datetime import datetime, timedelta, timezone

# 環境変数読み込み
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# モード判定（--auto なければテストモード）
IS_AUTO_MODE = "--auto" in sys.argv

# タイムゾーン（JST）
JST = timezone(timedelta(hours=9))

# チャンネルと除外キーワード定義
TARGET_CHANNEL_ID = 1398794128103309485
REMIND_CHANNEL_ID = 1398794128103309485
REPORT_CHANNEL_ID = 1398781319722565722
EXCLUDE_NICKNAME_KEYWORD = "管理用"

# ロール名キーワード定義
GEN_ROLE_KEYWORDS = ["期生", "推薦組"]  # ✅の対象
LIB_ROLE_KEYWORD = "図書委員会"        # ☑️の対象
NEW_ROLE_KEYWORD = "新人"              # 🌱の対象
VETERAN_ROLE_KEYWORD = "熟練"          # ⭕の対象

# Discord Bot設定
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.messages = True
intents.message_content = True
intents.reactions = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    # 自動実行モード
    if IS_AUTO_MODE:
        await run_reminder()
        await bot.close()


@bot.command()
@commands.has_permissions(administrator=True)
async def remind(ctx):
    await run_reminder()


async def run_reminder():
    # サーバー取得
    guild = bot.guilds[0]

    target_channel = guild.get_channel(TARGET_CHANNEL_ID)
    remind_channel = guild.get_channel(REMIND_CHANNEL_ID)
    report_channel = guild.get_channel(REPORT_CHANNEL_ID)

    # 現在時刻と対象期間
    now = datetime.now(JST)
    window = now - timedelta(days=8)

    # リマインド実行までの待機時間
    delay = timedelta(
        minutes=3 if not IS_AUTO_MODE else 2 * 24 * 60
    )

    # リアクションと対象ロールのキーワードマップ
    REACTION_ROLE_MAP = {
        "✅": GEN_ROLE_KEYWORDS,
        "☑️": LIB_ROLE_KEYWORD,
        "🌱": NEW_ROLE_KEYWORD,
        "⭕": VETERAN_ROLE_KEYWORD
    }

    # 対象メッセージ取得
    messages = []

    async for message in target_channel.history(
        limit=None,
        after=window
    ):
        created_at_jst = message.created_at.astimezone(JST)

        if created_at_jst + delay > now:
            continue

        if any(
            str(reaction.emoji) in REACTION_ROLE_MAP
            for reaction in message.reactions
        ):
            messages.append(message)

    # 対象メッセージがない場合
    if not messages:
        await report_channel.send(
            "🔔 現時点でリマインド対象者はいません。"
        )
        return

    # 未リアクション者を記録
    all_not_reacted = set()

    # メッセージごとに確認
    for message in messages:
        for reaction in message.reactions:
            emoji = str(reaction.emoji)

            if emoji not in REACTION_ROLE_MAP:
                continue

            role_keyword = REACTION_ROLE_MAP[emoji]

            # キーワードをリスト形式に統一
            role_keywords = (
                role_keyword
                if isinstance(role_keyword, list)
                else [role_keyword]
            )

            # 対象メンバーを絞り込み
            target_members = [
                m for m in guild.members
                if any(
                    keyword in role.name
                    for role in m.roles
                    for keyword in role_keywords
                )
                and EXCLUDE_NICKNAME_KEYWORD not in (
                    m.display_name or ""
                )
                and not m.bot
            ]

            # リアクション済みユーザー取得
            users = [
                user async for user in reaction.users()
            ]

            # 未リアクション者を抽出
            not_reacted = [
                m for m in target_members
                if m not in users
            ]

            # 未リアクション者がいる場合
            if not_reacted:
                mentions = "\n".join(
                    m.mention for m in not_reacted
                )

                await remind_channel.send(
                    f"⚠️ {emoji} 以下のメンバーが "
                    f"[このメッセージ]"
                    f"(https://discord.com/channels/"
                    f"{guild.id}/{TARGET_CHANNEL_ID}/{message.id}) "
                    f"に反応していません。\n{mentions}"
                )

                all_not_reacted.update(not_reacted)

    # 最終報告
    if not all_not_reacted:
        await report_channel.send(
            "🎉 全員リアクション済みです！"
        )
    else:
        mentions = "\n".join(
            member.mention
            for member in all_not_reacted
        )

        await report_channel.send(
            f"📝 未リアクション者一覧:\n{mentions}"
        )


# Bot起動
bot.run(DISCORD_TOKEN)
