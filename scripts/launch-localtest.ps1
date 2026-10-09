# 校园美食地图 · 本地调试一键启动（由「一键启动.cmd」调用）
#
# 功能：检查依赖 → 启动后端与前端窗口 → 等待服务就绪 → 打开浏览器。
# 环境变量：
#   CFM_NO_BROWSER=1  不自动打开浏览器（用于自动化验证）
#   CFM_NO_PAUSE=1    结束时不等按键（用于自动化验证）

param([int]$BackendPort = 8000, [int]$FrontendPort = 5173)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$backendPython = Join-Path $root "backend\.venv\Scripts\python.exe"
$frontendModules = Join-Path $root "frontend\node_modules"
$backendScript = Join-Path $PSScriptRoot "start-backend.ps1"
$frontendScript = Join-Path $PSScriptRoot "start-frontend.ps1"
$frontendUrl = "http://127.0.0.1:$FrontendPort/"

Write-Host "=================================================="
Write-Host "   校园美食地图 · 本地调试一键启动"
Write-Host "=================================================="
Write-Host ""

if (-not (Test-Path $backendPython)) {
    Write-Host "[错误] 未找到后端虚拟环境：$backendPython"
    Write-Host "       请先按《本地调试说明》安装后端依赖。"
    if ($env:CFM_NO_PAUSE -ne "1") { Read-Host "按回车键关闭本窗口" | Out-Null }
    exit 1
}

if (-not (Test-Path $frontendModules)) {
    Write-Host "[错误] 未找到前端依赖：$frontendModules"
    Write-Host "       请先在 frontend 目录执行：npm.cmd install"
    if ($env:CFM_NO_PAUSE -ne "1") { Read-Host "按回车键关闭本窗口" | Out-Null }
    exit 1
}

if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
    Write-Host "[错误] 未找到 npm.cmd，请确认已安装 Node.js 并加入系统 PATH（安装后需重新打开终端）。"
    if ($env:CFM_NO_PAUSE -ne "1") { Read-Host "按回车键关闭本窗口" | Out-Null }
    exit 1
}

# 服务已经在运行时不重复启动
$alreadyRunning = $false
try {
    $response = Invoke-WebRequest -Uri $frontendUrl -UseBasicParsing -TimeoutSec 3
    $alreadyRunning = $response.StatusCode -eq 200
}
catch {
    $alreadyRunning = $false
}

if ($alreadyRunning) {
    Write-Host "检测到本地服务已在运行，直接打开浏览器。"
    if ($env:CFM_NO_BROWSER -ne "1") {
        Start-Process $frontendUrl
    }
    if ($env:CFM_NO_PAUSE -ne "1") { Read-Host "按回车键关闭本窗口" | Out-Null }
    exit 0
}

Write-Host "正在启动后端（http://127.0.0.1:$BackendPort）……"
$backendWindow = Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", $backendScript, "-Port", "$BackendPort" -PassThru

Write-Host "正在启动前端（http://127.0.0.1:$FrontendPort）……"
$frontendWindow = Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", $frontendScript, "-Port", "$FrontendPort" -PassThru

# 记录服务窗口进程号：停止脚本按进程树结束时才能把 uvicorn / vite 一并结束
$pidFile = Join-Path $root ".localtest.pids"
Set-Content -LiteralPath $pidFile -Value @($backendWindow.Id, $frontendWindow.Id) -Encoding ASCII
Write-Host "已记录服务进程号：$pidFile"

Write-Host ""
Write-Host "正在等待服务就绪（最长 90 秒）……"
$deadline = (Get-Date).AddSeconds(90)
$ready = $false
while (-not $ready -and (Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 2
    try {
        $response = Invoke-WebRequest -Uri $frontendUrl -UseBasicParsing -TimeoutSec 3
        $ready = $response.StatusCode -eq 200
    }
    catch {
        $ready = $false
    }
}

if ($ready) {
    Write-Host "服务已就绪。"
    if ($env:CFM_NO_BROWSER -ne "1") {
        Start-Process $frontendUrl
        Write-Host "已打开浏览器：$frontendUrl"
    } else {
        Write-Host "浏览器未自动打开（CFM_NO_BROWSER=1），请手动访问：$frontendUrl"
    }
}
else {
    Write-Host "[提示] 等待超时，请查看“后端 / 前端”两个窗口中的日志排查问题。"
}

Write-Host ""
Write-Host "关闭“校园美食地图 · 后端 / 前端”两个窗口即可停止服务，"
Write-Host "也可以双击“一键停止.cmd”停止端口上的服务。"

if ($env:CFM_NO_PAUSE -ne "1") { Read-Host "按回车键关闭本窗口" | Out-Null }
