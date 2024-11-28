import discord
from discord.ext import commands
import random
import json
from datetime import datetime, timedelta
import os

class HotwireCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.orders_channel_id = 1308513443028140083  # ID del canal para los pedidos
        self.history_channel_id = 1308529052998570105  # ID del canal para el historial de pedidos
        self.pedidos = self.cargar_pedidos()

    def cargar_pedidos(self):
        """Carga los pedidos desde el archivo pedidos.json y convierte las claves a enteros."""
        if not os.path.exists("pedidos.json"):
            return {}
        with open("pedidos.json", "r", encoding="utf-8") as file:
            data = json.load(file)
            return {int(k): v for k, v in data.items()}

    def guardar_pedidos(self):
        """Guarda los pedidos en el archivo pedidos.json."""
        pedidos_guardar = {str(k): v for k, v in self.pedidos.items()}
        with open("pedidos.json", "w", encoding="utf-8") as file:
            json.dump(pedidos_guardar, file, indent=4, ensure_ascii=False)

    def generar_precio(self, price_range):
        """Genera un precio aleatorio basado en el rango de precios."""
        return random.randint(price_range[0], price_range[1])

    async def mover_a_historial(self, pedido, motivo):
        """Mueve un pedido al canal de historial."""
        channel = self.bot.get_channel(self.history_channel_id)
        if not channel:
            return

        # Construir la lista de personas que completaron el pedido (si aplica)
        completado_por = pedido.get("completed_by", [])
        completado_texto = ", ".join(completado_por) if completado_por else "No especificado"

        embed = discord.Embed(
            title="📜 **Pedido Movido al Historial** 📜",
            description=(
                f"**ID:** {pedido['id']}\n"
                f"**Nombre:** {pedido['name']}\n"
                f"**Tipo:** {pedido['type']}\n"
                f"**Precio Mercado Negro:** ${pedido['price']:,}\n"
                f"**Motivo:** {motivo}\n"
                f"**Completado por:** {completado_texto}"
            ),
            color=discord.Color.green() if motivo == "Completado" else discord.Color.orange()
        )

        if "image" in pedido and pedido["image"]:
            embed.set_thumbnail(url=pedido["image"])

        embed.set_footer(text="Historial de pedidos.")
        await channel.send(embed=embed)

    @commands.command(name="crear_pedido")
    async def crear_pedido(self, ctx):
        """Genera un pedido aleatorio de coche."""
        try:
            with open("coches.json", "r", encoding="utf-8") as file:
                cars = json.load(file)

            car = random.choice(cars)
            precio = self.generar_precio(car['price_range'])
            time_limit = datetime.now() + timedelta(hours=24)
            timestamp = int(time_limit.timestamp())

            pedido_id = random.randint(1000, 9999)
            self.pedidos[pedido_id] = {
                "id": pedido_id,
                "name": car['name'],
                "type": car['type'],
                "price": precio,
                "status": "Pendiente",
                "completed_by": [],
                "image": car.get("image", None)
            }
            self.guardar_pedidos()

            embed = discord.Embed(
                title="🚗 **Nuevo Pedido del Mercado Negro** 🚗",
                description=(
                    f"**ID:** {pedido_id}\n"
                    f"**Nombre:** {car['name']}\n"
                    f"**Tipo:** {car['type']}\n"
                    f"**Precio Mercado Negro:** ${precio:,}\n"
                    f"**Tiempo límite:** <t:{timestamp}:R>"
                ),
                color=discord.Color.red()
            )

            if "image" in car and car["image"]:
                embed.set_thumbnail(url=car["image"])

            embed.set_footer(text="¡Apresúrate! El mercado negro no espera.")

            channel = self.bot.get_channel(self.orders_channel_id)
            if channel is None:
                raise ValueError(f"El canal con ID {self.orders_channel_id} no se encontró.")
            mensaje = await channel.send(embed=embed)
            self.pedidos[pedido_id]['message_id'] = mensaje.id
            self.guardar_pedidos()

        except Exception as e:
            await ctx.send(f"Error al generar el pedido: {e}")

    @commands.command(name="listar_pedidos")
    async def listar_pedidos(self, ctx):
        """Lista todos los pedidos activos."""
        if not self.pedidos:
            await ctx.send("⚠️ No hay pedidos activos.")
            return

        mensaje = ""
        for pid, data in self.pedidos.items():
            mensaje += (
                f"**ID:** {pid} | **Nombre:** {data['name']} | "
                f"**Estado:** {data['status']}\n"
            )

        if mensaje:
            await ctx.send(f"**Pedidos Activos:**\n{mensaje}")
        else:
            await ctx.send("⚠️ No se encontraron pedidos activos.")

    @commands.command(name="completar_pedido")
    @commands.has_permissions(administrator=True)
    async def completar_pedido(self, ctx, pedido_id: int, *nombres):
        """Marca un pedido como completado e incluye los nombres de quienes lo completaron."""
        if pedido_id in self.pedidos:
            pedido = self.pedidos[pedido_id]
            pedido['status'] = "Completado"
            pedido['completed_by'] = list(nombres)  # Agregar las personas que lo completaron
            await self.mover_a_historial(pedido, "Completado")
            del self.pedidos[pedido_id]
            self.guardar_pedidos()

            await ctx.send(
                f"✅ El pedido {pedido_id} ha sido marcado como completado por {', '.join(nombres)}."
            )
        else:
            await ctx.send("Pedido no encontrado.")

    @commands.command(name="borrar_pedido")
    @commands.has_permissions(administrator=True)
    async def borrar_pedido(self, ctx, pedido_id: int):
        """Elimina un pedido de la lista."""
        if pedido_id in self.pedidos:
            pedido = self.pedidos[pedido_id]
            await self.mover_a_historial(pedido, "Expirado")
            del self.pedidos[pedido_id]
            self.guardar_pedidos()
            await ctx.send(f"❌ El pedido {pedido_id} ha sido eliminado.")
        else:
            await ctx.send("Pedido no encontrado.")

    @commands.command(name="limpiar_pedidos")
    @commands.has_permissions(administrator=True)
    async def limpiar_pedidos(self, ctx):
        """Elimina todos los pedidos activos y limpia el archivo pedidos.json."""
        self.pedidos.clear()
        self.guardar_pedidos()
        await ctx.send("🗑️ Todos los pedidos han sido eliminados.")

# Setup del Cog
async def setup(bot):
    await bot.add_cog(HotwireCog(bot))
