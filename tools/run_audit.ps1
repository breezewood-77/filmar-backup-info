<#
  One-step audit runner for Windows PowerShell.

  Usage, from anywhere:
      powershell -ExecutionPolicy Bypass -File .\_audit\tools\run_audit.ps1

  Optional:
      ... -Target "D:\SomeOtherFolder" -Days 60

  Handles the three things that usually stop the manual steps: the Python
  launcher being called `py` rather than `python`, PowerShell's `>` writing
  UTF-16 that nothing else can read, and the script being run from the wrong
  directory.
#>
[CmdletBinding()]
param(
    [string]$Target = "C:\Users\Francis\Documents\Code",
    [int]$Days = 90
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path

function Find-Python {
    foreach ($c in @("python", "py", "python3")) {
        $cmd = Get-Command $c -ErrorAction SilentlyContinue
        if (-not $cmd) { continue }
        # The Windows Store stub resolves but does nothing useful.
        if ($cmd.Source -like "*WindowsApps*" -and $c -eq "python") { continue }
        $args = if ($c -eq "py") { @("-3", "--version") } else { @("--version") }
        try {
            $v = & $cmd.Source @args 2>&1
            if ($LASTEXITCODE -eq 0) {
                return @{ Exe = $cmd.Source; Pre = $(if ($c -eq "py") { @("-3") } else { @() }); Ver = "$v" }
            }
        } catch { }
    }
    return $null
}

$py = Find-Python
if (-not $py) {
    Write-Host "No working Python found." -ForegroundColor Red
    Write-Host "Install it from https://www.python.org/downloads/ and tick"
    Write-Host "'Add python.exe to PATH' during setup, then reopen PowerShell."
    exit 1
}
Write-Host "Python: $($py.Ver)  [$($py.Exe)]" -ForegroundColor Green

if (-not (Test-Path -LiteralPath $Target)) {
    Write-Host "Target folder not found: $Target" -ForegroundColor Red
    Write-Host "Pass the right one, e.g.  -Target 'D:\Code'"
    exit 1
}
Write-Host "Target: $Target"

$audit = Join-Path $here "bloat_audit.py"
$check = Join-Path $here "registry_check.py"
$reg = Join-Path $here "registry.tsv"
foreach ($f in @($audit, $check, $reg)) {
    if (-not (Test-Path -LiteralPath $f)) {
        Write-Host "Missing: $f" -ForegroundColor Red
        Write-Host "Run this from inside the cloned repo's tools folder."
        exit 1
    }
}

$stamp = Get-Date -Format "yyyy-MM-dd"
$out = Join-Path (Get-Location) "audit-$stamp"

# Python must not buffer, or progress lines only appear at the very end.
$env:PYTHONUNBUFFERED = "1"

# Tee-Object streams to the console AND the file. Capturing into a variable
# instead (the previous approach) shows nothing until the run finishes, which
# is indistinguishable from a hang.
#
# Do NOT add 2>&1 here. PowerShell turns a native command's stderr into an
# error record, and with $ErrorActionPreference = "Stop" that aborts the run
# the first time the script prints progress. Left alone, stderr goes straight
# to the console and stdout goes through the pipe.
$ErrorActionPreference = "Continue"
Write-Host "`n--- audit ---" -ForegroundColor Cyan
Write-Host "(large folders take a few minutes; progress prints as it goes)"
& $py.Exe @($py.Pre) $audit $Target "--days" "$Days" | Tee-Object -FilePath "$out.txt"

Write-Host "`n--- json ---" -ForegroundColor Cyan
& $py.Exe @($py.Pre) $audit $Target "--days" "$Days" "--json" 2>$null |
    Out-File -FilePath "$out.json" -Encoding utf8

Write-Host "`n--- registry check ---" -ForegroundColor Cyan
& $py.Exe @($py.Pre) $check $Target "--registry" $reg |
    Tee-Object -FilePath "$out-registry.txt"

Write-Host "`nWrote:" -ForegroundColor Green
Write-Host "  $out.txt"
Write-Host "  $out.json"
Write-Host "  $out-registry.txt"
Write-Host "`nPaste the .txt into the chat."
