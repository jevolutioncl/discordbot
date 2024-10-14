import discord
from discord.ext import commands

class LimpiezaCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='limpiar')
    @commands.has_permissions(manage_messages=True)  # El usuario debe tener permisos para gestionar mensajes
    async def limpiar_mensajes(self, ctx, cantidad: int):
        """
        Elimina una cantidad específica de mensajes en el canal, incluidos los mensajes del bot.
        Uso: !limpiar mensajes [cantidad]
        """
        if cantidad < 1:
            await ctx.send("Debes especificar una cantidad válida de mensajes a eliminar.")
            return
        
        def is_bot_or_user_message(message):
            return message.author == self.bot.user or not message.author.bot

        try:
            deleted = await ctx.channel.purge(limit=cantidad + 1, check=is_bot_or_user_message)  
            await ctx.send(f"{len(deleted) - 1} mensajes eliminados, incluyendo mensajes del bot.", delete_after=5)  
        except discord.Forbidden:
            await ctx.send("No tengo permisos para eliminar mensajes.")
        except discord.HTTPException as e:
            await ctx.send(f"Ocurrió un error al intentar eliminar mensajes: {e}")

# Cargar el cog
async def setup(bot):
    await bot.add_cog(LimpiezaCog(bot))
