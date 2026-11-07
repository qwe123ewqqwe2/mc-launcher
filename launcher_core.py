import subprocess
import json
import os

def load_config():
    if not os.path.exists("config.json"):
        default_cfg = {
            "java_path": "java",
            "memory": {"min": 1024, "max": 4096},
            "game_dir": "./minecraft"
        }
        with open("config.json", "w", encoding="utf-8") as f:
            json.dump(default_cfg, f, indent=2)
    with open("config.json", "r", encoding="utf-8") as f:
        return json.load(f)


def build_mc_jvm_args(version_json: dict, auth_data: dict, game_dir: str, min_mem: int, max_mem: int):
    """
    组装MC Java版完整启动参数（正版，带access_token、uuid、玩家名）
    :param version_json: 从BMCLAPI下载的version.json版本配置
    :param auth_data: auth_cache.json的登录信息
    :param game_dir: 游戏根目录
    :param min_mem: 最小内存MB
    :param max_mem: 最大内存MB
    :return: 完整命令列表
    """
    # JVM基础内存参数
    jvm_args = [
        f"-Xms{min_mem}M",
        f"-Xmx{max_mem}M",
        "-cp"
    ]

    # 拼接所有libraries + version.jar classpath（简化版）
    lib_cp_list = []
    for lib in version_json["libraries"]:
        # 这里简化，后续下载模块会填充文件路径
        lib_path = os.path.join(game_dir, "libraries", lib["downloads"]["artifact"]["path"])
        lib_cp_list.append(lib_path)
    jar_path = os.path.join(game_dir, "versions", version_json["id"], f"{version_json['id']}.jar")
    lib_cp_list.append(jar_path)
    classpath = os.pathsep.join(lib_cp_list)
    jvm_args.append(classpath)

    # 主类 net.minecraft.client.main.Main
    main_class = version_json["mainClass"]
    jvm_args.append(main_class)

    # Minecraft 游戏参数
    game_args = [
        "--username", auth_data["mc_username"],
        "--uuid", auth_data["mc_uuid"],
        "--accessToken", auth_data["mc_access_token"],
        "--version", version_json["id"],
        "--gameDir", game_dir,
        "--assetsDir", os.path.join(game_dir, "assets"),
        "--assetIndex", version_json["assetIndex"]["id"]
    ]
    full_cmd = jvm_args + game_args
    return full_cmd


def launch_mc(version_json: dict, auth_data: dict):
    cfg = load_config()
    java_bin = cfg["java_path"]
    game_directory = cfg["game_dir"]
    min_m = cfg["memory"]["min"]
    max_m = cfg["memory"]["max"]

    cmd = build_mc_jvm_args(version_json, auth_data, game_directory, min_m, max_m)
    print("启动命令：", " ".join(cmd))
    # 启动游戏进程
    subprocess.Popen(cmd, cwd=game_directory)
