# FnO Replay Game launcher
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUNBUFFERED = "1"
$py = "C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Join-Path $here "server")
Start-Process "http://127.0.0.1:8787"
& $py -m uvicorn app:app --host 127.0.0.1 --port 8787
