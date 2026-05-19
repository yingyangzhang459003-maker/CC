# 数据库 Schema

数据库默认使用 SQLite，路径为 `data/radar.db`。Schema 由 `src/database.py` 中的 SQLAlchemy ORM 定义。

| 表 | 用途 | 关键字段 |
| --- | --- | --- |
| `markets` | NVIDIA 相关 Polymarket 盘口 | `market_id`, `title`, `yes_price`, `no_price`, `volume`, `liquidity`, `spread`, `resolution_rules` |
| `market_scores` | 盘口评分历史 | `market_id`, `total_score`, `grade`, `reason` |
| `messages` | 信息源消息 | `message_id`, `source`, `title`, `content`, `url`, `published_at`, `captured_at`, `processed` |
| `ai_signals` | AI 或启发式分析信号 | `signal_id`, `message_id`, `market_id`, `direction`, `confidence`, `impact_score`, `suggested_action` |
| `price_snapshots` | 盘口价格快照 | `market_id`, `yes_price`, `no_price`, `volume`, `liquidity`, `captured_at` |
| `paper_trades` | 纸面交易记录 | `paper_trade_id`, `signal_id`, `direction`, `entry_price`, `position_size`, `pnl`, `status` |
| `source_configs` | 信息源配置扩展 | `source`, `enabled`, `config_json` |
| `system_logs` | 系统日志 | `level`, `module`, `message`, `created_at` |

第一阶段的数据库设计偏向可解释与可迁移，而不是高频交易性能。后续如果数据量增长，可以迁移到 PostgreSQL。
