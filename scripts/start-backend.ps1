# 启动校园美食地图后端（FastAPI + Uvicorn）
#
# 用法（在项目根目录执行）：
#   powershell -ExecutionPolicy Bypass -File scripts\start-backend.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\start-backend.ps1 -Port 8001

param([int]$Port = 8000)

$ErrorActionPreference = "Stop"
$backend = Join-Path $PSScriptRoot "..\backend"
$python = Join-Path $backend ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    Write-Host "未找到后端虚拟环境：$python"
    Write-Host "请先按 README 安装依赖：cd backend; python -m venv .venv; .\.venv\Scripts\pip install -r requirements.txt"
    exit 1
}

Write-Host "正在启动后端：http://127.0.0.1:$Port"
Push-Location $backend
try {
    & $python -m uvicorn app.main:app --reload --host 127.0.0.1 --port $Port
}
finally {
    Pop-Location
}
