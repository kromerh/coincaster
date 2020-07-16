import jellyfish
import os
import pymongo
import requests
import bs4 as bs
import pandas as pd
import numpy as np
import re
import datetime

# Connect to mongo DB
cred = '../01.Original_data/credentials/mongodb.pw'
data_cred = pd.read_csv(cred, index_col=0, header=None)
USER = data_cred.loc['USER'].values[0]
DB = data_cred.loc['DB'].values[0]
PW = data_cred.loc['PW'].values[0]
HOST = data_cred.loc['HOST'].values[0]

def clean_numeric_columns(row, col):
    """
    Cleans the numeric columns given as a str col.
    Points are replaced with nothing and commas are replaced with decimal points.
    """
    row = row.astype(str)
    # replace commas
    entry = row[col].replace(',', '')
    # replace comma
#     entry = entry.replace(',', '.')
    # conver to float
    entry = np.float(entry)

    return entry


def mine_recent_data(link, log=True):
    """
    Mines more data from coinmarketcap for the link and returns the data as a dataframe
    """
    url = (link + '/historical-data/')
    r  = requests.get(url)
    r.status_code
    data = r.content
    soup = bs.BeautifulSoup(data, 'html.parser')
    tables = soup.findAll('table')
#     print(len(tables))
    if len(tables) == 4:
        table_rows = tables[2].findAll('tr')
        count = 0
        l = []
        for tr in table_rows:
            count += 1
            if count > 1:
                td = tr.find_all('td')
                row = [i.text.strip() for i in td]
                l.append(row)

        all_cols = ['Date','Open','High','Low','Close','Volume','Market_cap']
        data_ = pd.DataFrame.from_records(l, columns=all_cols)
        data_['date'] = pd.to_datetime(data_['Date'])

        cols = ['Open','High','Low','Close','Volume','Market_cap']

        for col in cols:
            new_col = col.lower()
            data_[new_col] = data_.apply(lambda x: clean_numeric_columns(x, col), axis=1)

        data_cleaned_ = data_.drop(columns=cols + ['Date'])

        # make sure the datatypes align
        for c in data_cleaned_.columns.tolist():
            if c != 'date':
                data_cleaned_[c] = data_cleaned_[c].astype(float)

        return data_cleaned_

    else:
        if log == True:
            date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            with open('./new_coin_data_into_mongoDB.log', 'a') as file:
                file.write(f"{date}: No new record for link {link} were found.\n")
                file.close()
        print(f"No new record for link {link} were found.")
        return pd.DataFrame({})


def get_new_data(data_mongo):
    """
    Mines new data for that coin and compares to the already mined data that is stored in the mongo DB.
    Then, uploads only the new data to the mongo DB
    """
    date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    #data_mongo = dict_coins[f]
    link = data_mongo.loc[0, 'link']
    coin_name = data_mongo.loc[0, 'coin_name']
    coin_symbol = data_mongo.loc[0, 'coin_symbol']
    fname = data_mongo.loc[0, 'fname']
    data_mongo = data_mongo.drop(columns='_id')

    data_mined = mine_recent_data(link)
    if data_mined.shape[0] > 0:
        # convert datetime to str
        data_mongo.loc[:, 'date'] = data_mongo.loc[:, 'date'].dt.strftime("%Y-%m-%d")
        data_mined.loc[:, 'date'] = data_mined.loc[:, 'date'].dt.strftime("%Y-%m-%d")
        # add other columns
        data_mined['coin_name'] = coin_name
        data_mined['coin_symbol'] = coin_symbol
        data_mined['fname'] = fname
        data_mined['link'] = link
        # reset index
        data_mongo = data_mongo.reset_index(drop=True)
        data_mined = data_mined.reset_index(drop=True)

        # new data that is not yet in the mongo DB
        data_new = data_mined[~data_mined['date'].isin(data_mongo['date'])]

        return data_new
    else:
        return pd.DataFrame({})


def upload_data_to_mongo(client, data_new, coin, log=True):
    """
    Connects to the mongoDB client and uploads the new data for the collection coin.
    """
    date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    db = client.coincaster

    coll = db[str(coin)]
    if data_new.shape[0] > 0:
        coll.insert_many(data_new.to_dict('records'))

        print(f"Uploaded {data_new.shape[0]} entries for coin {coin}.")
        if log == True:
        	with open('./new_coin_data_into_mongoDB.log', 'a') as file:
        		file.write(f"{date}: Uploaded {data_new.shape[0]} entries for coin {coin}.\n")
        		file.close()
    else:
        if log == True:
        	with open('./new_coin_data_into_mongoDB.log', 'a') as file:
        		file.write(f"{date}: No new record for coin {coin} were found.\n")
        		file.close()
        print(f"No new record for coin {coin} where found.")
    return None









client = pymongo.MongoClient(f"mongodb://{USER}:{PW}@{HOST}/{DB}") # defaults to port 27017





# get the data for the coins stored in the mongoDB

db = client.coincaster
# get the filenames of the coins
coins = db.list_collection_names()

# make sure to only capture csv
files = [f for f in coins if f.endswith('csv')]

log = True
for coin in files:
    data_mongo = pd.DataFrame(list(db[coin].find()))
    data_mongo['date'] = pd.to_datetime(data_mongo['date'])
    data_mongo = data_mongo.sort_values(by='date', ascending=False)
    data_new = get_new_data(data_mongo)
    upload_data_to_mongo(client, data_new, coin, log)
