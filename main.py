from ib_insync import *
import pandas as pd
import json
from copy import deepcopy
from ta.momentum import RSIIndicator
from ta.trend import SMAIndicator

def boot_IB():
    util.startLoop()
    ib = IB()
    ib.connect('127.0.0.1', 7497, clientId=1)
    myAccount = ib.accountSummary()
    return myAccount, ib

def get_config():
    with open('config.json') as f:
        config = json.load(f)
    return config
    
def get_parameters(ib,pair):
    contract = Forex(pair)
    bars = ib.reqHistoricalData(
        contract, endDateTime='', durationStr='150 D',
        barSizeSetting='1 day', whatToShow='MIDPOINT', useRTH=0) # if you want, you can show BID or ASK

    # convert to a pandas dataframe:
    myData = util.df(bars)
    
    SMA5_series = SMAIndicator(close=myData['close'], window=5).sma_indicator()
    SMA25_series = SMAIndicator(close=myData['close'], window=25).sma_indicator()
    RSI_series = RSIIndicator(close=myData['close'], window=14).rsi()

    if SMA5_series.iloc[-1] > SMA25_series.iloc[-1]:
        sma_period = "buy_period"
    else:
        sma_period = "short_period"
    
    if SMA5_series.iloc[-2] > SMA25_series.iloc[-2]:
        previous_sma_period = "buy_period"
    else:
        previous_sma_period = "short_period"

    return SMA5_series, SMA25_series, RSI_series, sma_period, myData, previous_sma_period

def detect_cross_SMA(config,ib):
    while True:
        std_deviation, average_last_5_days, average_last_25_days, sma_period, myData, previous_sma_period = get_parameters(ib, config['pair'])
        if sma_period != previous_sma_period:
            if sma_period == "buy_period":
                open_long()
            else:
                open_short()

def open_long(pair, price, take_profit, stop_loss):
    None

def open_short(pair, price, take_profit, stop_loss):
    None


def plot_indicators(SMA5_series, SMA25_series, RSI_series, myData):
    import matplotlib.pyplot as plt
    # Create the figure and primary axis
    fig, ax1 = plt.subplots(figsize=(12, 8))  # Increasing the figure size
    # Plot RSI on primary y-axis
    ax1.plot(myData.index, RSI_series, color='blue', label='RSI')
    ax1.set_ylabel('RSI', color='blue')
    ax1.tick_params(axis='y', labelcolor='blue')
    # Create a secondary y-axis for the SMA and price data
    ax2 = ax1.twinx()
    # Plot SMA5, SMA25, and close prices
    ax2.plot(myData.index, SMA5_series, color='red', label='SMA5')
    ax2.plot(myData.index, SMA25_series, color='green', label='SMA25')
    ax2.plot(myData.index, myData['close'], color='black', label='Close')
    ax2.set_ylabel('Price Indicators', color='black')
    ax2.tick_params(axis='y', labelcolor='black')
    # Combine legends from both axes
    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax2.legend(lines + lines2, labels + labels2, loc='upper left')
    # Improve layout to make room for rotated x-axis labels
    plt.tight_layout()  # This might help to avoid clipping of labels
    plt.show()

        


myAccount, ib = boot_IB()

config = get_config()

SMA5_series, SMA25_series, RSI_series, sma_period, myData = get_parameters(ib,config['pair'])

plot_indicators(SMA5_series, SMA25_series, RSI_series, myData)

detect_cross_SMA(config,ib)





    