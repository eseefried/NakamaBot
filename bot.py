import discord
from discord.ext import tasks
from discord import app_commands
import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))
TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")

# Setup bot
intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# Load or initialize nakama
try:
    with open("nakama.json", "r") as f:
        nakama = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    nakama = {}

currently_live = set()

def save_nakama():
    with open("nakama.json", "w") as f:
        json.dump(nakama, f)

def get_twitch_token():
    url = 'https://id.twitch.tv/oauth2/token'
    params = {
        'client_id': TWITCH_CLIENT_ID,
        'client_secret': TWITCH_CLIENT_SECRET,
        'grant_type': 'client_credentials'
    }
    response = requests.post(url, params=params)
    return response.json()['access_token']

def is_user_live(username, token):
    url = 'https://api.twitch.tv/helix/streams'
    headers = {
        'Client-ID': TWITCH_CLIENT_ID,
        'Authorization': f'Bearer {token}'
    }
    params = {
        'user_login': username
    }
    response = requests.get(url, headers=headers, params=params)
    data = response.json().get('data', [])
    return data[0] if data else None

@client.event
async def on_ready():
    print(f"⚓ NakamaBot has boarded the Sunny as {client.user}")
    await tree.sync()
    check_streams.start()

@tree.command(name="nakama", description="Join the crew and register your Twitch username")
async def register_nakama(interaction: discord.Interaction, twitch_username: str):
    nakama[str(interaction.user.id)] = twitch_username
    save_nakama()
    await interaction.response.send_message(
        f"🏴‍☠️ {interaction.user.display_name} joined the crew! "
        f"We’ll track **{twitch_username}**’s adventures on Twitch!"
    )

@tasks.loop(minutes=1)
async def check_streams():
    if not nakama:
        print("No nakama registered.")
        return

    token = get_twitch_token()
    print("Twitch token acquired.")
    channel = client.get_channel(DISCORD_CHANNEL_ID)

    for user_id, twitch_username in nakama.items():
        print(f"🔍 Checking Twitch user: {twitch_username}")
        stream = is_user_live(twitch_username, token)
        if stream:
            print(f"✅ {twitch_username} is live!")
        else:
            print(f"❌ {twitch_username} is offline.")

        if stream and twitch_username not in currently_live:
            currently_live.add(twitch_username)
            title = stream['title']
            url = f"https://twitch.tv/{twitch_username}"
            await channel.send(
                f"🏴‍☠️ **{twitch_username}** has set sail!\n"
                f"📺 **{title}**\n"
                f"🔗 {url}"
            )
        elif not stream and twitch_username in currently_live:
            currently_live.remove(twitch_username)

client.run(DISCORD_TOKEN)
