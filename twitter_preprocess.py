from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import os
import json
import re
import requests

DEEPSEEK_API_KEY = ""
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

INSAMPLE = True  # Set to True if running in InSample environment
FOLDER = "In Sample/Data/Twitter" if INSAMPLE else "Out of sample/Data/Twitter"

def clean_text(text):
    if text is None:
        return ""
    text = re.sub(r"http\S+|www\S+|https\S+", "", str(text))
    text = text.encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r"#\w+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r'@\w+', '', text)
    return text

def is_market_relevant(text):
    prompt = f"""
Determine if this tweet is related to financial markets, trading, investing, or cryptocurrency price movements.
Text: "{text}"
Respond only with "Yes" or "No".
"""
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are a financial relevance classifier. Classify tweets as market-relevant or not."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 5
    }

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(DEEPSEEK_API_URL, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"].strip().lower()
        return content.startswith("yes")
    except Exception as e:
        print(f"DeepSeek error: {e}")
        return False

def process_folder(base_dir):
    for root, dirs, files in os.walk(base_dir):
        if not files:
            continue

        tweets_to_check = []

        # If the directory has a csv file, skip processing
        if any(file.endswith(".csv") for file in files):
            print(f"Skipping {root} as it already contains a CSV file.")
            continue

        for file in files:
            if not file.endswith(".json"):
                continue

            path = os.path.join(root, file)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception as e:
                print(f"Failed to read {path}: {e}")
                continue

            for d in data:
                if d.get('noResults'):
                    continue
                if any(k in d.get('fullText', '').lower() for k in ['giveaway', 'win', 'prize']):
                    continue

                text = clean_text(d.get('fullText'))
                if not text:
                    continue

                tweets_to_check.append({
                    'created_at': d.get('createdAt'),
                    'text': text,
                    'user': d.get('author', {}).get('userName'),
                    'retweet_count': d.get('retweetCount'),
                    'favorite_count': d.get('likeCount'),
                    'followers': d.get('author', {}).get('followers'),
                    'is_verified': d.get('author', {}).get('isVerified')
                })

        if not tweets_to_check:
            continue

        print(f"Processing {len(tweets_to_check)} tweets in {root}")

        with ThreadPoolExecutor(max_workers=10) as executor:
            # Map calls is_market_relevant on tweet texts, returns boolean results in same order
            relevance_results = list(executor.map(is_market_relevant, [t['text'] for t in tweets_to_check]))

        # Filter tweets by relevance
        relevant_data = [tweet for tweet, is_relevant in zip(tweets_to_check, relevance_results) if is_relevant]

        if relevant_data:
            df = pd.DataFrame(relevant_data)
            df.set_index('created_at', inplace=True)
            crypto_name = os.path.basename(root.rstrip("/\\"))
            output_file = os.path.join(root, f"output.csv")
            df.to_csv(output_file)
            print(f"Saved: {output_file}")

if __name__ == "__main__":
    process_folder(FOLDER)
