# Requires separately installed official Ollama and Python dependencies; opt-in downloads.
param([string]$Writer = 'qwen2.5vl:3b', [string]$Reviewer = 'granite3.2-vision:2b')
$ErrorActionPreference = 'Stop'
if ($env:OLLAMA_HOST -and $env:OLLAMA_HOST -notin @('127.0.0.1:11434', 'http://127.0.0.1:11434')) {
  throw 'STOP: Configure OLLAMA_HOST=127.0.0.1:11434 (loopback only).'
}
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
  throw 'Install official Ollama from https://ollama.com/download/windows then rerun this script.'
}
python -c 'from PIL import Image'
if ($LASTEXITCODE -ne 0) { throw 'Install Python dependencies from requirements.txt first.' }
ollama pull $Writer
if ($LASTEXITCODE -ne 0) { throw 'Writer model download failed.' }
ollama pull $Reviewer
if ($LASTEXITCODE -ne 0) { throw 'Reviewer model download failed.' }
python -m inspection_engine model-preflight --writer-model $Writer --review-model $Reviewer
if ($LASTEXITCODE -ne 0) { throw 'Vision model preflight failed.' }
New-Item -Path local-results -ItemType Directory -Force | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
python -m inspection_engine model-smoke --writer-model $Writer --review-model $Reviewer --out "local-results/vision-smoke-$stamp.json"
if ($LASTEXITCODE -ne 0) { throw 'Live synthetic image inference did not pass.' }
Write-Host 'Synthetic model check completed; real property accuracy not verified.'
