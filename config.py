import os
from dotenv import load_dotenv
load_dotenv()
# ==== TOKEN & PREFIX ====
TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = "."

# ==== RUOLO SHOP AURA ====
AURA_SHOP_COST = 100000
# ==== RUOLI VERIFICA ====
# Non più hardcoded: si configurano ora per server con i comandi
# "roleverified" (ruolo assegnato alla verifica) e
# "roleunverified" (ruolo rimosso alla verifica), salvati in settings.json
# ==== BLACKLIST VERIFICA (controllo rischio account) ====
# Non hardcoded: si gestisce per server con i comandi "blacklistadd",
# "blacklistremove" e "blacklistlist", salvata in blacklist.json.
# Al momento della verifica il bot segnala allo staff (senza bloccare)
# gli account in blacklist o con segnali sospetti (account nuovo,
# nessun avatar, nome sospetto): vedi check_account_risk() in utility.py
# ==== RUOLI STAFF/TICKET (ping su ogni ticket) ====
# Non più hardcoded: si configurano ora per server (fino a 15 ruoli) con
# il comando "rolestaffconfig" (e si rimuovono con "rolestaffremove"),
# salvati in ticket_config.json
# ==== CANALE RECENSIONI TICKET ====
# Non più hardcoded: si configura ora per server con il comando
# "rateconfig" (e si rimuove con "rateremove"), salvato in ticket_config.json
# ==== CANALI DA CONFIGURARE (metti gli ID reali) ====
WELCOME_CHANNEL_ID = None
GOODBYE_CHANNEL_ID = None
WELCOME_GOODBYE_LOG_CHANNEL_ID = None
INVITES_LOG_CHANNEL_ID = None
AUTOMOD_LOG_CHANNEL_ID = None
TICKET_CATEGORY_ID = None  # categoria dove creare i canali ticket
# ==== ECONOMIA ====
CURRENCY_NAME = "Aura Coins"
BOX_PRICES = {
    "comuni": 150,
    "rare": 300,
    "epiche": 500,
    "mitiche": 750,
    "leggendaria": 1000,
}
