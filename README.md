# Polymarket NVIDIA Event Radar

**Polymarket NVIDIA Event Radar** 是一个只围绕 Polymarket 上 NVIDIA / NVDA 相关盘口构建的公开信息差监控与纸面交易验证系统。第一阶段严格不接真实钱包、不保存私钥、不自动下注，只做盘口发现、新闻与事件流监控、AI 事件分析、价格变化跟踪、纸面交易记录和复盘。

> 本项目不是投资建议，也不是自动交易系统。它的目标是验证公开消息出现后，Polymarket 上 NVIDIA 相关盘口是否存在可重复的延迟反应。

## 为什么只做 NVIDIA / NVDA

NVIDIA 是 AI 芯片、数据中心、GPU、出口管制、财报和供应链新闻的高频标的。只聚焦一个标的能够让系统先做窄、做深，避免在第一阶段扩张到多公司、多平台或真钱交易。

## 系统功能

| 模块 | 功能 | 第一阶段状态 |
| --- | --- | --- |
| Polymarket 盘口扫描器 | 扫描 active=true、closed=false 的市场，筛选 NVIDIA / NVDA 相关盘口 | 已实现，支持 Gamma API 与 mock 回退 |
| NVIDIA 盘口评分系统 | 按消息频率、流动性、价差、结算规则、AI 可判断性等维度评分 | 已实现启发式评分 |
| 信息源监控器 | 接入 NVIDIA 官方 RSS、SEC EDGAR、通用 RSS、mock X、mock YouTube | 已实现 |
| AI 事件分析器 | 输出结构化 YES / NO / WATCH / SKIP 信号 | 已实现，默认启发式，可开启 OpenAI |
| 价格变化跟踪 | 记录价格快照、刷新未实现盈亏，并根据止损止盈规则关闭纸面交易 | 已增强 |
| 纸面交易系统 | 根据信号创建模拟交易，加入置信度、影响分、总仓位预算和去重约束 | 已增强 |
| 运行健康监控 | 记录后台循环每次执行状态、耗时、错误和最近运行健康摘要 | 已增强 |
| Streamlit 仪表盘 | 展示市场、评分、消息、信号、纸面交易和价格快照 | 已实现 |
| GitHub 同步 | 本地 Git 仓库、规范 commit、可配置远程仓库 | 已实现本地仓库，远程需用户提供 URL 或授权 |

## 技术栈

项目采用 **Python 3.11、SQLite、SQLAlchemy、Requests、feedparser、OpenAI SDK、Pandas 和 Streamlit**。数据库默认写入 `data/radar.db`，真实密钥只应写入本地 `.env`，不得提交 GitHub。

## 安装步骤

```bash
cd polymarket-nvidia-event-radar
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp config/config.example.yaml config/config.yaml
cp .env.example .env
python -m src.main init-db --config config/config.yaml
```

## 环境变量配置

请在 `.env` 中配置真实 API Key。第一阶段即使没有 X、YouTube、付费新闻或 OpenAI Key，也可以使用 mock adapter 继续运行。

```env
OPENAI_API_KEY=
DATABASE_URL=sqlite:///data/radar.db
SEC_USER_AGENT=PolymarketNvidiaEventRadar/0.1 your_email@example.com
```

## 如何运行

| 场景 | 命令 |
| --- | --- |
| 初始化数据库 | `python -m src.main init-db --config config/config.yaml` |
| 运行一次完整 MVP 流水线 | `python -m src.main run-once --config config/config.yaml` |
| 仅扫描 Polymarket 盘口 | `python -m src.main scan-markets --config config/config.yaml` |
| 仅监控新闻源 | `python -m src.main monitor-news --config config/config.yaml` |
| 仅执行 AI 分析 | `python -m src.main analyze --config config/config.yaml` |
| 创建纸面交易 | `python -m src.main paper-trades --config config/config.yaml` |
| 按配置间隔循环运行 | `python -m src.main loop --config config/config.yaml` |
| 用脚本启动后台 worker | `./scripts/run_worker.sh` |
| 查看健康状态 JSON | `python scripts/health_check.py config/config.yaml` |
| 打开仪表盘 | `streamlit run app/dashboard.py` |

## 当前开发进度

第一阶段 MVP 的目录结构、核心模块、配置、数据库 schema、仪表盘、文档和测试已经完成。在核心增强版中，项目进一步加入了 **市场过滤与排序、纸面交易风险预算、YES/NO 统一损益计算、交易复盘窗口、后台循环运行记录、失败退避恢复和健康检查脚本**。默认配置中 `ai.use_llm=false`，系统会用启发式分析保证没有 API Key 时也能跑通。后续如果要让 AI 输出更强，可以在 `.env` 写入 `OPENAI_API_KEY`，并把配置中的 `ai.use_llm` 改为 `true`。

## 后续开发计划

下一步应把 mock X、mock YouTube、mock Tree News 替换为真实 API，并把连续运行部署到一台长期在线的服务器或本机定时任务中。仓库已提供 `scripts/run_worker.sh` 和 `deploy/polymarket-nvidia-event-radar.service`，可以在服务器上使用 systemd 托管。进入第二阶段之前，应至少连续运行 30 天，积累足够纸面交易样本，并人工复盘错误案例。

## GitHub 同步

```bash
git remote add origin YOUR_GITHUB_REPO_URL
git push -u origin main
```

请不要提交 `.env`、数据库文件、私钥、助记词或任何真实 API Key。如果希望由我直接推送，你需要提供 GitHub 仓库 URL，并通过浏览器登录、临时访问令牌或 `gh auth login` 授权其中一种方式完成认证。
