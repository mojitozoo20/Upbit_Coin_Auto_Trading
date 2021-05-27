# Import pandas
import pandas as pd

# Import pyupbit
import pyupbit

# Import matplotlib 
import matplotlib.pyplot as plt
plt.style.use('fast')

# Import talib
import talib

# Import times
import datetime
import time

TICKERS = ['KRW-ETC','KRW-XRP','KRW-ETH','KRW-DOGE','KRW-SBD','KRW-BTC','KRW-BTT','KRW-EOS','KRW-QKC','KRW-ADA','KRW-BCH','KRW-FLOW','KRW-MLK','KRW-QTUM','KRW-VET','KRW-LSK','KRW-STEEM','KRW-OMG']
#TICKERS = ['KRW-SBD']

for ticker in TICKERS:
    # Import data from Upbit
    if datetime.datetime.now().second == 0:
        time.sleep(1)
    df = pyupbit.get_ohlcv(ticker, interval="minute1", to=datetime.datetime.now(), count=4320, period=0.2)  # 3일 = 4320분

    # Drop the NaN values
    df = df.dropna()
    df.head()

    # Calculate Parabolic SAR
    df['SAR'] = talib.SAR(df.high, df.low, acceleration=0.02, maximum=0.2)

    # Calculate Bollinger Band
    df['BBAND_UPPER'], df['BBAND_MIDDLE'], df['BBAND_LOWER'] = talib.BBANDS(df['close'],20,2)
    
    signal = (df.SAR <= df.BBAND_LOWER)

    earning_rate = 1
    sell_date = None
    win_count = 0
    lose_count = 0
    price_count = []
    price_sum = 0
    price_sum_arr = []

    for b in df.index[signal]:
        if sell_date != None and b <= sell_date:
            continue

        target = df.loc[ b : ]
        price_buy = target.iloc[0].close

        sell_signal = (target.close < target.SAR)
        sell_candidate = target.index[sell_signal]

        if len(sell_candidate) == 0:
            break

        sell_date = sell_candidate[0]
        price_sell = target.loc[sell_date].close

        earning_rate *= (price_sell / price_buy) * 0.9987  # 수수료 0.05% 두 번 + 슬리피지 0.03%
        if price_buy < price_sell:
            win_count += 1
        else:
            lose_count += 1
        price_count.append(price_sell - price_buy)
        price_sum += (price_sell - price_buy)
        price_sum_arr.append(price_sum)

    print(f'{ticker} : {earning_rate} 승리횟수 : {win_count} 패배횟수 : {lose_count}')
    #print(f'손익내역 : {price_count}')
    #print(f'누적내역 : {price_sum_arr}')