#!/bin/bash
# Fresh push script for NexTTS/VibeVoice-main

# Navigate to the project directory
cd "$(dirname \"$0\")\"

# Remove any existing git history (fresh start)
rm -rf .git

# Initialize fresh git repo
git init

# Add all files
git add .

# Initial commit
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

# Create main branch
git branch -M main

echo ""
echo "Done! Now add your remote:"
echo "git remote add origin https://github.com/adrianpurty/YOUR-REPO-NAME.git"
echo "git push -u origin main"
echo ""