@echo off
chcp 65001 >nul
echo ============================================================
echo GitHub一键上传脚本
echo ============================================================
echo.

REM 检查Git是否安装
git --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Git，请先安装Git
    echo.
    echo 下载地址: https://git-scm.com/download/win
    echo.
    pause
    exit /b 1
)

echo [OK] Git已安装
echo.

REM 提示用户输入仓库地址
echo 请输入GitHub仓库地址（例如：https://github.com/用户名/仓库名.git）
echo.
set /p REPO_URL=仓库地址: 

if "%REPO_URL%"=="" (
    echo [错误] 仓库地址不能为空
    pause
    exit /b 1
)

echo.
echo ============================================================
echo 开始上传到: %REPO_URL%
echo ============================================================
echo.

REM 检查是否已经是Git仓库
if exist ".git" (
    echo [提示] 检测到已有Git仓库
) else (
    echo [1/5] 初始化Git仓库...
    git init
    if errorlevel 1 (
        echo [错误] Git初始化失败
        pause
        exit /b 1
    )
    echo [OK] Git初始化完成
    echo.
)

echo [2/5] 添加所有文件...
git add .
if errorlevel 1 (
    echo [错误] 添加文件失败
    pause
    exit /b 1
)
echo [OK] 文件添加完成
echo.

echo [3/5] 提交更改...
git commit -m "Initial commit: 商品期货AI分析系统 - 完整的Multi-Agent期货分析平台"
if errorlevel 1 (
    echo [提示] 没有新的更改需要提交，或提交失败
    echo 继续执行...
)
echo.

echo [4/5] 设置远程仓库...
git remote remove origin >nul 2>&1
git remote add origin %REPO_URL%
if errorlevel 1 (
    echo [错误] 设置远程仓库失败
    pause
    exit /b 1
)
echo [OK] 远程仓库设置完成
echo.

echo [5/5] 推送到GitHub...
echo.
echo [提示] 首次推送需要输入GitHub凭据
echo        用户名: 你的GitHub用户名
echo        密码: Personal Access Token (不是登录密码)
echo.
echo 如何获取Token:
echo 1. GitHub → Settings → Developer settings
echo 2. Personal access tokens → Tokens (classic)
echo 3. Generate new token → 勾选 repo 权限
echo.
pause
echo.

git branch -M main
git push -u origin main

if errorlevel 1 (
    echo.
    echo [错误] 推送失败
    echo.
    echo 常见问题:
    echo 1. 密码错误 → 使用Personal Access Token，不是登录密码
    echo 2. 仓库不存在 → 检查仓库地址是否正确
    echo 3. 权限不足 → 确保你有仓库的写入权限
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo [成功] 所有文件已上传到GitHub！
echo ============================================================
echo.
echo 访问你的仓库: %REPO_URL:~0,-4%
echo.
echo 下一步:
echo 1. 在GitHub添加仓库描述和Topics标签
echo 2. 检查README.md是否正确显示
echo 3. 分享给需要的朋友
echo.
pause

