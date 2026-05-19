# Polymarket NVIDIA Event Radar 实现报告

作者：**Manus AI**  
日期：2026-05-19

## 一、项目目标与第一阶段边界

本项目已按照附件上下文中 1 至 32 步的方向，完成 **Polymarket NVIDIA Event Radar 第一阶段 MVP**。系统只围绕 Polymarket 上的 **NVIDIA / NVDA / 英伟达** 相关预测市场，采集公开盘口、公开信息源、结构化事件信号、价格快照与纸面交易记录。Polymarket 官方文档将其 API 文档组织为市场发现、价格与交易等模块，适合作为第一阶段的公共盘口发现入口。[1] SEC 官方也提供 EDGAR 数据接口，可用于获取 NVIDIA 这类上市公司的公开申报数据。[2]

> 第一阶段的关键原则是：只做公开信息监控、AI 辅助判断和纸面交易验证，不连接真实钱包，不保存私钥，不自动下注，不承诺收益。

| 范围项 | 已完成状态 | 说明 |
| --- | --- | --- |
| 平台范围 | 已限定 | 只扫描 Polymarket，不接入 Kalshi、PredictIt 或其他平台。 |
| 标的范围 | 已限定 | 只关注 NVIDIA、NVDA、英伟达、Blackwell、CUDA、GPU、AI chip 等关键词。 |
| 信息源范围 | 已实现 | 已接入 RSS、NVIDIA 官方源配置、SEC EDGAR、mock X、mock YouTube、mock 新闻源。 |
| AI 判断 | 已实现 | 默认启发式判断，可通过配置启用 OpenAI JSON 结构化输出。 |
| 交易方式 | 已实现纸面交易 | 不涉及真钱、不接钱包、不需要私钥。 |
| 展示方式 | 已实现 | Streamlit 仪表盘展示市场、评分、消息、信号、纸面交易和价格快照。 |
| 版本管理 | 已准备 | 项目已具备 Git 仓库初始化条件和 GitHub 同步说明。 |
| 核心增强 | 已完成 | 已补充市场过滤排序、纸面交易风险预算、价格复盘、后台运行记录、健康检查和 systemd 模板。 |

## 二、系统架构概览

系统采用 Python 单体 MVP 架构，优先保证可读性、可迁移性和后续可扩展性。核心流程是：先扫描 Polymarket 市场，再采集 NVIDIA 相关信息源，随后生成结构化 AI 信号，最后根据纸面交易规则记录模拟入场与后续复盘数据。Polymarket 官方公共 API 文档说明其接口可用于获取市场与订单簿等公开数据；本项目第一阶段主要使用 Gamma API 做市场发现，不执行交易操作。[1]

| 层级 | 模块 | 文件 | 主要职责 |
| --- | --- | --- | --- |
| 配置层 | 配置加载 | `src/config_loader.py` | 读取 YAML 与 `.env`，隔离密钥和运行参数。 |
| 数据层 | 数据模型 | `src/database.py` | 定义 markets、messages、ai_signals、paper_trades 等表。 |
| 市场层 | 盘口扫描 | `src/market_scanner.py` | 调用 Polymarket Gamma API，筛选 NVIDIA 相关盘口。 |
| 市场层 | 盘口评分 | `src/market_ranker.py` | 按流动性、价差、规则清晰度、时效性等维度评分。 |
| 信息层 | 信息源监控 | `src/news_monitor.py`, `src/sources/*` | 统一接入 RSS、SEC 与 mock 源。 |
| 判断层 | AI 信号 | `src/ai_signal.py` | 输出 YES、NO、WATCH 或 SKIP，并给出置信度与原因。 |
| 交易层 | 纸面交易 | `src/paper_trader.py` | 根据信号创建模拟交易，不触达真实资金。 |
| 风控层 | 风险规则 | `src/risk_rules.py` | 计算止损、止盈和估算净 PnL。 |
| 追踪层 | 价格跟踪 | `src/price_tracker.py` | 记录价格快照、未实现盈亏、止损止盈和纸面交易观察窗口。 |
| 运行层 | 运行监控 | `src/runtime_monitor.py` | 记录后台循环每次执行的状态、耗时、结果 JSON 和错误信息。 |
| 部署层 | worker 与 systemd | `scripts/run_worker.sh`, `deploy/polymarket-nvidia-event-radar.service` | 提供长期运行入口与自恢复部署模板。 |
| 展示层 | 仪表盘 | `app/dashboard.py` | 用 Streamlit 展示运行状态和数据结果。 |

