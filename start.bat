@echo off
echo Backend ishga tushirilmoqda...
start cmd /k "cd /d C:\Users\Lenovo__\Desktop\bobur_1\zavod-health-monitoring\backend && uvicorn app.main:app --reload"

timeout /t 2 /nobreak > nul

echo Dashboard ishga tushirilmoqda...
start cmd /k "cd /d C:\Users\Lenovo__\Desktop\bobur_1\zavod-health-monitoring\dashboard && streamlit run app.py"