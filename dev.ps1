<#
.SYNOPSIS
  Starts the PronunciaPA backend server and UI with a single command.

.DESCRIPTION
  Launches the FastAPI backend (uvicorn) on port 8000 and the chosen UI
  (Flutter or Vite/React) in debug mode side-by-side. Press Ctrl+C to stop both.

.PARAMETER UI
  Which frontend to launch: "flutter" (default) or "vite" (React SPA on port 5173).

.PARAMETER Device
  Flutter target device. Default: "windows". Ignored when -UI vite.
  Use "chrome" for web, "emulator-5554" for Android emulator, etc.

.PARAMETER EnableImpeller
  Enable Impeller rendering backend for Flutter (experimental on Windows).

.PARAMETER SoftwareRendering
  Force software rendering (use if GPU/driver causes GL errors).

.PARAMETER ServerOnly
  Only start the backend server (skip UI).

.PARAMETER UIOnly
  Only start the UI (skip backend). Assumes backend is already running.

.EXAMPLE
  .\dev.ps1                    # Backend + Flutter (Windows desktop)
  .\dev.ps1 -UI vite           # Backend + React/Vite dev server
  .\dev.ps1 -Device chrome     # Backend + Flutter web
  .\dev.ps1 -ServerOnly        # Backend only
  .\dev.ps1 -UIOnly            # UI only (backend already running)
  .\dev.ps1 -UI vite -UIOnly   # Vite only
  .\dev.ps1 -DebugAudio        # Backend + Flutter con logs DEBUG del pipeline de audio
