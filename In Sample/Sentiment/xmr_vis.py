import os
import pandas as pd
import matplotlib.pyplot as plt
from collections import defaultdict

# === Paths ===
tweet_base_path = "../Data/Twitter"
sentiment_cache_path = "sentiment cache"

CRYPTOS = ["ADA", "BTC", "DOGE", "ETH", "SOL", "XMR", "XRP"]

# Initialize containers
avg_metrics = defaultdict(lambda: {'likes': [], 'retweets': [], 'followers': []})
total_tweet_counts = defaultdict(int)
xmr_sentiment_counts = defaultdict(int)
cached_sentiment_series = {}

# === Step 1: Process tweet folders ===
for crypto in CRYPTOS:
    crypto_path = os.path.join(tweet_base_path, crypto)

    for file in os.listdir(crypto_path):
        if file.endswith('relevant.csv'):
            full_path = os.path.join(crypto_path, file)
            try:
                df = pd.read_csv(full_path)
                df.columns = df.columns.str.lower()
                total_tweet_counts[crypto] += len(df)

                if 'favorite_count' in df.columns:
                    avg_metrics[crypto]['likes'].extend(df['favorite_count'].dropna().tolist())
                if 'retweet_count' in df.columns:
                    avg_metrics[crypto]['retweets'].extend(df['retweet_count'].dropna().tolist())
                if 'followers' in df.columns:
                    avg_metrics[crypto]['followers'].extend(df['followers'].dropna().tolist())

                if crypto == "XMR" and 'sentiment' in df.columns:
                    for label in ['Positive', 'Negative', 'Neutral']:
                        xmr_sentiment_counts[label] += (df['sentiment'] == label).sum()

            except Exception as e:
                print(f"Error reading {full_path}: {e}")

# === Step 2: Load sentiment cache time series ===
for crypto in CRYPTOS:
    if crypto != "XMR":
        continue

    filename = f"{crypto}USDT_1h_sentiment.csv"
    path = os.path.join(sentiment_cache_path, filename)
    if not os.path.exists(path):
        continue

    try:
        df = pd.read_csv(path)
        df.columns = df.columns.str.lower()
        if 'date' in df.columns and 'sentiment_twitter' in df.columns:
            df['timestamp'] = pd.to_datetime(df['date'])
            df = df.sort_values('timestamp')
            cached_sentiment_series[crypto] = df[['timestamp', 'sentiment_twitter']]
    except Exception as e:
        print(f"Couldn't load sentiment cache for {crypto}: {e}")

# === Step 3: Plot in 2x2 grid ===
fig, axs = plt.subplots(2, 2, figsize=(16, 7))
axs = axs.flatten()

# Font sizes
title_fontsize = 18
label_fontsize = 14
tick_fontsize = 12
legend_fontsize = 12

# 1. Plot Sentiment Over Time (first subplot)
for crypto, df in cached_sentiment_series.items():
    axs[0].plot(df['timestamp'], df['sentiment_twitter'], label=crypto, alpha=0.7)
axs[0].set_title("Twitter Sentiment Over Time", fontsize=title_fontsize)
axs[0].set_xlabel("Time", fontsize=label_fontsize)
axs[0].set_ylabel("Sentiment Score", fontsize=label_fontsize)
axs[0].legend(fontsize=legend_fontsize)
axs[0].tick_params(axis='both', labelsize=tick_fontsize)

# 2. Total Tweet Count per Crypto (second subplot)
cryptos_sorted = sorted(total_tweet_counts.keys())
tweet_totals = [total_tweet_counts[c] for c in cryptos_sorted]
axs[1].bar(cryptos_sorted, tweet_totals, color='skyblue')
axs[1].set_title("Total Tweet Count per Cryptocurrency", fontsize=title_fontsize)
axs[1].set_xlabel("Cryptocurrency", fontsize=label_fontsize)
axs[1].set_ylabel("Total Tweets", fontsize=label_fontsize)
axs[1].tick_params(axis='both', labelsize=tick_fontsize)

# 3. XMR Sentiment Label Distribution (third subplot)
labels = ['Positive', 'Negative', 'Neutral']
values = [xmr_sentiment_counts[l] for l in labels]
axs[2].bar(labels, values, color=['green', 'red', 'gray'])
axs[2].set_title("XMR Sentiment Label Distribution", fontsize=title_fontsize)
axs[2].set_xlabel("Sentiment", fontsize=label_fontsize)
axs[2].set_ylabel("Tweet Count", fontsize=label_fontsize)
axs[2].tick_params(axis='both', labelsize=tick_fontsize)

# 4. Average Followers, Likes, Retweets per Tweet (fourth subplot)
metrics = ['likes', 'retweets', 'followers']
bar_width = 0.25
x = list(range(len(CRYPTOS)))

# Compute average values
avg_values = {metric: [] for metric in metrics}
for crypto in CRYPTOS:
    for metric in metrics:
        values = avg_metrics[crypto][metric]
        avg = sum(values) / len(values) if values else 0
        avg_values[metric].append(avg)

# Primary axis for likes and retweets
ax1 = axs[3]
positions_likes = [pos - bar_width for pos in x]
positions_retweets = [pos + bar_width for pos in x]
bars_likes = ax1.bar(positions_likes, avg_values['likes'], width=bar_width, label='Likes', color='blue')
bars_retweets = ax1.bar(positions_retweets, avg_values['retweets'], width=bar_width, label='Retweets', color='orange')

ax1.set_ylabel('Average Likes & Retweets', fontsize=label_fontsize)
ax1.set_xticks(x)
ax1.set_xticklabels(CRYPTOS, fontsize=tick_fontsize)
ax1.set_title('Average Tweet Engagement per Crypto', fontsize=title_fontsize)
ax1.tick_params(axis='y', labelsize=tick_fontsize)

# Secondary axis for followers
ax2 = ax1.twinx()
positions_followers = x  # center followers bars
bars_followers = ax2.bar(positions_followers, avg_values['followers'], width=bar_width, alpha=0.5, label='Followers', color='green')

ax2.set_ylabel('Average Followers', fontsize=label_fontsize)
ax2.tick_params(axis='y', labelsize=tick_fontsize)

# Combine legends from both axes
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=legend_fontsize)

plt.tight_layout()
plt.savefig("xmr_visual.png")
plt.show()
