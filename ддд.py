import urllib.parse
import requests

def get_auth_url():
    params = {
        "client_id": "ztttaodeic4dbxo932w8ku7r7x87sc",  # Ваш актуальный TWITCH_CLIENT_ID
        "redirect_uri": "https://tgbottwitchchecker-production.up.railway.app",
        "response_type": "code",
        "scope": "moderator:read:followers",
    }
    return f"https://id.twitch.tv/oauth2/authorize?{urllib.parse.urlencode(params)}"

def exchange_code_for_token(code):
    url = "https://id.twitch.tv/oauth2/token"
    params = {
        "client_id": "ztttaodeic4dbxo932w8ku7r7x87sc",  # Ваш актуальный TWITCH_CLIENT_ID
        "client_secret": "k5jxe0ah07gi8g0ph048yh1c3u2m7a",  # Ваш актуальный TWITCH_CLIENT_SECRET
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": "https://tgbottwitchchecker-production.up.railway.app",
    }
    response = requests.post(url, params=params)
    if response.status_code == 200:
        data = response.json()
        print(f"Access Token: {data['access_token']}")
        print(f"Refresh Token: {data['refresh_token']}")
        return data["access_token"], data["refresh_token"]
    print(f"Ошибка: {response.text}")
    return None, None

print(get_auth_url())
