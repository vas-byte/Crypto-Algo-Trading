from multiprocessing import Pool
import backtrader as bt
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import pearsonr, spearmanr, kendalltau
from statsmodels.tsa.stattools import grangercausalitytests, adfuller
import warnings
from strategy import SentimentIndicator
import math

# Strategy to collect data
class SentimentCorrelationStrategy(bt.Strategy):
    params = (
        ('hours', ''),
        ('reddit_folders', []),
        ('ticker', ''),
        ('cryptoname', ''),
        ('k', 0.000001)
    )

    def __init__(self):
        ticker_name = self.p.ticker.replace('USDT', '')
        self.twitter = SentimentIndicator(ticker=ticker_name, crypto=self.p.cryptoname, k=self.p.k)
        self.sentiment_t = []
        self.prices = []
        self.dates = []

    def next(self):
        self.prices.append((self.data.close[0] / self.data.close[-1]) - 1)
        self.dates.append(self.data.datetime.datetime(0))
        self.sentiment_t.append(self.twitter.sentiment[0])

    def stop(self):
        sentiment_series_t = pd.Series(self.sentiment_t).dropna().reset_index(drop=True)
        price_series = pd.Series(self.prices).dropna().reset_index(drop=True)

        result = adfuller(sentiment_series_t)
        if result[1] > 0.05:
            exit("Twitter sentiment series is not stationary, please check the data.")

        result = adfuller(price_series)
        if result[1] > 0.05:
            exit("Price series is not stationary, please check the data.")

        min_len = min(len(price_series), len(sentiment_series_t))
        sentiment_series_t = sentiment_series_t[:min_len]
        price_series = price_series[:min_len]

        lags = range(-24, 25)
        lagged_pearson_t, lagged_spearman_t, lagged_kendall_t = [], [], []

        for lag in lags:
            if lag > 0:
                x_t = sentiment_series_t[:-lag]
                y = price_series[lag:]
            elif lag < 0:
                x_t = sentiment_series_t[-lag:]
                y = price_series[:lag]
            else:
                x_t = sentiment_series_t
                y = price_series

            if len(x_t) < 2 or len(y) < 2:
                lagged_pearson_t.append(np.nan)
                lagged_spearman_t.append(np.nan)
                lagged_kendall_t.append(np.nan)
                continue

            try:
                lagged_pearson_t.append(pearsonr(x_t, y)[0])
                lagged_spearman_t.append(spearmanr(x_t, y)[0])
                lagged_kendall_t.append(kendalltau(x_t, y)[0])
            except Exception:
                lagged_pearson_t.append(np.nan)
                lagged_spearman_t.append(np.nan)
                lagged_kendall_t.append(np.nan)

        # Granger Causality Test
        maxlag = 24

        df_gc_t = pd.DataFrame({'price': price_series, 'sentiment': sentiment_series_t})
        gc_results_t = grangercausalitytests(df_gc_t[['price', 'sentiment']], maxlag=maxlag, verbose=False)
        p_values_t = [gc_results_t[lag][0]['ssr_ftest'][1] for lag in range(1, maxlag + 1)]
        lags_gc_t = list(range(1, maxlag + 1))

        df_gc_t_price = pd.DataFrame({'sentiment': sentiment_series_t, 'price': price_series})
        gc_results_t_price = grangercausalitytests(df_gc_t_price[['sentiment', 'price']], maxlag=maxlag, verbose=False)
        p_values_t_price = [gc_results_t_price[lag][0]['ssr_ftest'][1] for lag in range(1, maxlag + 1)]
        lags_gc_t_price = list(range(1, maxlag + 1))

        # Granger Causality Side-by-Side Plot
        fig, axs = plt.subplots(1, 2, figsize=(16, 6), sharey=True)

        axs[0].plot(lags_gc_t, p_values_t, marker='o', linestyle='-', color='blue', label='Sentiment → Price')
        axs[0].axhline(0.05, color='red', linestyle='dotted', label='p = 0.05')
        axs[0].set_title(f'{self.p.ticker} - Sentiment Granger Causes Returns')
        axs[0].set_xlabel('Lag')
        axs[0].set_ylabel('p-value')
        axs[0].grid(True)
        axs[0].legend()
        axs[0].set_xticks([lag for lag in lags_gc_t if lag % 2 == 0])  # Show only even lags

        axs[1].plot(lags_gc_t_price, p_values_t_price, marker='o', linestyle='-', color='green', label='Price → Sentiment')
        axs[1].axhline(0.05, color='red', linestyle='dotted', label='p = 0.05')
        axs[1].set_title(f'{self.p.ticker} - Returns Granger Cause Sentiment')
        axs[1].set_xlabel('Lag')
        axs[1].grid(True)
        axs[1].legend()
        axs[1].set_xticks([lag for lag in lags_gc_t_price if lag % 2 == 0])  # Show only even lags

        plt.tight_layout()
        plt.savefig(f'correlation/{self.p.ticker}_{self.p.hours}_granger_side_by_side.png', bbox_inches='tight')
        plt.close()

        # Save results
        granger_p_aligned_t = [p_values_t[lag - 1] if 1 <= lag <= maxlag else np.nan for lag in lags]
        granger_p_aligned_t_price = [p_values_t_price[lag - 1] if 1 <= lag <= maxlag else np.nan for lag in lags]

        results_df = pd.DataFrame({
            'Lag': lags,
            'Pearson_Twitter': lagged_pearson_t,
            'Spearman_Twitter': lagged_spearman_t,
            'Kendall_Twitter': lagged_kendall_t,
            'Granger_Sentiment_Twitter_Price': granger_p_aligned_t,
            'Granger_Price_Twitter_Sentiment': granger_p_aligned_t_price,
        })

        results_df.to_csv(f'correlation/{self.p.ticker}_{self.p.hours}.csv', index=False)


# Run the correlation analysis
def run_correlation(ticker, cryptoname, reddit_folders, hours):
    data = pd.read_csv(f'../Data/{ticker}_{hours}.csv', parse_dates=True, index_col='timestamp')
    data_feed = bt.feeds.PandasData(dataname=data)

    cerebro = bt.Cerebro()
    cerebro.adddata(data_feed)
    cerebro.addstrategy(SentimentCorrelationStrategy,
                        hours=hours,
                        reddit_folders=reddit_folders,
                        ticker=ticker,
                        cryptoname=cryptoname)
    cerebro.run()


# Parameters
tickers = ['ADAUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT', 'ETHUSDT', 'BTCUSDT']
crypto_names = {
    'ADAUSDT': 'Cardano',
    'BTCUSDT': 'Bitcoin',
    'DOGEUSDT': 'Dogecoin',
    'ETHUSDT': 'Ethereum',
    'SOLUSDT': 'Solana',
    'XMRUSDT': 'Monero',
    'XRPUSDT': 'Ripple'
}
reddit_folders = {
    'ADAUSDT': ['cardano'],
    'BTCUSDT': ['bitcoin', 'bitcoinmarkets', 'btc'],
    'DOGEUSDT': ['dogecoin'],
    'ETHUSDT': ['ethereum', 'ethtrader'],
    'SOLUSDT': ['solana'],
    'XMRUSDT': ['monero', 'xmrtrader'],
    'XRPUSDT': ['ripple', 'xrp']
}
times = ['1h']

# Parallel processing
if __name__ == "__main__":
    num_workers = 10
    with Pool(processes=num_workers) as pool:
        results = pool.starmap(run_correlation, [(ticker, crypto_names[ticker], reddit_folders[ticker], time)
                                                  for ticker in tickers for time in times])
    print("Backtesting completed for all tickers and times.")