## 三、数据库设计

数据库默认使用 SQLite，路径为 `data/radar.db`。这种选择适合 MVP 阶段快速验证；如果后续连续运行 30 天以上并积累大量盘口、消息和价格快照，可以迁移到 PostgreSQL。

| 表名 | 用途 | 关键字段 |
| --- | --- | --- |
| `markets` | 保存 NVIDIA 相关 Polymarket 盘口 | `market_id`, `title`, `yes_price`, `no_price`, `volume`, `liquidity`, `spread` |
| `market_scores` | 保存盘口评分历史 | `market_id`, `total_score`, `grade`, `reason` |
| `messages` | 保存新闻、公告、SEC 和社交消息 | `message_id`, `source`, `title`, `content`, `url`, `processed` |
| `ai_signals` | 保存结构化 AI 事件判断 | `direction`, `confidence`, `impact_score`, `suggested_action`, `reason` |
| `price_snapshots` | 保存市场价格快照 | `market_id`, `yes_price`, `no_price`, `captured_at` |
| `paper_trades` | 保存模拟交易与复盘字段 | `entry_price`, `position_size`, `stop_loss`, `take_profit`, `pnl`, `status` |
| `source_configs` | 为后续动态配置源预留 | `source`, `enabled`, `config_json` |
| `system_logs` | 保存系统日志 | `level`, `module`, `message`, `created_at` |
| `runtime_runs` | 保存后台运行审计 | `run_id`, `command`, `status`, `duration_seconds`, `result_json`, `error_message` |

## 四、已完成的关键功能

系统已经具备端到端运行能力。盘口扫描模块会访问 Polymarket 公共市场接口，筛选与 NVIDIA 相关的盘口。如果当前 Polymarket 没有匹配盘口或外部 API 暂时不可用，系统会使用明确标记为 mock 的样例市场，以保证后续 AI 信号、纸面交易和仪表盘链路可验证。

| 功能 | 实现细节 | 文件 |
| --- | --- | --- |
| 关键词过滤 | 使用 NVIDIA、NVDA、英伟达、Blackwell、GPU、AI chip 等关键词筛选盘口与消息。 | `src/utils.py`, `config/config.example.yaml` |
| 盘口评分 | 对消息相关性、流动性、价差、规则清晰度、AI 可判断性、时效性等评分。 | `src/market_ranker.py` |
| SEC 监控 | 使用 SEC company submissions JSON 接口读取 NVIDIA filings。SEC 要求 API 请求携带合适的 User-Agent。[2] | `src/sources/sec_source.py` |
| RSS 监控 | 使用 `requests` 加超时读取 RSS，再交给 `feedparser` 解析，避免网络源卡住整个流程。 | `src/sources/rss_source.py` |
| AI 判断 | 默认启发式，可选 OpenAI；输出 JSON 风格字段并落库。 | `src/ai_signal.py` |
| 纸面交易 | 按配置生成模拟仓位、止损价、止盈价，并加入置信度、影响分、总持仓上限和同一信号去重约束。 | `src/paper_trader.py`, `src/risk_rules.py` |
| 价格复盘 | 刷新价格快照后更新纸面交易未实现盈亏，并按风险规则关闭触发止损或止盈的交易。 | `src/price_tracker.py`, `src/risk_rules.py` |
| 后台运行 | 循环运行时记录成功、失败、耗时和结果摘要；异常时按配置退避，避免单次公网 API 故障导致进程退出。 | `src/main.py`, `src/runtime_monitor.py` |
| 健康检查 | 输出市场、消息、信号、交易、价格快照和最近运行记录，便于外部监控或人工巡检。 | `scripts/health_check.py` |
| 仪表盘 | 用 Streamlit 展示数据表与核心指标。Streamlit 是面向数据应用的 Python Web 应用框架。[3] | `app/dashboard.py` |

