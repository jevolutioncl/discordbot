# info.py

import discord
from discord.ext import commands

class InfoCog(commands.Cog):
    """Cog para comandos de información del bot."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def info(self, ctx):
        """Proporciona información sobre los comandos disponibles y el estado del bot."""
        embed = discord.Embed(title="Información del Bot", color=discord.Color.blue())

        # Sección de Comandos de Fichas
        ficha_commands = (
            "**!crear_ficha**: Inicia el proceso de creación de tu ficha de corredor.\n"
            "**!modificar_ficha Nombre_Apellido**: (Administradores) Modifica una ficha existente.\n"
        )
        embed.add_field(name="Comandos de Fichas", value=ficha_commands, inline=False)

        # Sección de Comandos Generales
        general_commands = (
            "**!info**: Muestra este mensaje de información.\n"
            "**!limpiar cantidad**: (Administradores) Limpia la cantidad especificada de mensajes en un canal.\n"
        )
        embed.add_field(name="Comandos Generales", value=general_commands, inline=False)

        # Puedes agregar más secciones aquí si tienes más comandos

        embed.set_footer(text="Bot de LSOverdrive League.")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(InfoCog(bot))
