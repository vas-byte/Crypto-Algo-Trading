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

# CLEAN TEXT
def clean_text(text):
    if text is None:
        return ""
    text = re.sub(r"http\S+|www\S+|https\S+", "", str(text))
    text = text.encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r"#\w+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r'@\w+', '', text)
    return text

# DEEPSEEK SENTIMENT API
def classify_sentiment(text):
    try:
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": MODEL_NAME,
            "messages": [
                {"role": "system", "content": "You are a sentiment analysis assistant. Classify text as Positive, Negative, or Neutral."},
                {"role": "user", "content": f"Classify the sentiment of this text:\n{text}\n\nRespond only with one word: Positive, Negative, or Neutral."}
            ],
            "temperature": 0.2,
            "max_tokens": 10
        }

        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()["choices"][0]["message"]["content"].strip()

        if result.lower().startswith("positive"):
            return "Positive"
        elif result.lower().startswith("negative"):
            return "Negative"
        elif result.lower().startswith("neutral"):
            return "Neutral"
        else:
            return "Neutral"

    except Exception as e:
        print(f"⚠️ API error: {e}")
        return "ERROR"


# MAIN PIPELINE
def main():
    file_path = "In Sample/Data/cryptonews.csv"  # Replace with your path
    df = pd.read_csv(file_path)

    # Combine and clean text columns
    df['clean_text'] = (df['title'].fillna('') + ' ' + df['text'].fillna('')).apply(clean_text)
    texts = df['clean_text'].tolist()

    print(f"🔍 Classifying {len(texts)} news entries using DeepSeek with {MAX_WORKERS} threads...")

    # Parallel classification, order preserved by map
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        sentiments = list(executor.map(classify_sentiment, texts))

    df['sentiment'] = sentiments

    # Drop original text columns
    df.drop(columns=['title', 'text'], inplace=True)

    output_path = "In Sample/Data/news_deepseek.csv"
    df.to_csv(output_path, index=False)
    print(f"✅ Saved sentiment-enhanced dataset to {output_path}")

if __name__ == "__main__":
    main()
