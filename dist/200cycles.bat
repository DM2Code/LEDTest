@echo off
set /a var=0
:start
set /a var+=1
  serialLEDtest_22-2-2021.exe
  echo ===========================================================
  echo ============================   completed run #%var%.  =======
  echo ===========================================================
  if %var% EQU 200 goto end
goto start

:end
echo completed all runs.
pause
exit