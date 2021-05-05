import typing
import re
import io

import discord
from discord.ext import commands
import voxelbotutils as utils
from PIL import Image


class ImageUrl(commands.Converter):

    SLASH_COMMAND_ARG_TYPE = utils.interactions.ApplicationCommandOptionType.STRING
    regex = re.compile(r"(http(s?):)([/|.|\w|\s|-])*\.(?:jpg|gif|png)")

    async def convert(self, ctx:utils.Context, argument:str):
        """
        Make sure a given string argument is an image URL.
        """

        v = self.regex.search(argument)
        if v is None:
            raise commands.BadArgument()
        return argument


class EmojiCommands(utils.Cog):

    @utils.command(aliases=['removeemoji', 'delemoji'], add_slash_command=False)
    @commands.bot_has_permissions(manage_emojis=True)
    @commands.has_guild_permissions(manage_emojis=True)
    @commands.guild_only()
    async def deleteemoji(self, ctx:utils.Context, emoji:discord.Emoji):
        """
        Deletes an emoji from a server
        """

        if emoji.guild_id != ctx.guild.id:
            raise commands.BadArgument("The emoji you provided is not in this server.")

        emoji_name = emoji.name
        await emoji.delete()
        await ctx.send(f"Deleted emoji `emoji_name`.")

    @staticmethod
    def calculate_new_size(image:Image, intended_size:int=256_000) -> tuple:
        """
        Use the equation f(n) = n * h * w * c to calculate an image's size given a size modifier, the width, the height,
        and a calculated constant. This method is inaccurate because image compression isn't constant, but it's as close
        as we care to get.
        """

        width = image.width
        height = image.height
        initial_size = len(image.tobytes())
        magic_constant = (initial_size) / (width * height)  # The constant (c)
        size_mod = intended_size / (magic_constant * width * height)  # The size modifier to reach the intended size

        return (int(width * size_mod), int(height * size_mod))

    @utils.command(aliases=['addemoji'], add_slash_command=False)
    @commands.bot_has_permissions(manage_emojis=True)
    @commands.has_guild_permissions(manage_emojis=True)
    @commands.guild_only()
    async def stealemoji(self, ctx:utils.Context, emoji:typing.Optional[typing.Union[discord.PartialEmoji, int, ImageUrl]]=None, name:str=None, animated:bool=False):
        """
        Copies an emoji and uploads it to your server.
        """

        # Default to the first attachment in the message's URL if `emoji` (the image url) is None
        if emoji is None:
            if ctx.message.attachments:
                emoji = ctx.message.attachments[0].url
                await ImageUrl().convert(ctx, emoji)  # Make sure the url is an image
            else:
                raise utils.errors.MissingRequiredArgumentString("emoji")

        # See if we gave an emoji ID
        if isinstance(emoji, int):
            if name is None:
                raise utils.errors.MissingRequiredArgumentString("name")
            emoji = discord.PartialEmoji(name=name, animated=animated, id=emoji)

        # See if we gave an image URL or an emoji
        if isinstance(emoji, discord.PartialEmoji):
            url = str(emoji.url)
            name = name or emoji.name
        else:
            url = emoji

        # Grab image data
        async with self.bot.session.get(url) as r:
            data = await r.read()

        # If the size is too big for Discord
        if len(data) > 256_000:
            original_image = Image.open(io.BytesIO(data))
            new_size = self.calculate_new_size(original_image)
            resized_image = original_image.resize(new_size)  # .tobytes()
            new_image_file_handle = io.BytesIO()
            resized_image.save(new_image_file_handle, format="png")
            new_image_file_handle.seek(0)
            data = new_image_file_handle.read()

        # Upload that to Discord
        try:
            e = await ctx.guild.create_custom_emoji(name=name, image=data)
        except discord.HTTPException as e:
            return await ctx.send(f"I couldn't create that emoji - {e}")
        except discord.InvalidArgument:
            return await ctx.send("Unsupported image type - make sure you're providing the correct argument for the image's animation state.")
        await ctx.send(f"Emoji added - {e!s}")


def setup(bot:utils.Bot):
    x = EmojiCommands(bot)
    bot.add_cog(x)
