import os
import pandas as pd
import matplotlib.pyplot as plt
from collections import defaultdict

# === Paths ===
tweet_base_path_in = "In Sample/Data/Twitter"
tweet_base_path_oos = "Out of sample/Data"

CRYPTOS = ["ADA", "BTC", "DOGE", "ETH", "SOL", "XMR", "XRP"]

# === Function to load metrics from folder ===
def load_metrics(base_path, file_suffix):
    metrics = defaultdict(lambda: {'likes': [], 'retweets': [], 'followers': []})
    for crypto in CRYPTOS:
        crypto_path = os.path.join(base_path, crypto)
        if not os.path.exists(crypto_path):
            print(f"Path does not exist: {crypto_path}")
            continue
        for file in os.listdir(crypto_path):
            if file.endswith(file_suffix):
                full_path = os.path.join(crypto_path, file)
                try:
                    df = pd.read_csv(full_path)
                    df.columns = df.columns.str.lower()

                    if 'favorite_count' in df.columns:
                        metrics[crypto]['likes'].extend(df['favorite_count'].dropna().tolist())
                    if 'retweet_count' in df.columns:
                        metrics[crypto]['retweets'].extend(df['retweet_count'].dropna().tolist())
                    if 'followers' in df.columns:
                        metrics[crypto]['followers'].extend(df['followers'].dropna().tolist())

                except Exception as e:
                    print(f"Error reading {full_path}: {e}")
    return metrics

# === Load metrics ===
avg_metrics_in = load_metrics(tweet_base_path_in, 'relevant.csv')
avg_metrics_oos = load_metrics(tweet_base_path_oos, 'deepseek.csv')

# === Compute average values helper ===
def compute_averages(metrics):
    metrics_list = ['likes', 'retweets', 'followers']
    avg_vals = {metric: [] for metric in metrics_list}
    for crypto in CRYPTOS:
        for metric in metrics_list:
            vals = metrics[crypto][metric]
            avg = sum(vals) / len(vals) if vals else 0
            avg_vals[metric].append(avg)
    return avg_vals

avg_values_in = compute_averages(avg_metrics_in)
avg_values_oos = compute_averages(avg_metrics_oos)

# === Plotting parameters ===
fig, axs = plt.subplots(1, 2, figsize=(16, 4))

title_fontsize = 18
label_fontsize = 14
tick_fontsize = 12
legend_fontsize = 12
bar_width = 0.3
x = list(range(len(CRYPTOS)))

# Determine global y-axis limits for likes and retweets combined
all_likes = avg_values_in['likes'] + avg_values_oos['likes']
all_retweets = avg_values_in['retweets'] + avg_values_oos['retweets']
y_min = 0
y_max = max(all_likes + all_retweets) * 1.1  # 10% padding

# Plot In-Sample data
ax1 = axs[0]
pos_likes = [pos - bar_width/2 for pos in x]
pos_retweets = [pos + bar_width/2 for pos in x]

ax1.bar(pos_likes, avg_values_in['likes'], width=bar_width, label='Likes', color='blue')
ax1.bar(pos_retweets, avg_values_in['retweets'], width=bar_width, label='Retweets', color='orange')

ax1.set_title('In-Sample: Average Tweet Engagement per Crypto', fontsize=title_fontsize)
ax1.set_xticks(x)
ax1.set_xticklabels(CRYPTOS, fontsize=tick_fontsize)
ax1.set_ylabel('Average Likes & Retweets', fontsize=label_fontsize)
ax1.tick_params(axis='y', labelsize=tick_fontsize)
ax1.set_ylim(y_min, y_max)
ax1.legend(fontsize=legend_fontsize)

# Plot Out-of-Sample data
ax2 = axs[1]

ax2.bar(pos_likes, avg_values_oos['likes'], width=bar_width, label='Likes', color='blue')
ax2.bar(pos_retweets, avg_values_oos['retweets'], width=bar_width, label='Retweets', color='orange')

ax2.set_title('Out-of-Sample: Average Tweet Engagement per Crypto', fontsize=title_fontsize)
ax2.set_xticks(x)
ax2.set_xticklabels(CRYPTOS, fontsize=tick_fontsize)
ax2.set_ylabel('Average Likes & Retweets', fontsize=label_fontsize)
ax2.tick_params(axis='y', labelsize=tick_fontsize)
ax2.set_ylim(y_min, y_max)
ax2.legend(fontsize=legend_fontsize)

plt.tight_layout()
plt.savefig("crypto_sentiment_metrics.png")
plt.show()
