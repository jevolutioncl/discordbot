import discord
import re
import json
import os
from discord.ext import commands
from discord.ui import Button, View

class FichaCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ID_DEL_CANAL_DE_APROBACION = 1292985338880593960  
        self.ID_DEL_CANAL_PUBLICO = 1292934770812125294        
        self.ID_DEL_CANAL_CREAR_FICHAS = 1292986040835113000   
        self.fichas = {}
        self.ficha_message_id = None
        self.load_data()

    def load_data(self):
        if os.path.exists('fichas_data.json'):
            with open('fichas_data.json', 'r') as f:
                data = json.load(f)
                self.fichas = data.get('fichas', {})
                self.ficha_message_id = data.get('ficha_message_id')

    def save_data(self):
        with open('fichas_data.json', 'w') as f:
            json.dump({
                'fichas': self.fichas,
                'ficha_message_id': self.ficha_message_id
            }, f)

    class ApprovalView(View):
        def __init__(self, user_id, embed, cog):
            super().__init__()
            self.user_id = user_id
            self.embed = embed
            self.cog = cog

        @discord.ui.button(label="Aceptar", style=discord.ButtonStyle.green)
        async def accept_button(self, interaction: discord.Interaction, button: Button):
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("No tienes permisos para hacer esto.", ephemeral=True)
                return

            public_channel = self.cog.bot.get_channel(self.cog.ID_DEL_CANAL_PUBLICO)
            user = self.cog.bot.get_user(self.user_id)
            if public_channel:
                self.embed.description = None  

                await public_channel.send(embed=self.embed)

                await interaction.response.send_message(f"Ficha de {user.display_name} aprobada y publicada.", ephemeral=True)
                try:
                    await user.send("Tu ficha ha sido aprobada y publicada.")
                except discord.Forbidden:
                    await interaction.followup.send(f"No se pudo enviar un mensaje privado a {user.display_name}.")

                await interaction.message.delete()

                self.stop()
            else:
                await interaction.response.send_message("No se ha encontrado el canal público para publicar la ficha.", ephemeral=True)

        @discord.ui.button(label="Rechazar", style=discord.ButtonStyle.red)
        async def reject_button(self, interaction: discord.Interaction, button: Button):
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("No tienes permisos para hacer esto.", ephemeral=True)
                return

            user = self.cog.bot.get_user(self.user_id)
            try:
                await user.send("Lo sentimos, tu ficha ha sido rechazada por un administrador.")
            except discord.Forbidden:
                await interaction.followup.send(f"No se pudo enviar un mensaje privado a {user.display_name}.")
            await interaction.response.send_message(f"Ficha de {user.display_name} rechazada.", ephemeral=True)

            await interaction.message.delete()

            self.stop()

    class CreateFichaView(View):
        def __init__(self, bot):
            super().__init__()
            self.bot = bot

        @discord.ui.button(label="Crear Ficha", style=discord.ButtonStyle.green)
        async def create_button(self, interaction: discord.Interaction, button: Button):
            await interaction.response.send_message("Vamos a comenzar a crear tu ficha en privado.", ephemeral=True)
            await self.bot.get_cog('FichaCog').create_profile(interaction.user)

    async def ensure_ficha_message(self):
        ficha_channel = self.bot.get_channel(self.ID_DEL_CANAL_CREAR_FICHAS)
        if ficha_channel:
            await ficha_channel.purge(limit=100, check=lambda m: m.author == self.bot.user)

            view = self.CreateFichaView(self.bot)
            info_message = (
                "Para crear tu ficha de corredor, presiona el botón a continuación.\n"
                "Se te pedirá la siguiente información:\n"
                "- **Nombre y apellido** (Formato: Nombre_Apellido)\n"
                "- **Apodo**\n"
                "- **Edad** (entre 14 y 100 años)\n"
                "- **Número de teléfono**\n"
                "- **Coches** (puedes listar varios separados por comas)\n"
                "- **Link del PCU del servidor**\n"
                "- **Link del avatar** (opcional)\n\n"
                "Puedes escribir 'cancelar' en cualquier momento para detener el proceso."
            )
            ficha_message = await ficha_channel.send(info_message, view=view)
            self.ficha_message_id = ficha_message.id
            self.save_data()

    @commands.Cog.listener()
    async def on_ready(self):
        await self.ensure_ficha_message()

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def modificar_ficha(self, ctx, *, nombre_apellido: str):
        """Permite modificar una ficha publicada según el Nombre_Apellido"""
        user_id = None
        ficha = None
        for uid, f in self.fichas.items():
            if f['nombre_apellido'].lower() == nombre_apellido.lower():
                user_id = uid
                ficha = f
                break
        if user_id and ficha:
            user = self.bot.get_user(int(user_id))
            if user:
                await ctx.send(f"Vamos a modificar la ficha de {ficha['nombre_apellido']} en privado.")
                await self.modify_profile(ctx.author, user, ficha)
            else:
                await ctx.send("No se ha podido encontrar al usuario asociado a esa ficha.")
        else:
            await ctx.send("No se ha encontrado ninguna ficha con ese Nombre_Apellido.")

    @commands.command()
    async def crear_ficha(self, ctx):
        """Comienza la creación de la ficha del corredor"""
        await ctx.send("Vamos a comenzar la creación de tu ficha en privado.")
        await self.create_profile(ctx.author)

    async def create_profile(self, user, modificar=False):
        channel = await user.create_dm()

        def check(m):
            return m.author == user and isinstance(m.channel, discord.DMChannel)

        await channel.send("Vamos a comenzar a crear tu ficha. Puedes escribir 'cancelar' en cualquier momento para detener el proceso.")

        await channel.send("¿Cuál es tu nombre y apellido? (Formato: Nombre_Apellido)")
        while True:
            nombre_apellido = await self.bot.wait_for('message', check=check)
            if nombre_apellido.content.lower() == "cancelar":
                await channel.send("Proceso de creación de ficha cancelado.")
                return
            if re.match(r"^[A-Za-z]+_[A-Za-z]+$", nombre_apellido.content):
                break
            else:
                await channel.send("Formato incorrecto. Asegúrate de usar el formato: Nombre_Apellido")

        await channel.send("¿Cuál es tu apodo?")
        apodo = await self.bot.wait_for('message', check=check)
        if apodo.content.lower() == "cancelar":
            await channel.send("Proceso de creación de ficha cancelado.")
            return

        await channel.send("¿Cuál es tu edad? (Debe estar entre 14 y 80)")
        while True:
            edad = await self.bot.wait_for('message', check=check)
            if edad.content.lower() == "cancelar":
                await channel.send("Proceso de creación de ficha cancelado.")
                return
            if edad.content.isdigit() and 14 <= int(edad.content) <= 80:
                break
            else:
                await channel.send("Por favor, ingresa un número válido para la edad entre 14 y 80.")

        await channel.send("¿Cuál es tu número de teléfono? (Debe ser un número)")
        while True:
            telefono = await self.bot.wait_for('message', check=check)
            if telefono.content.lower() == "cancelar":
                await channel.send("Proceso de creación de ficha cancelado.")
                return
            if telefono.content.isdigit():
                break
            else:
                await channel.send("Por favor, ingresa un número válido para el teléfono.")

        await channel.send("¿Cuáles son tus coches? (Puedes separar los coches con comas si tienes más de uno)")
        coches = await self.bot.wait_for('message', check=check)
        if coches.content.lower() == "cancelar":
            await channel.send("Proceso de creación de ficha cancelado.")
            return
        
        await channel.send("Ingresa el link del PCU del servidor")
        while True:
            link_pcu = await self.bot.wait_for('message', check=check)
            if link_pcu.content.lower() == "cancelar":
                await channel.send("Proceso de creación de ficha cancelado.")
                return
            if re.match(r"^https?://", link_pcu.content):
                break
            else:
                await channel.send("Por favor, ingresa un link válido para el PCU.")

        await channel.send("Ingresa el link del avatar (opcional, envía 'ninguno' si no deseas agregarlo)")
        while True:
            avatar = await self.bot.wait_for('message', check=check)
            if avatar.content.lower() == "cancelar":
                await channel.send("Proceso de creación de ficha cancelado.")
                return
            if avatar.content.lower() == "ninguno" or re.match(r"^https?://", avatar.content):
                break
            else:
                await channel.send("Por favor, ingresa un link válido o envía 'ninguno' si no deseas agregar un avatar.")

        avatar_link = None if avatar.content.lower() == "ninguno" else avatar.content

        # Crear el embed de la ficha
        embed = discord.Embed(title=f"Ficha de {nombre_apellido.content}", color=discord.Color.orange())
        embed.add_field(name="Nombre", value=nombre_apellido.content, inline=False)
        embed.add_field(name="Apodo", value=apodo.content, inline=True)
        embed.add_field(name="Edad", value=f"{edad.content} años", inline=True)
        embed.add_field(name="Teléfono", value=telefono.content, inline=True)
        embed.add_field(name="Coches", value=coches.content, inline=False)
        embed.add_field(name="Link PCU", value=link_pcu.content, inline=False)
        embed.add_field(name="Bleeter", value=user.mention, inline=False)

        if avatar_link:
            embed.set_thumbnail(url=avatar_link)
        if not modificar:
            embed.description = "Pendiente de aprobación"

        self.fichas[str(user.id)] = {
            "nombre_apellido": nombre_apellido.content,
            "apodo": apodo.content,
            "edad": edad.content,
            "telefono": telefono.content,
            "coches": coches.content.split(','),
            "link_pcu": link_pcu.content,
            "avatar": avatar_link
        }
        self.save_data()  # Guarda la ficha en el archivo

        if not modificar:
            approval_channel = self.bot.get_channel(self.ID_DEL_CANAL_DE_APROBACION)
            if approval_channel:
                view = self.ApprovalView(user.id, embed, self)
                await approval_channel.send(embed=embed, view=view)
                await channel.send("Tu ficha ha sido enviada para aprobación. Te notificaremos cuando haya sido revisada.")
            else:
                await channel.send("No se ha podido encontrar el canal de aprobación.")
        else:
            public_channel = self.bot.get_channel(self.ID_DEL_CANAL_PUBLICO)
            if public_channel:
                async for message in public_channel.history(limit=200):
                    if message.embeds:
                        if message.embeds[0].title == f"Ficha de {nombre_apellido.content}":
                            await message.edit(embed=embed)
                            await channel.send("Tu ficha ha sido actualizada en el canal público.")
                            break
                else:
                    await channel.send("No se encontró la ficha en el canal público para actualizar.")
            else:
                await channel.send("No se ha podido encontrar el canal público.")

    async def modify_profile(self, admin_user, target_user, ficha):
        channel = await admin_user.create_dm()

        def check(m):
            return m.author == admin_user and isinstance(m.channel, discord.DMChannel)

        await channel.send(f"Vamos a modificar la ficha de {ficha['nombre_apellido']}. Puedes escribir 'cancelar' en cualquier momento para detener el proceso.")

        campos = [
            ("Nombre y apellido", "nombre_apellido"),
            ("Apodo", "apodo"),
            ("Edad", "edad"),
            ("Teléfono", "telefono"),
            ("Coches", "coches"),
            ("Link del PCU", "link_pcu"),
            ("Link del avatar", "avatar")
        ]

        for campo_nombre, campo_clave in campos:
            current_value = ficha[campo_clave]
            if campo_clave == "avatar":
                current_display = current_value if current_value else "Ninguno"
            elif campo_clave == "coches":
                current_display = ", ".join(ficha[campo_clave])
            else:
                current_display = ficha[campo_clave]

            await channel.send(f"**{campo_nombre}** (Actual: {current_display})\n¿Deseas modificar este campo? Responde 'sí' para modificar o 'no' para mantenerlo.")

            while True:
                decision = await self.bot.wait_for('message', check=check)
                if decision.content.lower() == "cancelar":
                    await channel.send("Proceso de modificación de ficha cancelado.")
                    return
                elif decision.content.lower() in ["sí", "si", "s", "yes", "y"]:
                    # Proceder a modificar el campo
                    break
                elif decision.content.lower() in ["no", "n"]:
                    # Saltar al siguiente campo
                    break
                else:
                    await channel.send("Por favor, responde 'sí' o 'no'.")

            if decision.content.lower() in ["no", "n"]:
                continue  # Saltar al siguiente campo

            # Solicitar el nuevo valor para el campo
            if campo_clave == "nombre_apellido":
                prompt = f"Ingrese el nuevo valor para **{campo_nombre}** (Formato: Nombre_Apellido):"
            elif campo_clave == "edad":
                prompt = f"Ingrese el nuevo valor para **{campo_nombre}** (Debe estar entre 14 y 100):"
            elif campo_clave == "telefono":
                prompt = f"Ingrese el nuevo valor para **{campo_nombre}** (Debe ser un número):"
            elif campo_clave == "coches":
                prompt = f"Ingrese el nuevo valor para **{campo_nombre}** (Puedes separar los coches con comas):"
            elif campo_clave == "link_pcu":
                prompt = f"Ingrese el nuevo valor para **{campo_nombre}** (Debe ser un link válido):"
            elif campo_clave == "avatar":
                prompt = f"Ingrese el nuevo valor para **{campo_nombre}** (Opcional, envía 'ninguno' si no deseas agregarlo):"
            else:
                prompt = f"Ingrese el nuevo valor para **{campo_nombre}**:"

            await channel.send(prompt)
            while True:
                respuesta = await self.bot.wait_for('message', check=check)
                if respuesta.content.lower() == "cancelar":
                    await channel.send("Proceso de modificación de ficha cancelado.")
                    return
                # Validaciones según el campo
                if campo_clave == "nombre_apellido":
                    if re.match(r"^[A-Za-z]+_[A-Za-z]+$", respuesta.content):
                        ficha[campo_clave] = respuesta.content
                        break
                    else:
                        await channel.send("Formato incorrecto. Asegúrate de usar el formato: Nombre_Apellido")
                elif campo_clave == "edad":
                    if respuesta.content.isdigit() and 14 <= int(respuesta.content) <= 100:
                        ficha[campo_clave] = respuesta.content
                        break
                    else:
                        await channel.send("Por favor, ingresa un número válido para la edad entre 14 y 100.")
                elif campo_clave == "telefono":
                    if respuesta.content.isdigit():
                        ficha[campo_clave] = respuesta.content
                        break
                    else:
                        await channel.send("Por favor, ingresa un número válido para el teléfono.")
                elif campo_clave == "coches":
                    ficha[campo_clave] = [coche.strip() for coche in respuesta.content.split(',')]
                    break
                elif campo_clave == "link_pcu":
                    if re.match(r"^https?://", respuesta.content):
                        ficha[campo_clave] = respuesta.content
                        break
                    else:
                        await channel.send("Por favor, ingresa un link válido para el PCU.")
                elif campo_clave == "avatar":
                    if respuesta.content.lower() == "ninguno":
                        ficha[campo_clave] = None
                        break
                    elif re.match(r"^https?://", respuesta.content):
                        ficha[campo_clave] = respuesta.content
                        break
                    else:
                        await channel.send("Por favor, ingresa un link válido o envía 'ninguno' si no deseas agregar el avatar.")
                else:
                    # Para cualquier otro campo sin validación específica
                    ficha[campo_clave] = respuesta.content
                    break

        # Actualizar los datos persistentes
        self.fichas[str(target_user.id)] = ficha
        self.save_data()

        embed = discord.Embed(title=f"Ficha de {ficha['nombre_apellido']}", color=discord.Color.orange())
        embed.add_field(name="Nombre", value=ficha['nombre_apellido'], inline=False)
        embed.add_field(name="Apodo", value=ficha['apodo'], inline=True)
        embed.add_field(name="Edad", value=f"{ficha['edad']} años", inline=True)
        embed.add_field(name="Teléfono", value=ficha['telefono'], inline=True)
        embed.add_field(name="Coches", value=", ".join(ficha['coches']), inline=False)
        embed.add_field(name="Link PCU", value=ficha['link_pcu'], inline=False)
        embed.add_field(name="Bleeter", value=target_user.mention, inline=False)

        if ficha['avatar']:
            embed.set_thumbnail(url=ficha['avatar'])

        public_channel = self.bot.get_channel(self.ID_DEL_CANAL_PUBLICO)
        if public_channel:
            async for message in public_channel.history(limit=200):
                if message.embeds:
                    if message.embeds[0].title == f"Ficha de {ficha['nombre_apellido']}":
                        await message.edit(embed=embed)
                        await channel.send("La ficha ha sido actualizada en el canal público.")
                        break
            else:
                await channel.send("No se encontró la ficha en el canal público para actualizar.")
        else:
            await channel.send("No se ha podido encontrar el canal público.")

async def setup(bot):
    await bot.add_cog(FichaCog(bot))
