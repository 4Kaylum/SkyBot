import typing
import re

import discord
from discord.ext import commands
import voxelbotutils as utils


class UserPoints(utils.Cog):

    @utils.group(invoke_without_command=True)
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
    async def points(self, ctx:utils.Context):
        """
        The parent group for the points commands.
        """

        # See if they're running a subcommand
        if ctx.invoked_subcommand is not None:
            return
        return await ctx.send_help(ctx.command)

    @points.command(name="get")
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
    async def points_get(self, ctx:utils.Context, user:discord.Member=None):
        """
        Get the number of points that a user has.
        """

        # Get data
        user = user or ctx.author
        async with self.bot.database() as db:
            rows = await db("SELECT * FROM user_points WHERE guild_id=$1 AND user_id=$2", ctx.guild.id, user.id)

        # Output data
        if rows:
            return await ctx.send(f"{user.mention} has {rows[0]['points']} points.")
        await ctx.send(f"{user.mention} has 0 points.", allowed_mentions=discord.AllowedMentions(users=False))

    @points.command(name="add")
    @commands.has_guild_permissions(manage_roles=True)
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
    async def points_add(self, ctx:utils.Context, user:typing.Optional[discord.Member], points:int=1):
        """
        Add a point to a user.
        """

        # Alter data
        user = user or ctx.author
        async with self.bot.database() as db:
            await db(
                """INSERT INTO user_points VALUES ($1, $2, $3) ON CONFLICT (guild_id, user_id)
                DO UPDATE SET points=user_points.points+excluded.points""",
                ctx.guild.id, user.id, points
            )

        # Send output
        await ctx.send(f"Added {points} points to {user.mention}.", allowed_mentions=discord.AllowedMentions(users=False))
        self.bot.dispatch("leaderboard_update", ctx.guild)

    @points.command(name="remove")
    @commands.has_guild_permissions(manage_roles=True)
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
    async def points_remove(self, ctx:utils.Context, user:typing.Optional[discord.Member], points:int=1):
        """
        Remove points from a user.
        """

        # Alter data
        user = user or ctx.author
        async with self.bot.database() as db:
            await db(
                """INSERT INTO user_points VALUES ($1, $2, $3) ON CONFLICT (guild_id, user_id)
                DO UPDATE SET points=user_points.points+excluded.points""",
                ctx.guild.id, user.id, -points
            )

        # Send output
        await ctx.send(f"Removed {points} points from {user.mention}.", allowed_mentions=discord.AllowedMentions(users=False))
        self.bot.dispatch("leaderboard_update", ctx.guild)

    @points.subcommand_group(name="leaderboard", invoke_without_command=True)
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    @commands.guild_only()
    async def points_leaderboard(self, ctx:utils.Context):
        """
        A parent group for the points leaderboard commands.
        """

        if ctx.invoked_subcommand is not None:
            return
        return await ctx.send_help(ctx.command)

    @points_leaderboard.command(name="show")
    @commands.has_guild_permissions(manage_roles=True)
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    @commands.guild_only()
    async def points_leaderboard_show(self, ctx:utils.Context):
        """
        Show the points leaderboard without creating a new one.
        """

        # See if they're running a subcommand
        if ctx.invoked_subcommand is not None:
            return

        # Get data
        async with self.bot.database() as db:
            rows = await db("SELECT * FROM user_points WHERE guild_id=$1 AND points > 0 ORDER BY points DESC", ctx.guild.id)

        # Format it into an embed
        valid_users = []
        for i in rows:
            member = ctx.guild.get_member(i['user_id'])
            if member is None:
                continue
            valid_users.append(f"{member.mention}: {i['points']:,}")
            if len(valid_users) >= 30:
                break
        with utils.Embed(use_random_colour=True) as embed:
            embed.description = '\n'.join(valid_users) or 'Nobody is on here :c'

        # Output
        await ctx.send(embed=embed)

    @points_leaderboard.command(name="create")
    @commands.has_guild_permissions(manage_roles=True)
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    @commands.guild_only()
    async def points_leaderboard_create(self, ctx:utils.Context):
        """
        Create a points leaderboard.
        """

        message = await ctx.send("Setting up leaderboard message...")
        async with self.bot.database() as db:
            await db(
                """INSERT INTO guild_settings (guild_id, leaderboard_message_url) VALUES ($1, $2)
                ON CONFLICT (guild_id) DO UPDATE SET leaderboard_message_url=excluded.leaderboard_message_url""",
                ctx.guild.id, message.jump_url,
            )
        self.bot.guild_settings[ctx.guild.id]['leaderboard_message_url'] = message.jump_url
        self.bot.dispatch("leaderboard_update", ctx.guild)

    @utils.Cog.listener()
    async def on_leaderboard_update(self, guild:discord.Guild):
        """
        Update the leaderboard message.
        """

        # See if we can get the leaderboard message
        class FakeContext:
            bot = self.bot
        leaderboard_message_url = self.bot.guild_settings[guild.id]['leaderboard_message_url']
        if not leaderboard_message_url:
            return
        try:
            message = await commands.MessageConverter().convert(FakeContext, leaderboard_message_url)
        except commands.BadArgument:
            return
        if message is None:
            return

        # Get data
        async with self.bot.database() as db:
            rows = await db("SELECT * FROM user_points WHERE guild_id=$1 AND points > 0 ORDER BY points DESC", guild.id)

        # Format it into an embed
        valid_users = []
        for i in rows:
            member = guild.get_member(i['user_id'])
            if member is None:
                continue
            valid_users.append(f"{member.mention}: {i['points']:,}")
            if len(valid_users) >= 30:
                break
        with utils.Embed(use_random_colour=True) as embed:
            embed.description = '\n'.join(valid_users) or 'Nobody is on here :c'

        # Output
        await message.edit(content=None, embed=embed)


def setup(bot:utils.Bot):
    x = UserPoints(bot)
    bot.add_cog(x)
