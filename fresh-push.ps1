# Fresh push script for NexTTS/VibeVoice-main

$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Navigate to project
Set-Location $projectDir
Write-Host "Starting fresh push from: $projectDir" -ForegroundColor Cyan

# Remove existing git history
if (Test-Path ".git") {
    Write-Host "Removing existing .git folder..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force ".git"
}

# Initialize fresh repo
git init

# Add all files
git add .

# Check what will be committed
Write-Host "`nFiles to be committed:" -ForegroundColor Cyan
git status --short

# Commit
Write-Host "`nCreating initial commit..." -ForegroundColor Cyan
git commit -m "NexTTS Production System - Initial commit

Features:
- Database models with SQLAlchemy
- API key authentication
- Rate limiting per plan
- Stripe billing integration
- Prometheus metrics
- Health checks
- CI/CD pipelines
- Flask serverless API"

# Rename branch
git branch -M main

Write-Host "`nDone!" -ForegroundColor Green
Write-Host "Now run these commands:" -ForegroundColor Yellow
Write-Host '  git remote add origin https://github.com/adrianpurty/YOUR-REPO-NAME.git' -ForegroundColor White
Write-Host '  git push -u origin main' -ForegroundColor White