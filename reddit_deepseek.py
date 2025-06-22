import os
import re
import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor


# CONFIG
API_KEY = ""
API_URL = "https://api.deepseek.com/v1/chat/completions"
MODEL_NAME = "deepseek-chat"
MAX_WORKERS = 20
INSAMPLE = True  # Set to True if running in InSample environment
FOLDER = "In Sample/Data/Reddit" if INSAMPLE else "Out of sample/Data/Reddit"

# TEXT CLEANING
def clean_text(text):
    text = re.sub(r"http\S+|www\S+|https\S+", "", str(text))
    text = re.sub(r"u/\w+", "", text)
    text = re.sub(r"\b(Telegram|Dextool|Links|removed|deleted)\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"#\w+", "", text)
    text = re.sub(r"@\w+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = text.encode('ascii', 'ignore').decode('ascii')
    return text


# MARKET RELEVANCE FILTER
def is_market_relevant(text):
    try:
        prompt = (
            f'Determine if this reddit post is related to financial markets, trading, investing, or cryptocurrency price movements.\n'
            f'Text: "{text}"\n\n'
            'Respond only with "Yes" or "No".'
        )

        payload = {
            "model": MODEL_NAME,
            "messages": [
                {"role": "system", "content": "You are a financial relevance classifier. Classify text as market-relevant or not."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 5
        }

        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }

        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"].strip().lower()

        return content.startswith("yes")

    except Exception as e:
        print(f"⚠️ Relevance API error: {e}")
        return False  # Default to not relevant on error



# DEEPSEEK SENTIMENT CLASSIFICATION
def classify_sentiment_with_ticker(text_ticker_tuple):
    text, ticker = text_ticker_tuple
    try:
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }

        prompt = (
            f"Classify the sentiment of {ticker}:\n{text}\n\n"
            "Respond only with one word: Positive, Negative, or Neutral."
        )

        payload = {
            "model": MODEL_NAME,
            "messages": [
                {"role": "system", "content": "You are a sentiment analysis assistant. Classify text as Positive, Negative, or Neutral."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 10
        }

        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"].strip()

        if content.lower().startswith("positive"):
            return "Positive"
        elif content.lower().startswith("negative"):
            return "Negative"
        elif content.lower().startswith("neutral"):
            return "Neutral"
        else:
            return "Neutral"

    except Exception as e:
        print(f"⚠️ Sentiment API error: {e}")
        return "ERROR"


# PROCESS SINGLE FILE
def process_file(file_path):
    print(f"\n📁 Processing file: {file_path}")
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        print(f"❌ Could not read {file_path}: {e}")
        return

    if 'title' not in df.columns:
        print(f"⚠️ Skipping {file_path} — no 'title' column")
        return
    if 'ticker' not in df.columns:
        print(f"⚠️ Skipping {file_path} — no 'ticker' column")
        return

    df['combined_text'] = (df['title'].fillna('') + " " + df['selftext'].fillna('')).apply(clean_text)

    print(f"🔍 Filtering {len(df)} posts for market relevance...")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        relevance_flags = list(executor.map(is_market_relevant, df['combined_text']))

    original_len = len(df)
    df = df[relevance_flags]
    print(f"✅ {len(df)} posts classified as market-relevant (filtered out {original_len - len(df)})")

    if df.empty:
        print(f"⚠️ No relevant posts remaining in {file_path}")
        return

    texts_and_tickers = list(zip(df['combined_text'], df['ticker'].fillna('')))
    print(f"🧠 Classifying {len(texts_and_tickers)} relevant posts with DeepSeek...")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        sentiments = list(executor.map(classify_sentiment_with_ticker, texts_and_tickers))

    df['sentiment'] = sentiments
    df.drop(columns=['selftext', 'title'], inplace=True)

    output_path = os.path.join(os.path.dirname(file_path), "sentiment_deepseek.csv")
    df.to_csv(output_path, index=False)
    print(f"✅ Saved: {output_path}")

# FIND CSV FILES
def find_all_csvs(base_folder=FOLDER):
    csv_files = []
    for root, _, files in os.walk(base_folder):
        for f in files:
            if f.endswith("submission.csv"):
                csv_files.append(os.path.join(root, f))
    return csv_files


# MAIN
def main():
    files = find_all_csvs()
    print(f"\n🔎 Found {len(files)} Reddit CSVs.")
    for file in files:
        process_file(file)

if __name__ == "__main__":
    main()
