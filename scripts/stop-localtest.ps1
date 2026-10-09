# 校园美食地图 · 停止本地调试服务（由「一键停止.cmd」调用）

param([int[]]$Ports = @(8000, 5173))

Write-Host "=================================================="
Write-Host "   校园美食地图 · 停止本地服务"
Write-Host "=================================================="
Write-Host ""

# 说明：uvicorn 使用 --reload 时会有一个守护进程；只结束监听进程的话，
# 守护进程会立刻把它重新拉起。因此这里沿父进程链向上收集需要一起结束的进程。
function Get-AncestorIds([int]$ProcessId) {
    $ancestors = New-Object System.Collections.Generic.List[int]
    $currentId = $ProcessId
    for ($depth = 0; $depth -lt 6; $depth++) {
        $process = Get-CimInstance Win32_Process -Filter "ProcessId = $currentId" -ErrorAction SilentlyContinue
        if (-not $process -or -not $process.ParentProcessId) { break }
        $parentId = [int]$process.ParentProcessId
        $parent = Get-CimInstance Win32_Process -Filter "ProcessId = $parentId" -ErrorAction SilentlyContinue
        if (-not $parent) { break }
        # 只向上追踪脚本/运行时进程，避免误杀 explorer 等系统进程
        if ($parent.Name -notin @("python.exe", "node.exe", "powershell.exe", "pwsh.exe", "cmd.exe")) { break }
        $ancestors.Add($parentId)
        $currentId = $parentId
    }
    return $ancestors
}

$listeners = New-Object System.Collections.Generic.List[int]
foreach ($port in $Ports) {
    $connections = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    foreach ($connection in $connections) {
        $listeners.Add([int]$connection.OwningProcess)
    }
}

$targets = New-Object System.Collections.Generic.List[int]

# 优先使用启动时记录的窗口进程号：按进程树结束可以同时结束 uvicorn 守护进程、
# multiprocessing 子进程与 vite，这是最可靠的方式。
$root = Split-Path -Parent $PSScriptRoot
$pidFile = Join-Path $root ".localtest.pids"
$stoppedByPidFile = 0
if (Test-Path -LiteralPath $pidFile) {
    foreach ($line in (Get-Content -LiteralPath $pidFile -ErrorAction SilentlyContinue)) {
        if ($line -match "^\d+$") {
            & taskkill /PID $line /T /F 2>&1 | Out-Null
            $stoppedByPidFile += 1
        }
    }
    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
}

foreach ($listenerId in ($listeners | Sort-Object -Unique)) {
    foreach ($ancestorId in (Get-AncestorIds -ProcessId $listenerId)) {
        $targets.Add($ancestorId)
    }
    $targets.Add($listenerId)
}

# uvicorn 在 --reload 模式下会通过 multiprocessing 启动子进程，监听套接字可能由
# 子进程继承；此时（父进程已退出）仅按端口无法定位真正的持有者。
# 由于后端只使用本部署目录内的虚拟环境 Python，这里按可执行文件路径精确匹配并结束。
$venvPython = Join-Path $root "backend\.venv\Scripts\python.exe"
foreach ($process in Get-CimInstance Win32_Process -ErrorAction SilentlyContinue) {
    if ($process.ExecutablePath -and ($process.ExecutablePath -ieq $venvPython)) {
        $targets.Add([int]$process.ProcessId)
        foreach ($ancestorId in (Get-AncestorIds -ProcessId ([int]$process.ProcessId))) {
            $targets.Add($ancestorId)
        }
    }
}

# 清理孤儿 multiprocessing 工作进程：uvicorn --reload 的子进程在父进程被强制结束后
# 会继续运行并占用端口，其命令行特征为 --multiprocessing-fork 且父进程已不存在。
foreach ($process in Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" -ErrorAction SilentlyContinue) {
    if (-not $process.CommandLine) { continue }
    # 命令行包含本部署目录的 Python 进程（uvicorn 主进程及其子进程）全部结束
    if ($process.CommandLine -like "*$root*") {
        $targets.Add([int]$process.ProcessId)
        continue
    }
    if ($process.CommandLine -notmatch "multiprocessing-fork") { continue }
    $parent = Get-CimInstance Win32_Process -Filter "ProcessId = $($process.ParentProcessId)" -ErrorAction SilentlyContinue
    if (-not $parent) {
        $targets.Add([int]$process.ProcessId)
    }
}

# 先结束父进程（守护进程 / 启动窗口），再结束监听进程，避免被重新拉起
$stopped = 0
foreach ($processId in ($targets | Select-Object -Unique)) {
    try {
        Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
        $stopped += 1
    }
    catch {
        # 忽略已经在退出的进程
    }
}

if ($stoppedByPidFile -gt 0) {
    Write-Host "已按记录的进程号结束 $stoppedByPidFile 个服务窗口（含其子进程）。"
}

if ($stopped -gt 0) {
    Write-Host "已停止 $stopped 个进程（端口：$($Ports -join '、')）。"
}
else {
    Write-Host "端口 $($Ports -join '、') 上没有正在运行的服务。"
}

Write-Host "如有残留的“后端 / 前端”窗口，直接关闭即可。"
if ($env:CFM_NO_PAUSE -ne "1") { Read-Host "按回车键关闭本窗口" | Out-Null }
