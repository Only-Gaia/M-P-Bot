import discord
import asyncio
import json
import os
import time
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Select, Button, Modal, TextInput

TICKET_CATEGORY_NAME = "🎫 Ticket"
CONFIG_FILE = "ticket_config.json"
CLAIM_COOLDOWN_SECONDS = 5


# ---------------------- GESTIONE CONFIGURAZIONE (JSON) ----------------------
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}


def save_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


config = load_config()


def get_guild_config(guild_id: int):
    gid = str(guild_id)
    if gid not in config:
        config[gid] = {
            "staff_roles": [],
            "review_channel": None,
            "tickets": {},
            "ratings": {"count": 0, "total": 0},
        }
        save_config(config)
    else:
        config[gid].setdefault("staff_roles", [])
        config[gid].setdefault("review_channel", None)
        config[gid].setdefault("tickets", {})
        config[gid].setdefault("ratings", {"count": 0, "total": 0})
    return config[gid]


def is_staff(member: discord.Member, guild_id: int) -> bool:
    gconf = get_guild_config(guild_id)
    staff_role_ids = gconf.get("staff_roles", [])
    return any(r.id in staff_role_ids for r in member.roles)


def update_and_get_average(guild_id: int, stars: int):
    gconf = get_guild_config(guild_id)
    ratings = gconf.setdefault("ratings", {"count": 0, "total": 0})
    ratings["count"] += 1
    ratings["total"] += stars
    save_config(config)
    return round(ratings["total"] / ratings["count"], 1)


async def resolve_member(guild: discord.Guild, member_id):
    if member_id is None:
        return None
    member = guild.get_member(member_id)
    if member is None:
        try:
            member = await guild.fetch_member(member_id)
        except (discord.NotFound, discord.HTTPException):
            member = None
    return member


async def restrict_channel_to_claimer(guild: discord.Guild, channel: discord.TextChannel, gconf: dict, claimer: discord.Member):
    """Al claim: nasconde il canale a tutti i ruoli staff, lascia visibile solo a chi ha claimato."""
    staff_role_ids = gconf.get("staff_roles", [])
    for rid in staff_role_ids:
        role = guild.get_role(rid)
        if role:
            try:
                await channel.set_permissions(role, view_channel=False, send_messages=False)
            except discord.Forbidden:
                pass
    try:
        await channel.set_permissions(claimer, view_channel=True, send_messages=True, read_message_history=True)
    except discord.Forbidden:
        pass


async def restore_staff_access(guild: discord.Guild, channel: discord.TextChannel, gconf: dict, previous_claimer_id):
    """All'unclaim: ridà accesso a tutti i ruoli staff e rimuove l'overwrite dedicato al vecchio claimer."""
    staff_role_ids = gconf.get("staff_roles", [])
    for rid in staff_role_ids:
        role = guild.get_role(rid)
        if role:
            try:
                await channel.set_permissions(role, view_channel=True, send_messages=True, read_message_history=True)
            except discord.Forbidden:
                pass
    if previous_claimer_id:
        member = await resolve_member(guild, previous_claimer_id)
        if member:
            try:
                await channel.set_permissions(member, overwrite=None)
            except (discord.Forbidden, discord.HTTPException):
                pass


# ---------------------- SISTEMA RECENSIONI ----------------------
class RatingReasonModal(Modal, title="Lascia una recensione"):
    reason = TextInput(
        label="Perché hai dato questo punteggio?",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=500
    )

    def __init__(self, stars: int, opener: discord.Member, claimed_by: discord.Member = None):
        super().__init__()
        self.stars = stars
        self.opener = opener
        self.claimed_by = claimed_by

    async def on_submit(self, interaction: discord.Interaction):
        channel = interaction.channel
        guild = interaction.guild
        gconf = get_guild_config(guild.id)

        stars_display = "⭐" * self.stars
        avg = update_and_get_average(guild.id, self.stars)

        embed = discord.Embed(title="⭐ Una nuova recensione è arrivata", color=discord.Color.gold())
        embed.add_field(name="👤 Staffer", value=self.claimed_by.mention if self.claimed_by else "Nessuno", inline=False)
        embed.add_field(name="👤 Utente", value=self.opener.mention, inline=False)
        embed.add_field(name="⭐ Stelle", value=f"{stars_display} ({self.stars}/5)", inline=False)
        embed.add_field(name="ℹ️ Media stelle", value=f"{avg}/5", inline=False)
        embed.add_field(name="❓ Motivazione", value=self.reason.value, inline=False)

        review_channel_id = gconf.get("review_channel")
        if review_channel_id:
            review_channel = guild.get_channel(review_channel_id)
            if review_channel:
                await review_channel.send(embed=embed)

        # pulizia dati ticket
        gconf.get("tickets", {}).pop(str(channel.id), None)
        save_config(config)

        await interaction.response.send_message("✅ Grazie per la recensione! Il ticket verrà chiuso tra pochi secondi...")
        await asyncio.sleep(5)
        try:
            await channel.delete()
        except (discord.NotFound, discord.Forbidden):
            pass


