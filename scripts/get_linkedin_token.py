"""
One-time local helper to get your LinkedIn access token.
Run this on your own machine (not in CI) — it opens a browser flow.

Steps before running:
1. Go to https://www.linkedin.com/developers/apps -> Create app
2. Under "Products", request "Share on LinkedIn" (usually instant/auto-approved
   for personal use) and "Sign In with LinkedIn using OpenID Connect"
3. Under "Auth", add redirect URL: http://localhost:8000/callback
4. Copy your Client ID and Client Secret below (or set as env vars)

Usage:
    pip install requests
    CLIENT_ID=xxx CLIENT_SECRET=yyy python get_linkedin_token.py
"""
from dotenv import load_dotenv
import os

load_dotenv()

client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
import os
import webbrowser
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

CLIENT_ID = os.environ.get("CLIENT_ID", "PASTE_YOUR_CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET", "PASTE_YOUR_CLIENT_SECRET")
REDIRECT_URI = "http://localhost:8000/callback"
SCOPE = "openid profile w_member_social"

auth_url = (
    "https://www.linkedin.com/oauth/v2/authorization"
    f"?response_type=code&client_id={CLIENT_ID}"
    f"&redirect_uri={REDIRECT_URI}&scope={SCOPE.replace(' ', '%20')}"
)

captured_code = {}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        qs = parse_qs(urlparse(self.path).query)
        if "code" in qs:
            captured_code["code"] = qs["code"][0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Success! You can close this tab and return to the terminal.")
        else:
            self.send_response(400)
            self.end_headers()

    def log_message(self, *args):
        pass


print(f"Opening browser for LinkedIn login...\n{auth_url}")
webbrowser.open(auth_url)

server = HTTPServer(("localhost", 8000), Handler)
while "code" not in captured_code:
    server.handle_request()

code = captured_code["code"]

token_resp = requests.post(
    "https://www.linkedin.com/oauth/v2/accessToken",
    data={
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    },
)
token_resp.raise_for_status()
access_token = token_resp.json()["access_token"]
print(f"\n✅ ACCESS TOKEN (expires in ~60 days):\n{access_token}\n")

# Fetch person URN via OpenID userinfo endpoint
userinfo = requests.get(
    "https://api.linkedin.com/v2/userinfo",
    headers={"Authorization": f"Bearer {access_token}"},
).json()
person_urn = f"urn:li:person:{userinfo['sub']}"
print(f"✅ YOUR PERSON URN:\n{person_urn}\n")

print("Add these as GitHub repo secrets:")
print("  LINKEDIN_ACCESS_TOKEN =", access_token)
print("  LINKEDIN_PERSON_URN   =", person_urn)
print("\n⚠️  Token expires in ~60 days. Re-run this script to refresh when needed.")
