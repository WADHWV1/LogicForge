param(
    [string]$ChatModel = "qwen2.5-coder:3b",
    [string]$EmbeddingModel = "nomic-embed-text"
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "Ollama is not installed and winget is unavailable. Install Ollama from https://ollama.com/download/windows, reopen PowerShell, and run this script again."
    }
    Write-Host "Installing Ollama for Windows..."
    winget install --id Ollama.Ollama --exact --accept-package-agreements --accept-source-agreements
    $env:PATH = "$env:PATH;$env:LOCALAPPDATA\Programs\Ollama"
}

if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    throw "Ollama was installed, but this terminal cannot find ollama.exe. Reopen PowerShell and run .\setup-local-ai.ps1 again."
}

Write-Host "Downloading local code model $ChatModel ..."
ollama pull $ChatModel
if ($LASTEXITCODE -ne 0) { throw "Could not download the chat model." }

Write-Host "Downloading local embedding model $EmbeddingModel ..."
ollama pull $EmbeddingModel
if ($LASTEXITCODE -ne 0) { throw "Could not download the embedding model." }

$env:LOGICFORGE_PROVIDER = "ollama"
$env:OLLAMA_CHAT_MODEL = $ChatModel
$env:OLLAMA_EMBED_MODEL = $EmbeddingModel
$env:OLLAMA_BASE_URL = "http://127.0.0.1:11434"

Write-Host "Starting LogicForge with local Ollama models. No Copilot or cloud model key is used."
python app.py
