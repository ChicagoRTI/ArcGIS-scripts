echo off
SETLOCAL EnableDelayedExpansion 

call local\env.bat

set /p "county=County: "
set /p "start_step=Start Step: "

%PYTHON_EXE%  -c "import fs.run; fs.run.run_from_bat ('%county%', '%start_step%')"