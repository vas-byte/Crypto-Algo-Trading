import os
import pandas as pd

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
                    print(f"Filename {file} does not have expected 7 parts, skipping.")
                    continue

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
                atr_meaning = parts[7] 

                df = pd.read_csv(file_path)
                
                # Add metadata columns
                df['sentiment'] = sentiment
                df['MACD'] = [macd_tuple] * len(df)
                df['MA'] = MA_period
                df['ATR'] = atr_period
                df['OBV'] = obv_period
                df['shorting'] = can_short
                df['ticker'] = ticker
                df['timeframe'] = timeframe
                df['atr_mean'] = atr_meaning

                all_results.append(df)

            except Exception as e:
                print(f"Error processing {file_path}: {e}")

if not all_results:
    print("No CSV files loaded, exiting.")
    exit()

df_all = pd.concat(all_results, ignore_index=True)
print(f"\nLoaded {len(df_all)} rows from {len(all_results)} files.")

# Check required columns
required_cols = ['Total Return (%)', 'Sharpe Ratio']
for col in required_cols:
    if col not in df_all.columns:
        raise ValueError(f"Required column '{col}' not found in data.")

# Normalize metrics for ranking
df_all['norm_return'] = (df_all['Total Return (%)'] - df_all['Total Return (%)'].min()) / (df_all['Total Return (%)'].max() - df_all['Total Return (%)'].min())
df_all['norm_sharpe'] = (df_all['Sharpe Ratio'] - df_all['Sharpe Ratio'].min()) / (df_all['Sharpe Ratio'].max() - df_all['Sharpe Ratio'].min())

# Weighted score without max_drawdown
df_all['score'] = (
    0.5 * df_all['norm_sharpe'] +
    0.5 * df_all['norm_return'] 
)

# Sort and show top 10 configs
df_sorted = df_all.sort_values(by='score', ascending=False)
top10 = df_sorted.head(10)

pd.set_option("display.max_columns", None)
print("\nTop 10 Best Configurations:\n")
print(top10[['ticker', 'sentiment', 'MACD', 'MA', 'ATR', 'atr_mean', 'OBV', 'shorting', 'timeframe',
             'Total Return (%)', 'Sharpe Ratio', 'score']])


top_per_ticker = (
    df_all.sort_values(by='score', ascending=False)
          .groupby('ticker')
          .head(100)
          .reset_index(drop=True)
)
generalization_results = []

for idx, row in top_per_ticker.iterrows():
    config_params = {
        'MACD': row['MACD'],
        'MA': row['MA'],
        'ATR': row['ATR'],
        'OBV': row['OBV'],
        'shorting': row['shorting'],
        'timeframe': row['timeframe'],
        'sentiment': row['sentiment']
    }
    
    # Filter df_all by these params but vary ticker
    filtered = df_all[
        (df_all['MACD'] == config_params['MACD']) &
        (df_all['MA'] == config_params['MA']) &
        (df_all['ATR'] == config_params['ATR']) &
        (df_all['OBV'] == config_params['OBV']) &
        (df_all['shorting'] == config_params['shorting']) &
        (df_all['timeframe'] == config_params['timeframe']) &
        (df_all['sentiment'] == config_params['sentiment'])
    ]
    
    score = \
        0.45 * filtered['norm_sharpe'].mean() + \
        0.45 * filtered['norm_return'].mean() + \
        0.1 * (1 / filtered['Total Return (%)'].std() if filtered['Total Return (%)'].std() != 0 else 0)
    

    avg_sharpe = filtered['Sharpe Ratio'].mean()
    avg_return = filtered['Total Return (%)'].mean()
    
    generalization_results.append({
        'base_ticker': row['ticker'],
        'MACD': config_params['MACD'],
        'MA': config_params['MA'],
        'ATR': config_params['ATR'],
        'atr_mean': row['atr_mean'],
        'OBV': config_params['OBV'],
        'shorting': config_params['shorting'],
        'timeframe': config_params['timeframe'],
        'sentiment': config_params['sentiment'],
        'avg_score': score,
        'avg_sharpe': avg_sharpe,
        'avg_return': avg_return
    })

gen_df = pd.DataFrame(generalization_results)
gen_df = gen_df.sort_values(by='avg_score', ascending=False)

print("\nGeneralization Results for Top Configurations per Ticker:\n")
print(gen_df)