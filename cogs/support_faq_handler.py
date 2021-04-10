import discord
from discord.ext import commands, tasks
import voxelbotutils as utils


SUPPORT_GUILD_ID = 830286019520626710
BOT_PICKER_CHANNEL_ID = 830286547247955998
PICKABLE_FAQ_CHANNELS = {
    "<:marriage_bot:643484716607209482>": 830294468929912842,  # MarriageBot Support
    "<:flower:777636276790624256>": 830294484045529140,  # Flower Support
    "<:big_ben:709600097574584420>": 830294528958398464,  # Big Ben Support
    "\N{BLACK QUESTION MARK ORNAMENT}": 830546400542589019,  # Other Support
    "\N{SPEECH BALLOON}": 830546422930604072,  # Hang out
}
FAQ_MESSAGES = {
    "830294468929912842": [
        "None of the commands are working",
        "I can't disown my child",
        "Can you copy my MarriageBot family into Gold?",
    ],
    "830294484045529140": [
        "None of the commands are working",
        "I can't water my plant",
        "What's the best plant?",
        "How do I give pots to people?",
    ],
    "830294528958398464": [
        "None of the commands are working",
        "How do I set it up?",
        "It isn't giving out the role",
    ],
}


class SupportFAQHandler(utils.Cog):

    BOT_PICKER_MESSAGE_ID = None

    def __init__(self, bot:utils.Bot):
        super().__init__(bot)
        self.guild_purge_loop.start()
        self.faq_webhook = discord.Webhook.from_url(
            bot.config['command_data']['faq_webhook'],
            adapter=discord.AsyncWebhookAdapter(bot.session),
        )
        self.faq_webhook._state = bot._connection

    def cog_unload(self):
        self.guild_purge_loop.cancel()

    @tasks.loop(hours=6)
    async def guild_purge_loop(self):
        """
        Automatically purges the support guild.
        """

        await self.bot.get_guild(SUPPORT_GUILD_ID).prune_members(days=7, compute_prune_count=False, reason="Automatic purge event.")

    @guild_purge_loop.before_loop
    async def before_guild_purge_loop(self):
        return await self.bot.wait_until_ready()

    def send_faq_log(self, *args, **kwargs) -> None:
        """
        Sends a message using the webhook.
        """

        self.bot.loop.create_task(self.faq_webhook.send(*args, **kwargs))

    def ghost_ping(self, channel:discord.TextChannel, user:discord.User) -> None:
        """
        Sends and deletes a user ping to the given channel
        """

        async def wrapper():
            m = await channel.send(user.mention)
            await m.delete()
        self.bot.loop.create_task(wrapper())

    @utils.Cog.listener()
    async def on_raw_reaction_add(self, payload:discord.RawReactionActionEvent):
        """
        Runs the support guild reaction handler.
        """

        # Make sure the guild is right
        if payload.guild_id != SUPPORT_GUILD_ID:
            return
        guild = self.bot.get_guild(SUPPORT_GUILD_ID)
        member = guild.get_member(payload.user_id)
        if member.bot:
            return

        # See if we're looking at the bot picker
        if payload.channel_id == BOT_PICKER_CHANNEL_ID:
            new_channel_id = PICKABLE_FAQ_CHANNELS[str(payload.emoji)]
            new_channel = self.bot.get_channel(new_channel_id)
            await new_channel.set_permissions(member, read_messages=True)
            self.send_faq_log(f"{member.mention} (`{member.id}`) has been given access to **{new_channel.category.name}**.")
            self.ghost_ping(new_channel, member)
            return

        # We could be looking at an faq channel
        current_channel = self.bot.get_channel(payload.channel_id)
        if current_channel.name == "faqs":
            current_category = current_channel.category
            try:
                emoji_number = int(str(payload.emoji)[0])
                new_channel = current_category.channels[emoji_number]  # They gave a number
                self.send_faq_log(f"{member.mention} (`{member.id}`) in {current_category.name} is looking at FAQ **{FAQ_MESSAGES[str(current_category.id)][emoji_number - 1]}**.")
            except ValueError:
                new_channel_id = PICKABLE_FAQ_CHANNELS["\N{BLACK QUESTION MARK ORNAMENT}"]  # Take them to other support
                new_channel = self.bot.get_channel(new_channel_id)
                self.send_faq_log(f"{member.mention} (`{member.id}`) in {current_category.name} has a question not in the FAQ.")
            await new_channel.set_permissions(member, read_messages=True)
            self.ghost_ping(new_channel, member)
            return

        # It's probably a tick mark
        if str(payload.emoji) == "\N{HEAVY CHECK MARK}":
            self.send_faq_log(f"{member.mention} (`{member.id}`) gave a tick mark in **{current_channel.mention}**.")

    @utils.command()
    @commands.is_owner()
    async def setupsupportguild(self, ctx:utils.Context):
        """
        Sends some sexy new messages into the support guild.
        """

        # Make sure we're in the right guild
        if ctx.guild is None or ctx.guild.id != SUPPORT_GUILD_ID:
            return await ctx.send("This can only be run on the set support guild.")

        # This could take a while
        async with ctx.typing():

            # Remake the FAQ channel for each channel
            for channel_id_str, embed_lines in FAQ_MESSAGES.items():

                # Get the category object
                channel = self.bot.get_channel(int(channel_id_str))
                category = channel.category

                # Get the faq channel and delete the old message
                faq_channel = category.channels[0]
                if faq_channel.name != "faqs":
                    return await ctx.send(
                        f"The first channel in the **{category_name}** category isn't called **faqs**.",
                        allowed_mentions=discord.AllowedMentions.none(),
                    )
                async for message in faq_channel.history(limit=3):
                    await message.delete()

                # Send a new message
                emoji_lines = [f"{index}\N{COMBINING ENCLOSING KEYCAP} **{string}**" for index, string in enumerate(embed_lines, start=1)]
                description = "\n".join(emoji_lines + ["\N{BLACK QUESTION MARK ORNAMENT} **Other**"])
                new_message = await faq_channel.send(embed=utils.Embed(
                    title="What issue are you having?", description=description, colour=0x1,
                ))
                for emoji, item in [i.strip().split(" ", 1) for i in new_message.embeds[0].description.strip().split("\n")]:
                    await new_message.add_reaction(emoji)

        # And we should be done at this point
        await ctx.okay()


def setup(bot:utils.Bot):
    x = SupportFAQHandler(bot)
    bot.add_cog(x)