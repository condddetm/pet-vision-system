@echo off
REM ============================================================
REM 智能宠物视觉系统 - 一键启动脚本 (自包含版)
REM 在两个独立窗口中分别运行 FastAPI 和 Vite 开发服务器
REM ============================================================

setlocal

echo [1/2] 正在启动后端 (FastAPI :8000) ...
start "Pet-Backend (FastAPI :8000)" cmd /k "cd /d %~dp0backend && python -m uvicorn app.main:app --reload --port 8000"

REM 给后端 3 秒预热，避免前端启动时接口未就绪
timeout /t 3 /nobreak > nul

echo [2/2] 正在启动前端 (Vite :5173) ...
start "Pet-Frontend (Vite :5173)" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo ============================================================
echo  服务已在两个独立窗口启动:
echo    - 后端: http://127.0.0.1:8000  (API 文档: /docs)
echo    - 前端: http://localhost:5173
echo  关闭对应窗口即可停止该服务。
echo ============================================================
echo.
pause
