set PYTHONPATH=../..
REM python.exe export_results.py --one %*
REM GOTO end_one

python.exe export_results.py --all
GOTO end_all

:end_one
ECHO Results exported for scenario %*

:end_all
ECHO Results exported for all scenarios