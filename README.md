# trading_project

Trading bot for forex. It checks for SMA Cross, Bollinger Bands and RSI. Once one or more (as the user prefer) trigger is detected the bot will open a position short or long, depending on the trend sentiment: reverse or trending. 


## Settings
```json
{
    "pair" : "USDCHF",
    "barSizeSetting" : "10 mins",
    "durationStr" : "1 D",

    "SMA_small_duration" : 30,
    "SMA_big_duration" : 150,
    "RSI_duration" : 84,
    "bolinger_band_duration" : 120,
    "bolinger_band_std_dev" : 2,
    "RSI_high" : 70,
    "RSI_low" : 30,

    "Fibonacci_duration" : 20,
    
    "minimum_indicators_to_open" : 2,
    "Trending" : "False",

    "Martingale_multiplier" : 1.3,
    "Martingale_max" : 3, 
    "Initial_size_trade" : 25000,
    
    "Max_drawdown" : 0.05,
    "Take_profit" : 0.005,

    "sleep_time" : 60,
    "Monitoring_order_sleep" : 0.5

}
```

## Graphic Representation of Indicators Calculated
![alt text](https://github.com/washednico/trading_project/blob/main/img/indicators.png?raw=true)
![alt text](https://github.com/washednico/trading_project/blob/main/img/indicators2.png?raw=true)


## Example of Execution

```text
 _ _   __  _ _    ___          __ _ _     _  _     _     ___                 _ 
| | | /  \| | |  | _ \_ _ ___ / _(_) |_  | \| |___| |_  | __|__ _  _ _ _  __| |
|_  _| () |_  _| |  _/ '_/ _ \  _| |  _| | .` / _ \  _| | _/ _ \ || | ' \/ _` |
  |_| \__/  |_|  |_| |_| \___/_| |_|\__| |_|\_\___/\__| |_|\___/\_,_|_||_\__,_|
                                                                               




Welcome to the trading bot, remember to open your IB Gateway before running the bot!
Press enter to continue...




[2024-09-02 11:38:08.385399]    IB Gateway connecting...
[2024-09-02 11:38:09.000091]    IB Gateway connected
[2024-09-02 11:38:09.000243]    Loading config file...
[2024-09-02 11:38:09.002168]    Config file loaded
[2024-09-02 11:38:09.002258]    Getting contract for USDCHF...
[2024-09-02 11:38:09.002302]    Contract for USDCHF retrived!
[2024-09-02 11:38:09.002477]    Getting historical data for USDCHF...
[2024-09-02 11:38:09.328540]    Historical data for USDCHF downloaded
[2024-09-02 11:38:09.328580]    Calculating indicators...
[2024-09-02 11:38:09.352453]    Indicators calculated
[2024-09-02 11:38:09.352830]    0 Indicators met
[2024-09-02 11:39:09.359235]    Getting historical data for USDCHF...
[2024-09-02 11:39:09.722820]    Historical data for USDCHF downloaded
[2024-09-02 11:39:09.722878]    Calculating indicators...
[2024-09-02 11:39:09.739321]    Indicators calculated
[2024-09-02 11:39:09.739765]    0 Indicators met
[2024-09-02 11:40:09.746132]    Getting historical data for USDCHF...
[2024-09-02 11:40:10.067555]    Historical data for USDCHF downloaded
[2024-09-02 11:40:10.067637]    Calculating indicators...
[2024-09-02 11:40:10.083534]    Indicators calculated
[2024-09-02 11:40:10.083974]    0 Indicators met

.
.
.

[2024-09-02 12:43:38.215261]    2 Indicators met
[2024-09-02 12:43:38.215298]    Sending market order: SIZE: 25000 TYPE: SELL
[2024-09-02 12:43:38.216027]    Market order sent!
[2024-09-02 12:43:45.546295]    Market order filled! PRICE: 0.85057
[2024-09-02 12:43:45.550644]    Fibonacci retracements calculated!
[2024-09-02 12:43:45.742782]    Placing take profit: SIZE: 25000 TYPE: BUY PRICE: 0.8548
[2024-09-02 12:43:45.744345]    Take profit placed!
[2024-09-02 12:43:45.744447]    Placing limit order: SIZE: 32500.0 TYPE: SELL PRICE: 0.8511
[2024-09-02 12:43:45.745334]    Limit order placed!
[2024-09-02 12:43:45.745402]    Placing limit order: SIZE: 42250.0 TYPE: SELL PRICE: 0.8514
[2024-09-02 12:43:45.746218]    Limit order placed!
[2024-09-02 12:43:45.746268]    Placing limit order: SIZE: 54925.0 TYPE: SELL PRICE: 0.8516
[2024-09-02 12:43:45.747113]    Limit order placed!
[2024-09-02 12:43:45.747217]    Monitoring 4 relevant trades...
[2024-09-02 12:43:45.747240]    Trade 6 monitoring started!
[2024-09-02 12:43:45.747255]    Trade 7 monitoring started!
[2024-09-02 12:43:45.747269]    Trade 8 monitoring started!
[2024-09-02 12:43:45.747282]    Trade 9 monitoring started!

.
.
.
.

[2024-09-02 12:43:50.980604]    Take profit filled! Cancelling all other orders.
[2024-09-02 12:43:50.981925]    Order 7 cancelled.
[2024-09-02 12:43:50.983041]    Order 8 cancelled.
[2024-09-02 12:43:50.984128]    Order 9 cancelled.


```