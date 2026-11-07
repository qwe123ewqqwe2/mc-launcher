import customtkinter as ctk
import json
import os
import threading

from downloader import get_version_list, download_file
from launcher_core import launch_mc, load_config
from auth import (
    generate_code_verifier, open_ms_login, run_callback_in_thread,
    get_ms_token, xbox_authenticate, xsts_authenticate, get_mc_token, get_mc_profile,
    save_auth, load_auth
)

# ===================== 全局配置 =====================
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")
# 使用可用公共ClientID
CLIENT_ID = "3b49194e-9b01-49f8-9476-15e85e812b6c"

app = ctk.CTk()
app.title("Computer Java MC launcher")
app.geometry("900x620")

# 加载本地配置与登录信息
cfg = load_config()
auth_info = load_auth()

# 获取版本列表
version_list_data = get_version_list()
version_names = [v["id"] for v in version_list_data["versions"]]

# UI绑定变量
var_select_ver = ctk.StringVar(value=version_names[0])
status_text = ctk.StringVar(value="就绪")
user_text = ctk.StringVar(value="未登录")
if auth_info:
    user_text.set(f"已登录: {auth_info['mc_username']}")

# ===================== 功能函数 =====================
def login_ms():
    """微软正版登录按钮回调"""
    def login_work():
        ver = generate_code_verifier()
        open_ms_login(ver, CLIENT_ID)
        code = run_callback_in_thread()
        if not code:
            status_text.set("登录失败：未获取授权码")
            return
        try:
            ms_token_data = get_ms_token(code, ver, CLIENT_ID)
            ms_at = ms_token_data["access_token"]

            xbox_data = xbox_authenticate(ms_at)
            xbox_tok = xbox_data["Token"]
            uhs = xbox_data["DisplayClaims"]["xui"][0]["uhs"]

            xsts_data = xsts_authenticate(xbox_tok)
            xsts_tok = xsts_data["Token"]

            mc_data = get_mc_token(xsts_tok, uhs)
            mc_at = mc_data["access_token"]
            profile = get_mc_profile(mc_at)

            auth_save = {
                "mc_username": profile["name"],
                "mc_uuid": profile["id"],
                "mc_access_token": mc_at,
                "ms_refresh_token": ms_token_data["refresh_token"]
            }
            save_auth(auth_save)
            user_text.set(f"已登录: {profile['name']}")
            status_text.set("微软账号登录成功！")
        except Exception as e:
            status_text.set(f"登录异常: {str(e)}")
    # 新线程执行登录，不会卡死GUI
    t = threading.Thread(target=login_work)
    t.start()


def btn_download_ver():
    """下载选中版本（简易框架，后续完善）"""
    selected = var_select_ver.get()
    status_text.set(f"开始获取版本 {selected} 信息...")
    def dl_thread():
        try:
            # 此处后续对接完整BMCLAPI下载逻辑
            status_text.set(f"版本{selected}下载任务启动（BMCLAPI）")
        except Exception as e:
            status_text.set(f"下载失败：{e}")
    threading.Thread(target=dl_thread).start()


def btn_start_game():
    """启动MC游戏，读取登录信息，调用launch_core"""
    auth_data = load_auth()
    if not auth_data:
        status_text.set("请先完成微软账号登录！")
        return
    selected_ver = var_select_ver.get()
    status_text.set(f"正在加载版本 {selected_ver} ...")

    try:
        # 读取该版本的version.json
        ver_file_path = os.path.join("./minecraft/versions", selected_ver, f"{selected_ver}.json")
        if not os.path.exists(ver_file_path):
            status_text.set(f"错误：版本{selected_ver}未下载，请先下载！")
            return
        with open(ver_file_path, "r", encoding="utf-8") as f:
            ver_json = json.load(f)

        status_text.set(f"启动 Minecraft {selected_ver}！")
        launch_mc(ver_json, auth_data)
    except Exception as e:
        status_text.set(f"启动失败：{str(e)}")

# ===================== UI界面组件 =====================
label_title = ctk.CTkLabel(app, text="Computer Java MC launcher", font=("Arial",24))
label_title.pack(pady=12)

# 账号信息
user_label = ctk.CTkLabel(app, textvariable=user_text, font=("Arial",14))
user_label.pack(pady=4)

# 版本下拉框
drop_ver = ctk.CTkOptionMenu(app, values=version_names, variable=var_select_ver, width=400)
drop_ver.pack(pady=8)

# 按钮组
btn_login = ctk.CTkButton(app, text="微软正版登录", command=login_ms, width=240)
btn_login.pack(pady=6)

btn_dl = ctk.CTkButton(app, text="下载选中版本", command=btn_download_ver, width=240)
btn_dl.pack(pady=6)

btn_run = ctk.CTkButton(app, text="启动游戏", command=btn_start_game, width=240)
btn_run.pack(pady=6)

# 状态提示
status_label = ctk.CTkLabel(app, textvariable=status_text, font=("Arial",12))
status_label.pack(pady=15)

app.mainloop()
