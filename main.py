from ib_insync import *
import json
from ta.momentum import RSIIndicator
from ta.trend import SMAIndicator
from ta.volatility import BollingerBands
from pyfiglet import Figlet
import datetime
from time import sleep

def welcome():
    # Welcome function
    f = Figlet(font='small')
    print(f.renderText('404 Profit Not Found'))
    print("\n\n\nWelcome to the trading bot, remember to open your IB Gateway before running the bot!")
    input("Press enter to continue...")
    print("\n\n\n")

def print_strings(string):
    #Function to print with timestamp
    print("["+str(datetime.datetime.now())+"]\t"+string)

def boot_IB():
    # This function attempts to connect to the Interactive Brokers (IB) Gateway
    # and retrieve the account summary information.
    try:
        print_strings("IB Gateway connecting...")
        ib = IB()
        ib.connect('127.0.0.1', 7497, clientId=1)
        print_strings("IB Gateway connected")
    except:
        print_strings("Error connecting to IB Gateway")
        return None

    try:
        print_strings("Retrieving Account Information...")
        myAccount = ib.accountSummary()
        available_funds = {}
        for item in myAccount:
            if item.tag == 'TotalCashBalance':
                # Store the total cash balance in the relevant currency
                available_funds[item.currency] = float(item.value)
            if item.tag == 'AvailableFunds':
                # Identify and store the home currency (currency of available funds)
                home_currency = item.currency
            if item.tag == "NetLiquidation":
                # Store the net liquidation value
                net_liquidation = float(item.value)

        # Set the initial funds to the cash balance in the home currency
        initial_funds = available_funds[home_currency]
        
        
        print_strings("Available funds: "+str(initial_funds)+" "+home_currency)
        print_strings("Net Liquidation: "+str(net_liquidation)+" "+home_currency)
        
        return myAccount, ib, home_currency, initial_funds, net_liquidation
    
    except:
        return None, None

        
def get_config():
    # This function loads the configuration settings from a 'config.json' file.
    print_strings("Loading config file...")
    try:
        with open('config.json') as f:
            config = json.load(f)
        print_strings("Config file loaded")
        # Check if the Martingale maximum level is within acceptable bounds
        if config["Martingale_max"] <= 5:
            return config
        else:
            print_strings("Martingale_max should be less than 5")
    except:
        print_strings("Error loading config file")
        return None
    
def get_contract(config):
    # This function retrieves the Forex contract based on the trading pair specified in the config
    try:
        print_strings("Getting contract for "+config["pair"]+"...")
        contract = Forex(config["pair"])
        print_strings("Contract for "+config["pair"]+" retrived!")
        return contract # Return the contract object
    except:
        print_strings("Error getting contract for "+config["pair"])
        return None
    # (no need to check for shortability in forex)

def check_parameters(contract, home_currency, ib, initial_funds,config):

    # This function checks whether the selected currency pair is appropriate given the home currency,
    # and whether the maximum potential trades size exceeds the available funds.

    # Check if the home currency is part of the currency pair
    if home_currency.lower() not in config["pair"].lower():
        print_strings("PLEASE USE A PAIR WITH YOUR HOME CURRENCY")
        return None
    
    # Determine if the home currency is the base currency or the quote currency in the pair
    if config["pair"].lower().startswith(home_currency.lower()):
        base_currency = False
    else:
        base_currency = True
    
    # Request market data for the contract to get the current exchange rate
    ticker = ib.reqMktData(contract)
    ib.sleep(2)  
    exchange_rate = ticker.ask

    # Calculate the maximum amount that could be traded with the Martingale strategy
    max_amount = config["Initial_size_trade"]
    for i in range(1,config["Martingale_max"]+1):
        max_amount += config["Initial_size_trade"]*config["Martingale_multiplier"]**i
    
    # If the home currency is the quote currency, convert max_amount to the home currency
    if not base_currency:
        max_amount = max_amount * exchange_rate

    # Check if the calculated max amount exceeds 90% of the available funds
    if max_amount > initial_funds*0.9:
        print_strings("PLEASE DECREASE THE MAXIMUM MARTINGALE AMOUNT, MARTINGAL MULTIPLIER OR INITIAL SIZE TRADE.")
        print_strings("IT'S SUGGESTED TO AVOID USING MORE THAN AVAILABLE FUNDS TO AVOID MARGIN CALLS")
        input("Please close the program....")
        return None # Return None to indicate that the configuration is unsafe

    return True # Return True if all checks are passed
        



