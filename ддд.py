import urllib.parse
from dotenv import load_dotenv
import os

load_dotenv()
TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")

def get_auth_url():
    params = {
        "client_id": TWITCH_CLIENT_ID,
        "redirect_uri": "http://localhost",
        "response_type": "token",
        "scope": "moderator:read:followers",
    }
    return f"https://id.twitch.tv/oauth2/authorize?{urllib.parse.urlencode(params)}"

print(get_auth_url())
