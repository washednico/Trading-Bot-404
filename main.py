import time
import datetime
from ib_insync import *
import pandas as pd
import json
from copy import deepcopy

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
    last_5_days_close = myData['close'].tail(5)
    last_25_days_close = myData['close'].tail(25)

    if average_last_5_days > average_last_25_days:
        sma_period = "buy_period"
    else:
        sma_period = "short_period"

    return last_5_days_close.std(), last_5_days_close.mean(), last_25_days_close.mean(), sma_period

def trigger_start(config,ib):
    start = True
    while True:
        std_deviation, average_last_5_days, average_last_25_days, sma_period = get_parameters(ib, config['pair'])
        if start:
            old_sma_period = deepcopy(sma_period)
            start = False
        else:
            if old_sma_period != sma_period:
                print(f"Detected a cross between the SMA periods")
        


    


myAccount, ib = boot_IB()
config = get_config()
std_deviation, average_last_5_days, average_last_25_days = get_parameters(ib,config['pair'])
trigger_start(config,ib)





    