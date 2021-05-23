# Import pandas
import pandas as pd

# Import pyupbit
import pyupbit

# Import matplotlib 
import matplotlib.pyplot as plt
plt.style.use('fast')

# Import talib
import talib

TICKERS = ['KRW-DOGE','KRW-SOLVE','KRW-XRP','KRW-ETC','KRW-HUNT','KRW-ETH','KRW-BTC','KRW-EMC2','KRW-SAND','KRW-DMT','KRW-TON','KRW-UPP','KRW-IOTA','KRW-ADA','KRW-SSX','KRW-EOS','KRW-BTT']

for ticker in TICKERS:
    # Import data from Upbit
    df = pyupbit.get_ohlcv(ticker, interval="minute1", to="20210523 11:00:00", count=10000, period=0.2)

    # Drop the NaN values
    df = df.dropna()
    df.head()

    # Calculate Parabolic SAR
    df['SAR'] = talib.SAR(df.high, df.low, acceleration=0.02, maximum=0.2)

    # Calculate Bollinger Band
    df['BBAND_UPPER'], df['BBAND_MIDDLE'], df['BBAND_LOWER'] = talib.BBANDS(df['close'],20,2)

    # Calculate Tenkan-sen
    high_9 = df.high.rolling(9).max()
    low_9 = df.low.rolling(9).min() 
    df['tenkan_sen_line'] = (high_9 + low_9) /2

    # Calculate Kijun-sen
    high_26 = df.high.rolling(26).max()
    low_26 = df.low.rolling(26).min()
    df['kijun_sen_line'] = (high_26 + low_26) / 2

    # Calculate Senkou Span A
    df['senkou_spna_A'] = ((df.tenkan_sen_line + df.kijun_sen_line) / 2).shift(26)

    # Calculate Senkou Span B
    high_52 = df.high.rolling(52).max()
    low_52 = df.low.rolling(52).min()
    df['senkou_spna_B'] = ((high_52 + low_52) / 2).shift(26)

    # Calculate Chikou Span B
    df['chikou_span'] = df.close.shift(-26)

    # Create Plot
    '''
    komu_cloud = df[['close','SAR','BBAND_UPPER','BBAND_MIDDLE','BBAND_LOWER']].plot(figsize=(10, 5), style=['','b.','','',''])

    komu_cloud.fill_between(df.index[:], df.senkou_spna_A, df.senkou_spna_B, where=df.senkou_spna_A >= df.senkou_spna_B, color='lightgreen')

    komu_cloud.fill_between(df.index[:], df.senkou_spna_A, df.senkou_spna_B, where=df.senkou_spna_A < df.senkou_spna_B, color='lightcoral')

    plt.legend()
    plt.show()
    '''
    signal = (df.SAR < df.BBAND_LOWER) & (df.senkou_spna_A < df.BBAND_MIDDLE) & (df.senkou_spna_B < df.BBAND_MIDDLE) & (df.close < df.BBAND_UPPER) & (df.senkou_spna_A > df.senkou_spna_B)

    earning_rate = 1
    sell_date = None

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
    print(ticker, ':', earning_rate)
