@echo off
ECHO Checking and installing dependencies from requirements.txt...
pip install -r requirements.txt

ECHO.
ECHO Launching Gantt Chart Planner...
python main.py