echo off
SETLOCAL EnableDelayedExpansion 

call pp\local\env.bat

%PYTHON_EXE%  -c "import pp.plantable_script_mp; pp.plantable_script_mp.run ()"