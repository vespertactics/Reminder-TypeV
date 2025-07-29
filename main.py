import os
import discord
from discord.ext import commands
from datetime import datetime, timedelta, timezone
import asyncio

# インテント設定
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True

# Bot設定
bot = commands.Bot(command_prefix="!", intents=intents)

# チャンネルID
TARGET_CHANNEL_ID = 1398794128103309485  # リアクション対象チャンネル
REMIND_CHANNEL_ID = 1398794128103309485  # リマインド送信チャンネル（＝同じ）
LIST_CHANNEL_ID = 1398781319722565722    # 未リアクション者リスト出力チャンネル

# 設定
REACTION_EMOJI = "\u2705"  # ✅（メッセージ本文には使用しない）
ROLE_KEYWORD = "期生"
EXCLUDE_KEYWORD = "管理用"
MESSAGE_LOOKBACK_DAYS = 14

# テスト・本番切替
IS_TEST_MODE = os.getenv("TEST_MODE", "false").lower() == "true"
REMIND_AFTER = timedelta(minutes=3) if IS_TEST_MODE else timedelta(days=3)

async def run_remind():
    print("🔎 run_remind 開始")
    start_time = datetime.now()

    guild = bot.guilds[0] if bot.guilds else None
    if not guild:
        print("❌ ギルド取得失敗")
        return

    print(f"✅ 対象ギルド: {guild.name} ({guild.id})")

    target_channel = guild.get_channel(TARGET_CHANNEL_ID)
    remind_channel = guild.get_channel(REMIND_CHANNEL_ID)
    list_channel = guild.get_channel(LIST_CHANNEL_ID)

    if not target_channel or not remind_channel or not list_channel:
        print("❌ 指定したチャンネルが見つかりません")
        return

    now = datetime.now(timezone.utc)
    lookback_limit = now - timedelta(days=MESSAGE_LOOKBACK_DAYS)
    remind_limit = now - REMIND_AFTER

    print(f"📅 現在時刻: {now}")
    print(f"📅 チェック対象: {lookback_limit} 以降、{remind_limit} より前")

    # 対象ロール（「期生」を含む）
    target_roles = [r for r in guild.roles if ROLE_KEYWORD in r.name]
    print(f"🎯 対象ロール: {[r.name for r in target_roles]}")

    # 対象メンバー（管理用を含む表示名は除外）
    target_members = [
        m for m in guild.members
        if not m.bot and any(role.id in [r.id for r in target_roles] for role in m.roles)
        and EXCLUDE_KEYWORD not in m.display_name
    ]
    print(f"👥 対象メンバー数（管理用除外済）: {len(target_members)}")

    async for message in target_channel.history(limit=200, after=lookback_limit):
        print(f"📝 チェック中メッセージ: {message.id} ({message.created_at})")

        if message.created_at > remind_limit:
            print("⏭ スキップ（まだ期限前）")
            continue

        reacted_users = set()
        for reaction in message.reactions:
            if str(reaction.emoji) == REACTION_EMOJI:
                async for user in reaction.users():
                    reacted_users.add(user.id)

        not_reacted = [m for m in target_members if m.id not in reacted_users]

        if not not_reacted:
            print("✅ 対象外または全員確認済み")
            continue

        mentions = " ".join(m.mention for m in not_reacted)
        await remind_channel.send(
            f"⚠️ 以下のメンバーが [このメッセージ](https://discord.com/channels/{guild.id}/{TARGET_CHANNEL_ID}/{message.id}) に反応していません。\n{mentions}"
        )

        names = ", ".join(m.display_name for m in not_reacted)
        await list_channel.send(
            f"📝 未リアクション者リスト（メッセージID {message.id}）：{names}"
        )

        print(f"📣 リマインド送信済み: {names}")

    end_time = datetime.now()
    print(f"⏱️ 処理時間: {end_time - start_time}")

@bot.command()
@commands.has_permissions(administrator=True)
async def remind(ctx):
    await ctx.send("リマインド処理を開始します…")
    await run_remind()
    await ctx.send("リマインド完了しました！")

if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_TOKEN")
    GITHUB_ACTIONS_MODE = os.getenv("GITHUB_ACTIONS_MODE", "true").lower() == "true"

    if not TOKEN:
        print("❌ DISCORD_TOKEN が設定されていません")
    else:
        if GITHUB_ACTIONS_MODE:
            print("🚀 GitHub Actions モードで run_remind を実行")

            async def run_bot_once():
                async with bot:
                    await bot.login(TOKEN)
                    await bot.connect()
                    await run_remind()
                    await bot.close()

            asyncio.run(run_bot_once())
        else:
            print("🟢 常駐モードで起動")
            bot.run(TOKEN)
