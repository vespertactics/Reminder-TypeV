async def run_reminder():
    guild = bot.guilds[0]
    target_channel = guild.get_channel(TARGET_CHANNEL_ID)
    remind_channel = guild.get_channel(REMIND_CHANNEL_ID)
    report_channel = guild.get_channel(REPORT_CHANNEL_ID)

    now = datetime.now(JST)
    window = now - timedelta(weeks=2)
    delay = timedelta(minutes=3 if not IS_AUTO_MODE else 3 * 24 * 60)

    # リアクションと対象ロールのキーワードマップ
    REACTION_ROLE_MAP = {
        "✅": GEN_ROLE_KEYWORD,
        "☑️": "図書委員会"
    }

    messages = []
    async for message in target_channel.history(limit=None, after=window):
        created_at_jst = message.created_at.astimezone(JST)
        if created_at_jst + delay > now:
            continue
        if any(str(reaction.emoji) in REACTION_ROLE_MAP for reaction in message.reactions):
            messages.append(message)

    if not messages:
        await report_channel.send("🔔 現時点でリマインド対象者はいません。")
        return

    all_not_reacted = set()

    for message in messages:
        for reaction in message.reactions:
            emoji = str(reaction.emoji)
            if emoji not in REACTION_ROLE_MAP:
                continue

            role_keyword = REACTION_ROLE_MAP[emoji]

            # 対象メンバーを絞る
            target_members = [
                m for m in guild.members
                if any(role_keyword in r.name for r in m.roles)
                and EXCLUDE_NICKNAME_KEYWORD not in (m.display_name or "")
                and not m.bot
            ]

            users = [user async for user in reaction.users()]
            not_reacted = [m for m in target_members if m not in users]

            if not_reacted:
                mentions = "\n".join(m.mention for m in not_reacted)
                await remind_channel.send(
                    f"⚠️ {emoji} 以下のメンバーが [このメッセージ](https://discord.com/channels/{guild.id}/{TARGET_CHANNEL_ID}/{message.id}) に反応していません。\n{mentions}"
                )
                all_not_reacted.update(not_reacted)

    if not all_not_reacted:
        await report_channel.send("🎉 全員リアクション済みです！")
    else:
        mentions = "\n".join(member.mention for member in all_not_reacted)
        await report_channel.send(f"📝 未リアクション者一覧:\n{mentions}")
