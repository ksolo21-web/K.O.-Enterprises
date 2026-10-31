# Operator-initiated, local-only install and acceptance. Public model weights download only by explicit invocation.
param([string]$Writer='qwen2.5vl:3b',[string]$Reviewer='granite3.2-vision:2b')
$ErrorActionPreference='Stop'
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
  throw 'Install Ollama from https://ollama.com/download/windows first. No new account required.'
}
New-Item -Path local-results -ItemType Directory -Force | Out-Null
$stamp=(Get-Date -Format 'yyyyMMdd-HHmmss')+'-'+([guid]::NewGuid().ToString('N').Substring(0,8))
$proof="local-results/activation-$stamp"
python -m scripts.activate_vision --out-dir $proof --writer-model $Writer --review-model $Reviewer --start-server --download-models --run-live-gate
$code=$LASTEXITCODE
Write-Host "Full activation record: $proof/activation_status.json"
if ($code -ne 0) { throw "Live acceptance remains blocked; see the activation record. Exit: $code" }
