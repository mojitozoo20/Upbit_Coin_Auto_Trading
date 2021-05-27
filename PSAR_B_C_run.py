import threading
import queue

import pyupbit

import pandas as pd
import talib

import time
import datetime

TICKER = "KRW-SBD"

class Consumer(threading.Thread):
    def __init__(self, q):
        super().__init__()
        self.q = q
        self.ticker = TICKER

    def run(self):
        price_curr = None  # 현재 가격
        price_buy = None  # 마지막 구매가
        hold_flag = False  # 보유 여부
        wait_flag = False  # 대기 여부

        with open("upbit_key.txt", "r") as f:
            access = f.readline().strip()
            secret = f.readline().strip()

        upbit = pyupbit.Upbit(access, secret)
        cash  = upbit.get_balance()  # 2개 이상 종목 돌릴 시 모든 cash 코드 임의 설정
        CASH = cash  # 수익률 계산을 위한 초기 보유 KRW
        print("보유 KRW:", cash)

        i = 0

        while True:
            try:
                if not self.q.empty():
                    df = pyupbit.get_ohlcv(self.ticker, interval="minute1", to=datetime.datetime.now())  # DataFrame 갱신
                    df['SAR'] = talib.SAR(df.high, df.low, acceleration=0.02, maximum=0.2)  # Parabolic SAR 계산
                    df['BBAND_UPPER'], df['BBAND_MIDDLE'], df['BBAND_LOWER'] = talib.BBANDS(df['close'], 20, 2)  # Bollinger Band 계산

                    high_9 = df.high.rolling(9).max()
                    low_9 = df.low.rolling(9).min()
                    df['tenkan_sen_line'] = (high_9 + low_9) /2  # 전환선

                    high_26 = df.high.rolling(26).max()
                    low_26 = df.low.rolling(26).min()
                    df['kijun_sen_line'] = (high_26 + low_26) / 2  # 기준선

                    df['senkou_spna_A'] = ((df.tenkan_sen_line + df.kijun_sen_line) / 2).shift(26)  # 선행1 스팬

                    high_52 = df.high.rolling(52).max()
                    low_52 = df.low.rolling(52).min()
                    df['senkou_spna_B'] = ((high_52 + low_52) / 2).shift(26)  # 선행2 스팬

                    df['chikou_span'] = df.close.shift(-26)  # 후행 스팬

                    curr = df.iloc[-1]  # 마지막 행을 현재로 저장

                    price_open = self.q.get()  # Queue를 비우기 위해 필수. 삭제 금지
                    price_curr = pyupbit.get_current_price(self.ticker)
                    
                    wait_flag  = False  # 매 봉 대기모드 해제

                if hold_flag == False and wait_flag == False and \
                    curr.SAR <= curr.BBAND_LOWER and curr.senkou_spna_A <= curr.BBAND_MIDDLE and \
                    curr.senkou_spna_B <= curr.BBAND_MIDDLE and curr.senkou_spna_A >= curr.senkou_spna_B:

                    price_buy = price_curr

                    while True:
                        ret = upbit.buy_market_order(self.ticker, int(cash * 0.9995))  # 0.05%
                        if ret == None or "error" in ret:
                            print("<< 매수 주문 Error >>")
                            time.sleep(0.5)
                            continue
                        print("매수 주문", ret)
                        break

                    while True:
                        order = upbit.get_order(ret['uuid'])
                        if order != None and len(order['trades']) > 0:
                            print("<< 매수 주문이 체결되었습니다 >>\n", order)
                            hold_flag = True
                            break
                        else:
                            print("매수 주문 대기 중...")
                            time.sleep(0.5)

                    while True:
                        volume = upbit.get_balance(self.ticker)
                        if volume != None and volume != 0:
                            break
                        print("보유량 계산중...")
                        time.sleep(0.5)
                    
                    cash = upbit.get_balance()

                if hold_flag == True and curr.close < curr.SAR:
                    upbit.sell_market_order(self.ticker, volume)
                    while True:
                        volume = upbit.get_balance(self.ticker)
                        if volume == 0:
                            print("<< 매도 주문이 완료되었습니다 >>")
                            cash = upbit.get_balance()
                            price_buy = None
                            hold_flag = False
                            wait_flag = True
                            break
                        else:
                            print("매도 주문 처리 대기중...")
                            time.sleep(0.5)

                # 10 seconds
                if i == (5 * 10):
                    print(f"\t{TICKER} [{datetime.datetime.now()}]")
                    print(f"보유량: {upbit.get_balance_t(self.ticker)}, 보유KRW: {cash},  hold_flag= {hold_flag}, wait_flag= {wait_flag}, cloud_location= {curr.senkou_spna_A <= curr.BBAND_MIDDLE and curr.senkou_spna_B <= curr.BBAND_MIDDLE and curr.senkou_spna_A >= curr.senkou_spna_B}, SAR_location= {curr.SAR <= curr.BBAND_LOWER}")
                    print(f"BBAND: [{int(curr.BBAND_UPPER)} {int(curr.BBAND_MIDDLE)} {int(curr.BBAND_LOWER)}], PSAR: {curr.SAR}, 선행1: {curr.senkou_spna_A}, 선행2: {curr.senkou_spna_B}")
                    print(f"전봉 종가: {price_curr}, 구매가: {price_buy}, 누적 수익: {cash - CASH} ({100 - (cash / CASH * 100)}%)")
                    i = 0
                i += 1
            except:
                print("error")

            time.sleep(0.2)

class Producer(threading.Thread):
    def __init__(self, q):
        super().__init__()
        self.q = q

    def run(self):
        while True:
            price = pyupbit.get_current_price(TICKER)
            self.q.put(price)
            time.sleep(60)

now = datetime.datetime.now()
print(f'환영합니다 -- Upbit Auto Trading -- [{now.year}-{now.month}-{now.day} {now.hour}:{now.minute}:{now.second}]')
print('트레이딩 대기중...')
while True:
    now = datetime.datetime.now()
    if  now.second == 1:  # 대기 후 1초에 시작
        q = queue.Queue()
        Producer(q).start()
        Consumer(q).start()
        break
