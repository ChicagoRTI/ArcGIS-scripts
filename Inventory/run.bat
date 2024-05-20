echo off

SETLOCAL EnableDelayedExpansion 

SET PYTHON_EXE="C:\\Users\\dmorrison\\AppData\\Local\\ESRI\\conda\\envs\\arcgispro-py3-clone\\python.exe"
%PYTHON_EXE%  -c "import inv.scheduled_job; inv.scheduled_job.run ()"