#>
param(
    [ValidateSet("flutter", "vite")]
    [string]$UI = "flutter",
    [string]$Device = "windows",
    [switch]$ServerOnly,
    [switch]$UIOnly,
    [switch]$EnableImpeller,
    [switch]$SoftwareRendering,
    # Activa logs DEBUG del pipeline de audio (AudioChain, VAD, AGC, ensure_wav).
    # Los mensajes aparecen en la terminal del servidor con prefijo [AudioChain].
    [switch]$DebugAudio
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$ClientDir = Join-Path $Root "pronunciapa_client"
$FrontendDir = Join-Path $Root "frontend"
$PythonCandidates = @(
    (Join-Path $Root ".venv\Scripts\python.exe"),
    (Join-Path $Root ".venv310\Scripts\python.exe")
)
$PythonExe = $PythonCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

# ── Colors ───────────────────────────────────────────────────────────
function Write-Header { param([string]$msg) Write-Host "`n  $msg" -ForegroundColor Cyan }
function Write-Ok     { param([string]$msg) Write-Host "  ✓ $msg" -ForegroundColor Green }
function Write-Info   { param([string]$msg) Write-Host "  → $msg" -ForegroundColor DarkGray }

# ── Preflight checks ────────────────────────────────────────────────
Write-Header "PronunciaPA Dev Launcher"

if (-not $UIOnly) {
    if (-not $PythonExe) {
        Write-Error "Required Python not found. Expected one of: .venv\\Scripts\\python.exe or .venv310\\Scripts\\python.exe"
    }
}
if (-not $ServerOnly) {
    if ($UI -eq "flutter") {
        if (-not (Get-Command flutter -ErrorAction SilentlyContinue)) {
            Write-Error "Flutter not found on PATH"
        }
        if (-not (Test-Path $ClientDir)) {
            Write-Error "Flutter project not found at $ClientDir"
        }
    } else {
        if (-not (Get-Command npx -ErrorAction SilentlyContinue)) {
            Write-Error "Node.js/npx not found on PATH"
        }
        if (-not (Test-Path $FrontendDir)) {
            Write-Error "React frontend not found at $FrontendDir"
        }
    }
}

# ── Track child processes for cleanup ────────────────────────────────
$jobs = @()

function Cleanup {
    Write-Host ""
    Write-Header "Shutting down..."
    foreach ($j in $script:jobs) {
        if ($j -and -not $j.HasExited) {
            Write-Info "Stopping PID $($j.Id)..."
            Stop-Process -Id $j.Id -Force -ErrorAction SilentlyContinue
        }
    }
    Write-Ok "All processes stopped."
}

# Register cleanup on Ctrl+C
$null = Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action { Cleanup }

try {
    # ── Start Backend ────────────────────────────────────────────────
    if (-not $UIOnly) {
        Write-Header "Starting backend server (port 8000)..."

        $env:PYTHONPATH = $Root
        if ($DebugAudio) {
            $env:PRONUNCIAPA_DEBUG_AUDIO = "1"
            Write-Info "Audio debug logging ENABLED (PRONUNCIAPA_DEBUG_AUDIO=1)"
        } else {
            Remove-Item Env:PRONUNCIAPA_DEBUG_AUDIO -ErrorAction SilentlyContinue
        }
        if ($env:PRONUNCIAPA_ASR) {
            Write-Info "Clearing PRONUNCIAPA_ASR override: $($env:PRONUNCIAPA_ASR)"
            Remove-Item Env:PRONUNCIAPA_ASR -ErrorAction SilentlyContinue
        }
        $pyVersion = & $PythonExe --version 2>&1
        Write-Info "Using Python runtime: $pyVersion"

        $serverProc = Start-Process -FilePath $PythonExe `
            -ArgumentList "-u", (Join-Path $Root "start_server.py") `
            -WorkingDirectory $Root `
            -PassThru `
            -NoNewWindow

        $jobs += $serverProc
        Write-Ok "Backend PID: $($serverProc.Id)"

        # Wait for server to be ready
        Write-Info "Waiting for backend health check..."
        $ready = $false
        for ($i = 0; $i -lt 30; $i++) {
            Start-Sleep -Milliseconds 500
            try {
                $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" `
                    -TimeoutSec 2 -ErrorAction SilentlyContinue
                if ($resp.StatusCode -eq 200) {
                    $ready = $true
                    break
                }
            } catch { }
        }
        if ($ready) {
            Write-Ok "Backend is ready at http://127.0.0.1:8000"
        } else {
            Write-Host "  ⚠ Backend didn't respond on /health after 15s (may still be loading models)" -ForegroundColor Yellow
        }
    }

    # ── Start UI ─────────────────────────────────────────────────────
    if (-not $ServerOnly) {
        if ($UI -eq "vite") {
            Write-Header "Starting React/Vite dev server (port 5173)..."

            $viteProc = Start-Process -FilePath "npx" `
                -ArgumentList "vite", "--port", "5173", "--open" `
                -WorkingDirectory $FrontendDir `
                -PassThru `
                -NoNewWindow

            $jobs += $viteProc
            Write-Ok "Vite PID: $($viteProc.Id)"
        } else {
            Write-Header "Starting Flutter UI ($Device)..."

            $flutterArgs = @("run", "-d", $Device, "--hot")
            if ($EnableImpeller) { $flutterArgs += "--enable-impeller" }
            if ($SoftwareRendering) { $flutterArgs += "--enable-software-rendering" }

            $flutterProc = Start-Process -FilePath "flutter" `
                -ArgumentList $flutterArgs `
                -WorkingDirectory $ClientDir `
                -PassThru `
                -NoNewWindow

            $jobs += $flutterProc
            Write-Ok "Flutter PID: $($flutterProc.Id)"
        }
    }

    # ── Wait ─────────────────────────────────────────────────────────
    Write-Header "Running! Press Ctrl+C to stop all."
    Write-Info "Backend:  http://127.0.0.1:8000/docs"
    if ($UI -eq "vite") {
        Write-Info "Frontend: http://localhost:5173"
    } else {
        Write-Info "Flutter:  $Device"
    }
    Write-Host ""

    # Block until any process exits
    while ($true) {
        foreach ($j in $jobs) {
            if ($j.HasExited) {
                Write-Host "  ⚠ Process $($j.Id) exited with code $($j.ExitCode)" -ForegroundColor Yellow
                Cleanup
                return
            }
        }
        Start-Sleep -Seconds 1
    }
}
catch {
    # Ctrl+C or error
    Cleanup
}
finally {
    Cleanup
}
