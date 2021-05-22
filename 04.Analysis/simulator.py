import numpy as np

def simulate(df_true, df_prediction, buy_threshold, balance, dump_time):
    # df_prediction is the dataframe with column 'prediction'


    buy_price = 0 # price for which coins were bought
    wallet = 0 # coins in the wallet
    spend = 0
    buy_points, sell_points, dump_points = [], [], []
    profits = []
    cnt = 0
    # Calculate predicted values
    for row in df_prediction.iterrows():
        # current timestamp, the predictionis for the next timestamp
        ts = row[1]['ts_end']

        # current price
        current_close = df_true['close'].loc[ts]

        # predicted price change in the next 1 hour
        pred = row[1]['prediction']

        # Buy/Sell depending on threshold
        if pred > buy_threshold and wallet == 0:
            # BUY
            buy_price = current_close

            quantity = balance / buy_price # how much can we buy at the current price with our balance
            quantity = np.round(quantity, 10) # round to avoid floating point errors

            spend = quantity * buy_price # what we spend
            wallet = quantity # buy at the current price
            balance = balance - spend
            balance = np.round(balance, 6)
            buy_points.append(ts)
#             print(f"BUY ::::: SPEND {spend} :::: BALANCE {balance} :::: WALLET {wallet} :::: BUY PRICE {buy_price}")


        elif pred < -buy_threshold and wallet > 0 and current_close > buy_price: # never sell at a loss
            # SELL
            sell_price = current_close
            revenue = sell_price * wallet # how much we make from the sale
            profit = revenue - spend # profit that we made
            profits.append(profit)
            sell_points.append(ts)
            balance = balance + revenue
            revenue = 0
            wallet = 0
#             print(f"SELL ::::: BALANCE {balance} :::: WALLET {wallet} :::: BUY PRICE {buy_price}")

        elif pred < -buy_threshold and wallet > 0 and (ts-buy_points[-1]).days > dump_time: # sell after dump_time days
            # SELL if we have not traded for the past 4 weeks
            sell_price = current_close
            revenue = sell_price * wallet # how much we make from the sale
            profit = revenue - spend # profit that we made
            profits.append(profit)
            sell_points.append(ts)
            dump_points.append(ts)
            balance = balance + revenue
            revenue = 0
            wallet = 0
#             print(f"DUMP ::::: BALANCE {balance} :::: WALLET {wallet} :::: BUY PRICE {buy_price}")
#         print(ts, pred, buy_price, current_close, pred < -buy_threshold)
#         if cnt > 2000:
#             break
#         cnt += 1

    return balance, buy_points, sell_points, dump_points, profits


