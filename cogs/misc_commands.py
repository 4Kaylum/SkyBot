import typing
import random
from urllib.parse import urlencode
import io
import http

import discord
from discord.ext import commands
import unicodedata
from PIL import Image
import voxelbotutils as utils


class MiscCommands(utils.Cog):

    @utils.command()
    async def fpf(self, ctx:utils.Context, *, text:commands.clean_content):
        """
        Give you some fluffy pink font text.
        """

        if len(text) > 50:
            return await ctx.send("Your text input is too long.")
        base_url = "https://flamingtext.com/net-fu/proxy_form.cgi"
        params = {
            "script": "fluffy-logo",
            "fillTextColor": "#fde",
            "outlineSize": "3",
            "fillOutlineColor": "#ffcdcd",
            "shadowType": "0",
            "shadowXOffset": "-20",
            "shadowBlur": "0",
            "backgroundRadio": "0",
            "text": text,
            "_loc": "generate",
            "imageoutput": "true",
        }
        url = base_url + '?' + urlencode(params)
        embed = utils.Embed(use_random_colour=True).set_image(url)
        return await ctx.send(embed=embed)

    @utils.command()
    async def hpf(self, ctx:utils.Context, *, text:commands.clean_content):
        """
        Give you some Harry Potter font text.
        """

        if len(text) > 50:
            return await ctx.send("Your text input is too long.")
        base_url = "https://flamingtext.com/net-fu/proxy_form.cgi"
        params = {
            "script": "harry-potter-logo",
            "fillTextColor": "#fde",
            "outlineSize": "3",
            "fillOutlineColor": "#ffcdcd",
            "shadowType": "0",
            "shadowXOffset": "-20",
            "shadowBlur": "0",
            "backgroundRadio": "0",
            "text": text,
            "_loc": "generate",
            "imageoutput": "true",
        }
        url = base_url + '?' + urlencode(params)
        embed = utils.Embed(use_random_colour=True).set_image(url)
        return await ctx.send(embed=embed)

    @utils.command(ignore_extra=False, aliases=['imposter', 'crewmate', 'amongus', 'amogus'])
    @commands.bot_has_permissions(send_messages=True, attach_files=True)
    async def impostor(self, ctx:utils.Context, user1:discord.User, user2:discord.User, user3:discord.User, user4:discord.User, user5:discord.User=None):
        """
        Puts you and your friends into an impostor image.
        """

        # Fix up input args
        if user5 is None:
            user3, user4, user5 = ctx.author, user3, user4
        user_list = [user1, user2, user3, user4, user5]

        # Grab everyone's profile pictures
        avatar_bytes = []
        for user in user_list:
            async with self.bot.session.get(str(user.avatar_url_as(format="png", size=256))) as r:
                avatar_bytes.append(await r.read())

        # io them up
        base_image = Image.open("config/crewmate.png")
        avatar_images = [Image.open(io.BytesIO(i)) for i in avatar_bytes]

        # Resize our avatars
        avatar_positions = [
            ((394, 427), (469, 502)),
            ((510, 438), (594, 522)),
            ((636, 429), (755, 547)),
            ((773, 438), (853, 518)),
            ((895, 430), (969, 505)),
        ]
        get_size = lambda i: (avatar_positions[i][1][0] - avatar_positions[i][0][0], avatar_positions[i][1][1] - avatar_positions[i][0][1])
        avatar_images = [i.resize(get_size(index)) for index, i in enumerate(avatar_images)]

        # Paste them onto our base
        for index, i in enumerate(avatar_images):
            base_image.paste(i, avatar_positions[index][0])

        # And output
        output_image = io.BytesIO()
        base_image.save(output_image, format="png")
        output_image.seek(0)
        return await ctx.send(file=discord.File(output_image, filename="imposter.png"))

    @utils.group(aliases=['topics'], invoke_without_command=False)
    @commands.bot_has_permissions(send_messages=True)
    async def topic(self, ctx:utils.Context):
        """
        Gives you a conversation topic.
        """

        async with self.bot.database() as db:
            rows = await db("SELECT * FROM topics ORDER BY RANDOM() LIMIT 1")
        if not rows:
            return await ctx.send("There aren't any topics set up in the database for this bot :<")
        return await ctx.send(rows[0]['topic'])

    @topic.command(name="add")
    @utils.checks.is_bot_support()
    @commands.bot_has_permissions(send_messages=True)
    async def topic_add(self, ctx:utils.Context, *, topic:str):
        """
        Add a new topic to the database.
        """

        async with self.bot.database() as db:
            await db("INSERT INTO topics VALUES ($1)", topic)
        return await ctx.send("Added to database.")

    @utils.command()
    @commands.bot_has_permissions(send_messages=True)
    async def coinflip(self, ctx:utils.Context):
        """
        Flips a coin.
        """

        coin = ["Heads", "Tails"]
        return await ctx.send(random.choice(coin))

    @utils.command()
    @commands.bot_has_permissions(manage_channels=True)
    @commands.has_permissions(manage_channels=True)
    @commands.guild_only()
    async def slowmode(self, ctx:utils.Context, time:utils.TimeValue):
        """
        Sets slowmode for a channel.
        """

        try:
            await ctx.channel.edit(slowmode_delay=time.delta.total_seconds())
        except discord.HTTPException as e:
            return await ctx.send(str(e))
        await ctx.okay()

    @utils.command(aliases=['http'])
    @utils.cooldown.cooldown(1, 5, commands.BucketType.channel)
    async def httpcat(self, ctx:utils.Context, errorcode:str):
        """
        Gives you a cat based on an HTTP error code.
        """

        standard_errorcodes = [error.value for error in http.HTTPStatus]

        if errorcode in ('random', 'rand', 'r'):
            errorcode = random.choice(standard_errorcodes)
        else:
            try:
                errorcode = int(errorcode)
            except ValueError:
                return ctx.channel.send('Converting to "int" failed for parameter "errorcode".')

        await ctx.channel.trigger_typing()
        headers = {"User-Agent": self.bot.user_agent}
        async with self.bot.session.get(f"https://http.cat/{errorcode}", headers=headers) as r:
            if r.status == 404:
                if errorcode not in standard_errorcodes:
                    await ctx.send("That HTTP code doesn't exist.")
                else:
                    await ctx.send('Image for HTTP code not found on provider.')
                return
            if r.status != 200:
                await ctx.send(f'Something went wrong, try again later. ({r.status})')
                return
        with utils.Embed(use_random_colour=True) as embed:
            embed.set_image(url=f'https://http.cat/{errorcode}')
        await ctx.send(embed=embed)

    @utils.command()
    @utils.cooldown.cooldown(1, 5, commands.BucketType.channel)
    async def httpdog(self, ctx:utils.Context, errorcode:str):
        """
        Gives you a dog based on an HTTP error code.
        """

        standard_errorcodes = [error.value for error in http.HTTPStatus]

        if errorcode in ('random', 'rand', 'r'):
            errorcode = random.choice(standard_errorcodes)
        else:
            try:
                errorcode = int(errorcode)
            except ValueError:
                return ctx.channel.send('Converting to "int" failed for parameter "errorcode".')

        await ctx.channel.trigger_typing()
        headers = {"User-Agent": self.bot.user_agent}
        async with self.bot.session.get(f"https://httpstatusdogs.com/img/{errorcode}.jpg",
                                        headers=headers, allow_redirects=False) as r:
            if str(r.status)[0] != "2":
                if errorcode not in standard_errorcodes:
                    await ctx.send("That HTTP code doesn't exist.")
                else:
                    await ctx.send('Image for HTTP code not found on provider.')
                return
        with utils.Embed(use_random_colour=True) as embed:
            embed.set_image(url=f'https://httpstatusdogs.com/img/{errorcode}.jpg')
        await ctx.send(embed=embed)

    @utils.command(aliases=['pip'])
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def pypi(self, ctx:utils.Context, module:commands.clean_content):
        """
        Grab data from PyPi.
        """

        # Get data
        async with self.bot.session.get(f"https://pypi.org/pypi/{module}/json") as r:
            if r.status != 200:
                with utils.Embed(use_random_colour=True) as embed:
                    embed.title = f"Module `{module}` not found"
                    embed.description = f"[Search Results](https://pypi.org/search/?q={module})"
                return await ctx.send(embed=embed)
            data = await r.json()

        # Format into an embed
        with utils.Embed(use_random_colour=True) as embed:
            embed.set_author(name=data['info']['name'], url=f"https://pypi.org/project/{module}")
            embed.description = data['info']['summary']
        return await ctx.send(embed=embed)

    @utils.command(aliases=['npmjs'])
    async def npm(self, ctx:utils.Context, package_name:str):
        """
        Check NPM for a package.
        """

        # Get our data
        async with self.bot.session.get(f"http://registry.npmjs.com/{package_name}/") as e:
            if e.status == 404:
                await ctx.send(f"I could not find anything about `{package_name}` :c")
                return
            if e.status != 200:
                await ctx.send("Something went wrong, try again later...")
                return
            data = await e.json()

        # make a lil embed
        with utils.Embed(use_random_colour=True) as embed:
            embed.set_author(name=data['name'], url=f"https://www.npmjs.com/package/{package_name}")
            embed.description = data['description']
        await ctx.send(embed=embed)

    @utils.command()
    async def nuget(self, ctx:utils.Context, package_name:str):
        """
        Check nuget for a package.
        """

        # Get our data
        async with self.bot.session.get(f"https://azuresearch-usnc.nuget.org/query?q={package_name}") as e:
            if e.status != 200:
                await ctx.send("Something went wrong, try again later...")
                return
            data = await e.json()

        # make a lil embed
        with utils.Embed(use_random_colour=True) as embed:
            if data['data']:
                embed.set_author(name=data['data'][0]['title'], url=f"https://www.nuget.org/packages/{data['data'][0]['id']}")
                embed.description = data['data'][0]['description']
            else:
                await ctx.send(f"I could not find anything for `{package_name}` :c")
                return
        await ctx.send(embed=embed)

    @utils.command(aliases=['color'], add_slash_command=False)
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def colour(self, ctx:utils.Context, *, colour:typing.Union[discord.Role, discord.Colour, discord.Member]):
        """
        Get you a colour.
        """

        # https://www.htmlcsscolor.com/preview/gallery/5dadec.png
        if isinstance(colour, discord.Role):
            colour = colour.colour
        elif isinstance(colour, discord.Member):
            try:
                colour = [i for i in colour.roles if i.colour.value > 0][-1].colour
            except IndexError:
                colour = discord.Colour(0)
        hex_colour = colour.value
        with utils.Embed(colour=hex_colour,title=f"#{hex_colour:0>6X}") as embed:
            embed.set_image(url=f"https://www.htmlcsscolor.com/preview/gallery/{hex_colour:0>6X}.png")
        await ctx.send(embed=embed)

    @utils.command()
    @commands.bot_has_permissions(send_messages=True)
    async def charinfo(self, ctx, *, characters: str):
        """
        Shows you information about a number of characters.
        """

        def to_string(c):
            digit = f'{ord(c):x}'
            name = unicodedata.name(c, 'Name not found.')
            return f'`\\U{digit:>08}`: {name} - {c} \N{EM DASH} <http://www.fileformat.info/info/unicode/char/{digit}>'
        msg = '\n'.join(map(to_string, characters))
        if len(msg) > 2000:
            return await ctx.send('Output too long to display.')
        await ctx.send(msg)

    @utils.command(cooldown_after_parsing=True)
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(send_messages=True)
    @utils.cooldown.cooldown(1, 60, commands.BucketType.guild)
    async def spam(self, ctx:utils.Context, amount:int, *, text:str):
        """
        Spams a message a given amount of times.
        """

        if amount > 10:
            return await ctx.send("That's too much to spam.")
        for _ in range(amount):
            await ctx.send(text)

    @utils.command(aliases=['disconnectvc', 'clearvc'])
    @commands.has_guild_permissions(move_members=True)
    @commands.bot_has_guild_permissions(move_members=True)
    @commands.bot_has_permissions(send_messages=True)
    async def emptyvc(self, ctx:utils.Context, channel:discord.VoiceChannel):
        """
        Removes all the people from a given VC.
        """

        if not channel.members:
            return await ctx.send("There are no people in that VC for me to remove.")
        member_count = len(channel.members)
        for member in channel.members:
            try:
                await member.edit(voice_channel=None)
            except discord.Forbidden:
                return await ctx.send("I don't have permission to remove members from that channel.")
        return await ctx.send(f"Dropped {member_count} members from the VC.")

    @utils.command()
    async def square(self, ctx:utils.Context, *, text:commands.clean_content):
        """
        Makes your input into a sexy lil square.
        """

        builder = [' '.join(text)]
        space_count = ((len(text) - 2) * 2) + 1
        for index, (i, o) in enumerate(zip(text[1:-1], text[1:-1][::-1])):
            builder.append(f"{i}{' ' * space_count}{o}")
        builder.append(' '.join(text[::-1]))
        output = '\n'.join(builder)
        returned_string = f"```\n{output}```"
        if len(returned_string) > 2000:
            return await ctx.send("The output square for this is too many characters.")
        return await ctx.send(returned_string)

    @utils.command()
    async def getinterval(self, ctx:utils.Context, message1:int, message2:int):
        """
        Get the interval between two messages.
        """

        timestamps = sorted([discord.Object(message1).created_at, discord.Object(message2).created_at], reverse=True)
        return await ctx.send(timestamps[0] - timestamps[1])

    @utils.command(hidden=True)
    async def rolecount(self, ctx:utils.Context, user:discord.Member=None):
        """
        Returns how many roles the user has
        """

        user_r = user or ctx.author
        return await ctx.send(f"That user has: {len(user_r.roles)} roles.")


    @utils.command()
    @commands.bot_has_permissions(send_messages=True, attach_files=True)
    async def randompicture(self, ctx:utils.Context, x_size:int=256, y_size:int=None):
        """
        Sends some random noise into chat.
        """

        await ctx.trigger_typing()
        y_size = y_size or x_size
        image_size = (x_size, y_size)
        if min(image_size) < 10 or max(image_size) > 500:
            return await ctx.send("Size must be between 10 and 500.")

        x = Image.new("RGB", image_size)
        for i in range(0, x.size[0]):
            for o in range(0, x.size[1]):
                x.putpixel((i, o), (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))
        y = x.resize((x.size[0] * 5, x.size[1] * 5), Image.NEAREST)
        handle = io.BytesIO()
        y.save(handle, format="PNG")
        handle.seek(0)
        return await ctx.send(file=discord.File(handle, filename="random.png"))


def setup(bot:utils.Bot):
    x = MiscCommands(bot)
    bot.add_cog(x)
