import io
import re
import csv

import discord
from discord.ext import commands
import voxelbotutils as utils


DISCORD_EMOTE_REGEX = re.compile(r'<:(\w*):\d*>')
RATELIMIT_MESSAGE_PER_SECOND = 100
PROGRESS_REPORT_INTERVAL_DEFAULT = 1000


class AnalyticsCommands(utils.Cog, command_attrs={"add_slash_command": False}):

    progress_report_interval = PROGRESS_REPORT_INTERVAL_DEFAULT

    async def progress_report(self, ctx:commands.Context, messages_processed:int, current_channel:discord.TextChannel):
        if messages_processed == 0:
            await ctx.send(f'Processing... ({RATELIMIT_MESSAGE_PER_SECOND} messages/second - Discord ratelimit)')
        elif messages_processed % self.progress_report_interval == 0:
            await ctx.send(f'Processed {messages_processed} so far, currently in #{current_channel.name}')

    @utils.command(name='set-analytics-progress-report-interval', aliases=['sapri'])
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(send_messages=True)
    async def set_interval(self, ctx:utils.Context, interval:int):
        await ctx.send(
            f'Previous interval: {self.progress_report_interval}, '
            f'Default: {PROGRESS_REPORT_INTERVAL_DEFAULT}'
        )
        self.progress_report_interval = interval
        await ctx.send(f'Set interval to {self.progress_report_interval}')

    @utils.command()
    @utils.cooldown.cooldown(1, 60 * 60, commands.BucketType.guild)
    @commands.bot_has_permissions(read_message_history=True, send_messages=True, attach_files=True)
    async def linkdump(self, ctx:utils.Context, target_channels:commands.Greedy[discord.TextChannel]=None, regex=None):
        """
        Get all links ever sent in a channel and dump them to a txt file.

        Takes channels as arguments, or defaults to the channel in which the command was invoked.
        """

        if target_channels is None:
            target_channels = [ctx.channel]
        if regex is not None:
            try:
                regex = re.compile(regex)
            except re.error:
                return await ctx.send('Bad regex.')

        all_links = []
        messages_processed = 0
        for target_channel in target_channels:
            async for message in target_channel.history(limit=None):
                self.bot.loop.create_task(self.progress_report(ctx, messages_processed, target_channel))
                for embed in message.embeds:
                    if regex is not None:
                        if re.fullmatch(regex, embed.url):
                            all_links.append(embed.url)
                    else:
                        all_links.append(embed.url)
                messages_processed += 1

        with io.StringIO('\n'.join(all_links)) as file_stream:
            discord_file = discord.File(file_stream, filename='links.txt')
            return await ctx.send(
                'Here are all the links ever sent in the channels:',
                file=discord_file
            )

    @utils.command(name='analyse-emote-usage')
    @utils.cooldown.cooldown(1, 60 * 60, commands.BucketType.guild)
    @commands.bot_has_permissions(read_message_history=True, send_messages=True, attach_files=True)
    async def emotes(self, ctx:utils.Context, target_channels:commands.Greedy[discord.TextChannel]=None):
        """
        Get a csv containing the timestamp of every discord emote ever sent in a guild.

        Takes channels as arguments, or defaults to every channel in the guild.
        The user can take this and make a graph or whatever. Useful for figuring out which emotes to remove
        when you're at the cap!
        """

        if target_channels is None:
            target_channels = ctx.guild.channels

        with io.StringIO() as file_stream:
            csvw = csv.writer(file_stream)
            messages_processed = 0
            for target_channel in target_channels:
                if target_channel.type == discord.ChannelType.text:
                    async for message in target_channel.history(limit=None):
                        self.bot.loop.create_task(self.progress_report(ctx, messages_processed, target_channel))
                        emotes_used = re.findall(DISCORD_EMOTE_REGEX, message.content)
                        message_timestamp = message.created_at.timestamp()
                        csvw.writerows([[message_timestamp, emote_used] for emote_used in emotes_used])
                        messages_processed += 1
            discord_file = discord.File(file_stream, filename='emotes.csv')
            return await ctx.send('Here are all the emotes used in this guild:', file=discord_file)


def setup(bot:utils.Bot):
    x = AnalyticsCommands(bot)
    bot.add_cog(x)
