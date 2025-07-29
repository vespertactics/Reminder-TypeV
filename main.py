import os
import discord
from discord.ext import commands
from datetime import datetime, timedelta, timezone
import asyncio

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True

bot = commands.Bot(command_prefix="!", intents=intents)

TARGET_CHANNEL_ID = 1398794128103309485
REMIND_CHANNEL_ID = 1398794128103309485
LIST_CHANNEL_ID = 1398781319722565722

REACTION_EMOJI = "✅"
ROLE_KEYWORD = "期生"
MESSAGE_LOOKBACK_DAYS = 14

# テストモードを有効にすると3分でリマインド
IS_TEST_MODE = os.getenv("TEST_MODE", "false").lower() == "true"
REMIND_AFTER = timedelta(minutes=3) if IS_TEST_MODE else timedelta(days=3)

async def run_remind():
    print("🔎 run_remind 開始")
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

    target_roles = [r for r in guild.roles if ROLE_KEYWORD in r.name]
    print(f"🎯 対象ロール: {[r.name for r in target_roles]}")

    target_members = [
        m for m in guild.members
        if not m.bot and any(role.id in [r.id for r in target_roles] for role in m.roles)
    ]
    print(f"👥 対象メンバー数: {len(target_members)}")

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

        # 「管理用」がニックネームに含まれているメンバーを除外
        not_reacted = [
            m for m in target_members
            if m.id not in reacted_users and "管理用" not in m.display_name
        ]

        if not not_reacted:
            print("✅ 全員リアクション済み（または除外対象）")
            continue

        mentions = " ".join(m.mention for m in not_reacted)
        await remind_channel.send(
            f":warning: 以下のメンバーが [このメッセージ](https://discord.com/channels/{guild.id}/{TARGET_CHANNEL_ID}/{message.id}) に ✅ を押していません。\n{mentions}"
        )

        names = ", ".join(m.display_name for m in not_reacted)
        await list_channel.send(
            f"未リアクション者リスト（メッセージID {message.id}）：{names}"
        )

        print(f"📣 リマインド送信済み: {names}")

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
