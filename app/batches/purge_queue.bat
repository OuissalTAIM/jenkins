set PYTHONPATH=../..
IF /i "%*" == "all" GOTO all
python.exe purge_queue.py %*
GOTO end

:all
python.exe purge_queue.py mine2farm mine2farm_detailed_results mine2farm_global_results
GOTO end

:end
ECHO Queues purged