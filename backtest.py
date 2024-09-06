from ib_insync import *
from ta.momentum import RSIIndicator
from ta.trend import SMAIndicator
from ta.volatility import BollingerBands
from pyfiglet import Figlet
import matplotlib.pyplot as plt
import datetime
import json

def welcome():
    # Initial logging.
    f = Figlet(font='small')
    print(f.renderText('404 Profit Not Found'))
    print("\n\n\nWelcome to the trading bot, remember to open your IB Gateway before running the bot!")
    input("Press enter to continue...")
    print("\n\n\n")

def print_strings(string):
    # Fuction for logging management. 
    print("["+str(datetime.datetime.now())+"]\t"+string)

def print_index(index, string):
    print(f"[ {index}]\t"+string)

def boot_IB():
    #Function for trying to establish connection with IB Gateway. 
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
    # Load configuration settings from config.json.
    print_strings("Loading config file...")
    try:
        with open('config.json') as f:
            config = json.load(f)
        print_strings("Config file loaded")

        # Check if Martingale_Max is less or equal than a constant (5).
        if config["Martingale_max"] <= 5:
            return config
        else:
            print_strings("Martingale_max should be less than 5")
    except:
        print_strings("Error loading config file")
        return None
    
def get_contract(config):
    # Get contract of a specifc pair defined in config.json.
    try:
        print_strings("Getting contract for "+config["pair"]+"...")
        contract = Forex(config["pair"])
        print_strings("Contract for "+config["pair"]+" retrived!")
        return contract
    except Exception as e:
        print_strings(f"Error getting contract for {config['pair']}: {str(e)}")
        return None
    
