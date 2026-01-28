@echo off
echo ============================================================
echo PolyMind MCP - Git 推送脚本
echo ============================================================

cd /d "%~dp0"

echo.
echo [1] 检查 Git 状态...
git status

echo.
echo [2] 从追踪中移除敏感文件...
git rm --cached .env 2>nul
git rm --cached polymarket.db 2>nul

echo.
echo [3] 添加所有更改...
git add -A

echo.
echo [4] 显示将要提交的更改...
git status --short

echo.
echo [5] 创建提交...
git commit -m "feat: 完善项目功能，修复CSS兼容性，添加安装指南和SETUP.md"

echo.
echo [6] 检查远程仓库...
git remote -v

echo.
echo [7] 推送到 GitHub...
git push -u origin main
if errorlevel 1 (
    echo 尝试推送到 master 分支...
    git push -u origin master
)

echo.
echo ============================================================
echo 完成! 
echo ============================================================
pause