class RatingButton(Button):
    def __init__(self, stars: int, opener: discord.Member, claimed_by: discord.Member):
        super().__init__(label=str(stars), emoji="⭐", style=discord.ButtonStyle.secondary, custom_id=f"rate_{stars}")
        self.stars = stars
        self.opener = opener
        self.claimed_by = claimed_by

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(RatingReasonModal(self.stars, self.opener, self.claimed_by))


class RatingView(View):
    def __init__(self, opener: discord.Member, claimed_by: discord.Member = None):
        super().__init__(timeout=600)
        self.opener = opener
        self.claimed_by = claimed_by
        for i in range(1, 6):
            self.add_item(RatingButton(i, opener, claimed_by))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.opener and interaction.user.id != self.opener.id:
            await interaction.response.send_message(
                "❌ Solo chi ha aperto il ticket può lasciare una recensione.", ephemeral=True
            )
            return False
        return True


# ---------------------- BOTTONI COMUNI DI GESTIONE TICKET ----------------------
class TicketManageView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.green, custom_id="ticket_claim")
    async def claim(self, interaction: discord.Interaction, button: Button):
        if not is_staff(interaction.user, interaction.guild.id):
            return await interaction.response.send_message("❌ Non hai i permessi per fare claim.", ephemeral=True)

        gconf = get_guild_config(interaction.guild.id)
        ticket = gconf["tickets"].setdefault(str(interaction.channel.id), {})

        if ticket.get("claimed_by_id"):
            return await interaction.response.send_message("❌ Questo ticket è già stato preso in carico.", ephemeral=True)

        cooldown_until = ticket.get("claim_cooldown_until", 0)
        remaining = cooldown_until - time.time()
        if remaining > 0:
            return await interaction.response.send_message(
                f"⏳ Aspetta ancora {remaining:.1f}s prima di poter fare claim.", ephemeral=True
            )

        ticket["claimed_by_id"] = interaction.user.id
        save_config(config)

        await restrict_channel_to_claimer(interaction.guild, interaction.channel, gconf, interaction.user)

        await interaction.channel.send(
            f"✅ Ticket preso in carico da {interaction.user.mention}.\n"
            f"🔒 Da ora solo {interaction.user.mention} può vedere e scrivere in questo ticket."
        )
        await interaction.response.defer()

    @discord.ui.button(label="Unclaim", style=discord.ButtonStyle.gray, custom_id="ticket_unclaim")
    async def unclaim(self, interaction: discord.Interaction, button: Button):
        if not is_staff(interaction.user, interaction.guild.id):
            return await interaction.response.send_message("❌ Non hai i permessi.", ephemeral=True)

        gconf = get_guild_config(interaction.guild.id)
        ticket = gconf["tickets"].setdefault(str(interaction.channel.id), {})

        previous_claimer_id = ticket.get("claimed_by_id")
        ticket["claimed_by_id"] = None
        ticket["claim_cooldown_until"] = time.time() + CLAIM_COOLDOWN_SECONDS
        save_config(config)

        await restore_staff_access(interaction.guild, interaction.channel, gconf, previous_claimer_id)

        await interaction.channel.send(
            f"↩️ Ticket rilasciato da {interaction.user.mention}.\n"
            f"👀 Tutto lo staff può ora rivedere il ticket. Si potrà fare nuovamente claim tra "
            f"{CLAIM_COOLDOWN_SECONDS} secondi."
        )
        await interaction.response.defer()

    @discord.ui.button(label="Close", style=discord.ButtonStyle.red, custom_id="ticket_close")
    async def close(self, interaction: discord.Interaction, button: Button):
        gconf = get_guild_config(interaction.guild.id)
        ticket = gconf["tickets"].get(str(interaction.channel.id), {})

        opener = await resolve_member(interaction.guild, ticket.get("opener_id"))
        claimed_by = await resolve_member(interaction.guild, ticket.get("claimed_by_id"))

        if opener is None:
            opener = interaction.user  # fallback: chi ha premuto Close

        await interaction.response.send_message(
            f"🔒 Chiusura richiesta da {interaction.user.mention}.\n"
            f"{opener.mention}, prima di chiudere lascia una recensione da 1 a 5 stelle:",
            view=RatingView(opener, claimed_by)
        )

    @discord.ui.button(label="Close with reason", style=discord.ButtonStyle.red, custom_id="ticket_close_reason")
    async def close_with_reason(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(CloseReasonModal())

    @discord.ui.button(label="Add user", style=discord.ButtonStyle.blurple, custom_id="ticket_add_user")
    async def add_user(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(AddUserModal())


class CloseReasonModal(Modal, title="Chiudi ticket con motivazione"):
    reason = TextInput(label="Motivazione", style=discord.TextStyle.paragraph, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"🔒 Ticket in chiusura tra 5 secondi.\n**Motivo:** {self.reason.value}"
        )
        channel = interaction.channel
        gconf = get_guild_config(interaction.guild.id)
        gconf["tickets"].pop(str(channel.id), None)
        save_config(config)
        await asyncio.sleep(5)
        await channel.delete()


class AddUserModal(Modal, title="Aggiungi utente al ticket"):
    user_id = TextInput(label="ID o menzione utente", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            uid = int(self.user_id.value.strip("<@!>"))
            member = interaction.guild.get_member(uid)
            if member is None:
                return await interaction.response.send_message("❌ Utente non trovato.", ephemeral=True)
            await interaction.channel.set_permissions(member, view_channel=True, send_messages=True, read_message_history=True)
            await interaction.response.send_message(f"✅ {member.mention} è stato aggiunto al ticket.")
        except ValueError:
            await interaction.response.send_message("❌ ID non valido.", ephemeral=True)


# ---------------------- FUNZIONE CREAZIONE CANALE TICKET ----------------------
async def create_ticket_channel(interaction: discord.Interaction, prefix: str, topic: str):
    guild = interaction.guild
    gconf = get_guild_config(guild.id)

    staff_role_ids = gconf.get("staff_roles", [])
    staff_roles = [guild.get_role(rid) for rid in staff_role_ids if guild.get_role(rid)]

    category = discord.utils.get(guild.categories, name=TICKET_CATEGORY_NAME)
    if category is None:
        category = await guild.create_category(TICKET_CATEGORY_NAME)

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
    }
    for role in staff_roles:
        overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

    channel = await guild.create_text_channel(
        name=f"{prefix}-{interaction.user.name}",
        category=category,
        overwrites=overwrites,
        topic=topic
    )

    gconf["tickets"][str(channel.id)] = {"opener_id": interaction.user.id, "claimed_by_id": None}
    save_config(config)

    embed = discord.Embed(
        title=f"🎫 {topic}",
        description=f"Ticket aperto da {interaction.user.mention}\nUno staff member ti risponderà a breve.",
        color=discord.Color.blurple()
    )

    role_mentions = " ".join(role.mention for role in staff_roles)

    await channel.send(
        content=f"{interaction.user.mention} {role_mentions}".strip(),
        embed=embed,
        view=TicketManageView()
    )

    await interaction.response.send_message(f"✅ Ticket creato: {channel.mention}", ephemeral=True)


# ---------------------- PANNELLO TICKET PRINCIPALE (SELECT MENU) ----------------------
class MainTicketSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Aiuto generale", value="aiuto", emoji="❓"),
            discord.SelectOption(label="Segnala utente", value="segnala", emoji="🚨"),
            discord.SelectOption(label="Reclama giveaway", value="giveaway", emoji="🎁"),
            discord.SelectOption(label="Provino staff", value="provino", emoji="📋"),
            discord.SelectOption(label="Partnership", value="partnership", emoji="🤝"),
            discord.SelectOption(label="Idee server", value="idee", emoji="💡"),
        ]
        super().__init__(placeholder="Seleziona il motivo del ticket...", options=options, custom_id="main_ticket_select")

    async def callback(self, interaction: discord.Interaction):
        topics = {
            "aiuto": "Aiuto generale",
            "segnala": "Segnalazione utente",
            "giveaway": "Reclamo giveaway",
            "provino": "Provino staff",
            "partnership": "Partnership",
            "idee": "Idee server"
        }
        await create_ticket_channel(interaction, self.values[0], topics[self.values[0]])


class MainTicketView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(MainTicketSelect())


# ---------------------- COG ----------------------
class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        # Registra le view persistenti (necessario dopo un riavvio del bot)
        self.bot.add_view(TicketManageView())
        self.bot.add_view(MainTicketView())

    # ---------------------- COMANDI PANNELLI ----------------------
    @commands.hybrid_command(name="pannelloticket", description="Invia il pannello ticket principale")
    @commands.has_permissions(administrator=True)
    async def pannello_ticket(self, ctx):
        embed = discord.Embed(
            title="🎫 Apri un ticket",
            description=(
                "Aprendo ticket qua puoi richiedere:\n\n"
                "❓| Aiuto Generale\n"
                "🚨| Segnala Utente\n"
                "🎁| Reclama Giveaway\n"
                "📋| Provino Staff\n"
                "🤝| Partnership\n\n"
                "⚠️ ATTENZIONE: ⚠️ Ci teniamo il diritto di chiudere i ticket aperti inutilmente"
            ),
            color=discord.Color.blurple()
        )
        await ctx.send(embed=embed, view=MainTicketView())

    # ---------------------- COMANDI CONFIGURAZIONE RUOLI STAFF ----------------------
    # NOTA: con "/" Discord non supporta un numero variabile di parametri, quindi
    # il comando accetta fino a 15 ruoli come opzioni singole (la prima obbligatoria,
    # le altre facoltative). Con "." puoi comunque scrivere fino a 15 menzioni di
    # ruolo in fila, nello stesso ordine.
    @commands.hybrid_command(name="rolestaffconfig", description="Configura fino a 15 ruoli staff da pingare nei ticket")
    @commands.has_permissions(administrator=True)
    @app_commands.describe(
        role1="Ruolo staff", role2="Ruolo staff", role3="Ruolo staff", role4="Ruolo staff",
        role5="Ruolo staff", role6="Ruolo staff", role7="Ruolo staff", role8="Ruolo staff",
        role9="Ruolo staff", role10="Ruolo staff", role11="Ruolo staff", role12="Ruolo staff",
        role13="Ruolo staff", role14="Ruolo staff", role15="Ruolo staff"
    )
    async def role_staff_config(
        self, ctx,
        role1: discord.Role,
        role2: discord.Role = None, role3: discord.Role = None, role4: discord.Role = None,
        role5: discord.Role = None, role6: discord.Role = None, role7: discord.Role = None,
        role8: discord.Role = None, role9: discord.Role = None, role10: discord.Role = None,
        role11: discord.Role = None, role12: discord.Role = None, role13: discord.Role = None,
        role14: discord.Role = None, role15: discord.Role = None
    ):
        roles = [r for r in [
            role1, role2, role3, role4, role5, role6, role7, role8,
            role9, role10, role11, role12, role13, role14, role15
        ] if r is not None]

        gconf = get_guild_config(ctx.guild.id)
        gconf["staff_roles"] = [r.id for r in roles]
        save_config(config)

        mentions = ", ".join(r.mention for r in roles)
        await ctx.send(f"✅ Ruoli staff configurati ({len(roles)}/15): {mentions}\n"
                        f"Questi ruoli verranno pingati nei nuovi ticket e potranno usare Claim/Unclaim.")

    @commands.hybrid_command(name="rolestaffremove", description="Rimuove tutti i ruoli staff configurati")
    @commands.has_permissions(administrator=True)
    async def role_staff_remove(self, ctx):
        gconf = get_guild_config(ctx.guild.id)
        gconf["staff_roles"] = []
        save_config(config)
        await ctx.send("✅ Tutti i ruoli staff configurati sono stati rimossi.")

    # ---------------------- COMANDI CONFIGURAZIONE CANALE RECENSIONI ----------------------
    @commands.hybrid_command(name="rateconfig", description="Configura il canale dove arrivano le recensioni")
    @commands.has_permissions(administrator=True)
    @app_commands.describe(channel="Canale dove inviare le recensioni")
    async def rate_config(self, ctx, channel: discord.TextChannel):
        gconf = get_guild_config(ctx.guild.id)
        gconf["review_channel"] = channel.id
        save_config(config)
        await ctx.send(f"✅ Le recensioni verranno inviate in {channel.mention}")

    @commands.hybrid_command(name="rateremove", description="Rimuove il canale delle recensioni configurato")
    @commands.has_permissions(administrator=True)
    async def rate_remove(self, ctx):
        gconf = get_guild_config(ctx.guild.id)
        gconf["review_channel"] = None
        save_config(config)
        await ctx.send("✅ Canale delle recensioni rimosso.")


async def setup(bot):
    await bot.add_cog(Tickets(bot))
