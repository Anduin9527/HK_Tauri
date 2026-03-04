$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$frontendDir = Split-Path -Parent $PSScriptRoot
$repoRoot = Split-Path -Parent $frontendDir
$backendDir = Join-Path $repoRoot "backend"
$tauriDir = Join-Path $frontendDir "src-tauri"
$tauriBinDir = Join-Path $tauriDir "bin"

if (-not (Test-Path $backendDir)) { throw "backend目录不存在: $backendDir" }
if (-not (Test-Path $tauriDir)) { throw "src-tauri目录不存在: $tauriDir" }

function Get-RustTargetTriple() {
  $rustc = Get-Command rustc -ErrorAction Stop
  $out = & $rustc.Source -vV
  $hostLine = ($out | Where-Object { $_ -like "host:*" } | Select-Object -First 1)
  if (-not $hostLine) { throw "无法从 rustc -vV 获取 host" }
  return $hostLine.Replace("host:", "").Trim()
}

function Get-PythonPath() {
  $explicit = $env:HK_TAURI_PYTHON
  if ($explicit -and (Test-Path $explicit)) { return $explicit }

  $envName = $env:HK_TAURI_CONDA_ENV
  if (-not $envName) { $envName = "hk_tauri" }

  $conda = Get-Command conda -ErrorAction SilentlyContinue
  if ($conda) {
    $base = (& $conda.Source info --base).Trim()
    if ($base) {
      $py = Join-Path $base "envs\$envName\python.exe"
      if (Test-Path $py) { return $py }
    }
  }

  $pyCmd = Get-Command python -ErrorAction Stop
  return $pyCmd.Source
}

$python = Get-PythonPath
Write-Host "Using Python: $python"

try {
  & $python -m PyInstaller --version | Out-Null
} catch {
  Write-Host "PyInstaller not found. Installing backend deps..."
  Push-Location $backendDir
  & $python -m pip install --upgrade pip
  & $python -m pip install -r requirements.txt pyinstaller
  Pop-Location
}

Write-Host "Building backend.exe via PyInstaller..."
Push-Location $backendDir
& $python -m PyInstaller build_backend_onefile.spec --noconfirm
Pop-Location

$backendExe = Join-Path $backendDir "dist\backend.exe"
if (-not (Test-Path $backendExe)) { throw "未找到后端产物: $backendExe" }

$triple = Get-RustTargetTriple
New-Item -ItemType Directory -Force -Path $tauriBinDir | Out-Null
$sidecarExe = Join-Path $tauriBinDir ("backend-{0}.exe" -f $triple)
Copy-Item -Force $backendExe $sidecarExe
Write-Host "Sidecar ready: $sidecarExe"

