#!/bin/bash
cd "$(dirname "$0")"
python3 web_app.py &
sleep 2
xdg-open http://localhost:5000
