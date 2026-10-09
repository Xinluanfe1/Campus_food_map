# 启动校园美食地图前端（Vite 开发服务器）
#
# 用法（在项目根目录执行）：
#   powershell -ExecutionPolicy Bypass -File scripts\start-frontend.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\start-frontend.ps1 -Port 5174

param([int]$Port = 5173)

$ErrorActionPreference = "Stop"
$frontend = Join-Path $PSScriptRoot "..\frontend"

if (-not (Test-Path (Join-Path $frontend "node_modules"))) {
    Write-Host "未找到前端依赖，请先在 frontend 目录执行：npm.cmd install"
    exit 1
}

if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
    Write-Host "未找到 npm.cmd，请确认已安装 Node.js 并将其加入系统 PATH（安装后需重新打开终端）。"
    exit 1
}

Write-Host "正在启动前端：http://127.0.0.1:$Port"
Push-Location $frontend
try {
    # 使用 npm.cmd 而不是 npm：部分 Windows 环境禁止运行 npm.ps1（PowerShell 执行策略限制）
    npm.cmd run dev -- --host 127.0.0.1 --port $Port
}
finally {
    Pop-Location
}
