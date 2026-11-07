import base64
import hashlib
import requests
import webbrowser
import json
import os
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

AUTH_FILE = "auth_cache.json"

def generate_code_verifier() -> str:
    return base64.urlsafe_b64encode(os.urandom(40)).decode('utf-8').rstrip('=')

def get_code_challenge(verifier: str) -> str:
    sha256 = hashlib.sha256(verifier.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(sha256).decode('utf-8').rstrip('=')

def open_ms_login(verifier: str, client_id: str):
    challenge = get_code_challenge(verifier)
    url = (
        f"https://login.microsoftonline.com/consumers/oauth2/v2.0/authorize"
        f"?client_id={client_id}"
        "&response_type=code"
        "&scope=XboxLive.signin%20offline_access"
        "&redirect_uri=http://localhost:12750/callback"
        f"&code_challenge={challenge}"
        "&code_challenge_method=S256"
    )
    webbrowser.open(url)

def save_auth(data):
    with open(AUTH_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def load_auth():
    if os.path.exists(AUTH_FILE):
        with open(AUTH_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

# 回调服务器
class OAuthHandler(BaseHTTPRequestHandler):
    result_code = None
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        if "code" in params:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"<h1>登录成功，可以关闭页面，回到启动器</h1>")
            OAuthHandler.result_code = params["code"][0]
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"<h1>登录失败</h1>")
        self.server.shutdown()

def start_callback_server():
    OAuthHandler.result_code = None
    server = HTTPServer(("127.0.0.1", 12750), OAuthHandler)
    server.serve_forever()
    return OAuthHandler.result_code

# 多线程包装，防止GUI卡死
def run_callback_in_thread():
    res = [None]
    def worker():
        res[0] = start_callback_server()
    t = threading.Thread(target=worker)
    t.start()
    t.join()
    return res[0]

# ========== 新增：换取token + Xbox + Minecraft认证 ==========
def get_ms_token(code:str, verifier:str, client_id:str):
    url = "https://login.microsoftonline.com/consumers/oauth2/v2.0/token"
    data = {
        "client_id": client_id,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": "http://localhost:12750/callback",
        "code_verifier": verifier,
        "scope": "XboxLive.signin offline_access"
    }
    r = requests.post(url, data=data)
    return r.json()

def xbox_authenticate(ms_access_token:str):
    payload = {
        "Properties": {
            "AuthMethod": "RPS",
            "SiteName": "user.auth.xboxlive.com",
            "RpsTicket": f"d={ms_access_token}"
        },
        "RelyingParty": "http://auth.xboxlive.com",
        "TokenType": "JWT"
    }
    r = requests.post("https://user.auth.xboxlive.com/user/authenticate", json=payload)
    return r.json()

def xsts_authenticate(xbox_token:str):
    payload = {
        "Properties": {"SandboxId": "RETAIL", "UserTokens": [xbox_token]},
        "RelyingParty": "rp://api.minecraftservices.com/",
        "TokenType": "JWT"
    }
    r = requests.post("https://xsts.auth.xboxlive.com/xsts/authorize", json=payload)
    return r.json()

def get_mc_token(xsts_token, uhs):
    payload = {"identityToken": f"XBL3.0 x={uhs};{xsts_token}"}
    r = requests.post("https://api.minecraftservices.com/authentication/login_with_xbox", json=payload)
    return r.json()

def get_mc_profile(mc_access_token):
    headers = {"Authorization": f"Bearer {mc_access_token}"}
    r = requests.get("https://api.minecraftservices.com/minecraft/profile", headers=headers)
    return r.json()
