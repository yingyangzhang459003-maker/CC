# GitHub 同步说明

本项目已经完成本地 Git 初始化、远程仓库配置、推送前安全检查与 GitHub 同步。远程仓库为 [`yingyangzhang459003-maker/CC`](https://github.com/yingyangzhang459003-maker/CC)，当前 `main` 分支已包含 Polymarket NVIDIA Event Radar 的 MVP 与核心增强代码。

## 同步状态

| 项目 | 状态 | 说明 |
| --- | --- | --- |
| 目标仓库 | 已配置 | `https://github.com/yingyangzhang459003-maker/CC.git`。 |
| 本地分支 | 已配置 | 本地 `main` 分支已经设置为跟踪远程 `origin/main`。 |
| 推送结果 | 已完成 | 本地 `main` 已成功推送到 GitHub。 |
| 本地 HEAD | 已验证 | `602cf10014a9d2532a196b8461224ca943c72fe2`。 |
| 远程 HEAD | 已验证 | `602cf10014a9d2532a196b8461224ca943c72fe2`，与本地 HEAD 一致。 |
| 关键目录 | 已验证 | 远程仓库包含 `src/`、`tests/`、`config/`、`scripts/`、`deploy/`、`docs/`、`app/` 等目录，以及 `README.md`、`requirements.txt`、`.env.example`、`.gitignore` 和 `LICENSE`。 |

## 当前提交历史

| 提交 | 说明 |
| --- | --- |
| `0de2d6c` | Initial Polymarket NVIDIA Event Radar MVP。 |
| `2401d6d` | Enhance core trading loop and runtime monitoring。 |
| `602cf10` | Merge GitHub initial repository metadata，合并远程初始仓库元数据并保留远程 `LICENSE`。 |

## 安全边界

本次同步遵循 **只推送代码、文档、配置模板和部署模板，不推送真实密钥、钱包信息或生产数据库** 的原则。项目中的 `.env.example` 和 `config/config.example.yaml` 仅作为配置模板使用；真实 API Key、钱包私钥、助记词、GitHub token、交易账户凭据和本地运行数据库不应提交到 Git。

| 风险项 | 当前处理 | 后续建议 |
| --- | --- | --- |
| 环境变量与 API Key | 仅保留模板文件。 | 在部署主机上通过 `.env` 或系统服务环境变量注入真实值。 |
| Polymarket 钱包或资金凭据 | 未纳入项目代码。 | 第一阶段为纸面交易，不应配置真实资金权限。 |
| SQLite 本地数据库 | 通过 `.gitignore` 排除实际数据库文件。 | 如需备份数据，使用单独的私有存储或加密归档。 |
| GitHub 认证凭据 | 使用授权集成完成推送。 | 推送完成后，如不再需要，可在 GitHub 设置中撤销临时授权。 |

## 手动克隆与运行

如果需要在本地或服务器上重新部署项目，可以执行以下命令。首次运行前请根据 `README.md` 配置 Python 虚拟环境、依赖和配置文件。

```bash
git clone https://github.com/yingyangzhang459003-maker/CC.git
cd CC
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp config/config.example.yaml config/config.yaml
python -m src.main status
```

如需启动后台监控循环，可以使用项目内的脚本或 systemd 模板。对于需要长期稳定运行、分钟级或小时级监控的场景，建议部署到一台持续在线的 Linux 主机，并使用 `scripts/run_worker.sh`、`scripts/health_check.py` 和 `deploy/polymarket-nvidia-event-radar.service` 管理运行状态。

## 后续同步命令

后续如果继续修改代码，可以在项目目录中执行以下命令提交并同步。

```bash
git status
git add .
git commit -m "Describe changes"
git push
```

在每次提交前，建议执行以下安全检查，确认没有误提交敏感数据。

```bash
git status --short
git ls-files | grep -E '(^\.env$|data/.*\.db|secrets|private|mnemonic|wallet|token)'
```

如果第二条命令输出真实敏感文件，应立即从 Git 暂存区或历史中移除后再推送。