def get_parameters(ib,config,contract):
    # This function retrieves historical market data and calculates several technical indicators
    # based on the provided configuration.

    print_strings("Getting historical data for "+config["pair"]+"...")
    try:
        bars = ib.reqHistoricalData(
            contract, endDateTime='', durationStr = config["durationStr"],
            barSizeSetting= config["barSizeSetting"], whatToShow='MIDPOINT', useRTH=0)
        print_strings("Historical data for "+config["pair"]+" downloaded")
    except:
        print_strings("Error downloading historical data for "+config["pair"])
        return None
    
    try:
        print_strings("Calculating indicators...")
        myData = util.df(bars) # Convert bars to a DataFrame

        # Calculate the SMA (Simple Moving Average) for two different window sizes
        SMA5_series = SMAIndicator(close=myData['close'], window=config["SMA_small_duration"]).sma_indicator()
        SMA25_series = SMAIndicator(close=myData['close'], window=config["SMA_big_duration"]).sma_indicator()
        
        # Calculate the RSI (Relative Strength Index)
        RSI_series = RSIIndicator(close=myData['close'], window=config["RSI_duration"]).rsi()
        
        # Calculate the Bollinger Bands (upper and lower bands)
        Bollinger_H_series = BollingerBands(close=myData['close'], window=config["bolinger_band_duration"], window_dev=config["bolinger_band_std_dev"]).bollinger_hband()
        Bollinger_L_series = BollingerBands(close=myData['close'], window=config["bolinger_band_duration"], window_dev=config["bolinger_band_std_dev"]).bollinger_lband()
        
        print_strings("Indicators calculated")
    except:
        print_strings("Error calculating indicators")
        return None

    return SMA5_series, SMA25_series, RSI_series, Bollinger_H_series, Bollinger_L_series, myData, contract

def get_fibonacci_levels(myData, fill,config):
    fill_price = fill.execution.price
    print_strings("Market order filled! PRICE: "+str(fill_price))

    # Determine the highest high and lowest low over the defined duration
    highest_price = myData['high'].tail(config["Fibonacci_duration"]).max()
    lowest_price = myData['low'].tail(config["Fibonacci_duration"]).min()
    
    # Calculate the difference between the high and low
    delta_diff = highest_price - lowest_price
    
    # Calculate Fibonacci levels with the first order (fill price) sitting at Level 0
    # This positions the fill price as the central reference point for the Fibonacci retracement levels.
    retracements = {
        1: [(fill_price+delta_diff*0.236).round(4),  (fill_price-delta_diff*0.236).round(4)],
        2: [(fill_price+delta_diff*0.382).round(4),  (fill_price-delta_diff*0.382).round(4)],
        3: [(fill_price+delta_diff*0.5).round(4),    (fill_price-delta_diff*0.5).round(4)],
        4: [(fill_price+delta_diff*0.618).round(4),   (fill_price-delta_diff*0.618).round(4)],
        5: [(fill_price+delta_diff*0.786).round(4),   (fill_price-delta_diff*0.786).round(4)]
    }
    
    print_strings("Fibonacci retracements calculated!")

    return retracements, fill_price


