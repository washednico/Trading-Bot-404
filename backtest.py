from ib_insync import *
from ta.momentum import RSIIndicator
from ta.trend import SMAIndicator
from ta.volatility import BollingerBands
from pyfiglet import Figlet
import datetime
import json

def welcome():
    f = Figlet(font='small')
    print(f.renderText('404 Profit Not Found'))
    print("\n\n\nWelcome to the trading bot, remember to open your IB Gateway before running the bot!")
    input("Press enter to continue...")
    print("\n\n\n")

def print_strings(string):
    print("["+str(datetime.datetime.now())+"]\t"+string)

def boot_IB():
    try:
        print_strings("IB Gateway connecting...")
        ib = IB()
        ib.connect('127.0.0.1', 7497, clientId=1)
        myAccount = ib.accountSummary()
        print_strings("IB Gateway connected")
        return myAccount, ib
    except:
        print_strings("Error connecting to IB Gateway")
        return None, None
    
def get_config():
    print_strings("Loading config file...")
    try:
        with open('config.json') as f:
            config = json.load(f)
        print_strings("Config file loaded")

        if config["Martingale_max"] <= 5:
            return config
        else:
            print_strings("Martingale_max should be less than 5")
    except:
        print_strings("Error loading config file")
        return None
    
def get_contract(config):
    try:
        print_strings("Getting contract for "+config["pair"]+"...")
        contract = Forex(config["pair"])
        print_strings("Contract for "+config["pair"]+" retrived!")
        return contract
    except Exception as e:
        print_strings(f"Error getting contract for {config['pair']}: {str(e)}")
        return None
    
def get_data(config, ib, contract):
    print_strings("Retrieving data from IB for "+config["pair"]+"...")
    try:
        bars = ib.reqHistoricalData(
            contract, endDateTime='20240815-23:59:59', durationStr=config["durationStr"],
            barSizeSetting=config["barSizeSetting"], whatToShow='MIDPOINT', useRTH=0
        )
        myData = util.df(bars)
        if myData.empty:
            raise ValueError("Retrieved data is empty")
        print_strings("Historical data for "+config["pair"]+" downloaded")
    except Exception as e:
        print_strings(f"Error downloading historical data for {config['pair']}: {str(e)}")
        return None

    return myData

def detect_cross(sma_small, sma_big):
    if sma_small.iloc[-1] > sma_big.iloc[-1] and sma_small.iloc[-2] < sma_big.iloc[-2]:
        return -1  # Long
    elif sma_small.iloc[-1] < sma_big.iloc[-1] and sma_small.iloc[-2] > sma_big.iloc[-2]:
        return 1  # Short
    return 0

def detect_RSI(RSI_series, config):
    if RSI_series.iloc[-1] > config["RSI_high"]:
        return 1
    elif RSI_series.iloc[-1] < config["RSI_low"]:
        return -1
    return 0

def detect_bollinger(data, Bollinger_H_series, Bollinger_L_series):
    if data['close'].iloc[-1] > Bollinger_H_series.iloc[-1]:
        return 1
    elif data['close'].iloc[-1] < Bollinger_L_series.iloc[-1]:
        return -1
    return 0

