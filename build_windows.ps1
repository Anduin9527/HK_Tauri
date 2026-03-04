param(
  [string]$CondaEnvName = "hk_tauri",
  [string]$NodeDir = "C:\Program Files\nodejs",
  [switch]$SkipBackendDeps,
  [switch]$SkipFrontendDeps,
  [switch]$SkipCargoTauriInstall
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $repoRoot "backend"
$frontendDir = Join-Path $repoRoot "frontend"
$tauriDir = Join-Path $frontendDir "src-tauri"
$tauriBinDir = Join-Path $tauriDir "bin"

if (-not (Test-Path $backendDir)) { throw "backend目录不存在: $backendDir" }
if (-not (Test-Path $frontendDir)) { throw "frontend目录不存在: $frontendDir" }
if (-not (Test-Path $tauriDir)) { throw "src-tauri目录不存在: $tauriDir" }

if (Test-Path $NodeDir) {
  $env:PATH = "$NodeDir;$env:PATH"
} else {
  Write-Host "未找到Node目录: $NodeDir，后续npm命令可能失败"
}

$cargoBinDir = Join-Path $env:USERPROFILE ".cargo\bin"
if (Test-Path $cargoBinDir) {
  $env:PATH = "$cargoBinDir;$env:PATH"
} else {
  Write-Host "未找到Rust Cargo目录: $cargoBinDir，后续cargo命令可能失败"
}

function Get-CondaPythonPath([string]$envName) {
  $conda = Get-Command conda -ErrorAction Stop
  $base = (& $conda.Source info --base).Trim()
  if (-not $base) { throw "无法获取conda base路径" }
  $py = Join-Path $base "envs\$envName\python.exe"
  if (-not (Test-Path $py)) { throw "未找到conda环境python: $py" }
  return $py
}

function Get-RustTargetTriple() {
  $rustc = Get-Command rustc -ErrorAction Stop
  $out = & $rustc.Source -vV
  $hostLine = ($out | Where-Object { $_ -like "host:*" } | Select-Object -First 1)
  if (-not $hostLine) { throw "无法从 rustc -vV 获取 host" }
  return $hostLine.Replace("host:", "").Trim()
}

$python = Get-CondaPythonPath $CondaEnvName
Write-Host "Using Python: $python"

if (-not $SkipBackendDeps) {
  Write-Host "Installing backend deps..."
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
Write-Host "Rust target triple: $triple"

New-Item -ItemType Directory -Force -Path $tauriBinDir | Out-Null
$sidecarExeName = "backend-$triple.exe"
$sidecarExe = Join-Path $tauriBinDir $sidecarExeName
Copy-Item -Force $backendExe $sidecarExe
Write-Host "Sidecar ready: $sidecarExe"

if (-not $SkipFrontendDeps) {
  Write-Host "Installing frontend deps..."
  Push-Location $frontendDir
  & npm ci
  Pop-Location
}

Write-Host "Building frontend dist..."
Push-Location $frontendDir
& npm run build
Pop-Location

if (-not $SkipCargoTauriInstall) {
  $cargo = Get-Command cargo -ErrorAction Stop
  $cargoTauri = Join-Path $cargoBinDir "cargo-tauri.exe"
  if (-not (Test-Path $cargoTauri)) {
    Write-Host "Installing tauri-cli (cargo-tauri)..."
    & $cargo.Source install tauri-cli --locked
  }
}

Write-Host "Building Tauri installer (NSIS)..."
Push-Location $frontendDir
& cargo-tauri build
Pop-Location

$bundleDir = Join-Path $tauriDir "target\release\bundle\nsis"
Write-Host "Done. Check output in: $bundleDir"
Get-ChildItem -Path $bundleDir -Filter "*setup*.exe" -ErrorAction SilentlyContinue | Select-Object FullName, Length, LastWriteTime