def detect_trigger(config,ib,contract,net_liquidation):
    while True:
        
        # Get the latest data and indicators, sleep if there is an error and check again
        try:
            SMA5_series, SMA25_series, RSI_series, Bollinger_H_series, Bollinger_L_series, myData, contract = get_parameters(ib, config,contract)
        except:
            print_strings("Error getting parameters, retrying...")
            sleep(config["sleep_time"])
            continue
        
        # Determine if there's a crossover between the short and long SMAs
        if SMA5_series.iloc[-1] > SMA25_series.iloc[-1] and SMA5_series.iloc[-2] < SMA25_series.iloc[-2]:
            cross_value = -1 
        elif SMA5_series.iloc[-1] < SMA25_series.iloc[-1] and SMA5_series.iloc[-2] > SMA25_series.iloc[-2]:
            cross_value = 1
        else:
            cross_value = 0
        
        # Check if the RSI is above or below predefined thresholds
        if RSI_series.iloc[-1] > config["RSI_high"]:
            RSI_value = 1
        elif RSI_series.iloc[-1] < config["RSI_low"]:
            RSI_value = -1
        else:
            RSI_value = 0
        
        # Check if the price is above or below the Bollinger Bands
        if myData['close'].iloc[-1] > Bollinger_H_series.iloc[-1]:
            bollinger_value = 1
        elif myData['close'].iloc[-1] < Bollinger_L_series.iloc[-1]:
            bollinger_value = -1
        else:
            bollinger_value = 0

        
        print_strings(str(abs(cross_value)+abs(RSI_value)+abs(bollinger_value))+" Indicators met")

        # Check if the combined indicators suggest opening a position
        if cross_value + RSI_value + bollinger_value >= config["minimum_indicators_to_open"]:
            order_info = {}
            if config["Trending"].lower() == "true":  
                order_info["type"] = "BUY"  # Enter a buy position if trending
            else:
                order_info["type"] = "SELL"   # Enter a sell position if counter-trending
            
            if(initiate_strategy(contract, order_info, ib, config, myData, net_liquidation)): #THIS WILL LAUNCH THE STRATEGY
                #Initiate_strategy return True if the strategy hit a drawdown. The program will stop here.
                return None  

            if config["monitor_forever"].lower() == "false":
                # Exit the tradingbot if strategy successfull and monitor_forever is set to false
                break 
            else:
                #if monitor_forever is set to true, sleep for the specified time before starting the strategy again
                sleep(config["sleep_time"]) 
    
        elif cross_value + RSI_value + bollinger_value <= -config["minimum_indicators_to_open"]:
            order_info = {}
            if config["Trending"].lower() == "true":
                order_info["type"] = "SELL" # Enter a sell position if trending
            else:
                order_info["type"] = "BUY" # Enter a buy position if counter-trending
            
            if(initiate_strategy(contract, order_info, ib, config, myData, net_liquidation)):  #THIS WILL LAUNCH THE STRATEGY
                #Initiate_strategy return True if the strategy hit a drawdown. The program will stop here.
                return None
            
            if config["monitor_forever"].lower() == "false":
                # Exit the tradingbot if strategy successfull and monitor_forever is set to false
                break
            else:
                #if monitor_forever is set to true, sleep for the specified time before starting the strategy again
                sleep(config["sleep_time"])

        else:
            sleep(config["sleep_time"]) # No trigger met, continue monitoring


def initiate_strategy(contract, order_info, ib, config, myData, net_liquidation):
    print_strings("Sending market order: SIZE: "+str(config["Initial_size_trade"])+" TYPE: "+order_info["type"])
    
    # Place the market order through the Interactive Brokers
    order = MarketOrder(order_info["type"], config["Initial_size_trade"])
    trade = ib.placeOrder(contract, order)
    print_strings("Market order sent!")

    retracements = None # To store Fibonacci retracement levels
    fill_processed = [False] # Track whether the order fill has been processed
    fill_price = None # To store the price at which the order is filled

    # Define a function to handle the order fill event
    def on_fill(trade, fill):
        nonlocal retracements, fill_price
        retracements, fill_price = get_fibonacci_levels(myData, fill, config) # Calculate Fibonacci levels
        fill_processed[0] = True  # Mark the fill as processed
    
    # Attach the on_fill function to the trade's fill event
    trade.fillEvent += on_fill  
    
    # Wait until the order is filled and processed
    while not fill_processed[0]:
        ib.sleep(0.5)

    # Send a take-profit order based on the filled price
    tp_type, tp_trade = send_tp(order_info,fill_price,ib,config,contract)
    
    # Send limit orders for additional trades based on Fibonacci retracement levels
    sizes_tp, limit_trades = send_limit_orders(order_info, config,ib,retracements,contract,fill_price)

    # Monitor and manage the orders, checking against the net liquidation value
    if(monitor_and_check_orders(ib, contract, order_info, config, tp_type, sizes_tp, tp_trade, limit_trades, net_liquidation)):
        return True #return True if the strategy hit a drawdown
  


def send_tp(order_info, price, ib, config,contract):
    tp_trade = [] # List to hold the take-profit trade
    if order_info["type"] == "BUY": 
        order_type = "SELL"
    else: 
        order_type = "BUY"
    
    # Calculate the take-profit price limit based on the order type
    if order_type == "BUY":
        price_limit = round((1-config["Take_profit"])*price,4)
    else:
        price_limit = round((config["Take_profit"]+1)*price,4)

    print_strings("Placing take profit: SIZE: "+ str(config["Initial_size_trade"])+" TYPE: "+order_type+" PRICE: "+str(price_limit))
    # Create a limit order for the take-profit
    order = LimitOrder(order_type, config["Initial_size_trade"], price_limit)
    # Place the take-profit order with Interactive Brokers
    trade = ib.placeOrder(contract, order)
    # Append the trade to the tp_trade list
    tp_trade.append(trade)
    print_strings("Take profit placed!")
    return order_type, tp_trade