def backtest_strategy(config, historical_data):
    # Initialize variables
    positions = []  
    trades = []
    tp_trades = [] #List take profit orders
    initial_cash = 100000
    cash = initial_cash #TODO: fix it 
    minimum_indicators_to_open = config["minimum_indicators_to_open"]
    open_position = None
    retracements = None
    fill_price = None
    
    def calculate_indicators(current_data):
        """
        Calculate and return the required indicators.
        """

        # Load indicator windows
        sma_small_duration = config["SMA_small_duration"]
        sma_big_duration = config["SMA_big_duration"]
        rsi_duration = config["RSI_duration"]
        bollinger_band_duration = config["bolinger_band_duration"]
        bollinger_band_std_dev = config["bolinger_band_std_dev"]
        try:
            sma_small = SMAIndicator(close=current_data['close'], window=sma_small_duration).sma_indicator()
            sma_big = SMAIndicator(close=current_data['close'], window=sma_big_duration).sma_indicator()
            rsi = RSIIndicator(close=current_data['close'], window=rsi_duration).rsi()
            bollinger = BollingerBands(
                close=current_data['close'],
                window=bollinger_band_duration,
                window_dev=bollinger_band_std_dev
            )
            bollinger_h = bollinger.bollinger_hband()
            bollinger_l = bollinger.bollinger_lband()

            return sma_small, sma_big, rsi, bollinger_h, bollinger_l
        except:
            print_strings("Error in calculating indicators...")
            return None, None, None, None, None
        
    def get_fibonacci_levels(current_data, config, fill_price):
        highest_price = current_data['high'].tail(config["Fibonacci_duration"]).max()
        lowest_price = current_data['low'].tail(config["Fibonacci_duration"]).min()
        
        delta_diff = highest_price - lowest_price
        
        retracements = {
            1: [(fill_price+delta_diff*0.236).round(4),(fill_price-delta_diff*0.236).round(4)],
            2: [(fill_price+delta_diff*0.382).round(4),(fill_price-delta_diff*0.382).round(4)],
            3: [(fill_price+delta_diff*0.5).round(4),(fill_price-delta_diff*0.5).round(4)],
            4: [(fill_price+delta_diff*0.618).round(4),(fill_price-delta_diff*0.618).round(4)],
            5: [(fill_price+delta_diff*0.786).round(4),(fill_price-delta_diff*0.786).round(4)]
        }
        
        print_strings("Fibonacci retracements calculated!")
        
        return retracements

    def execute_trade(order_type, config, price, cash):
        size = config["Initial_size_trade"]
        position_value = size * price
        if order_type == "BUY":
            cash -= position_value
        elif order_type == "SELL":
            cash += position_value
        position = {"type": order_type, "size": size, "price": price, "value": position_value}
        print_strings(f"Executed {order_type} trade at price {price}")
        return cash, position
    
    def tp_order(position, config):
        
        if position["type"] == "BUY": order_type == "SELL"
        else: order_type == "BUY"
        price_limit = round((config["Take_profit"]+1)*(position["price"]),4)
        tp_position = {"type": order_type, "size": position['size'], "price": price_limit, "value": price_limit* position['size']}
        print_strings(f"Placing take profit order. Type: {tp_position['type']}, Value: {tp_position['value']}")
        return tp_position

    def fibonacci_order(position, config, retracements):
        
        fibo_trades = []
        for i in range(1,config["Martingale_max"]+1): 
            if position["type"] == "BUY":
                price_limit = retracements[i][1]
            else: 
                price_limit = retracements[i][0]
            size = round(position['size']*config["Martingale_multiplier"]**i,4)
            fibo_position =  {"type": order_type, "size": size, "price": price_limit, "value": price_limit*position['size']}
            fibo_trades.append(fibo_position)
            print_strings(f"Placing fibonacci order. Type: {fibo_position['type']}, Value: {fibo_position['value']}")

        return fibo_trades
    
    def order_filled(order, current_price):
        if order['type'] == 'BUY' and current_price <= order['price']:
            return True
        elif order['type'] == 'SELL' and current_price >= order['price']:
            return True
        return False

    #TODO: add a filter to start from the biggest btw all the metrics 
    for i in range(config["SMA_big_duration"], len(historical_data)):

        current_data = historical_data.iloc[:i+1] # Extract data up to the current point
        sma_small, sma_big, rsi, bollinger_h, bollinger_l = calculate_indicators(current_data)

        # Detect signal values
        cross_value = detect_cross(sma_small, sma_big)
        rsi_value = detect_RSI(rsi, config)
        bollinger_value = detect_bollinger(current_data, bollinger_h, bollinger_l)

        # Check for trade conditions
        indicators_sum = cross_value + rsi_value + bollinger_value

        if open_position is None:
            if indicators_sum >= minimum_indicators_to_open:
                #Initial Order
                order_type = "BUY" if config["Trending"].lower() == "true" else "SELL"
                cash, open_position = execute_trade(order_type, config, current_data.iloc[-1]['close'], cash)
                trades.append(open_position)

                # Order based on Fibonacci (place a series of limit orders based on the martingale strategy)
                retracements  = get_fibonacci_levels(current_data, config, fill_price=current_data.iloc[-1]['close'])
                fibo_trades = fibonacci_order(position=open_position, config=config, retracements=retracements)

                # Take Profit
                tp_position = tp_order(open_position, config)
                tp_trades.append(tp_position)

            elif indicators_sum <= -minimum_indicators_to_open:
                order_type = "SELL" if config["Trending"].lower() == "true"  else "BUY"
                cash, open_position = execute_trade(order_type, config, current_data.iloc[-1]['close'], cash)
                trades.append(open_position)

                # Order based on Fibonacci (place a series of limit orders based on the martingale strategy)
                retracements  = get_fibonacci_levels(current_data, config, fill_price=current_data.iloc[-1]['close'])
                fibo_trades = fibonacci_order(open_position, config, retracements)

                # Take Profit
                tp_position = tp_order(open_position, config)
                tp_trades.append(tp_position)

        # Check existing orders
        else:
            if fibo_trades:
                for fibo_trade in fibo_trades:
                    if order_filled(fibo_trade,  current_data.iloc[-1]['close']):  # Function to check if order is filled
                        if fibo_trade["type"] == "BUY": 
                            cash -= fibo_trade["value"] 
                        else: 
                            cash += fibo_trade["value"]
                        fibo_trades.remove(fibo_trade)
                        print(f"Fibonacci order filled at {current_data.iloc[-1]['close']} for {fibo_trade['type']}")
                        open_position = None # Close position 

            if tp_trades:
                for tp_trade in tp_trades:
                    if order_filled(tp_trade,  current_data.iloc[-1]['close']):  
                        if tp_trade['type'] == "BUY":
                            cash -= tp_trade["value"] 
                        else: 
                            cash += tp_trade["value"]

                        tp_trades.remove(tp_trade)
                        print(f"Take profit order filled at {current_data.iloc[-1]['close']}")
                        open_position = None  # Close position 


    print(cash)
    #TODO: caluclate backtest overall performances 


# The main script execution
welcome()
myAccount, ib = boot_IB()
#.....

#NOTE: Debugging form
if ib is not None:
    config = get_config()
    if config is not None:
        contract = get_contract(config)
        if contract is not None:
            historical_data = get_data(config, ib, contract)
            print_strings(f"{historical_data}")
            backtest_strategy(config, historical_data)