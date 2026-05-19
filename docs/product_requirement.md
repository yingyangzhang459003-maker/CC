# 产品需求说明：Polymarket NVIDIA Event Radar

本项目第一阶段严格限定为 **Polymarket + NVIDIA / NVDA + 公开信息源 + 纸面交易**。系统的核心目标不是预测未来，也不是实盘下注，而是记录公开消息出现后，Polymarket 相关盘口是否存在尚未被充分反映的信息差。

| 范围 | 第一阶段处理方式 |
| --- | --- |
| 平台 | 只接入 Polymarket |
| 标的 | 只关注 NVIDIA / NVDA / 英伟达相关盘口 |
| 信息源 | 官方公告、SEC、RSS 新闻、mock X、mock YouTube |
| 交易 | 只做纸面交易，不接钱包、不自动下注 |
| 输出 | SQLite 数据、Streamlit 仪表盘、GitHub 可迁移代码 |

成功标准是系统能够持续扫描 NVIDIA 相关盘口，收集消息，生成结构化 AI 信号，记录纸面交易，并为 30 天复盘提供数据基础。
