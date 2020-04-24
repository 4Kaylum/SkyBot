import string
import random
import typing

import discord
from discord.ext import commands

from cogs import utils


def create_id(n:int=5):
    """Generates a generic 5 character-string to use as an ID"""

    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=n)).lower()


class QuoteCommands(utils.Cog):

    @commands.command(cls=utils.Command)
    @commands.guild_only()
    async def quote(self, ctx:utils.Context, message:typing.Union[discord.Message, discord.Member]):
        """Qutoes a user babeyyyyy lets GO"""

        # Validate input
        # if not text and isinstance(user, discord.Member):
        #     return await ctx.send("You need to provide some text to quote.")
        # elif isinstance(user, discord.Message):
        text = message.content
        timestamp = message.created_at
        user = message.author
        text = message.content
        # else:
        #     timestamp = ctx.message.created_at

        # Make sure they're not quoting themself
        if user.id == ctx.author.id:
            return await ctx.send("You can't quote yourself :/")

        # Save to db
        quote_id = create_id()
        async with self.bot.database() as db:
            await db(
                "INSERT INTO user_quotes (quote_id, guild_id, user_id, text, timestamp) VALUES ($1, $2, $3, $4, $5)",
                quote_id, ctx.guild.id, user.id, text, timestamp
            )

        # Make embed
        with utils.Embed(use_random_colour=True) as embed:
            embed.set_author_to_user(user)
            embed.description = text
            embed.set_footer(text=f"Quote ID {quote_id.upper()}")
            embed.timestamp = timestamp

        # See if they have a quotes channel
        quote_channel_id = self.bot.guild_settings[ctx.guild.id].get('quote_channel_id')
        if quote_channel_id:
            channel = self.bot.get_channel(quote_channel_id) or await self.bot.fetch_channel(quote_channel_id)
            try:
                await channel.send(embed=embed)
            except (discord.Forbidden, AttributeError):
                pass

        # Output to user
        await ctx.send(f"Quote saved with ID `{quote_id.upper()}`", embed=embed)

    @commands.command(cls=utils.Command)
    async def getquote(self, ctx:utils.Context, quote_id:commands.clean_content):
        """Gets a quote from the database"""

        # Grab data from db
        async with self.bot.database() as db:
            rows = await db("SELECT * FROM user_quotes WHERE quote_id=$1", quote_id.lower())
        if not rows:
            return await ctx.send(f"There's no quote with the ID `{quote_id.upper()}`.")

        # Format into embed
        data = rows[0]
        with utils.Embed(use_random_colour=True) as embed:
            user_id = data['user_id']
            user = self.bot.get_user(user_id)
            if user is None:
                embed.set_author(name=f"User ID {user_id}")
            else:
                embed.set_author_to_user(user)
            embed.description = data['text']
            embed.set_footer(text=f"Quote ID {quote_id.upper()}")
            embed.timestamp = data['timestamp']

        # Output to user
        return await ctx.send(embed=embed)

    @commands.command(cls=utils.Command)
    async def searchquotes(self, ctx:utils.Context, user:typing.Optional[discord.Member]=None, *, search_term:str):
        """Searches the datbase for a quote with some text in it babeyeyeyey"""

        # Grab data from the database
        async with self.bot.database() as db:
            if user is None:
                rows = await db("SELECT * FROM user_quotes WHERE text LIKE CONCAT('%', $1::text, '%') ORDER BY timestamp DESC", search_term)
            else:
                rows = await db("SELECT * FROM user_quotes WHERE user_id=$1 AND text LIKE CONCAT('%', $2::text, '%') ORDER BY timestamp DESC", user.id, search_term)
        if not rows:
            return await ctx.send("I couldn't find any text matching that pattern.")

        # Format output
        rows = rows[:10]
        text_rows = []
        for row in rows:
            if len(row['text']) <= 50:
                text_rows.append(f"`{row['quote_id'].upper()}` - {row['text']}")
            else:
                text_rows.append(f"`{row['quote_id'].upper()}` - {row['text'][:50]}...")
        return await ctx.send('\n'.join(text_rows))


def setup(bot:utils.Bot):
    x = QuoteCommands(bot)
    bot.add_cog(x)