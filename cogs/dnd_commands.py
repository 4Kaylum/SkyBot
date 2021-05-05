import re
import typing
import random
import string
from urllib.parse import quote

from discord.ext import commands
import voxelbotutils as utils


class DNDCommands(utils.Cog):

    DICE_REGEX = re.compile(r"^(?P<count>\d+)?[dD](?P<type>\d+) *(?P<modifier>(?P<modifier_parity>[+-]) *(?P<modifier_amount>\d+))?$")
    ATTRIBUTES = {
        "strength": "STR",
        "dexterity": "DEX",
        "constitution": "CON",
        "intelligence": "INT",
        "wisdom": "WIS",
        "charisma": "CHR",
    }

    @utils.command(aliases=['roll'])
    @commands.bot_has_permissions(send_messages=True)
    async def dice(self, ctx:utils.Context, *, dice:str):
        """
        Rolls a dice for you.
        """

        # Validate the dice
        if not dice:
            raise utils.errors.MissingRequiredArgumentString(dice)
        match = self.DICE_REGEX.search(dice)
        if not match:
            raise commands.BadArgument("Your dice was not in the format `AdB+C`.")

        # Roll em
        dice_count = int(match.group("count") or 1)
        dice_type = int(match.group("type"))
        modifier = int((match.group("modifier") or "+0").replace(" ", ""))
        rolls = [random.randint(1, dice_type) for _ in range(dice_count)]
        total = sum(rolls) + modifier
        dice_string = f"{dice_count}d{dice_type}{modifier:+}"
        if not modifier:
            dice_string = dice_string[:-2]

        # Output formatted
        if dice_count > 1 or modifier:
            equals_string = f"{sum(rolls)} {'+' if modifier > 0 else '-'} {abs(modifier)}"
            if modifier:
                return await ctx.send(f"Total **{total:,}** ({dice_string})\n({', '.join([str(i) for i in rolls])}) = {equals_string}")
            return await ctx.send(f"Total **{total:,}** ({dice_string})\n({', '.join([str(i) for i in rolls])}) = {equals_string}")
        return await ctx.send(f"Total **{total}** ({dice_string})")

    async def send_web_request(self, resource:str, item:str) -> typing.Optional[dict]:
        """
        Send a web request to the dnd5eapi website.
        """

        url = f"https://www.dnd5eapi.co/api/{resource}/{quote(item.lower().replace(' ', '-'))}/"
        headers = {"User-Agent": self.bot.user_agent}
        async with self.bot.session.get(url, headers=headers) as r:
            v = await r.json()
        if v.get("error"):
            return None
        return v

    @staticmethod
    def group_field_descriptions(embed, field_name, input_list) -> None:
        """
        Add fields grouped to the embed character limit.
        """

        original_field_name = field_name
        joiner = "\n"
        action_text = [f"**{i['name']}**{joiner}{i['desc']}" for i in input_list]
        add_text = ""
        for index, text in enumerate(action_text):
            if len(add_text) + len(text) + 1 > 1024:
                embed.add_field(
                    field_name, add_text, inline=False,
                )
                field_name = f"{original_field_name} Continued"
                add_text = ""
            add_text += joiner + text
        if add_text:
            embed.add_field(
                field_name, add_text, inline=False,
            )

    @utils.group(aliases=["d&d"])
    @commands.bot_has_permissions(send_messages=True)
    async def dnd(self, ctx:utils.Context):
        """
        The parent group for the D&D commands.
        """

        if ctx.invoked_subcommand is None:
            return await ctx.send_help(ctx.command)

    @dnd.command(name="spell", aliases=["spells"])
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def dnd_spell(self, ctx:utils.Context, *, spell_name:str):
        """
        Gives you information on a D&D spell.
        """

        async with ctx.typing():
            data = await self.send_web_request("spells", spell_name)
        if not data:
            return await ctx.send("I couldn't find any information for that spell.")
        embed = utils.Embed(
            use_random_colour=True,
            title=data['name'],
            description=data['desc'][0],
        ).add_field(
            "Casting Time", data['casting_time'],
        ).add_field(
            "Range", data['range'],
        ).add_field(
            "Components", ', '.join(data['components']),
        ).add_field(
            "Material", data.get('material', 'N/A'),
        ).add_field(
            "Duration", data['duration'],
        ).add_field(
            "Classes", ', '.join([i['name'] for i in data['classes']]),
        ).add_field(
            "Ritual", data['ritual'],
        ).add_field(
            "Concentration", data['concentration'],
        )
        if data.get('higher_level'):
            embed.add_field(
                "Higher Level", "\n".join(data['higher_level']), inline=False,
            )
        elif data.get('damage'):
            text = ""
            if data['damage'].get('damage_at_character_level'):
                text += "\nCharacter level " + ", ".join([f"{i}: {o}" for i, o in data['damage']['damage_at_character_level'].items()])
            if data['damage'].get('damage_at_slot_level'):
                text += "\nSlot level " + ", ".join([f"{i}: {o}" for i, o in data['damage']['damage_at_slot_level'].items()])
            embed.add_field(
                "Damage", text.strip(), inline=False,
            )
        return await ctx.send(embed=embed)

    @dnd.command(name="monster", aliases=["monsters"])
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def dnd_monster(self, ctx:utils.Context, *, monster_name:str):
        """
        Gives you information on a D&D monster.
        """

        async with ctx.typing():
            data = await self.send_web_request("monsters", monster_name)
        if not data:
            return await ctx.send("I couldn't find any information for that monster.")
        embed = utils.Embed(
            use_random_colour=True,
            title=data['name'],
            description="\n".join([
                f"{data['size'].capitalize()} | {data['type']} | {data['hit_points']:,} ({data['hit_dice']}) HP | {data['xp']:,} XP",
                ", ".join([f"{o} {data[i]}" for i, o in self.ATTRIBUTES.items()]),
            ])
        ).add_field(
            "Proficiencies", ", ".join([f"{i['proficiency']['name']} {i['value']}" for i in data['proficiencies']]) or "None",
        ).add_field(
            "Damage Vulnerabilities", "\n".join(data['damage_vulnerabilities']).capitalize() or "None",
        ).add_field(
            "Damage Resistances", "\n".join(data['damage_resistances']).capitalize() or "None",
        ).add_field(
            "Damage Immunities", "\n".join(data['damage_immunities']).capitalize() or "None",
        ).add_field(
            "Condition Immunities", "\n".join([i['name'] for i in data['condition_immunities']]).capitalize() or "None",
        ).add_field(
            "Senses", "\n".join([f"{i.replace('_', ' ').capitalize()} {o}" for i, o in data['senses'].items()]) or "None",
        )
        self.group_field_descriptions(embed, "Actions", data['actions'])
        self.group_field_descriptions(embed, "Legendary Actions", data.get('legendary_actions', list()))
        if data.get('special_abilities'):
            embed.add_field(
                "Special Abilities", "\n".join([f"**{i['name']}**\n{i['desc']}" for i in data['special_abilities'] if i['name'] != 'Spellcasting']) or "None", inline=False,
            )
        spellcasting = [i for i in data.get('special_abilities', list()) if i['name'] == 'Spellcasting']
        if spellcasting:
            spellcasting = spellcasting[0]
            embed.add_field(
                "Spellcasting", spellcasting['desc'].replace('\n\n', '\n'), inline=False,
            )
        return await ctx.send(embed=embed)

    @dnd.command(name="condition", aliases=["conditions"])
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def dnd_condition(self, ctx:utils.Context, *, condition_name:str):
        """
        Gives you information on a D&D condition.
        """

        async with ctx.typing():
            data = await self.send_web_request("conditions", condition_name)
        if not data:
            return await ctx.send("I couldn't find any information for that condition.")
        embed = utils.Embed(
            use_random_colour=True,
            title=data['name'],
            description="\n".join(data['desc']),
        )
        return await ctx.send(embed=embed)

    @dnd.command(name="class", aliases=["classes"])
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def dnd_class(self, ctx:utils.Context, *, class_name:str):
        """
        Gives you information on a D&D class.
        """

        async with ctx.typing():
            data = await self.send_web_request("classes", class_name)
        if not data:
            return await ctx.send("I couldn't find any information for that class.")
        embed = utils.Embed(
            use_random_colour=True,
            title=data['name'],
        ).add_field(
            "Proficiencies", ", ".join([i['name'] for i in data['proficiencies']]),
        ).add_field(
            "Saving Throws", ", ".join([i['name'] for i in data['saving_throws']]),
        ).add_field(
            "Starting Equipment", "\n".join([f"{i['quantity']}x {i['equipment']['name']}" for i in data['starting_equipment']]),
        )
        return await ctx.send(embed=embed)


def setup(bot:utils.Bot):
    x = DNDCommands(bot)
    bot.add_cog(x)
