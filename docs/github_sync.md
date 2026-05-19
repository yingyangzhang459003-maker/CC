# GitHub 同步说明

本项目已经初始化为本地 Git 仓库，并按模块拆分 commit。用户提供 GitHub 仓库地址后，可以执行以下命令同步：

```bash
git remote add origin YOUR_GITHUB_REPO_URL
git push -u origin main
```

必须遵守以下安全要求：不得提交 `.env`、真实 API Key、钱包私钥、助记词、数据库密码、`data/*.db`、`*.sqlite` 或 `secrets/` 目录。`.gitignore` 已包含这些规则。

| 操作 | 命令 |
| --- | --- |
| 查看状态 | `git status` |
| 查看提交记录 | `git log --oneline --decorate` |
| 添加远程仓库 | `git remote add origin <url>` |
| 推送到 GitHub | `git push -u origin main` |
