# 启动校园美食地图前端（Vite 开发服务器）
#
# 用法（在项目根目录执行）：
#   powershell -ExecutionPolicy Bypass -File scripts\start-frontend.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\start-frontend.ps1 -Port 5174

param([int]$Port = 5173)

$ErrorActionPreference = "Stop"
$frontend = Join-Path $PSScriptRoot "..\frontend"

if (-not (Test-Path (Join-Path $frontend "node_modules"))) {
    Write-Host "未找到前端依赖，请先在 frontend 目录执行：npm install"
    exit 1
}

Write-Host "正在启动前端：http://127.0.0.1:$Port"
Push-Location $frontend
try {
    npm run dev -- --host 127.0.0.1 --port $Port
}
finally {
    Pop-Location
}
