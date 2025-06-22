import os
import pandas as pd
import matplotlib.pyplot as plt

# Bigger text globally
plt.rcParams.update({
    'font.size': 25,             # General font size
    'axes.titlesize': 16,        # Subplot title
    'axes.labelsize': 18,        # Axis labels
    'xtick.labelsize': 17,       # X tick labels
    'ytick.labelsize': 17,       # Y tick labels
    'figure.titlesize': 25       # Main title
})

# Folder and coin identifiers
folder = "correlation"
coins = ["BTC", "SOL", "DOGE", "ETH", "XRP", "ADA"]

# Loop through each file
for file in os.listdir(folder):
    for symbol in coins:
        if symbol in file:

            if "1h.csv" not in file:
                continue

            print(f"Processing {file} for {symbol}")

            df = pd.read_csv(os.path.join(folder, file))

            fig, axes = plt.subplots(2, 2, figsize=(20, 10))
            fig.suptitle("Correlation and Granger Causality over 24 Lags")

            lags = df['Lag']

            # Pearson
            axes[0, 0].plot(lags, df['Pearson_Twitter'], label='Pearson', marker='o')
            axes[0, 0].set_title(f"{symbol} - Pearson (X)")
            axes[0, 0].set_xticks(range(-24, 25, 4))
            axes[0,0].set_ylabel("p-value")

            # Spearman
            axes[0, 1].plot(lags, df['Spearman_Twitter'], label='Spearman', color='orange', marker='o')
            axes[0, 1].set_title(f"{symbol} - Spearman (X)")
            axes[0, 1].set_xticks(range(-24, 25, 4))
            axes[0,1].set_ylabel("value")

            # Granger: Sentiment → Price
            axes[1, 0].plot(lags, df['Granger_Sentiment_Twitter_Price'], label='Sentiment Granger-causes Price', color='green', marker='o')
            axes[1, 0].axhline(0.05, color='red', linestyle='--')
            axes[1, 0].set_title(f"{symbol} - Returns Granger-causes Price (X)")
            axes[1, 0].set_xticks(range(0, 25, 2))
            axes[1,0].set_ylabel("p-value")

            # Granger: Price → Sentiment (if available)
            if 'Granger_Price_Twitter_Sentiment' in df.columns:
                axes[1, 1].plot(lags, df['Granger_Price_Twitter_Sentiment'], label='Price Granger-causes Sentiment', color='purple', marker='o')
                axes[1, 1].axhline(0.05, color='red', linestyle='--')
                axes[1, 1].set_title(f"{symbol} - Returns Granger-cause Sentiment (X)")
                axes[1, 1].set_xticks(range(0, 25, 2))
                axes[1,1].set_ylabel("p-value")
            else:
                axes[1, 1].text(0.5, 0.5, 'Not available', ha='center', va='center', fontsize=14)
                axes[1, 1].set_title(f"{symbol} - Granger R→S")

            # Axis labels
            for row in range(2):
                for col in range(2):
                    ax = axes[row, col]
                    ax.set_xlabel("Lag (hours)")
                    ax.grid(True)
                    ax.tick_params(axis='x', labelbottom=True)

            plt.tight_layout(rect=[0, 0, 1, 0.96])
            plt.savefig(f"{symbol}_correlation_visualization.png", dpi=300)
            plt.close(fig)
