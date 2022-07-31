from os import getenv

from interactions import Client
from dotenv import load_dotenv

load_dotenv()

TOKEN = getenv("TOKEN")
if not TOKEN:
    raise Exception("Bot token not provided in env")

client = Client(TOKEN)
client.load("psu_parser")

client.start()