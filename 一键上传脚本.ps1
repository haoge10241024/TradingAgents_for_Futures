# GitHub一键上传脚本 (PowerShell版本)
# 更稳定、更可靠

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "GitHub一键上传脚本" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# 检查Git是否安装
try {
    $gitVersion = git --version
    Write-Host "[OK] Git已安装: $gitVersion" -ForegroundColor Green
    Write-Host ""
} catch {
    Write-Host "[错误] 未检测到Git，请先安装Git" -ForegroundColor Red
    Write-Host ""
    Write-Host "下载地址: https://git-scm.com/download/win" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "按回车键退出"
    exit 1
}

# 提示用户输入仓库地址
Write-Host "请输入GitHub仓库地址" -ForegroundColor Yellow
Write-Host "例如：https://github.com/用户名/仓库名.git" -ForegroundColor Gray
Write-Host ""
$repoUrl = Read-Host "仓库地址"

if ([string]::IsNullOrWhiteSpace($repoUrl)) {
    Write-Host ""
    Write-Host "[错误] 仓库地址不能为空" -ForegroundColor Red
    Read-Host "按回车键退出"
    exit 1
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "开始上传到: $repoUrl" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# 检查是否已经是Git仓库
if (Test-Path ".git") {
    Write-Host "[提示] 检测到已有Git仓库" -ForegroundColor Yellow
} else {
    Write-Host "[1/5] 初始化Git仓库..." -ForegroundColor Cyan
    git init
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[错误] Git初始化失败" -ForegroundColor Red
        Read-Host "按回车键退出"
        exit 1
    }
    Write-Host "[OK] Git初始化完成" -ForegroundColor Green
    Write-Host ""
}

Write-Host "[2/5] 添加所有文件..." -ForegroundColor Cyan
git add .
if ($LASTEXITCODE -ne 0) {
    Write-Host "[错误] 添加文件失败" -ForegroundColor Red
    Read-Host "按回车键退出"
    exit 1
}
Write-Host "[OK] 文件添加完成" -ForegroundColor Green
Write-Host ""

Write-Host "[3/5] 提交更改..." -ForegroundColor Cyan
git commit -m "Initial commit: 商品期货AI分析系统 - 完整的Multi-Agent期货分析平台"
if ($LASTEXITCODE -ne 0) {
    Write-Host "[提示] 没有新的更改需要提交，继续执行..." -ForegroundColor Yellow
}
Write-Host ""

Write-Host "[4/5] 设置远程仓库..." -ForegroundColor Cyan
git remote remove origin 2>$null
git remote add origin $repoUrl
if ($LASTEXITCODE -ne 0) {
    Write-Host "[错误] 设置远程仓库失败" -ForegroundColor Red
    Read-Host "按回车键退出"
    exit 1
}
Write-Host "[OK] 远程仓库设置完成" -ForegroundColor Green
Write-Host ""

Write-Host "[5/5] 推送到GitHub..." -ForegroundColor Cyan
Write-Host ""
Write-Host "[提示] 首次推送需要输入GitHub凭据" -ForegroundColor Yellow
Write-Host "       用户名: 你的GitHub用户名" -ForegroundColor Gray
Write-Host "       密码: Personal Access Token (不是登录密码)" -ForegroundColor Gray
Write-Host ""
Write-Host "如何获取Token:" -ForegroundColor Yellow
Write-Host "1. GitHub -> Settings -> Developer settings" -ForegroundColor Gray
Write-Host "2. Personal access tokens -> Tokens (classic)" -ForegroundColor Gray
Write-Host "3. Generate new token -> 勾选 repo 权限" -ForegroundColor Gray
Write-Host ""
Read-Host "准备好后按回车继续"
Write-Host ""

git branch -M main
git push -u origin main

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[错误] 推送失败" -ForegroundColor Red
    Write-Host ""
    Write-Host "常见问题:" -ForegroundColor Yellow
    Write-Host "1. 密码错误 -> 使用Personal Access Token，不是登录密码" -ForegroundColor Gray
    Write-Host "2. 仓库不存在 -> 检查仓库地址是否正确" -ForegroundColor Gray
    Write-Host "3. 权限不足 -> 确保你有仓库的写入权限" -ForegroundColor Gray
    Write-Host ""
    Read-Host "按回车键退出"
    exit 1
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "[成功] 所有文件已上传到GitHub！" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "访问你的仓库: $($repoUrl -replace '.git$', '')" -ForegroundColor Cyan
Write-Host ""
Write-Host "下一步:" -ForegroundColor Yellow
Write-Host "1. 在GitHub添加仓库描述和Topics标签" -ForegroundColor Gray
Write-Host "2. 检查README.md是否正确显示" -ForegroundColor Gray
Write-Host "3. 分享给需要的朋友" -ForegroundColor Gray
Write-Host ""
Read-Host "按回车键退出"

