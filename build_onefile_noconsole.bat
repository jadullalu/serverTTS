@echo off
setlocal
cd /d %~dp0
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install "pyinstaller>=6.6"
pyinstaller --noconfirm --onefile --noconsole --clean ^
  --name ServerTTS ^
  --icon assets\tts.ico ^
  --version-file version_info.txt ^
  --add-data "assets;assets" ^
  --add-data "portable_vlc;portable_vlc" ^
  --hidden-import pycaw ^
  --hidden-import comtypes ^
  --hidden-import pystray ^
  app.py
echo.
echo Selesai -> dist\ServerTTS.exe
pause
