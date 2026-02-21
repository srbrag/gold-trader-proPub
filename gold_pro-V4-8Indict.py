import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CONFIG ---
st.set_page_config(page_title="Gold Sentinel v3", layout="wide")

def get_gold_signals():
    gold = yf.Ticker("GC=F")
    df = gold.history(period="60d", interval="1h")
    
    # 1. CORE TREND & VOLATILITY
    df.ta.bbands(length=20, std=2, append=True)         # BB
    df.ta.adx(length=14, append=True)                  # DMI / ADX
    
    # 2. MOMENTUM & OSCILLATORS
    df.ta.rsi(length=14, append=True)                  # RSI
    df.ta.stoch(length=14, append=True)                # STOCH
    df.ta.stochrsi(length=14, append=True)             # STOCK RSI
    df.ta.cci(length=20, append=True)                  # CCI
    
    # 3. VOLUME & FLOW
    df.ta.mfi(length=14, append=True)                  # MFI
    
    # 4. SPECIALIZED (CRSI - Connors RSI)
    # CRSI = (RSI(3) + RSI(Streak, 2) + PercentRank(100)) / 3
    df['CRSI'] = (ta.rsi(df['Close'], length=3) + 
                  ta.rsi(df['Close'].diff().apply(lambda x: 1 if x > 0 else -1), length=2) + 
                  df['Close'].pct_change().rolling(100).rank(pct=True)*100) / 3
    
    return df

st.title("🏆 Gold Sentinel v3: Full Confluence Engine")

if st.button('🎯 GENERATE ALPHA TRADE ORDER'):
    df = get_gold_signals()
    
    # --- DYNAMIC KEY DETECTION (Prevents KeyError) ---
    def get_col(df, keyword): return [c for c in df.columns if keyword in c][0]
    
    last = df.iloc[-1]
    price = last['Close']
    
    # Mapping Indicators for Analysis
    indicators = {
        "RSI": last['RSI_14'],
        "MFI": last['MFI_14'],
        "CCI": last['CCI_20_0.015'],
        "ADX": last[get_col(df, 'ADX')],
	"DMP": last[get_col(df, 'DMP')], #SRB ADDED THIS
	"DMN": last[get_col(df, 'DMN')], #SRB ADDED THIS
        "STOCH_K": last[get_col(df, 'STOCHk')],
        "STOCK_RSI_K": last[get_col(df, 'STOCHRSIk')],
        "CRSI": last['CRSI']
    }

    # --- ZERO-LOSS CONFLUENCE LOGIC ---
    buy_score = 0
    if indicators["RSI"] <= 30: buy_score += 1 #SRB OR <30 >70
    if indicators["MFI"] <= 20: buy_score += 1 #SRB OR <20 >80
    if indicators["STOCH_K"] <= 20: buy_score += 1 #SRB OR <20 >80
    if indicators["STOCK_RSI_K"] <= 20: buy_score += 1 #SRB OR <20 >80
    if indicators["CRSI"] <= 30: buy_score += 1 #SRB OR <20 >80
    if price <= last[get_col(df, 'BBL')]: buy_score += 1
    if indicators["CCI"] <= -100: buy_score += 1 #SRB ADDED THIS
 	
    if indicators["ADX"] >= 25: #SRB ADDED THIS: if indicators["ADX"] >= 25: buy_score += 1 # Confirming Trend Strength
        if indicators["DMP"] > indicators["DMN"]: buy_score += 1 # DI+ > DI-


    sell_score = 0 #SRB ADDED THIS entire sell block
    if indicators["RSI"] >= 70: sell_score += 1 #SRB OR <30 >70
    if indicators["MFI"] >= 80: sell_score += 1 #SRB OR <20 >80
    if indicators["STOCH_K"] >= 80: sell_score += 1 #SRB OR <20 >80
    if indicators["STOCK_RSI_K"] >= 80: sell_score += 1 #SRB OR <20 >80
    if indicators["CRSI"] >= 70: sell_score += 1 #SRB OR <20 >80
    if price >= last[get_col(df, 'BBU')]: sell_score += 1
    if indicators["CCI"] >= 100: sell_score += 1 #SRB ADDED THIS

    if indicators["ADX"] >= 25: #SRB ADDED THIS: if indicators["ADX"] >= 25: buy_score += 1 # Confirming Trend Strength
        if indicators["DMN"] > indicators["DMP"]: sell_score += 1 # DI- > DI+


    action = "WAIT / NEUTRAL"
    if buy_score >= 5: action = "PROBABLE BUY"
    if buy_score >= 7: action = "ULTRA HIGH PROBABILITY BUY"

    # --- UI DISPLAY ---
    st.header(f"System Verdict: {action}")
    st.info(f"BUY Confluence Score: {buy_score}/8 Indicators Aligning")
    st.info(f"SELL Confluence Score: {sell_score}/8 Indicators Aligning") #SRB ADDED THIS
    
    st.info(f"PRICE Score: {price}")
    st.info(f"STOCK_RSI_K Score(20/80): {indicators["STOCK_RSI_K"]}")
    st.info(f"CCI Score(100/-100): {indicators["CCI"]}")
    st.info(f"CRSI Score(30/70): {indicators["CRSI"]}")
    st.info(f"MFI Score(20/80): {indicators["MFI"]}")
    st.info(f"STOCH_K Score(20/80): {indicators["STOCH_K"]}")
    st.info(f"RSI Score(30/70): {indicators["RSI"]}")
    st.info(f"ADX Score(25): {indicators["ADX"]}")
    st.info(f"DMP Score(): {indicators["DMP"]}")
    st.info(f"DMN Score(): {indicators["DMN"]}")

    st.info(f"PRICE<=BBL? Score: {price } , {last[get_col(df, 'BBL')]}")
    st.info(f"PRICE>=BBU? Score: {price } , {last[get_col(df, 'BBU')]}")




    c1, c2, c3 = st.columns(3)
    c1.metric("ENTRY", f"${price:.2f}")
    c2.metric("TP (Take Profit)", f"${price + 45:.2f}")
    c3.metric("SL (Stop Loss)", f"${price - 22:.2f}")

    # --- FULL INDICATOR CHART ---
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.02,
                        subplot_titles=('Price & BB', 'RSI/MFI/CRSI', 'STOCH/STOCK-RSI', 'DMI/ADX'))
    
    # Subplot 1: Price
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Gold'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df[get_col(df, 'BBU')], line=dict(color='gray'), name='Upper BB'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df[get_col(df, 'BBL')], line=dict(color='gray'), name='Lower BB'), row=1, col=1)
    
    # Subplot 2: Momentum
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI_14'], name='RSI'), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MFI_14'], name='MFI'), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['CRSI'], name='CRSI'), row=2, col=1)
    
    # Subplot 3: Stochastics
    fig.add_trace(go.Scatter(x=df.index, y=df[get_col(df, 'STOCHk')], name='STOCH K'), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df[get_col(df, 'STOCHRSIk')], name='STOCK RSI K'), row=3, col=1)
    
    # Subplot 4: Trend
    fig.add_trace(go.Scatter(x=df.index, y=df[get_col(df, 'ADX')], name='ADX Strength'), row=4, col=1)

    fig.update_layout(height=1000, template="plotly_dark", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)
