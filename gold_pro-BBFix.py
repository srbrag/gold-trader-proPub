import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- APP CONFIG ---
st.set_page_config(page_title="Gold Sentinel Pro", layout="wide")

def get_full_analysis():
    # 1. Fetch High-Res Data
    gold = yf.Ticker("GC=F")
    df = gold.history(period="60d", interval="1h")
    
    # 2. Add ALL Requested Indicators
    df.ta.rsi(length=14, append=True)           # RSI
    df.ta.stoch(append=True)                    # STOCH (%K, %D)
    df.ta.stochrsi(append=True)                 # STOCK RSI
    df.ta.bbands(length=20, std=2, append=True) # BB
    df.ta.cci(length=20, append=True)           # CCI
    df.ta.mfi(length=14, append=True)           # MFI
    df.ta.adx(append=True)                      # DMI (ADX, DMP, DMN)
    
    # Custom CRSI (Connors RSI) Implementation
    def calc_crsi(close, rsi_len=3, streak_len=2, rank_len=100):
        rsi = ta.rsi(close, length=rsi_len)
        diff = close.diff()
        streak = diff.apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0)).rolling(streak_len).sum()
        streak_rsi = ta.rsi(streak, length=rsi_len)
        rank = close.rolling(rank_len).apply(lambda x: (x < x[-1]).sum() / rank_len * 100)
        return (rsi + streak_rsi + rank) / 3

    df['CRSI'] = calc_crsi(df['Close'])
    return df

st.title("🏆 Gold Sentinel: Zero-Lag Decision Engine")
st.sidebar.header("Trading Parameters")
risk_reward = st.sidebar.slider("Risk/Reward Ratio", 1.5, 5.0, 2.5)

if st.button('🎯 ANALYZE & GENERATE TRADE ORDER'):
    df = get_full_analysis()
    last = df.iloc[-1]
    
    # --- CONFLUENCE LOGIC ---
    # BUY signal if RSI < 35, MFI < 30, and Price near Lower BB
    is_oversold = (last['RSI_14'] < 40) and (last['MFI_14'] < 30) and (last['STOCHk_14_3_3'] < 20)
    is_trend_up = (last['DMP_14'] > last['DMN_14']) and (last['ADX_14'] > 25)
    
    action = "WAIT"
    if is_oversold and is_trend_up: action = "STRONG BUY"
    elif not is_oversold and not is_trend_up: action = "STRONG SELL"

    # --- DISPLAY RESULTS ---
    st.subheader(f"Strategy Recommendation: {action}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Current Price", f"${last['Close']:.2f}")
    c2.metric("Take Profit", f"${last['Close'] + 45:.2f}")
    c3.metric("Stop Loss", f"${last['Close'] - 18:.2f}")

    # --- ADVANCED CHARTING ---
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.05,
                        subplot_titles=('Price & BB', 'RSI & MFI', 'ADX (Trend Strength)'))
    
    # Price + BB
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='XAU/USD'), row=1, col=1)
     # Find the correct Bollinger Band column names (handle different pandas_ta versions)
    bb_cols = [col for col in df.columns if 'BB' in col]
    bb_upper = [col for col in bb_cols if 'U' in col][0] if any('U' in col for col in bb_cols) else None
    bb_lower = [col for col in bb_cols if 'L' in col][0] if any('L' in col for col in bb_cols) else None
    
    if bb_upper and bb_lower:
        fig.add_trace(go.Scatter(x=df.index, y=df[bb_upper], line=dict(color='gray', dash='dash'), name='Upper BB'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df[bb_lower], line=dict(color='gray', dash='dash'), name='Lower BB'), row=1, col=1)
    
    
    # Indicators
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI_14'], name='RSI'), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MFI_14'], name='MFI', line=dict(color='green')), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['ADX_14'], name='ADX', line=dict(color='orange', width=3)), row=3, col=1)
    
    fig.update_layout(height=800, template="plotly_dark", showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