def send_limit_orders(order_info, config,ib,retracements,contract,fill_price):
    sizes_tp = {} # Dictionary to store cumulative trade sizes and their corresponding take-profit prices
    cumulative_size = config["Initial_size_trade"]
    total_value = config["Initial_size_trade"] * fill_price
    
    limit_trades = [] # List to keep track of all limit trades

    # Loop to place a series of limit orders based on the Martingale strategy
    for i in range(1,config["Martingale_max"]+1):
        # Determine the limit price for the order based on the retracement levels
        if order_info["type"] == "BUY":
            price_limit = retracements[i][1]
        else:
            price_limit = retracements[i][0]
        
        # Calculate the size of the order based on the Martingale multiplier
        size = round(config["Initial_size_trade"]*config["Martingale_multiplier"]**i,4)
        # Create and place the limit order through the Interactive Brokers 
        print_strings("Placing limit order: SIZE: "+str(size)+" TYPE: "+order_info["type"]+" PRICE: "+str(price_limit))
        order = LimitOrder(order_info["type"], size, price_limit)
        trade = ib.placeOrder(contract, order)
        limit_trades.append(trade) # Add the trade to the limit_trades list
        print_strings("Limit order placed!")

        # Update cumulative size and total value after placing the new limit order
        cumulative_size += size
        total_value += size * price_limit
        # Calculate the new average price after placing the limit order
        average_price = total_value / cumulative_size
        # Determine the take-profit price based on the average price and the order type
        if order_info["type"] == "BUY":
            tp_price = average_price * (1 + config["Take_profit"])
        else:  
            tp_price = average_price * (1 - config["Take_profit"])

        # Store the cumulative size and corresponding take-profit price in sizes_tp
        sizes_tp[i] = {'tp_size': round(cumulative_size,4), 'tp_price': round(tp_price,4)}
    
    # Return the dictionary of sizes and take-profit prices, and the list of limit trades
    return sizes_tp, limit_trades

def monitor_and_check_orders(ib, contract, order_info, config, tp_type, sizes_tp, tp_trade,  limit_trades, net_liquidation):
    # Warning: This function has more moving parts than a Swiss watch!
    # Prepare yourself for a wild ride through order management and drawdown control.

    take_profit_filled = False
    filled_limit_orders_count = 0  # Counter for filled limit orders
    canceled_orders = set()  # Track canceled orders

    important_trades = tp_trade + limit_trades
    
    print_strings(f"Monitoring {len(important_trades)} relevant trades...") 

    def handle_order_status(trade):
        nonlocal filled_limit_orders_count, take_profit_filled
          
        if trade.orderStatus.status == 'Filled':
            
            important_trades.remove(trade) # Remove the filled trade from the monitoring list
            
            if trade in tp_trade:
                print_strings("Take profit filled! Cancelling all other orders.")
                for other_trade in limit_trades:
                            ib.cancelOrder(other_trade.order) # Cancel all limit orders if TP is hit
                            canceled_orders.add(other_trade.order.orderId)
                            print_strings(f"Order {other_trade.order.orderId} cancelled.")
                take_profit_filled = True

                return False #Means that drawdown was not hit
            
            elif trade in limit_trades:

                limit_trades.remove(trade)
                
                filled_limit_orders_count += 1
                print_strings(f"{filled_limit_orders_count}st limit order filled! Adjusting TP price.")
                
                tp_details = sizes_tp[filled_limit_orders_count]

                tp_old = tp_trade[0]
                tp_trade.remove(tp_old)
                
                ib.cancelOrder(tp_old.order) # Cancel the old TP order
                canceled_orders.add(tp_old.order.orderId)
                print_strings(f"Order {tp_old.order.orderId} cancelled.")
                
                new_order = LimitOrder(tp_type, tp_details['tp_size'], tp_details['tp_price']) # Place a new TP order
                new_tp = ib.placeOrder(contract, new_order)
                
                tp_trade.append(new_tp)

                new_tp.statusEvent += handle_order_status  # Attach the status handler to the new order
                important_trades.append(new_tp)

                print_strings(f"New TP order placed: SIZE {tp_details['tp_size']} PRICE {tp_details['tp_price']}")

    for trade in important_trades:
        trade.statusEvent += handle_order_status  # Start monitoring each trade's status
        print_strings(f"Trade {trade.order.orderId} monitoring started!")  

    while not take_profit_filled:
        for trade in important_trades:
            myAccount = ib.accountSummary()
            try:
                for item in myAccount:
                    if item.tag == "NetLiquidation":
                        new_liquidation = float(item.value)

                # Check if net liquidation has dropped below the max drawdown threshold
                if new_liquidation < net_liquidation*(1-config["Max_drawdown"]):
                    print_strings("Max drawdown reached, closing all orders...")
                    # Cancel all open orders if the drawdown threshold is reached
                    for trade in important_trades:
                        ib.cancelOrder(trade.order)
                        canceled_orders.add(trade.order.orderId)
                        print_strings(f"Order {trade.order.orderId} cancelled.")
                    
                    # Place a market order to close the first market order
                    if filled_limit_orders_count == 0:
                        config["Initial_size_trade"]
                        new_order = MarketOrder(tp_type, config["Initial_size_trade"])
                        new_tp = ib.placeOrder(contract, new_order)
                        print_strings(f"Market order placed: SIZE {config["Initial_size_trade"]} TYPE {tp_type}")
                        return True #Return True if the strategy hit a drawdown
                    
                    #Place a market order to close firt market order and following limit orders
                    else:
                        filled_limit_orders_count += 1
                        tp_details = sizes_tp[filled_limit_orders_count]
                        new_order = MarketOrder(tp_type, tp_details['tp_size'])
                        new_tp = ib.placeOrder(contract, new_order)
                        print_strings(f"Market order placed: SIZE {tp_details['tp_size']} TYPE {tp_type}")
                        return True #Return True if the strategy hit a drawdown
                
                else:
                    percentage_cg = round((new_liquidation - net_liquidation) / net_liquidation,4)*100 
                    print("["+str(datetime.datetime.now())+"]\t"+"Monitoring open orders and balance ["+str(percentage_cg)+"%]", end='\r')
            
            except:
                print_strings("Error getting account information")
            

            ib.sleep(config["Monitoring_order_sleep"]) #sleep for the specified time before checking the orders again


