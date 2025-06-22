# Algorithmic Cryptocurrency Trading

Trading a portfolio of cryptocurrencies using sentiment from X, reddit and news sources.

Access my report [here](https://github.com/vas-byte/Crypto-Algo-Trading/blob/main/Report/Report.pdf)

## Run Locally

Clone the project

```bash
  git clone https://github.cs.adelaide.edu.au/a1887068/CryptoProject
```

Go to the project directory

```bash
  cd CryptoProject
```

Install dependencies

```bash
  pip3 install -r requirements.txt
```



## Collecting Data

### OHCLV (Price Data)
To collect price data run
```python3 binance_data.py```

Note, you can change the following variables:
- start_str which is the starting date in YYYY-MM-DD
- end_str which is the ending date in YYYY-MM-DD
- symbols_raw which is a string of market tickers separated by a space e.g. "ADA/USDT BTC/USDT DOGE/USDT"

Please note for the momentum strategies, we use data from Coinmarketcap since binance does not provide market cap data. We downloaded a daily CSV of OHCLV data which includes market cap. To use the data with the strategy code, execute ```python3 clean.py``` in either the ```\In Sample``` or ```\Out of sample``` folder

##

### Sentiment Data
To collect this data register for Apify at https://console.apify.com/

For  in-sample scraping, run ```python3 apify_in_sample.py```

Note you change the following variables:
- TOKEN which is your API key for Apify
- CRYPTO_TICKERS which is a list of cryptocurrency tickers
- CRYTP_NAMES which is a list of cryptocurrency names
- MIN_LIKES a list which filters posts based on the minnimum number of likes for a cryptocurrency
- MIN_RETWEETS a list which filters posts based on the minnimum number of retweets for a cryptocurrency
- MIN_REPLIES a list which filters posts based on the minnimum number of replies for a post about a cryptocurrency
- START_MONTH in YYYY-MM
- END_MONTH in YYYY-MM

For  out-of-sample scraping, run ```python3 apify_out_sample.py```

Note you change the following variables:
- TOKEN which is your API key for Apify
- CRYPTO_TICKERS which is a list of cryptocurrency tickers
- CRYTP_NAMES which is a list of cryptocurrency names
- MIN_LIKES a list which filters posts based on the minnimum number of likes for a cryptocurrency
- START_MONTH in YYYY-MM
- END_MONTH in YYYY-MM

## Preprocessing Data

### Twitter (X)
Make sure a CSV file with at least timestamp and text are in the in-sample or out-of-sample Data folder

Then run
```python3 twitter_preprocess.py```

Followed by
```python3 twitter_deepseek.py```

Both scripts have variables that need to be set:
- API_KEY: API key for deepseek
- INSAMPLE: True/False, is the data located in the in-sample or out-of-sample folder
##

### Reddit
Make sure a CSV file with at least timestamp and text are in the in-sample or out-of-sample Data folder

Then run ```python3 reddit_deepseek.py```

Note the following variables may need adjustment
- API_KEY: API Key for deepseek
- INSAMPLE: True/False, is the data located in the in-sample or out-of-sample folder
##

### News
Make sure a CSV file with text and timestamps are located in the in-sample folder.

Then run ```python3 news_deepseek.py```

Make sure to update ```API_KEY``` variable


## In-sample back-testing

Our in-sample back-testing folder contains the code used to develop, optimize and test the sentiment strategy.

Each folder represents a strategy, these include 

- Buy and Hold
- Cross Sectional Momentum
- Time Series Momentum
- Multi-indicator Hierarchical Strategy (MIHS) - Technical Analysis
- Multi-indicator Hierarchical Constrained Strategy (MIHCS) - Technical Analysis

To run a strategy, navigate to that folder and simply run the following 
```python3 base.py```
##

### Sentiment Strategy
Navigate to the sentiment folder

```cd "In Sample/Sentiment"```

Run the strategy
```python3 base.py```

However, the strategy has a variety of parameters in base.py
- macd_settings: tuple of (fast, slow, signal)
- MA_period: Moving average period length
- atr: atr MA_period
- obv_periods: number of periods for the OBV slope
- allow_shorting: True/False, can the strategy execute short selling?
- sentiment_thresholds_positive: positive sentiment score threshold
- sentiment_thresholds_negative: negative sentiment score threshold
- atr_means: lookback period to get average atr
- reddit_source: True/False, include/exclude reddit sentiment
- news_source: True/False, include/exclude news sentiment
- X_source: True/False, include/exclude X sentiment

##

To fine-tune the strategy, first run

```python3 sentiment_correlation.py```

This file caches the sentiment score for each method making the optimization process quicker. It also plots Spearman, Pearson, Kendall and Granger Causality in the ```/correlation``` folder.

Then select the best strategy with

```python3 strategy_search.py```

##

To produce the parameter matrix as shown below:

![](https://github.cs.adelaide.edu.au/a1887068/CryptoProject/blob/main/In%20Sample/Sentiment/param_vs_return_sharpe_combined.png)

run ```python3 parameter_matrix.py```


## Out-of-sample back-testing

Our out-of-sample folder contains
- Buy-and-hold
- Cross-Sectional Momentum
- MIHS
- MIHCS
- Our Sentiment Strategy
- Sentiment Benchmark

Note ```base.py``` is still the file used to execute the strategies

##

### MIHS and MIHCS
To adjust the signal parameters of MIHS or MIHCS go to ```MIHS.py``` or ```MIHCS.py``` in the corresponding strategy folders.

change the ```signal_period``` parameter under ```params```

##

### Momentum

To adjust the look-back and holding periods, or portfolio weighting, go to ```TimeSeries.py``` or ```CrossSectional.py``` and change ```lookback```, ```holding``` or ```portfolio``` under params

Note ```portfolio``` takes the values 

- ```market_cap``` which weights position sizes based on market cap
- ```volume``` which weights the position sizes based on volume
- ```equal``` which equally weights the position sizes in the portfolio

You can also cap position sizes to 5% by setting ```capped_weights``` to True

##

### Sentiment
For the method used in our paper, there are no adjustments that need to be made.

Just execute ```python3 base.py```

##

### Sentiment (Benchmark)
For each cryptocurrency do the following process

Get your X posts dataset (timestamp and text)

We used our in-sample data to fine-tune CRYPTOBERT. Note, the name of this file must be ```twitter_train.csv``` 

We used our in-sample price data to support training. Again the program expects the name ```{TICKER}USDT_1d_2022```

We then ran the notebook ```train_CA.ipynb```

Alternatively, you can download our finetuned models [here](https://universityofadelaide.box.com/s/hlkohoqgcp2sgckncepkv7rc6uaad3yf)

We then prepared our prediction data.
- Make sure to name your twitter file ```twitter_pred.csv```

- Make sure that your price file has 6 months of data before the testing period. For us this was 2023 data, we called our file ```{TICKER}USDT_1d_2023```

After this you can execute ```predict_CA_lag_maj.ipynb``` and  ```predict_CA_lag_mean.ipynb``` to back-test the strategies on each coin

Once completed for all coins (we did ADA, BTC, DOGE, SOL, XRP, ETH), you can execute 

- ```python3 all_maj_tbl_lag.py``` to back-test the portfolio using majority signal prediction (of individual posts)

- ```python3 all_mean_tbl_lag.py``` to back-test the portfolio using mean signal prediction (of individual posts)

- ```python3 ablation.py``` to back-test our second ablation study



## Visualisations

In the project root directory

```python3 social_sentiment.py``` to produce the following visual showing the difference in enagagement metrics over the back-testing periods:
![](https://github.cs.adelaide.edu.au/a1887068/CryptoProject/assets/4547/229fa15b-730c-451e-91ff-8707242a5f7c)

```python3 "In Sample"/Sentiment/xmr_vis.py``` to show engagement metrics for XMR during the in-sample period, as shown below:

![](https://github.cs.adelaide.edu.au/a1887068/CryptoProject/blob/main/In%20Sample/Sentiment/xmr_visual.png)

```python3 "In Sample"/Sentiment/sentiment_correlation.py``` to plot Granger Causality, Pearson and Spearman coefficients, as shown below:

![](https://github.cs.adelaide.edu.au/a1887068/CryptoProject/blob/main/In%20Sample/Sentiment/correlation/ADA_correlation_visualization.png)

```python3 "Out of sample"/Sentiment/correlation.py``` to plot Granger Causality, as shown below:

![](https://github.cs.adelaide.edu.au/a1887068/CryptoProject/assets/4547/e8761535-e5a0-48b8-a409-2ebf07ea9b80)


## Live Trading

Change Directories to the Live Strategy folder

in ```strategy.py``` specify the following:
- API_KEY: Binance API Key
- API_SECRET: Binance API secret
- SYMBOLS: Tickers of markets to trade
- COINNAMES: full names of the coins (dictionary key=SYMBOL value=COINNAME)
- DEEPSEEK_API_KEY: API key for deepseek
- LIVE: True/False, False for dry-run
- TRAILING_STOP_PCT: set trailing stop percentage
- TRADE_PCT: percentage of portfolio to risk on a position
- SLIPPAGE: determinins percentage above/below market price on orders

In ```sentiment.py``` provide credentials for 3 twitter accounts and residential proxies (if you have any!!)

update
- self.username, self.username2, self.username3 - user names of X accounts
- self.email, self.email2, self.email3 - emails of X accounts
- self.password, self.password2, self.password3 - passwords of X accounts
