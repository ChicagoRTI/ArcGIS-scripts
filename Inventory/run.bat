echo off
SETLOCAL EnableDelayedExpansion 

SET PYTHON_EXE="C:\\Program Files\\ArcGIS\\Pro\\bin\\Python\\envs\\arcgispro-py3\\python.exe"

%PYTHON_EXE%  -c "import code.merge_records; code.merge_records.run ()"