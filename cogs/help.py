import discord
from discord.ext import commands
class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    @commands.command(name="help")
    async def help_command(self, ctx):
        embed = discord.Embed(
            title="📖 Lista Comandi",
            description="Prefissi disponibili: `.` e `/`",
            color=discord.Color.blurple()
        )
        embed.add_field(
            name="🛡️ Moderazione",
            value=(
                "`pex` `depex` `ban` `unban` `warn` `clearwarn` `showwarn` "
                "`kick` `mute` `unmute` `purge` `lock` `unlock` `slowmode` "
                "`messagecount` `messageadd` `messageremove`"
            ),
            inline=False
        )
        embed.add_field(
            name="⭐ Livelli",
            value=(
                "`livelli` `levelleaderboard` `ranking`"
            ),
            inline=False
        )
        embed.add_field(
            name="💰 Economia",
            value=(
                "`work` `balance` `tris` `blackjack` `coinflip` `add` `remove` "
                "`roulette` `luckybox` `pay` `lucky` `daily` `mine` `inventory` "
                "`openbox` `shop`"
            ),
            inline=False
        )
        embed.add_field(
            name="🤖 Automod",
            value=(
                "`automod on/off` `automod links on/off` `automod spam on/off` "
                "`automodlog set`"
            ),
            inline=False
        )
        embed.add_field(
            name="🎉 Gioco / Fun",
            value=(
                "`8ball` `say` `kiss` `kill` `slap` `clap` `hug` `marry` `divorce` "
                "`fakenitro` `ship` `rendigay` `aura`"
            ),
            inline=False
        )
        embed.add_field(
            name="🎫 Supporto",
            value=(
                "`pannelloticket`"
            ),
            inline=False
        )
        embed.add_field(
            name="🎟️ Config Ticket",
            value=(
                "`rolestaffconfig` `rolestaffremove` `rateconfig` `rateremove`"
            ),
            inline=False
        )
        embed.add_field(
            name="✅ Config Verifica",
            value=(
                "`verifica` `roleverified` `roleunverified` `blacklistadd` "
                "`blacklistremove` `blacklistlist`"
            ),
            inline=False
        )
        embed.add_field(
            name="⚙️ Utility",
            value=(
                "`setwelcome` `setgoodbye` `setwelcomegoodbylogs` `invites` "
                "`showinvites` `resetinvites` `resetinvitesall` `setinviteschannel` "
                "`invitebot` `userinfo` `serverinfo`"
            ),
            inline=False
        )
        embed.set_footer(text=f"Richiesto da {ctx.author}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)
async def setup(bot):
    await bot.add_cog(Help(bot))
