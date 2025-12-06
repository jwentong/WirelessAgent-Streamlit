@echo off
REM 如果你需要激活虚拟环境，请取消下面一行的注释
REM call venv\Scripts\activate.bat
REM 依次运行Python脚本，并把输出及错误信息记录到log.txt中


python Prompt_Based_North.py >> log_Prompt_North_02.txt 2>&1
python Prompt_Based_South.py >> log_Prompt_South_02.txt 2>&1

python Optimal_RA_North.py >> log_Optimal_North_02.txt 2>&1
python Optimal_RA_South.py >> log_Optimal_South_02.txt 2>&1