def plot_indicators(SMA5_series, SMA25_series, RSI_series, myData, Bollinger_H_series, Bollinger_L_series):
    import matplotlib.pyplot as plt
    # Create the figure and primary axis
    fig, ax1 = plt.subplots(figsize=(12, 8))  # Increasing the figure size
    # Create a secondary y-axis for the SMA and price data
    ax2 = ax1.twinx()
    # Plot SMA5, SMA25, and close prices
    ax2.plot(myData.index, SMA5_series, color='red', label='SMA5')
    ax2.plot(myData.index, SMA25_series, color='green', label='SMA25')
    ax2.plot(myData.index, Bollinger_H_series, color='purple', label='Bollinger')
    ax2.plot(myData.index, Bollinger_L_series, color='purple', label='Bollinger')
    ax2.plot(myData.index, myData['close'], color='black', label='Close')
    ax2.set_ylabel('Price Indicators', color='black')
    ax2.tick_params(axis='y', labelcolor='black')
    # Create a separate axis for RSI
    fig, ax3 = plt.subplots(figsize=(12, 4))  # Create a separate figure for RSI
    # Plot RSI on separate axis
    ax3.plot(myData.index, RSI_series, color='blue', label='RSI')
    ax3.set_ylabel('RSI', color='blue')
    ax3.tick_params(axis='y', labelcolor='blue')
    # Combine legends from both axes
    lines2, labels2 = ax2.get_legend_handles_labels()
    lines3, labels3 = ax3.get_legend_handles_labels()
    ax2.legend(lines2, labels2, loc='upper left')  # Only show legend for SMA and price data
    ax3.legend(lines3, labels3, loc='upper left')  # Show legend for RSI
    # Improve layout to make room for rotated x-axis labels
    plt.tight_layout()  # This might help to avoid clipping of labels
    plt.show()




welcome()

myAccount, ib, home_currency, initial_funds, net_liquidation = boot_IB()
config = get_config()
contract = get_contract(config)
if check_parameters(contract, home_currency, ib, initial_funds,config):
    detect_trigger(config,ib,contract, net_liquidation)
    print_strings("All orders filled, closing connection...")
    input("Press enter to close the connection...")


#Uncomment this to plot the indicators after the contract <3
#SMA5_series, SMA25_series, RSI_series, Bollinger_H_series, Bollinger_L_series, myData, contract = get_parameters(ib,config,contract)
#plot_indicators(SMA5_series, SMA25_series, RSI_series, myData, Bollinger_H_series, Bollinger_L_series)

