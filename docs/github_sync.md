# GitHub 同步说明

本项目已经初始化为本地 Git 仓库，并已包含源码、配置模板、文档、测试、运行脚本和部署模板。远程同步到 GitHub 时，核心原则是 **只推送代码与非敏感配置模板，不推送真实密钥、钱包信息或本地数据库**。

## 需要你提供什么

| 信息 | 是否必须 | 说明 |
| --- | --- | --- |
| GitHub 仓库 URL | 必须 | 例如 `https://github.com/yourname/polymarket-nvidia-event-radar.git` 或 SSH 格式 `git@github.com:yourname/polymarket-nvidia-event-radar.git`。 |
| 仓库可见性 | 建议提供 | 确认是 private 还是 public。量化交易研究项目建议先用 private。 |
| 授权方式 | 必须选择一种 | 可选浏览器登录、GitHub CLI 登录、或提供临时 fine-grained token。 |
| 是否需要我直接推送 | 建议确认 | 如果你只需要命令，我可以给出本地操作步骤；如果要我代推，需要完成授权。 |

## 推荐授权方式

| 方式 | 适用场景 | 操作说明 | 安全建议 |
| --- | --- | --- | --- |
| 浏览器登录 GitHub | 你希望我在当前环境直接推送 | 我打开 GitHub 页面后，你接管浏览器完成登录与授权。 | 不要在聊天中发送密码或 2FA 验证码。 |
| GitHub CLI 登录 | 你接受设备码授权 | 执行 `gh auth login`，你在浏览器完成设备码确认。 | 授权完成后可随时在 GitHub settings 撤销。 |
| Fine-grained token | 你已有目标仓库且希望快速推送 | 提供只对该仓库有 `Contents: Read and write` 权限的临时 token。 | 设置短有效期；推送后立即撤销。 |

## 手动同步命令

如果你自己在本地同步，可以进入项目目录后执行以下命令。首次推送前请确认 `.gitignore` 已生效，且 `.env`、数据库、私钥、助记词和任何 API Key 没有被加入 Git。

```bash
cd polymarket-nvidia-event-radar
git status
git remote add origin YOUR_GITHUB_REPO_URL
git branch -M main
git push -u origin main
```

如果远程仓库已经存在 `origin`，应改用：

```bash
git remote set-url origin YOUR_GITHUB_REPO_URL
git push -u origin main
```

## 推送前安全检查

| 检查项 | 命令 | 预期结果 |
| --- | --- | --- |
| 查看未提交文件 | `git status --short` | 只看到预期源码、文档和配置模板。 |
| 检查敏感文件 | `git ls-files | grep -E '(^\.env$|data/.*\.db|secrets|key|private|mnemonic)'` | 不应输出真实敏感文件。 |
| 查看提交历史 | `git log --oneline --decorate -5` | 最近提交应描述核心增强或 MVP。 |
| 查看远程地址 | `git remote -v` | 指向你的 GitHub 仓库。 |

## 我可以直接帮你推送时的流程

你回复 GitHub 仓库 URL，并说明采用哪种授权方式。如果需要我通过浏览器或 GitHub CLI 登录，我会先打开对应页面或启动授权流程，然后请你接管完成登录。完成后，我会执行安全检查、添加远程仓库、推送 `main` 分支，并把最终仓库链接与提交哈希反馈给你。
