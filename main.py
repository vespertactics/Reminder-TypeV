import os
import discord
from discord.ext import commands
from datetime import datetime, timedelta, timezone

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
IS_TEST_MODE = os.getenv("TEST_MODE", "true").lower() == "true"
REMIND_AFTER = timedelta(minutes=3) if IS_TEST_MODE else timedelta(days=3)

async def run_remind():
    if not bot.guilds:
        print("❌ bot.guilds が空です（Botがギルドに参加していない？）")
        return

    guild = bot.guilds[0]
    print(f"✅ 対象ギルド: {guild.name} (ID: {guild.id})")

    target_channel = guild.get_channel(TARGET_CHANNEL_ID)
    remind_channel = guild.get_channel(REMIND_CHANNEL_ID)
    list_channel = guild.get_channel(LIST_CHANNEL_ID)

    if not target_channel or not remind_channel or not list_channel:
        print("❌ チャンネル取得に失敗しました")
        print(f"target_channel: {target_channel}")
        print(f"remind_channel: {remind_channel}")
        print(f"list_channel: {list_channel}")
        return

    now = datetime.now(timezone.utc)
    lookback_limit = now - timedelta(days=MESSAGE_LOOKBACK_DAYS)
    remind_limit = now - REMIND_AFTER

    print(f"🕒 現在時刻: {now.isoformat()}")
    print(f"🔍 対象メッセージ: {lookback_limit} 以降、{remind_limit} より前")

    target_roles = [r for r in guild.roles if ROLE_KEYWORD in r.name]
    print(f"🎯 対象ロール: {[r.name for r in target_roles]}")

    target_members = [
        m for m in guild.members
        if not m.bot and any(role.id in [r.id for r in target_roles] for role in m.roles)
    ]
    print(f"👥 対象メンバー数: {len(target_members)}人")

    async for message in target_channel.history(limit=200, after=lookback_limit):
        print(f"💬 メッセージID {message.id}: {message.created_at.isoformat()}")

        if message.created_at > remind_limit:
            print("⏩ スキップ（投稿が新しすぎる）")
            continue

        reacted_users = set()
        for reaction in message.reactions:
            print(f"   🔁 リアクション: {reaction.emoji} x{reaction.count}")
            if str(reaction.emoji) == REACTION_EMOJI:
                async for user in reaction.users():
                    reacted_users.add(user.id)
                print(f"   ✅ リアクション済: {len(reacted_users)}人")

        not_reacted = [m for m in target_members if m.id not in reacted_users]
        print(f"   🚫 未リアクション: {len(not_reacted)}人")

        if not not_reacted:
            print("✔️ 全員リアクション済、スキップ")
            continue

        mentions = " ".join(m.mention for m in not_reacted)
        await remind_channel.send(
            f":warning: 以下のメンバーが [このメッセージ](https://discord.com/channels/{guild.id}/{TARGET_CHANNEL_ID}/{message.id}) に ✅ を押していません。\n{mentions}"
        )

        names = ", ".join(m.display_name for m in not_reacted)
        await list_channel.send(
            f"未リアクション者リスト（メッセージID {message.id}）：{names}"
        )
        print("📢 リマインド送信完了")

@bot.event
async def on_ready():
    print(f"🔔 ログイン成功: {bot.user} (ID: {bot.user.id})")
    print(f"テストモード: {IS_TEST_MODE}, リマインド間隔: {REMIND_AFTER}")

    if os.getenv("GITHUB_ACTIONS_MODE") == "true":
        print("🤖 GitHub Actions モードで起動 → run_remind 実行")
        await run_remind()
        print("✅ 処理完了。Bot停止します")
        await bot.close()

@bot.command()
@commands.has_permissions(administrator=True)
async def remind(ctx):
    print("🛠️ !remind コマンド実行")
    await ctx.send("リマインド処理を開始します…")
    await run_remind()
    await ctx.send("リマインド完了しました！")

if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_TOKEN")
    if TOKEN:
        print("🔑 トークン取得済、Bot起動中…")
        bot.run(TOKEN)
    else:
        print("❌ DISCORD_TOKEN が設定されていません")
