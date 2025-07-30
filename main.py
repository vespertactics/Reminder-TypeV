import discord
import asyncio
import os
import argparse
from datetime import datetime, timedelta, timezone

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.messages = True
intents.message_content = True
intents.reactions = True

client = discord.Client(intents=intents)

# 固定設定（必要に応じて編集）
TARGET_CHANNEL_ID = 1398794128103309485  # ✅リアクション対象チャンネル
REPORT_CHANNEL_ID = 1398781319722565722  # リスト報告用チャンネル
REMIND_DAYS = 3
LOOKBACK_DAYS = 14
TARGET_ROLE_KEYWORDS = ["期生"]
EXCLUDED_NICKNAME_KEYWORD = "管理用"

# 引数処理
parser = argparse.ArgumentParser()
parser.add_argument("--auto", action="store_true")
args = parser.parse_args()

@client.event
async def on_ready():
    print(f"ログイン成功: {client.user}")
    await run_reminder()
    await client.close()

async def run_reminder():
    guild = client.guilds[0]
    target_channel = guild.get_channel(TARGET_CHANNEL_ID)
    report_channel = guild.get_channel(REPORT_CHANNEL_ID)

    now = datetime.now(timezone.utc)
    after_time = now - timedelta(days=LOOKBACK_DAYS)

    # リアクションチェック対象メッセージ収集
    messages = [
        msg async for msg in target_channel.history(after=after_time, limit=None)
        if (now - msg.created_at).days >= REMIND_DAYS and msg.reactions
    ]

    # 対象ロールメンバー収集
    target_members = [
        member for member in guild.members
        if any(role.name.endswith("期生") for role in member.roles)
        and not (member.nick and EXCLUDED_NICKNAME_KEYWORD in member.nick)
        and not member.bot
    ]

    # 結果格納
    reminders_sent = 0
    report_lines = []

    for msg in messages:
        # ✅リアクションオブジェクト取得
        reaction = discord.utils.get(msg.reactions, emoji="✅")
        if not reaction:
            continue

        # リアクションしたユーザー取得
        reactors = [user async for user in reaction.users() if not user.bot]
        non_reactors = [member for member in target_members if member not in reactors]

        if not non_reactors:
            continue

        # メッセージリンク
        msg_link = f"https://discord.com/channels/{guild.id}/{target_channel.id}/{msg.id}"

        # リマインド送信
        mention_text = "、".join(m.mention for m in non_reactors)
        await target_channel.send(
            f"{mention_text}\n以下のタスクに✅リアクションがまだのようです（投稿から3日以上経過）\n{msg_link}"
        )
        reminders_sent += 1

        # 報告用出力
        name_list = ", ".join(f"{m.display_name}" for m in non_reactors)
        report_lines.append(f"- [タスク]({msg_link}): {name_list}")

    # 報告送信
    if reminders_sent == 0:
        await report_channel.send("現時点でリマインド対象者はいません。")
    else:
        header = f"✅ リマインドを送信したタスク一覧（{now.astimezone(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M')} JST）"
        await report_channel.send(f"{header}\n" + "\n".join(report_lines))

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("DISCORD_TOKENが設定されていません。")
        exit(1)
    client.run(token)
