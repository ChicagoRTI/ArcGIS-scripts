echo off
SETLOCAL EnableDelayedExpansion 

call local\env.bat

%PYTHON_EXE%  -m "pp.locate_trees"