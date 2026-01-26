#!/bin/bash

# Start scheduler in background
python scheduler.py &

# Start Flask server in foreground
gunicorn server:app --bind 0.0.0.0:$PORT