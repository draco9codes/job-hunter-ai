#!/bin/bash
# Daily pipeline run: scrape -> match (capped) -> generate-resume -> track.
#
# Naukri/Foundit deliberately launch a *visible* browser (so a captcha can be
# solved by hand instead of silently failing), which means this script needs
# an active desktop session -- DISPLAY/XAUTHORITY below assume you're logged
# into seat0 at run time. If you're logged out when this fires, those two
# scrapers will fail to launch a browser; everything else in the pipeline
# (Greenhouse, Lever, Instahyre, match, generate-resume, track) doesn't need
# a display and will run fine regardless.
set -uo pipefail

PROJECT_DIR="/home/shivamkumar/Projects/job-hunter-ai"
cd "$PROJECT_DIR"

export DISPLAY=:0
export XAUTHORITY="$(find /run/user/1000 -maxdepth 1 -name 'xauth_*' 2>/dev/null | head -1)"

mkdir -p logs
LOG_FILE="logs/pipeline_$(date +%Y%m%d_%H%M%S).log"

{
    echo "=== Pipeline run started at $(date) ==="

    if ! curl -s -m 3 http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "ollama not running, starting it..."
        nohup ollama serve > /tmp/ollama_serve.log 2>&1 &
        sleep 5
    fi

    .venv/bin/python main.py scrape
    .venv/bin/python main.py match --limit 30
    .venv/bin/python main.py generate-resume
    .venv/bin/python main.py track

    echo "=== Pipeline run finished at $(date) ==="
} >> "$LOG_FILE" 2>&1
