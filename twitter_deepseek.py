import os
import re
import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from functools import partial


# CONFIG
API_KEY = ""
API_URL = "https://api.deepseek.com/v1/chat/completions"
MODEL_NAME = "deepseek-chat"
MAX_WORKERS = 20

INSAMPLE = True  # Set to True if running in InSample environment
FOLDER = "In Sample/Data/Twitter" if INSAMPLE else "Out of sample/Data/Twitter"


# TEXT CLEANING
def clean_text(text):
    text = re.sub(r"http\S+|www\S+|https\S+", "", str(text))
    text = re.sub(r"#\w+", "", text)
    text = re.sub(r"@\w+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = text.encode('ascii', 'ignore').decode('ascii')
    return text

# DEEPSEEK API CALL
def classify_sentiment_api(text, crypto_name="this cryptocurrency"):
    try:
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }

        prompt = f"Classify the sentiment of {crypto_name}:\n{text}\n\nRespond only with one word: Positive, Negative, or Neutral."

        payload = {
            "model": MODEL_NAME,
            "messages": [
                {"role": "system", "content": "Classify text as Positive, Negative, or Neutral."},
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
        print(f"⚠️ API error: {e}")
        return "ERROR"

# PROCESS SINGLE FILE
def process_file(file_path):
    print(f"Processing file: {file_path}")
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        print(f"Could not read {file_path}: {e}")
        return

    if 'text' not in df.columns:
        print(f"Skipping {file_path} — no 'text' column")
        return

    # Extract crypto name/ticker from folder name or file name
    crypto_name = os.path.basename(os.path.dirname(file_path))

    # Clean the text
    df['clean_text'] = df['text'].fillna('').apply(clean_text)
    texts = df['clean_text'].tolist()

    # Thread pool with order-preserving map
    print(f"🚀 Sending {len(texts)} API requests with ThreadPoolExecutor...")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        classify = partial(classify_sentiment_api, crypto_name=crypto_name)
        results = list(executor.map(classify, texts))  # Order preserved

    # Update DataFrame
    df['sentiment'] = results

    # Save output
    output_path = os.path.join(os.path.dirname(file_path), "twitter_deepseek.csv")
    df.to_csv(output_path, index=False)
    print(f"✅ Saved: {output_path}")


# FIND FILES
def find_all_csvs(base_folder=FOLDER):
    csv_files = []
    for root, _, files in os.walk(base_folder):

        # If the directory has a csv file, skip processing
        if any(file.endswith("deepseek.csv") for file in files):
            print(f"Skipping {root} as it already contains a CSV file.")
            continue

        for f in files:
            if f.endswith("output.csv"):
                csv_files.append(os.path.join(root, f))
    return csv_files


# MAIN
def main():
    files = find_all_csvs(FOLDER)
    print(f"\n🔎 Found {len(files)} Twitter CSVs.")
    for file in files:
        process_file(file)

if __name__ == "__main__":
    main()
