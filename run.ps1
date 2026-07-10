# Sindibad launcher
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$patchTarget = ".venv\Lib\site-packages\chainlit\cli\__init__.py"
if (Test-Path $patchTarget) {
    $content = Get-Content $patchTarget -Raw
    if ($content -match "nest_asyncio\.apply\(\)" -and $content -notmatch "sys\.version_info < \(3, 14\)") {
        Write-Host "Applying Chainlit Python 3.14 patch..."
    }
}

Write-Host ""
Write-Host "=== Sindibad Dashboard (Recommended) ===" -ForegroundColor Cyan
Write-Host "  http://localhost:8002" -ForegroundColor Green
Write-Host ""
Write-Host "=== Chainlit Chat (Legacy) ===" -ForegroundColor Yellow
Write-Host "  http://localhost:8001" -ForegroundColor Green
Write-Host ""

$mode = $args[0]
if ($mode -eq "chainlit") {
    & .\.venv\Scripts\chainlit run chainlit_app.py --port 8001 --host 127.0.0.1
} else {
    & .\.venv\Scripts\uvicorn app.main:app --reload --host 127.0.0.1 --port 8002
}
