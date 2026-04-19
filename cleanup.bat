@echo off
REM 删除versions文件夹
rmdir /s /q "d:\Pythonprojectcode\versions"

if %errorlevel% equ 0 (
    echo [成功] versions 文件夹已删除
) else (
    echo [失败] 无法删除 versions 文件夹
)

pause