## 五、运行与验证结果

本地验证已经完成依赖安装、语法编译、数据库初始化、盘口扫描、消息监控、AI 信号分析、纸面交易创建和 Streamlit 短启动测试。由于当前公开接口阶段性未检索到真实 NVIDIA 盘口，系统按设计进入 mock 回退路径，这符合第一阶段 MVP 的稳定性要求。

| 验证项 | 命令 | 结果 |
| --- | --- | --- |
| 依赖安装 | `sudo pip3 install -r requirements.txt` | 已完成。 |
| 语法检查 | `python3.11 -m compileall src app tests` | 已通过。 |
| 数据库初始化 | `python3.11 -m src.main init-db --config config/config.example.yaml` | 已生成 `data/radar.db`。 |
| 盘口扫描 | `python3.11 -m src.main scan-markets --config config/config.example.yaml` | 已写入 2 个 mock NVIDIA 盘口、评分和价格快照。 |
| 消息监控 | `python3.11 -m src.main monitor-news --config config/config.example.yaml` | 已写入 26 条消息；部分公网 RSS 超时或 403 被记录为 warning。 |
| AI 分析 | `python3.11 -m src.main analyze --config config/config.example.yaml` | 已生成 26 条结构化信号。 |
| 纸面交易 | `python3.11 -m src.main paper-trades --config config/config.example.yaml` | 已创建 3 条纸面交易。 |
| 仪表盘 | `timeout 12 streamlit run app/dashboard.py --server.headless true --server.port 8501` | 服务成功启动后按测试超时停止。 |
| 核心增强回归 | `pytest -q` | 4 个测试全部通过，覆盖交易、风险退出与状态摘要。 |
| 健康状态 | `python3.11 -m src.main status --config config/config.example.yaml` | 可输出 `health_status=ok` 与最近运行记录。 |

## 六、如何继续运行

首次运行建议复制示例配置，而不是直接修改模板文件。真实 API Key 和邮箱形式的 SEC User-Agent 应写入 `.env`，不要提交到 GitHub。

| 场景 | 命令 |
| --- | --- |
| 创建本地配置 | `cp config/config.example.yaml config/config.yaml && cp .env.example .env` |
| 初始化数据库 | `python3.11 -m src.main init-db --config config/config.yaml` |
| 跑一次完整流水线 | `python3.11 -m src.main run-once --config config/config.yaml` |
| 循环运行 | `python3.11 -m src.main loop --config config/config.yaml` |
| 启动 worker 脚本 | `./scripts/run_worker.sh` |
| 查看健康状态 | `python3.11 scripts/health_check.py config/config.yaml` |
| 打开仪表盘 | `streamlit run app/dashboard.py` |
| 查看数据库概览 | `python3.11 scripts/db_summary.py` |

## 七、下一阶段建议

后续如果要进入第二阶段，建议先把 mock X、mock YouTube 和 mock 新闻源替换为真实 API adapter，并将系统放到长期在线环境中连续运行至少 30 天。只有当纸面交易样本足够、复盘结果稳定、误判来源可解释后，才应讨论是否接入真实钱包；即便进入后续阶段，也应继续保持密钥隔离和人工确认机制。

| 优先级 | 下一步 | 原因 |
| --- | --- | --- |
| 高 | 增加真实 X / YouTube / Tree News adapter | 提高信息源覆盖和时效性。 |
| 高 | 增强 Polymarket CLOB 价格采样 | 当前主要是 Gamma 市场发现，价格更新可进一步细化。 |
| 高 | 部署到长期在线环境 | 纸面交易验证需要连续样本。 |
| 中 | 增加错误复盘页面 | 便于分析 AI 判断错误来源。 |
| 中 | 迁移 PostgreSQL | 当数据量增长后提升可靠性。 |
| 低 | 多标的扩展 | 第一阶段不建议过早扩展，避免削弱 NVIDIA 深度。 |

## References

[1]: https://docs.polymarket.com/api-reference/introduction "Polymarket API Reference Introduction"  
[2]: https://www.sec.gov/search-filings/edgar-application-programming-interfaces "SEC EDGAR Application Programming Interfaces"  
[3]: https://streamlit.io/ "Streamlit"
