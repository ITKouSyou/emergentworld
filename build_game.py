import subprocess
import shutil
import os
import PyInstaller.__main__
from pathlib import Path

def main():
    print("=== 1. 清理旧的打包残留 ===")
    os.system("taskkill /F /IM EmergentWorldServer.exe /T >nul 2>&1")
    shutil.rmtree("build", ignore_errors=True)
    shutil.rmtree("dist", ignore_errors=True)
    for f in Path(".").glob("*.spec"):
        f.unlink()

    print("=== 2. 生成安全入口文件 ===")
    code = '''import sys
import os
import traceback

if getattr(sys, 'frozen', False):
    base_dir = os.path.dirname(sys.executable)
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, base_dir)

log_file = open(os.path.join(base_dir, "server_error.log"), "w", encoding="utf-8")
sys.stderr = log_file

try:
    import uvicorn
    from server.main import app
    if __name__ == "__main__":
        uvicorn.run(app, host="127.0.0.1", port=8000, log_config=None)
except Exception as e:
    traceback.print_exc(file=log_file)
    log_file.flush()
'''
    Path("main_server.py").write_text(code, encoding="utf-8")

    print("=== 3. 开始全自动打包后端 (静默模式) ===")
    PyInstaller.__main__.run([
        'main_server.py',
        '--name=EmergentWorldServer',
        '--onedir',
        '--windowed',  # 隐藏黑框
        '--noconfirm',
        '--clean',
        '--add-data=content;content',
        '--add-data=server/prompts;server/prompts',
        '--collect-all=pydantic_settings',
        '--collect-all=sqlmodel',
        '--collect-all=fastapi',
        '--collect-all=uvicorn',
        '--collect-all=sqlalchemy',
        '--collect-all=openai',
        '--collect-all=dotenv',
        '--hidden-import=server',
        '--hidden-import=server.main',
    ])

    print("=== 4. 复制必要文件和前端 ===")
    dist_dir = Path("dist/EmergentWorldServer")
    shutil.copytree("server", dist_dir / "server", dirs_exist_ok=True)
    
    if Path(".env").exists():
        shutil.copy2(".env", dist_dir / ".env")

    game_exe = Path("client/Game.exe")
    if not game_exe.exists():
        game_exe = Path("Game.exe")
    if game_exe.exists():
        shutil.copy2(game_exe, dist_dir / "Game.exe")
        print("[OK] 前端已复制")

    db_file = dist_dir / "data" / "world.db"
    if db_file.exists():
        db_file.unlink()
        print("[OK] 旧测试存档已清理")

    print("=== 5. 生成一键静默启动器 ===")
    bat_content = """@echo off
start "" "Game.exe"
start /b "" "EmergentWorldServer.exe"
:wait_loop
timeout /t 3 /nobreak >nul
tasklist | findstr "EmergentWorldServer.exe" >nul
if errorlevel 1 exit
goto wait_loop
"""
    (dist_dir / "启动游戏.bat").write_text(bat_content, encoding="gbk")

    vbs_content = """Set WshShell = CreateObject("WScript.Shell") 
WshShell.Run chr(34) & "启动游戏.bat" & Chr(34), 0
Set WshShell = Nothing
"""
    (dist_dir / "启动游戏.vbs").write_text(vbs_content, encoding="gbk")

    print("\n=== 打包完成 ===")
    print("进入 dist/EmergentWorldServer/，双击【启动游戏.vbs】即可游玩！")
    print("如果卡住，请查看该目录下的 server_error.log 文件。")

if __name__ == "__main__":
    main()