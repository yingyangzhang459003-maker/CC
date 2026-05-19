from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config_loader import load_config
from src.database import init_db

st.set_page_config(page_title="Polymarket NVIDIA Event Radar", layout="wide")
st.title("Polymarket NVIDIA Event Radar")
st.caption("第一阶段仅做公开信息监控与纸面交易，不接钱包、不保存私钥、不自动下注。")

config_path = st.sidebar.text_input("配置文件", "config/config.example.yaml")
config = load_config(config_path)
init_db(config.database_url)
engine = create_engine(config.database_url, future=True)


def table_df(name: str) -> pd.DataFrame:
    try:
        return pd.read_sql(f"SELECT * FROM {name}", engine)
    except Exception:
        return pd.DataFrame()

markets = table_df("markets")
scores = table_df("market_scores")
messages = table_df("messages")
signals = table_df("ai_signals")
trades = table_df("paper_trades")
snapshots = table_df("price_snapshots")
logs = table_df("system_logs")

col1, col2, col3, col4 = st.columns(4)
col1.metric("NVIDIA 活跃盘口", len(markets))
col2.metric("消息记录", len(messages))
col3.metric("AI 信号", len(signals))
col4.metric("纸面交易", len(trades))

if not trades.empty and "pnl" in trades.columns:
    closed = trades.dropna(subset=["pnl"])
    if not closed.empty:
        win_rate = (closed["pnl"] > 0).mean() * 100
        avg_pnl = closed["pnl"].mean()
        st.metric("纸面交易胜率", f"{win_rate:.1f}%")
        st.metric("平均 PnL", f"{avg_pnl:.2f} USDC")

st.header("当前 Polymarket NVIDIA 活跃盘口")
st.dataframe(markets.sort_values("updated_at", ascending=False) if not markets.empty else markets, use_container_width=True)

st.header("NVIDIA 盘口评分")
st.dataframe(scores.sort_values("created_at", ascending=False) if not scores.empty else scores, use_container_width=True)

st.header("最新 NVIDIA 消息流")
st.dataframe(messages.sort_values("captured_at", ascending=False) if not messages.empty else messages, use_container_width=True)

st.header("最新 AI 判断结果")
st.dataframe(signals.sort_values("created_at", ascending=False) if not signals.empty else signals, use_container_width=True)

st.header("纸面交易记录")
st.dataframe(trades.sort_values("created_at", ascending=False) if not trades.empty else trades, use_container_width=True)

st.header("价格快照")
st.dataframe(snapshots.sort_values("captured_at", ascending=False) if not snapshots.empty else snapshots, use_container_width=True)

st.header("GitHub 同步状态")
if (PROJECT_ROOT / ".git").exists():
    st.success("本地 Git 仓库已初始化。请在终端配置远程仓库后执行 git push。")
else:
    st.warning("尚未初始化 Git 仓库。")
