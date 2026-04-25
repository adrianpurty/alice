#!/usr/bin/env python3
"""Local development server for NexTTS."""

from dotenv import load_dotenv

load_dotenv()

from cloud.serverless.vercel import api

if __name__ == "__main__":
    print("Starting NexTTS server at http://localhost:5000")
    print("API endpoints available at http://localhost:5000/api/")
    print("\nHealth check: http://localhost:5000/api/health")
    print("Metrics: http://localhost:5000/api/metrics")
    print("\nPress Ctrl+C to stop\n")

    api.run(host="0.0.0.0", port=5000, debug=True)