def get_data(config, ib, contract):
    # Requesting historical bar data from IB. 
    # Documentation can be found here: https://interactivebrokers.github.io/tws-api/historical_bars.html
    print_strings("Retrieving data from IB for "+config["pair"]+"...")
    try:
        bars = ib.reqHistoricalData(
            contract, endDateTime= '', durationStr=config["durationStr"],
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
    # Detect MA indicator based on config.json parameters. 
    if sma_small.iloc[-1] > sma_big.iloc[-1] and sma_small.iloc[-2] < sma_big.iloc[-2]:
        return -1  
    elif sma_small.iloc[-1] < sma_big.iloc[-1] and sma_small.iloc[-2] > sma_big.iloc[-2]:
        return 1 
    return 0

def detect_RSI(RSI_series, config):
    # Detect RSI indicator based on config.json parameters.
    if RSI_series.iloc[-1] > config["RSI_high"]:
        return 1 
    elif RSI_series.iloc[-1] < config["RSI_low"]:
        return -1
    return 0

def detect_bollinger(data, Bollinger_H_series, Bollinger_L_series):
    # Detect Bollinger indicator based on config.json parameters. 
    if data['close'].iloc[-1] > Bollinger_H_series.iloc[-1]:
        return 1
    elif data['close'].iloc[-1] < Bollinger_L_series.iloc[-1]:
        return -1
    return 0

def backtest_strategy(config, historical_data):
    
    def calculate_indicators(current_data):
        # Load indicator parameters from config.json.
        sma_small_duration = config["SMA_small_duration"]
        sma_big_duration = config["SMA_big_duration"]
        rsi_duration = config["RSI_duration"]
        bollinger_band_duration = config["bolinger_band_duration"]
        bollinger_band_std_dev = config["bolinger_band_std_dev"]

        # Calculate indicators with ta library.
        # Documentation can be found here: https://technical-analysis-library-in-python.readthedocs.io/en/latest/
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
        # Calculate fibonacci retracements based on market order price and duration defined in config.json.
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
        # Simulate execution of market order and return order's info with position(dict).
        size = config["Initial_size_trade"]
        position_value = size * price
        position = {"type": order_type, "size": size, "price": price, "value": position_value, "order_type":"market"}
        print_strings(f"Executed {order_type} trade at price {price}")
        return position
    
    def tp_order(position, config):
        # Function for define a take profit order and return order's info with tp_postion(dict).
        # The type of order is opposite to the market order one's. 
        if position["type"] == "BUY": 
            type_order = "SELL"
        else:
            type_order = "BUY"
        
        # Calculate the take profit order's price based on the defined percentage in config.json.
        if type_order == "BUY":
            price_limit = round((1-config["Take_profit"])*position["price"],4)
        else:
            price_limit = round((config["Take_profit"]+1)*position["price"],4)

        tp_position = {"type": type_order, "size": position['size'], "price": price_limit, "value": price_limit* position['size'],  "order_type":"tp_order"}
        print_strings(f"Placing take profit order. Type: {tp_position['type']}, Size: {tp_position['size']}")
        return tp_position

    def fibonacci_order(position, config, retracements):
        # Function for define fibonacci orders and their respective take profit orders.
        # Return the dictionary of sizes and take-profit prices, and the list of limit trades

        sizes_tp = {} # Dictionary to store cumulative trade sizes and their corresponding take-profit prices.
        cumulative_size = config["Initial_size_trade"] 
        total_value = config["Initial_size_trade"] * position["price"]

        fibo_trades = []
        # Start loop based on the given Martingale_max in config.json.
        for i in range(1,config["Martingale_max"]+1): 
            if position["type"] == "BUY":
                price_limit = retracements[i][1]
            if position["type"] == "SELL": 
                price_limit = retracements[i][0]
            size = round(position['size']*config["Martingale_multiplier"]**i,4)
            fibo_position =  {"type": position["type"], "size": size, "price": price_limit, "value": price_limit*size,  "order_type":"fibo_order"}
            fibo_trades.append(fibo_position)
            print_strings(f"Placing fibonacci order. Type: {fibo_position['type']}, Price: {price_limit}")

            # Update cumulative size and total value after placing the new limit order.
            cumulative_size += size
            total_value += size * price_limit
            # Calculate the new average price after placing the limit order.
            average_price = total_value / cumulative_size


            # Store the cumulative size and corresponding take-profit price in sizes_tp.
            # Determine the take-profit price based on the average price and the order type.
            if position["type"] == "BUY":
                tp_price = average_price * (1 + config["Take_profit"])
                tp_type = "SELL"
                sizes_tp[i] = {'size': round(cumulative_size,4), 'price': round(tp_price,4), 'type': tp_type}
            else:  
                tp_price = average_price * (1 - config["Take_profit"])
                tp_type = "BUY"
                sizes_tp[i] = {'size': round(cumulative_size,4), 'price': round(tp_price,4), 'type': tp_type}
        
        return sizes_tp, fibo_trades


    # Define initial variables.
    filled_orders = {} # Contains all filled orders (market, fibonacci, take profit).
    limit_orders = {} # Contains existing limit orders (fibonacci, take profit).
    trade_history = [] # Contains time series for plotting purposes. 
    cash = 100000 # Initial cash. 
    minimum_indicators_to_open = config["minimum_indicators_to_open"] # The minimum indicators that should be met in order to open a position.
    
    # Filter to ensure the loop starts only after the longest required time duration 
    # from the indicator settings has been reached. The loop will only begin once 
    # the maximum duration (across SMA, RSI, and Bollinger Bands) is satisfied, 
    # ensuring all indicators have enough data to generate valid signals.
    filter = max(config["SMA_big_duration"],  config["RSI_duration"], config["bolinger_band_duration"], config["bolinger_band_std_dev"], config["RSI_high"], config["RSI_low"]) 
    
    # Starts iteration over each row of historical data. 
    for i in range(filter, len(historical_data)):
        # Extract data up to the current point and calculate indicators
        current_data = historical_data.iloc[:i+1]
       
        # Continue with market order execution only if no limit orders exist. 
        if len(limit_orders) == 0:

            # Calculate indicators.
            sma_small, sma_big, rsi, bollinger_h, bollinger_l = calculate_indicators(current_data)

            # Detect signal values.
            cross_value = detect_cross(sma_small, sma_big)
            rsi_value = detect_RSI(rsi, config)
            bollinger_value = detect_bollinger(current_data, bollinger_h, bollinger_l)

            # Check if trade conditions are met.
            indicators_sum = cross_value + rsi_value + bollinger_value

            if indicators_sum >= minimum_indicators_to_open:
                # Execute markert order.
                order_type = "BUY" if config["Trending"].lower() == "true" else "SELL" # Define the type of order based on Trending variable in config.json.
                position = execute_trade(order_type, config, current_data.iloc[-1]['close'])

                # Append to trade_history(list) for plotting purposes. 
                trade_history.append({"position": f"MKT_{order_type}", "type": "BUY", "price": current_data.iloc[-1]['close'], "step": i})

                # Dict management. 
                key = len(filled_orders) # Use actual length of the dict as key.
                filled_orders[key] = position # Add the new position.

                # Order based on Fibonacci (place a series of limit orders based on the martingale strategy).
                retracements  = get_fibonacci_levels(current_data, config, fill_price=current_data.iloc[-1]['close'])
                sizes_tp, fibo_trades = fibonacci_order(position, config, retracements)

                # Take Profit. 
                tp_position = tp_order(position, config)

                # Update respective dictionary with the new limit orders. 
                limit_orders["fibo_orders"] = fibo_trades
                limit_orders["tp_orders"] = tp_position
        
            # The process is specular from the previous one. 
            elif indicators_sum <= -minimum_indicators_to_open:
                # Execute markert order.
                order_type = "SELL" if config["Trending"].lower() == "true"  else "BUY"
                position = execute_trade(order_type, config, current_data.iloc[-1]['close'])
                
                # Dict management. 
                key = len(filled_orders)
                filled_orders[key] = position

                # Append to trade_history(list) for plotting purposes. 
                trade_history.append({"position": f"MKT_{order_type}", "type": "BUY", "price": current_data.iloc[-1]['close'], "step": i})

                # Order based on Fibonacci (place a series of limit orders based on the martingale strategy).
                retracements  = get_fibonacci_levels(current_data, config, fill_price=current_data.iloc[-1]['close'])
                sizes_tp, fibo_trades = fibonacci_order(position, config, retracements)

                # Take Profit.
                tp_position = tp_order(position, config)

                # Update respective dictionary with the new limit orders. 
                limit_orders["fibo_orders"] = fibo_trades
                limit_orders["tp_orders"] = tp_position


        # Check if limit ordes stored in their respective dictionaries are filled
        # For backtest purpose we assume a limit order is filled once the correct price is reached. 
        else: 

            # Iterate over fibonacci orders dict.
            for fibo_trades in limit_orders["fibo_orders"]:   
                
                # Check if a BUY order is filled.
                if fibo_trades["type"] == "BUY":
                    if fibo_trades["price"] >= current_data.iloc[i]["close"]: 
                        # Remove the order from the dict once is filled.
                        limit_orders["fibo_orders"].remove(fibo_trades) 
                        print_strings(f"Fibo orders filled")

                        # print(current_data.iloc[-1]['close'])
                        # print(fibo_trades["price"])
                        # print_index(i, "FIBO ORDER FILLED")

                        # Reset tp_orders and add the new take profit based on the fibonacci one. 
                        limit_orders["tp_orders"] = 0  
                        limit_orders["tp_orders"] = list(sizes_tp.items())[0][1]
                        # print(limit_orders["tp_orders"])

                        # Modify the take profit (of fibo orders) dict adequately. 
                        first_key = next(iter(sizes_tp))
                        sizes_tp.pop(first_key)
                        print_strings(f"Take profit of the following fibo order is executed")

                        # Append to trade_history(list) for plotting purposes. 
                        trade_history.append({"position": "FIBO_BUY", "type": "BUY", "price": current_data.iloc[-1]['close'], "step": i})
                        
                # Check if a SELL order is filled (specular from the previous one)
                if fibo_trades["type"] == "SELL":
                    if fibo_trades["price"] <= current_data.iloc[i]["close"]: 
                        # Remove the order from the dict once is filled.
                        limit_orders["fibo_orders"].remove(fibo_trades)
                        print_strings(f"Fibo orders filled")

                        # print_index(i, "FIBO ORDER FILLED")
                        # print(current_data.iloc[-1]['close'])
                        # print(fibo_trades["price"])

                        # Reset tp_orders and add the new take profit based on the fibonacci one. 
                        limit_orders["tp_orders"] = 0 
                        limit_orders["tp_orders"] = list(sizes_tp.items())[0][1]
                        # print(limit_orders["tp_orders"])

                        # Modify the take profit (of fibo orders) dict adequately. 
                        first_key = next(iter(sizes_tp))
                        sizes_tp.pop(first_key)
                        print_strings(f"Take profit the following fibo order is executed ")

                        # Append to trade_history(list) for plotting purposes. 
                        trade_history.append({"position": "FIBO_SELL", "type": "SELL", "price": current_data.iloc[-1]['close'], "step": i})
                        

            # Check if BUY tp_orders are filled. 
            if limit_orders["tp_orders"]["type"] == "BUY":
                if limit_orders["tp_orders"]["price"] >= current_data.iloc[i]["close"]:
                    print_strings(f"TP orders filled {str(limit_orders['tp_orders']['price'])}")
                    # print_index(i, "TP ORDER FILLED")
                    # print(current_data.iloc[-1]['close'])
                    # print(limit_orders["tp_orders"]["price"])

                    # Append to trade_history(list) for plotting purposes. 
                    trade_history.append({"position": "TP_BUY", "type": "BUY", "price": current_data.iloc[-1]['close'], "step": i})
                    
                    #Reset the dict 
                    limit_orders = {}

            # Check if SELL tp_orders are filled (specular to the previous one).
            if limit_orders["tp_orders"]["type"] == "SELL": 
                if limit_orders["tp_orders"]["price"] <= current_data.iloc[i]["close"]: 
                    print_strings(f"TP orders filled {str(limit_orders["tp_orders"]["price"])}")
                    # print_index(i, "TP ORDER FILLED")
                    # print(current_data.iloc[-1]['close'])
                    # print(fibo_trades["price"])

                    # Append to trade_history(list) for plotting purposes. 
                    trade_history.append({"position": "TP_SELL", "type": "BUY", "price": current_data.iloc[-1]['close'], "step": i})
                    
                    #Reset the dict 
                    limit_orders = {}
    
    # Return entire dataset and trade_history list for plotting purposes. 
    return historical_data, trade_history


# The main script execution.
welcome() # Launch the initial logging.
myAccount, ib = boot_IB() # Get IB gateaway established. 
if ib is not None:
    config = get_config() # Read configuration parameters from config.json.
    if config is not None:
        contract = get_contract(config) # Get the requested pair contract.
        if contract is not None:
            historical_data = get_data(config, ib, contract) # Get historical data from IB gateaway.
            historical_data, trade_history = backtest_strategy(config, historical_data) # Get historical data and list of trades for plotting purposes. 
            
            # Plot the results. 
            plt.plot(historical_data['close'], label='Price')  # Plot the historical price series.
            for trade in trade_history:  # Iterate over list of trades and plot each trade as a point
                if trade['position'] == 'open':
                    plt.scatter(trade['step'], trade['price'], color='green', marker='^', label='Buy' if trade['type'] == 'BUY' else 'Sell')
                elif trade['position'] == 'close':
                    plt.scatter(trade['step'], trade['price'], color='red', marker='v', label='Close')

            plt.legend()
            plt.title('Price Series with Buy/Sell Points')
            plt.show()