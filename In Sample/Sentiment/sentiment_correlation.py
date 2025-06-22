from multiprocessing import Pool
import backtrader as bt
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import pearsonr, spearmanr, kendalltau
from statsmodels.tsa.stattools import grangercausalitytests, adfuller
import warnings
from all.strategy import SentimentIndicator as a
from news.strategy import SentimentIndicator as n
from reddit.strategy import SentimentIndicator as r
from reddit_twitter.strategy import SentimentIndicator as rt
from twitter.strategy import SentimentIndicator as t
from news_twitter.strategy import SentimentIndicator as nt
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
        self.all = a(ticker=ticker_name, crypto=self.p.cryptoname, k=self.p.k, reddit_folders=self.p.reddit_folders, double_dot=False)
        self.news = n(ticker=ticker_name, crypto=self.p.cryptoname, k=1, reddit_folders=self.p.reddit_folders, double_dot=False)
        self.reddit = r(ticker=ticker_name, crypto=self.p.cryptoname, k=self.p.k, reddit_folders=self.p.reddit_folders, double_dot=False)
        self.reddit_twitter = rt(ticker=ticker_name, crypto=self.p.cryptoname, k=self.p.k, reddit_folders=self.p.reddit_folders, double_dot=False)
        self.twitter = t(ticker=ticker_name, crypto=self.p.cryptoname, k=self.p.k, reddit_folders=self.p.reddit_folders, double_dot=False)
        self.news_twitter = nt(ticker=ticker_name, crypto=self.p.cryptoname, k=self.p.k, reddit_folders=self.p.reddit_folders, double_dot=False)

        self.sentiment_a = []
        self.sentiment_n = []
        self.sentiment_r = []
        self.sentiment_rt = []
        self.sentiment_t = []
        self.sentiment_nt = []
        self.prices = []
        self.dates = []

    def next(self):

        # Calculate returns
        self.prices.append((self.data.close[0] /self.data.close[-1])-1)
       
        self.dates.append(self.data.datetime.datetime(0))
        self.sentiment_a.append(self.all.sentiment[0])
        self.sentiment_n.append(self.news.sentiment[0])
        self.sentiment_r.append(self.reddit.sentiment[0])
        self.sentiment_rt.append(self.reddit_twitter.sentiment[0])
        self.sentiment_t.append(self.twitter.sentiment[0])
        self.sentiment_nt.append(self.news_twitter.sentiment[0])


    def stop(self):
        sentiment_series_a = pd.Series(self.sentiment_a).dropna().reset_index(drop=True)
        sentiment_series_n = pd.Series(self.sentiment_n).dropna().reset_index(drop=True)
        sentiment_series_r = pd.Series(self.sentiment_r).dropna().reset_index(drop=True)
        sentiment_series_rt = pd.Series(self.sentiment_rt).dropna().reset_index(drop=True)
        sentiment_series_t = pd.Series(self.sentiment_t).dropna().reset_index(drop=True)
        sentiment_series_nt = pd.Series(self.sentiment_nt).dropna().reset_index(drop=True)
        price_series = pd.Series(self.prices).dropna().reset_index(drop=True)

        result = adfuller(sentiment_series_a)
        if result[1] > 0.05:
            exit("All sentiment series is not stationary, please check the data.")
        
        result = adfuller(sentiment_series_n)
        if result[1] > 0.05:
            exit("News sentiment series is not stationary, please check the data.")
        
        result = adfuller(sentiment_series_r)
        if result[1] > 0.05:
            exit("Reddit sentiment series is not stationary, please check the data.")
        
        result = adfuller(sentiment_series_rt)
        if result[1] > 0.05:
            exit("Reddit+Twitter sentiment series is not stationary, please check the data.")
        
        result = adfuller(sentiment_series_t)
        if result[1] > 0.05:
            exit("Twitter sentiment series is not stationary, please check the data.")

        result = adfuller(sentiment_series_nt)
        if result[1] > 0.05:
            exit("News+Twitter sentiment series is not stationary, please check the data.")

        result = adfuller(price_series)
        if result[1] > 0.05:
            exit("Price series is not stationary, please check the data.")

        min_len = min(len(price_series), 
                      len(sentiment_series_a), len(sentiment_series_n),
                      len(sentiment_series_r), len(sentiment_series_rt),
                      len(sentiment_series_t), len(sentiment_series_nt))
        
        sentiment_series_a = sentiment_series_a[:min_len]
        sentiment_series_n = sentiment_series_n[:min_len]
        sentiment_series_r = sentiment_series_r[:min_len]
        sentiment_series_rt = sentiment_series_rt[:min_len]
        sentiment_series_t = sentiment_series_t[:min_len]
        sentiment_series_nt = sentiment_series_nt[:min_len]

        price_series = price_series[:min_len]

        # Save CSV with sentiment data and dates
        sentiment_df = pd.DataFrame({
            'Date': self.dates[:min_len],
            'Sentiment_All': self.sentiment_a[:min_len],
            'Sentiment_News': self.sentiment_n[:min_len],
            'Sentiment_Reddit': self.sentiment_r[:min_len],
            'Sentiment_RedditTwitter': self.sentiment_rt[:min_len],
            'Sentiment_Twitter': self.sentiment_t[:min_len],
            'Sentiment_NewsTwitter': self.sentiment_nt[:min_len],
            'Price': price_series
        })

        sentiment_df.to_csv(f'sentiment cache/{self.p.ticker}_{self.p.hours}_sentiment.csv', index=False)

        # Compute lagged correlations for all sentiment sources
        lags = range(-24, 25)

        if self.p.hours == '4h':
            lags = range(-6, 7)

        lagged_pearson_a = []
        lagged_spearman_a = []
        lagged_kendall_a = []
        lagged_pearson_n = []
        lagged_spearman_n = []
        lagged_kendall_n = []
        lagged_pearson_r = []
        lagged_spearman_r = []
        lagged_kendall_r = []
        lagged_pearson_rt = []
        lagged_spearman_rt = []
        lagged_kendall_rt = []
        lagged_pearson_t = []
        lagged_spearman_t = []
        lagged_kendall_t = []
        lagged_pearson_nt = []
        lagged_spearman_nt = []
        lagged_kendall_nt = []
        
        for lag in lags:
            if lag > 0:
                x_a = sentiment_series_a[:-lag]
                x_n = sentiment_series_n[:-lag]
                x_r = sentiment_series_r[:-lag]
                x_rt = sentiment_series_rt[:-lag]
                x_t = sentiment_series_t[:-lag]
                x_nt = sentiment_series_nt[:-lag]
                y = price_series[lag:]
            elif lag < 0:
                x_a = sentiment_series_a[-lag:]
                x_n = sentiment_series_n[-lag:]
                x_r = sentiment_series_r[-lag:]
                x_rt = sentiment_series_rt[-lag:]
                x_t = sentiment_series_t[-lag:]
                x_nt = sentiment_series_nt[-lag:]
                y = price_series[:lag]
            else:
                x_a = sentiment_series_a
                x_n = sentiment_series_n
                x_r = sentiment_series_r
                x_rt = sentiment_series_rt
                x_t = sentiment_series_t
                x_nt = sentiment_series_nt
                y = price_series

            if len(x_a) < 2 or len(y) < 2:
                lagged_pearson_a.append(np.nan)
                lagged_spearman_a.append(np.nan)
                lagged_kendall_a.append(np.nan)
                

            if len(x_n) < 2 or len(y) < 2:
                lagged_pearson_n.append(np.nan)
                lagged_spearman_n.append(np.nan)
                lagged_kendall_n.append(np.nan)

            if len(x_r) < 2 or len(y) < 2:
                lagged_pearson_r.append(np.nan)
                lagged_spearman_r.append(np.nan)
                lagged_kendall_r.append(np.nan)
            
            if len(x_rt) < 2 or len(y) < 2:
                lagged_pearson_rt.append(np.nan)
                lagged_spearman_rt.append(np.nan)
                lagged_kendall_rt.append(np.nan)
            
            if len(x_nt) < 2 or len(y) < 2:
                lagged_pearson_nt.append(np.nan)
                lagged_spearman_nt.append(np.nan)
                lagged_kendall_nt.append(np.nan)
            
            if len(x_t) < 2 or len(y) < 2:
                lagged_pearson_t.append(np.nan)
                lagged_spearman_t.append(np.nan)
                lagged_kendall_t.append(np.nan)
                continue

            # Calculate correlations
            try:
                p_corr_a = pearsonr(x_a, y)[0]
                s_corr_a = spearmanr(x_a, y)[0]
                k_corr_a = kendalltau(x_a, y)[0]
            except Exception:
                p_corr_a = s_corr_a = k_corr_a = np.nan
            
            try:
                p_corr_n = pearsonr(x_n, y)[0]
                s_corr_n = spearmanr(x_n, y)[0]
                k_corr_n = kendalltau(x_n, y)[0]
            except Exception:
                p_corr_n = s_corr_n = k_corr_n = np.nan
            
            try:
                p_corr_r = pearsonr(x_r, y)[0]
                s_corr_r = spearmanr(x_r, y)[0]
                k_corr_r = kendalltau(x_r, y)[0]
            except Exception:
                p_corr_r = s_corr_r = k_corr_r = np.nan
            
            try:
                p_corr_rt = pearsonr(x_rt, y)[0]
                s_corr_rt = spearmanr(x_rt, y)[0]
                k_corr_rt = kendalltau(x_rt, y)[0]
            except Exception:
                p_corr_rt = s_corr_rt = k_corr_rt = np.nan
            
            try:
                p_corr_t = pearsonr(x_t, y)[0]
                s_corr_t = spearmanr(x_t, y)[0]
                k_corr_t = kendalltau(x_t, y)[0]
            except Exception:
                p_corr_t = s_corr_t = k_corr_t = np.nan
            
            try:
                p_corr_nt = pearsonr(x_nt, y)[0]
                s_corr_nt = spearmanr(x_nt, y)[0]
                k_corr_nt = kendalltau(x_nt, y)[0]
            except Exception:
                p_corr_nt = s_corr_nt = k_corr_nt = np.nan
            
            # Append results
            lagged_pearson_a.append(p_corr_a)
            lagged_spearman_a.append(s_corr_a)
            lagged_kendall_a.append(k_corr_a)
            lagged_pearson_n.append(p_corr_n)
            lagged_spearman_n.append(s_corr_n)
            lagged_kendall_n.append(k_corr_n)
            lagged_pearson_r.append(p_corr_r)
            lagged_spearman_r.append(s_corr_r)
            lagged_kendall_r.append(k_corr_r)
            lagged_pearson_rt.append(p_corr_rt)
            lagged_spearman_rt.append(s_corr_rt)
            lagged_kendall_rt.append(k_corr_rt)
            lagged_pearson_t.append(p_corr_t)
            lagged_spearman_t.append(s_corr_t)
            lagged_kendall_t.append(k_corr_t)
            lagged_pearson_nt.append(p_corr_nt)
            lagged_spearman_nt.append(s_corr_nt)
            lagged_kendall_nt.append(k_corr_nt)

        # Plot Pearson correlation
        plt.figure(figsize=(10,5))
        plt.plot(lags, lagged_pearson_a, marker='o', linestyle='-', label='All Sentiment')
        plt.plot(lags, lagged_pearson_n, marker='o', linestyle='-', label='News Sentiment', color='green')
        plt.plot(lags, lagged_pearson_r, marker='o', linestyle='-', label='Reddit Sentiment', color='red')
        plt.plot(lags, lagged_pearson_rt, marker='o', linestyle='-', label='Reddit+Twitter Sentiment', color='purple')
        plt.plot(lags, lagged_pearson_t, marker='o', linestyle='-', label='Twitter Sentiment', color='blue')
        plt.plot(lags, lagged_pearson_nt, marker='o', linestyle='-', label='News+Twitter Sentiment', color='orange')
        plt.legend()
        plt.axhline(0, color='black', lw=0.5, linestyle='--')
        plt.title('Lagged Pearson Correlation')
        plt.xlabel('Lag (positive lag = sentiment leads price)')
        plt.ylabel('Pearson Correlation')
        plt.grid(True)
        plt.xticks(range(-24, 25, 2))
        plt.savefig(f'correlation/{self.p.ticker}_{self.p.hours}_pearson.png', bbox_inches='tight')
        plt.close()

        # Plot Spearman correlation
        plt.figure(figsize=(10,5))
        plt.plot(lags, lagged_spearman_a, marker='o', linestyle='-', color='orange', label='All Sentiment')
        plt.plot(lags, lagged_spearman_n, marker='o', linestyle='-', color='green', label='News Sentiment')
        plt.plot(lags, lagged_spearman_r, marker='o', linestyle='-', color='red', label='Reddit Sentiment')
        plt.plot(lags, lagged_spearman_rt, marker='o', linestyle='-', color='purple', label='Reddit+Twitter Sentiment')
        plt.plot(lags, lagged_spearman_t, marker='o', linestyle='-', color='blue', label='Twitter Sentiment')
        plt.plot(lags, lagged_spearman_nt, marker='o', linestyle='-', color='orange', label='News+Twitter Sentiment')
        plt.legend()
        plt.axhline(0, color='black', lw=0.5, linestyle='--')
        plt.title('Lagged Spearman Correlation')
        plt.xlabel('Lag (positive lag = sentiment leads price)')
        plt.ylabel('Spearman Correlation')
        plt.grid(True)
        plt.xticks(range(-24, 25, 2))
        plt.savefig(f'correlation/{self.p.ticker}_{self.p.hours}_spearman.png', bbox_inches='tight')
        plt.close()

        # Plot Kendall correlation
        plt.figure(figsize=(10,5))
        plt.plot(lags, lagged_kendall_a, marker='o', linestyle='-', color='purple', label='All Sentiment')
        plt.plot(lags, lagged_kendall_n, marker='o', linestyle='-', color='green', label='News Sentiment')
        plt.plot(lags, lagged_kendall_r, marker='o', linestyle='-', color='red', label='Reddit Sentiment')
        plt.plot(lags, lagged_kendall_rt, marker='o', linestyle='-', color='orange', label='Reddit+Twitter Sentiment')
        plt.plot(lags, lagged_kendall_t, marker='o', linestyle='-', color='blue', label='Twitter Sentiment')
        plt.plot(lags, lagged_kendall_nt, marker='o', linestyle='-', color='cyan', label='News+Twitter Sentiment')
        plt.legend()
        plt.axhline(0, color='black', lw=0.5, linestyle='--')
        plt.title('Lagged Kendall Correlation')
        plt.xlabel('Lag (positive lag = sentiment leads price)')
        plt.ylabel('Kendall Correlation')
        plt.grid(True)
        plt.xticks(range(-24, 25, 2))
        plt.savefig(f'correlation/{self.p.ticker}_{self.p.hours}_kendall.png', bbox_inches='tight')
        plt.close()

        # Granger causality test and plot p-values
        maxlag = 24

        if self.p.hours == '4h':
            maxlag = 6

        # Sentiment Granger Causes Price
        df_gc_a = pd.DataFrame({'price': price_series, 'sentiment': sentiment_series_a})
        df_gc_n = pd.DataFrame({'price': price_series, 'sentiment': sentiment_series_n})
        df_gc_r = pd.DataFrame({'price': price_series, 'sentiment': sentiment_series_r})
        df_gc_rt = pd.DataFrame({'price': price_series, 'sentiment': sentiment_series_rt})
        df_gc_t = pd.DataFrame({'price': price_series, 'sentiment': sentiment_series_t})
        df_gc_nt = pd.DataFrame({'price': price_series, 'sentiment': sentiment_series_nt})
       
        gc_results_a = grangercausalitytests(df_gc_a[['price', 'sentiment']], maxlag=maxlag, verbose=False)
        gc_results_n = grangercausalitytests(df_gc_n[['price', 'sentiment']], maxlag=maxlag, verbose=False)
        gc_results_r = grangercausalitytests(df_gc_r[['price', 'sentiment']], maxlag=maxlag, verbose=False)
        gc_results_rt = grangercausalitytests(df_gc_rt[['price', 'sentiment']], maxlag=maxlag, verbose=False)
        gc_results_t = grangercausalitytests(df_gc_t[['price', 'sentiment']], maxlag=maxlag, verbose=False)
        gc_results_nt = grangercausalitytests(df_gc_nt[['price', 'sentiment']], maxlag=maxlag, verbose=False)

        p_values_a = []
        lags_gc_a = []
        p_values_n = []
        lags_gc_n = []
        p_values_r = []
        lags_gc_r = []
        p_values_rt = []
        lags_gc_rt = []
        p_values_t = []
        lags_gc_t = []
        p_values_nt = []
        lags_gc_nt = []
        
        for lag in range(1, maxlag+1):
            test_res = gc_results_a[lag][0]['ssr_ftest']  # (F-stat, p-value, df1, df2)
            p_val = test_res[1]
            p_values_a.append(p_val)
            lags_gc_a.append(lag)

            test_res = gc_results_n[lag][0]['ssr_ftest']  # (F-stat, p-value, df1, df2)
            p_val = test_res[1]
            p_values_n.append(p_val)
            lags_gc_n.append(lag)

            test_res = gc_results_r[lag][0]['ssr_ftest']  # (F-stat, p-value, df1, df2)
            p_val = test_res[1]
            p_values_r.append(p_val)
            lags_gc_r.append(lag)

            test_res = gc_results_rt[lag][0]['ssr_ftest']  # (F-stat, p-value, df1, df2)
            p_val = test_res[1]
            p_values_rt.append(p_val)
            lags_gc_rt.append(lag)

            test_res = gc_results_t[lag][0]['ssr_ftest']  # (F-stat, p-value, df1, df2)
            p_val = test_res[1]
            p_values_t.append(p_val)
            lags_gc_t.append(lag)

            test_res = gc_results_nt[lag][0]['ssr_ftest']  # (F-stat, p-value, df1, df2)
            p_val = test_res[1]
            p_values_nt.append(p_val)
            lags_gc_nt.append(lag)
       
        plt.figure(figsize=(10,5))
        plt.plot(lags_gc_a, p_values_a, marker='o', linestyle='-', label='All Sentiment')
        plt.plot(lags_gc_n, p_values_n, marker='o', linestyle='-', label='News Sentiment', color='green')
        plt.plot(lags_gc_r, p_values_r, marker='o', linestyle='-', label='Reddit Sentiment', color='red')
        plt.plot(lags_gc_rt, p_values_rt, marker='o', linestyle='-', label='Reddit+Twitter Sentiment', color='purple')
        plt.plot(lags_gc_t, p_values_t, marker='o', linestyle='-', label='Twitter Sentiment', color='blue')
        plt.plot(lags_gc_nt, p_values_nt, marker='o', linestyle='-', label='News+Twitter Sentiment', color='orange')
        plt.axhline(0.05, color='red', linestyle='dotted', label='Threshold = 0.05')
        plt.title('Granger Causality p-values by Lag')
        plt.xlabel('Lag')
        plt.ylabel('p-value')
        plt.legend()
        plt.grid(True)
        plt.xticks(lags_gc_a)
        plt.savefig(f'correlation/{self.p.ticker}_{self.p.hours}_s_granger_p.png', bbox_inches='tight')
        plt.close()

        granger_p_aligned_a = []
        granger_p_aligned_n = []
        granger_p_aligned_r = []
        granger_p_aligned_rt = []
        granger_p_aligned_t = []
        granger_p_aligned_nt = []

        # Align Granger p-values with lags
        for lag in lags:
            if 1 <= lag <= maxlag:
                granger_p_aligned_a.append(p_values_a[lag-1])
                granger_p_aligned_n.append(p_values_n[lag-1])
                granger_p_aligned_r.append(p_values_r[lag-1])
                granger_p_aligned_rt.append(p_values_rt[lag-1])
                granger_p_aligned_t.append(p_values_t[lag-1])
                granger_p_aligned_nt.append(p_values_nt[lag-1])
            else:
                granger_p_aligned_a.append(np.nan)
                granger_p_aligned_n.append(np.nan)
                granger_p_aligned_r.append(np.nan)
                granger_p_aligned_rt.append(np.nan)
                granger_p_aligned_t.append(np.nan)
                granger_p_aligned_nt.append(np.nan)

        # Price Granger Causes Sentiment
        df_gc_a_price = pd.DataFrame({'sentiment': sentiment_series_a, 'price': price_series})
        df_gc_n_price = pd.DataFrame({'sentiment': sentiment_series_n, 'price': price_series})
        df_gc_r_price = pd.DataFrame({'sentiment': sentiment_series_r, 'price': price_series})
        df_gc_rt_price = pd.DataFrame({'sentiment': sentiment_series_rt, 'price': price_series})
        df_gc_t_price = pd.DataFrame({'sentiment': sentiment_series_t, 'price': price_series})
        df_gc_nt_price = pd.DataFrame({'sentiment': sentiment_series_nt, 'price': price_series})

        gc_results_a_price = grangercausalitytests(df_gc_a_price[['sentiment', 'price']], maxlag=maxlag, verbose=False)
        gc_results_n_price = grangercausalitytests(df_gc_n_price[['sentiment', 'price']], maxlag=maxlag, verbose=False)
        gc_results_r_price = grangercausalitytests(df_gc_r_price[['sentiment', 'price']], maxlag=maxlag, verbose=False)
        gc_results_rt_price = grangercausalitytests(df_gc_rt_price[['sentiment', 'price']], maxlag=maxlag, verbose=False)
        gc_results_t_price = grangercausalitytests(df_gc_t_price[['sentiment', 'price']], maxlag=maxlag, verbose=False)
        gc_results_nt_price = grangercausalitytests(df_gc_nt_price[['sentiment', 'price']], maxlag=maxlag, verbose=False)

        p_values_a_price = []
        lags_gc_a_price = []
        p_values_n_price = []
        lags_gc_n_price = []
        p_values_r_price = []
        lags_gc_r_price = []
        p_values_rt_price = []
        lags_gc_rt_price = []
        p_values_t_price = []
        lags_gc_t_price = []
        p_values_nt_price = []
        lags_gc_nt_price = []

        for lag in range(1, maxlag+1):
            test_res = gc_results_a_price[lag][0]['ssr_ftest']
            p_val = test_res[1]
            p_values_a_price.append(p_val)
            lags_gc_a_price.append(lag)

            test_res = gc_results_n_price[lag][0]['ssr_ftest']
            p_val = test_res[1]
            p_values_n_price.append(p_val)
            lags_gc_n_price.append(lag)

            test_res = gc_results_r_price[lag][0]['ssr_ftest']
            p_val = test_res[1]
            p_values_r_price.append(p_val)
            lags_gc_r_price.append(lag)

            test_res = gc_results_rt_price[lag][0]['ssr_ftest']
            p_val = test_res[1]
            p_values_rt_price.append(p_val)
            lags_gc_rt_price.append(lag)

            test_res = gc_results_t_price[lag][0]['ssr_ftest']
            p_val = test_res[1]
            p_values_t_price.append(p_val)
            lags_gc_t_price.append(lag)

            test_res = gc_results_nt_price[lag][0]['ssr_ftest']
            p_val = test_res[1]
            p_values_nt_price.append(p_val)
            lags_gc_nt_price.append(lag)
        
        plt.figure(figsize=(10,5))
        plt.plot(lags_gc_a_price, p_values_a_price, marker='o', linestyle='-', label='All Sentiment')
        plt.plot(lags_gc_n_price, p_values_n_price, marker='o', linestyle='-', label='News Sentiment', color='green')
        plt.plot(lags_gc_r_price, p_values_r_price, marker='o', linestyle='-', label='Reddit Sentiment', color='red')
        plt.plot(lags_gc_rt_price, p_values_rt_price, marker='o', linestyle='-', label='Reddit+Twitter Sentiment', color='purple')
        plt.plot(lags_gc_t_price, p_values_t_price, marker='o', linestyle='-', label='Twitter Sentiment', color='blue')
        plt.plot(lags_gc_nt_price, p_values_nt_price, marker='o', linestyle='-', label='News+Twitter Sentiment', color='orange')
        plt.axhline(0.05, color='red', linestyle='dotted', label='Threshold = 0.05')
        plt.title('Granger Causality p-values by Lag')
        plt.xlabel('Lag')
        plt.ylabel('p-value')
        plt.legend()
        plt.grid(True)
        plt.xticks(lags_gc_a_price)
        plt.savefig(f'correlation/{self.p.ticker}_{self.p.hours}_p_granger_s.png', bbox_inches='tight')
        plt.close()

        # Align Granger p-values with lags
        granger_p_aligned_a_price = []
        granger_p_aligned_n_price = []
        granger_p_aligned_r_price = []
        granger_p_aligned_rt_price = []
        granger_p_aligned_t_price = []
        granger_p_aligned_nt_price = []

        for lag in lags:
            if 1 <= lag <= maxlag:
                granger_p_aligned_a_price.append(p_values_a_price[lag-1])
                granger_p_aligned_n_price.append(p_values_n_price[lag-1])
                granger_p_aligned_r_price.append(p_values_r_price[lag-1])
                granger_p_aligned_rt_price.append(p_values_rt_price[lag-1])
                granger_p_aligned_t_price.append(p_values_t_price[lag-1])
                granger_p_aligned_nt_price.append(p_values_nt_price[lag-1])
            else:
                granger_p_aligned_a_price.append(np.nan)
                granger_p_aligned_n_price.append(np.nan)
                granger_p_aligned_r_price.append(np.nan)
                granger_p_aligned_rt_price.append(np.nan)
                granger_p_aligned_t_price.append(np.nan)
                granger_p_aligned_nt_price.append(np.nan)

        # Save results to CSV
        results_df = pd.DataFrame({
            'Lag': lags,
            'Pearson_All': lagged_pearson_a,
            'Spearman_All': lagged_spearman_a,
            'Kendall_All': lagged_kendall_a,
            'Pearson_News': lagged_pearson_n,
            'Spearman_News': lagged_spearman_n,
            'Kendall_News': lagged_kendall_n,
            'Pearson_Reddit': lagged_pearson_r,
            'Spearman_Reddit': lagged_spearman_r,
            'Kendall_Reddit': lagged_kendall_r,
            'Pearson_Reddit_Twitter': lagged_pearson_rt,
            'Spearman_Reddit_Twitter': lagged_spearman_rt,
            'Kendall_Reddit_Twitter': lagged_kendall_rt,
            'Pearson_Twitter': lagged_pearson_t,
            'Spearman_Twitter': lagged_spearman_t,
            'Kendall_Twitter': lagged_kendall_t,
            'Pearson_News_Twitter': lagged_pearson_nt,
            'Spearman_News_Twitter': lagged_spearman_nt,
            'Kendall_News_Twitter': lagged_kendall_nt,
            'Granger_Sentiment_All_Price': granger_p_aligned_a,
            'Granger_Sentiment_News_Price': granger_p_aligned_n,
            'Granger_Sentiment_Reddit_Price': granger_p_aligned_r,
            'Granger_Sentiment_Reddit_Twitter_Price': granger_p_aligned_rt,
            'Granger_Sentiment_Twitter_Price': granger_p_aligned_t,
            'Granger_Sentiment_News_Twitter_Price': granger_p_aligned_nt,
            'Granger_Price_All_Sentiment': granger_p_aligned_a_price,
            'Granger_Price_News_Sentiment': granger_p_aligned_n_price,
            'Granger_Price_Reddit_Sentiment': granger_p_aligned_r_price,
            'Granger_Price_Reddit_Twitter_Sentiment': granger_p_aligned_rt_price,
            'Granger_Price_Twitter_Sentiment': granger_p_aligned_t_price,
            'Granger_Price_News_Twitter_Sentiment': granger_p_aligned_nt_price
        })
        

        results_df.to_csv(f'correlation/{self.p.ticker}_{self.p.hours}.csv', index=False)

# Load price data
def run_correlation(ticker, cryptoname, reddit_folders, hours):
    
    # Load price data
    data = pd.read_csv(f'../Data/{ticker}_{hours}.csv', parse_dates=True, index_col='timestamp')
    data_feed = bt.feeds.PandasData(dataname=data)

    # Backtrader engine
    cerebro = bt.Cerebro()
    cerebro.adddata(data_feed)
    cerebro.addstrategy(SentimentCorrelationStrategy, 
                        hours=hours,
                        reddit_folders=reddit_folders,
                        ticker=ticker,
                        cryptoname=cryptoname)
    cerebro.run()

tickers = ['ADAUSDT', 'BTCUSDT', 'DOGEUSDT', 'ETHUSDT', 'SOLUSDT', 'XMRUSDT', 'XRPUSDT']
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
times = ['1h', '4h']

if __name__ == "__main__":
    
    num_workers = 32
    with Pool(processes=num_workers) as pool:
        results = pool.starmap(run_correlation, [(ticker, crypto_names[ticker], reddit_folders[ticker], time) for ticker in tickers for time in times])
    
    print("Backtesting completed for all tickers and times.")
