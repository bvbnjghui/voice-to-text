@echo off
:: 設定編碼為 UTF-8
chcp 65001 >nul
title AI 逐字稿專家 - 啟動器

echo ======================================================
echo           AI 逐字稿專家 - 啟動環境檢查
echo ======================================================
echo.

:: 檢查 Python 是否存在
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [錯誤] 找不到 Python 指令！請安裝並勾選 "Add Python to PATH"。
    pause
    exit
)

:: 進入程式目錄
cd /d "%~dp0"

echo [1/2] 正在檢查虛擬環境...
if not exist "venv" (
    echo 正在建立 venv，請稍候...
    python -m venv venv
)

echo [2/2] 正在檢查/安裝套件 (這需要一點時間，請勿關閉)...
call .\venv\Scripts\activate
:: 檢查 pip 版本並安裝需求
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt

echo.
echo ======================================================
echo 🚀 正在啟動伺服器... 瀏覽器將於數秒後自動開啟。
echo ======================================================
:: 移除 start 指令，讓 streamlit 預設自動開啟一個頁面即可
streamlit run app.py

pause