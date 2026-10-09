# 同时启动后端与前端（各自打开一个新的 PowerShell 窗口，便于查看日志与停止服务）
#
# 用法（在项目根目录执行）：
#   powershell -ExecutionPolicy Bypass -File scripts\start-all.ps1

$backendScript = Join-Path $PSScriptRoot "start-backend.ps1"
$frontendScript = Join-Path $PSScriptRoot "start-frontend.ps1"

Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", $backendScript
Start-Sleep -Seconds 2
Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", $frontendScript

Write-Host "已打开两个窗口：后端 http://127.0.0.1:8000，前端 http://127.0.0.1:5173"
Write-Host "关闭对应窗口即可停止服务。"
