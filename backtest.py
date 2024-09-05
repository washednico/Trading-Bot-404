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

def print_index(index, string):
    print(f"[ {index}]\t"+string)

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
    
def get_data(config, ib, contract, endTimeBacktest):
    print_strings("Retrieving data from IB for "+config["pair"]+"...")
    try:
        bars = ib.reqHistoricalData(
            contract, endDateTime= endTimeBacktest, durationStr=config["durationStr"],
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

    # Define orders dictionaries 
    filled_orders = {
                    
                }
    limit_orders = {

                }
    
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

    def execute_trade(order_type, config, price):

        #Execute trade
        size = config["Initial_size_trade"]
        position_value = size * price
        position = {"type": order_type, "size": size, "price": price, "value": position_value, "order_type":"market"}
        print_strings(f"Executed {order_type} trade at price {price}")

        return position
    
    def tp_order(position, config):
        
        if position["type"] == "BUY": 
            type_order = "SELL"
        else:
            type_order = "BUY"
        price_limit = round((config["Take_profit"]+1)*(position["price"]),4)
        tp_position = {"type": type_order, "size": position['size'], "price": price_limit, "value": price_limit* position['size'],  "order_type":"tp_order"}
        print_strings(f"Placing take profit order. Type: {tp_position['type']}, Value: {tp_position['value']}")
        return tp_position

    def fibonacci_order(position, config, retracements):
        
        sizes_tp = {} # Dictionary to store cumulative trade sizes and their corresponding take-profit prices
        cumulative_size = config["Initial_size_trade"]
        total_value = config["Initial_size_trade"] * position["price"]

        fibo_trades = []
        for i in range(1,config["Martingale_max"]+1): 
            if position["type"] == "BUY":
                price_limit = retracements[i][1]
            if position["type"] == "SELL": 
                price_limit = retracements[i][0]
            size = round(position['size']*config["Martingale_multiplier"]**i,4)
            fibo_position =  {"type": position["type"], "size": size, "price": price_limit, "value": price_limit*size,  "order_type":"fibo_order"}
            fibo_trades.append(fibo_position)
            print_strings(f"Placing fibonacci order. Type: {fibo_position['type']}, Price: {price_limit}")

            # Update cumulative size and total value after placing the new limit order
            cumulative_size += size
            total_value += size * price_limit
            # Calculate the new average price after placing the limit order
            average_price = total_value / cumulative_size


            # Store the cumulative size and corresponding take-profit price in sizes_tp
            # Determine the take-profit price based on the average price and the order type
            if position["type"] == "BUY":
                tp_price = average_price * (1 + config["Take_profit"])
                tp_type = "SELL"
                sizes_tp[i] = {'size': round(cumulative_size,4), 'price': round(tp_price,4), 'type': tp_type}
            else:  
                tp_price = average_price * (1 - config["Take_profit"])
                tp_type = "BUY"
                sizes_tp[i] = {'size': round(cumulative_size,4), 'price': round(tp_price,4), 'type': tp_type}
        
        # Return the dictionary of sizes and take-profit prices, and the list of limit trades
        return sizes_tp, fibo_trades

    def order_filled(order, current_price):
        if order['type'] == 'BUY' and current_price <= order['price']:
            return True
        elif order['type'] == 'SELL' and current_price >= order['price']:
            return True
        return False

    def cash_calculator(order, cash):
        if order["type"] == "BUY": 
            cash -= order["value"] 
        else: 
            cash += order["value"]

        return cash
        

    # Initialize variables
    trades = []
    tp_trades = [] #List take profit orders
    cash = 100000
    minimum_indicators_to_open = config["minimum_indicators_to_open"]
    open_position = False
    retracements = None
    
    filter = max(config["SMA_big_duration"], 
                 config["RSI_duration"], 
                 config["bolinger_band_duration"], 
                 config["bolinger_band_std_dev"],
                 config["RSI_high"],
                 config["RSI_low"]
                 )

    for i in range(filter, len(historical_data)):
        
        # Extract data up to the current point and calculate indicators
        current_data = historical_data.iloc[:i+1]

        if len(limit_orders) == 0:
            sma_small, sma_big, rsi, bollinger_h, bollinger_l = calculate_indicators(current_data)

            # Detect signal values
            cross_value = detect_cross(sma_small, sma_big)
            rsi_value = detect_RSI(rsi, config)
            bollinger_value = detect_bollinger(current_data, bollinger_h, bollinger_l)

            # Check for trade conditions
            indicators_sum = cross_value + rsi_value + bollinger_value


            if indicators_sum >= minimum_indicators_to_open:
                #Initial Order
                order_type = "BUY" if config["Trending"].lower() == "true" else "SELL"
                position = execute_trade(order_type, config, current_data.iloc[-1]['close'])
                #cash = cash_calculator(position, cash)
                key = len(filled_orders)
                filled_orders[key] = position

                # Order based on Fibonacci (place a series of limit orders based on the martingale strategy)
                retracements  = get_fibonacci_levels(current_data, config, fill_price=current_data.iloc[-1]['close'])
                sizes_tp, fibo_trades = fibonacci_order(position, config, retracements)

                # Take Profit
                tp_position = tp_order(position, config)

                limit_orders["fibo_orders"] = fibo_trades
                limit_orders["tp_orders"] = tp_position

            elif indicators_sum <= -minimum_indicators_to_open:

                order_type = "SELL" if config["Trending"].lower() == "true"  else "BUY"
                position = execute_trade(order_type, config, current_data.iloc[-1]['close'])
                cash = cash_calculator(position, cash)
                trades.append(position)

                # Order based on Fibonacci (place a series of limit orders based on the martingale strategy)
                retracements  = get_fibonacci_levels(current_data, config, fill_price=current_data.iloc[-1]['close'])
                sizes_tp, fibo_trades = fibonacci_order(position, config, retracements)

                # Take Profit
                tp_position = tp_order(position, config)


                limit_orders["fibo_orders"] = fibo_trades
                limit_orders["tp_orders"] = tp_position


        else: 
        #Start check if condition is met
            for fibo_trades in limit_orders["fibo_orders"]:   
                #filled condition fibo
                if fibo_trades["type"] == "BUY":
                    if fibo_trades["price"] >= current_data.iloc[i]["close"]: 
                        print_strings(f"Fibo orders filled")
                        print_index(i, "FIBO ORDER FILLED")

                        limit_orders["tp_orders"] = 0 
                        limit_orders["tp_orders"] = list(sizes_tp.items())[0][1]
                        print_strings(f"Take profit the following fibo order is executed ")
                        

                if fibo_trades["type"] == "SELL":
                    if fibo_trades["price"] <= current_data.iloc[i]["close"]: 
                        print_strings(f"Fibo orders filled")
                        print_index(i, "FIBO ORDER FILLED")
                        
                        limit_orders["tp_orders"] = 0 
                        limit_orders["tp_orders"] = list(sizes_tp.items())[0][1]
                        print_strings(f"Take profit the following fibo order is executed ")
                        

            #filled condition 
            if limit_orders["tp_orders"]["type"] == "BUY":
                if limit_orders["tp_orders"]["price"] >= current_data.iloc[i]["close"]:
                    print_strings(f"TP orders filled")
                    print_index(i, "TP ORDER FILLED")
            
                    #Reset the dict 
                    limit_orders = {}
            
            else: 
                if limit_orders["tp_orders"]["price"] <= current_data.iloc[i]["close"]: 
                    print_strings(f"TP orders filled")
                    print_index(i, "TP ORDER FILLED")

                    #Reset the dict 
                    limit_orders = {}


            


        # # Check existing orders
        # if open_position:
        #     if fibo_trades:
        #         for fibo_trade in fibo_trades[:]:
        #             if order_filled(fibo_trade,  current_data.iloc[-1]['close']):  # Function to check if order is filled
        #                 cash = cash_calculator(fibo_trade, cash)
        #                 fibo_trades.remove(fibo_trade)
        #                 print_strings(f"Fibonacci order filled at {current_data.iloc[-1]['close']} for {fibo_trade['type']}")
        #                 open_position = False # Close position 

        #     if tp_trades:
        #         for tp_trade in tp_trades[:]:
        #             if order_filled(tp_trade,  current_data.iloc[-1]['close']):  
        #                 cash = cash_calculator(tp_trade, cash)
        #                 tp_trades.remove(tp_trade)
        #                 print_strings(f"Take profit order filled at {current_data.iloc[-1]['close']}")
        #                 open_position = False  # Close position 


    #TODO: caluclate backtest overall performances 
    # print(cash)




# The main script execution
welcome()
myAccount, ib = boot_IB()


if ib is not None:
    config = get_config()
    if config is not None:
        contract = get_contract(config)
        if contract is not None:

            endTimeBacktest = "20240831-23:59:59" #NOTE: endDateTime format must be "YYYYMMDD-HH:MM:SS"
            historical_data = get_data(config, ib, contract, endTimeBacktest)
            # print_strings(f"{historical_data}")
            backtest_strategy(config, historical_data)