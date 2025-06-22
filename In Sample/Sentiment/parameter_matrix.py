import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import os


# Map last MACD number in filename to full MACD tuple
macd_map = {
    1: (12, 26, 9, 1),
    2: (8, 24, 9, 2),
    3: (5, 15, 9, 3)
}

sentiments = ['all', 'news', 'news_twitter', 'reddit', 'reddit_twitter', 'twitter']
base_path = './'  # Adjust if needed

all_results = []

for sentiment in sentiments:
    performance_path = os.path.join(base_path, sentiment, 'performance')
    if not os.path.exists(performance_path):
        print(f"Warning: Folder '{performance_path}' does not exist, skipping.")
        continue

    for file in os.listdir(performance_path):
        if file.endswith('.csv'):
            file_path = os.path.join(performance_path, file)
            try:
                fname = file.replace('_perf.csv', '')  # remove suffix
                parts = fname.split('_')
                if len(parts) < 8:
                    print(f"Filename {file} does not have expected 9 parts, skipping.")
                    continue

                # sentiment_positive = parts[0]
                # sentiment_negative = parts[1]

                macd_last_num = int(parts[0])
                macd_tuple = macd_map.get(macd_last_num, None)
                if macd_tuple is None:
                    print(f"Unknown MACD last number {macd_last_num} in file {file}")
                    continue

                MA_period = int(parts[1])
                atr_period = int(parts[2])
                obv_period = int(parts[3])
                shorting_str = parts[4]

                if "No" in shorting_str:
                    can_short = False
                elif "Yes" in shorting_str:
                    can_short = True
              
                ticker = parts[5]
                timeframe = parts[6]
                atr_mean = int(parts[7])

                df = pd.read_csv(file_path)
                
                # Add metadata columns
                df['sentiment'] = sentiment
                df['macd_slow'] = macd_tuple[0]
                df['macd_fast'] = macd_tuple[1]
                df['macd_signal'] = macd_tuple[2]
                df['ma_period'] = MA_period
                df['atr'] = atr_period
                df['obv'] = obv_period
                df['shorting'] = can_short
                df['ticker'] = ticker
                df['timeframe'] = timeframe
                df['atr_mean'] = atr_mean
                # df['sentiment_positive'] = sentiment_positive
                # df['sentiment_negative'] = sentiment_negative

                all_results.append(df)

            except Exception as e:
                print(f"Error processing {file_path}: {e}")

if not all_results:
    print("No CSV files loaded, exiting.")
    exit()

df_corr = pd.concat(all_results, ignore_index=True)

df_corr['shorting'] = df_corr['shorting'].apply(lambda x: 1 if x else 0)
df_corr['non_shorting'] = df_corr['shorting'].apply(lambda x: 1 if x == 0 else 0)

df_corr['all'] = df_corr['sentiment'].apply(lambda x: 1 if x == 'all' else 0)
df_corr['news'] = df_corr['sentiment'].apply(lambda x: 1 if x == 'news' else 0)
df_corr['news_X'] = df_corr['sentiment'].apply(lambda x: 1 if x == 'news_twitter' else 0)
df_corr['reddit'] = df_corr['sentiment'].apply(lambda x: 1 if x == 'reddit' else 0)
df_corr['reddit_X'] = df_corr['sentiment'].apply(lambda x: 1 if x == 'reddit_twitter' else 0)
df_corr['X'] = df_corr['sentiment'].apply(lambda x: 1 if x == 'twitter' else 0)

df_corr['macd_12_26_9'] = df_corr['macd_slow'].apply(lambda x: 1 if x == 12 else 0)
df_corr['macd_8_24_9'] = df_corr['macd_slow'].apply(lambda x: 1 if x == 8 else 0)
df_corr['macd_5_15_9'] = df_corr['macd_slow'].apply(lambda x: 1 if x == 5 else 0)

df_corr['ma_20'] = df_corr['ma_period'].apply(lambda x: 1 if x == 20 else 0)
df_corr['ma_50'] = df_corr['ma_period'].apply(lambda x: 1 if x == 50 else 0)

df_corr['atr_10'] = df_corr['atr'].apply(lambda x: 1 if x == 10 else 0)
df_corr['atr_14'] = df_corr['atr'].apply(lambda x: 1 if x == 14 else 0)
df_corr['atr_20'] = df_corr['atr'].apply(lambda x: 1 if x == 20 else 0)
df_corr['atr_50'] = df_corr['atr'].apply(lambda x: 1 if x == 20 else 0)

df_corr['obv_slope_10'] = df_corr['obv'].apply(lambda x: 1 if x == 10 else 0)
df_corr['obv_slope_14'] = df_corr['obv'].apply(lambda x: 1 if x == 14 else 0)
df_corr['obv_slope_20'] = df_corr['obv'].apply(lambda x: 1 if x == 20 else 0)
df_corr['obv_slope_50'] = df_corr['obv'].apply(lambda x: 1 if x == 50 else 0)

df_corr['atr_mean_14'] = df_corr['atr_mean'].apply(lambda x: 1 if x == 14 else 0)
df_corr['atr_mean_20'] = df_corr['atr_mean'].apply(lambda x: 1 if x == 20 else 0)
df_corr['atr_mean_50'] = df_corr['atr_mean'].apply(lambda x: 1 if x == 50 else 0)
df_corr['1h'] = df_corr['timeframe'].apply(lambda x: 1 if x == '1h' else 0)
df_corr['4h'] = df_corr['timeframe'].apply(lambda x: 1 if x == '4h' else 0)

# Select relevant columns
numeric_cols = [
    'macd_12_26_9', 'macd_8_24_9', 'macd_5_15_9',
    'ma_20', 'ma_50',
    'atr_10', 'atr_14', 'atr_20', 'atr_50',
    'obv_slope_10', 'obv_slope_14', 'obv_slope_20', 'obv_slope_50',
    'atr_mean_14', 'atr_mean_20', 'atr_mean_50',
    'shorting',
    'all', 'news', 'news_X', 'reddit',
    'reddit_X', 'X', '1h', '4h',
    'Total Return (%)', 'Sharpe Ratio'
]

# --------- Compute correlation matrix ---------
corr = df_corr[numeric_cols].corr()

# --------- Extract correlations with performance metrics ---------
performance_metrics = ['Total Return (%)', 'Sharpe Ratio']
corr_perf = corr[performance_metrics].drop(index=performance_metrics)

# --------- Plot a single heatmap ---------
plt.figure(figsize=(12, 6))
sns.heatmap(
    corr_perf.T,  # transpose so metrics are on the y-axis
    annot=True,
    cmap='coolwarm',
    center=0,
    fmt=".2f"
)
plt.title("Correlation of Parameters with Total Return and Sharpe Ratio")
plt.ylabel("Performance Metric")
plt.xlabel("Parameter")
plt.tight_layout()
plt.savefig("param_vs_return_sharpe_combined.png")
plt.show()
