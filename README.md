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

```