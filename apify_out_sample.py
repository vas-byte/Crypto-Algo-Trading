import asyncio
from apify_client import ApifyClientAsync
import os
import json
from datetime import datetime, timedelta

# CONFIGURATION
TOKEN = ""
ACTOR_ID = "apidojo/tweet-scraper"
CRYPTO_TICKERS = ['$ada', '$btc', '$doge', '$eth', '$sol', '$xmr', '$xrp']
CRYTP_NAMES = ["cardano", "bitcoin", "dogecoin", "ethereum", "solana", "monero", "ripple"]
MIN_LIKES = [100,1000,20,60,5,5,5]
START_MONTH = "2024-01"
END_MONTH = "2024-12"
OUTPUT_FOLDER = "Out of sample"


# GENERATE MONTH RANGES
def generate_month_ranges(start, end):
    current = datetime.strptime(start, "%Y-%m")
    # Move to the LAST day of the END month
    next_month = datetime.strptime(end, "%Y-%m").replace(day=28) + timedelta(days=4)
    end_date = next_month - timedelta(days=next_month.day)

    while current <= end_date:
        month_start = current.strftime("%Y-%m-01")
        next_month = current.replace(day=28) + timedelta(days=4)
        month_end = (next_month - timedelta(days=next_month.day)).strftime("%Y-%m-%d")
        yield (month_start, month_end)
        current = next_month



# RUN SCRAPE TASK
async def run_scrape(client, search_terms, start_date, end_date, likes):
    actor = client.actor(ACTOR_ID)

    input_data = {
        "start": start_date,
        "end": end_date,
        "searchTerms": search_terms,
        "minimumFavorites": likes,
        "minimumReplies": 0,
        "minimumRetweets": 0,
        "tweetLanguage": "en",
        "sort": "Latest",
        "includeSearchTerms": False,
        "onlyVerifiedUsers": False,
        "onlyTwitterBlue": False,
        "onlyImage": False,
        "onlyVideo": False,
        "onlyQuote": False,
        "customMapFunction": "(object) => { return {...object} }",
    }

    run = await actor.call(run_input=input_data)
    dataset_id = run["defaultDatasetId"]
    dataset = client.dataset(dataset_id)
    data = await dataset.list_items()
    return data.items


# MAIN
async def main():
    client = ApifyClientAsync(token=TOKEN)

    for ticker, name, likes in zip(CRYPTO_TICKERS, CRYTP_NAMES, MIN_LIKES):
       
        search_terms = [f"(f{ticker}) OR (#{name})"]

        for start_date, end_date in generate_month_ranges(START_MONTH, END_MONTH):
            print(f"🔍 Scraping {ticker} from {start_date} to {end_date}")
            try:
                data = await run_scrape(client, search_terms, start_date, end_date, likes)

                filename = f"{ticker}_{start_date[:7]}.json"
                filepath = os.path.join(OUTPUT_FOLDER, filename)
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                print(f"✅ Saved {filename} ({len(data)} items)")

            except Exception as e:
                print(f"❌ Failed for {ticker} {start_date}: {e}")


if __name__ == "__main__":
    asyncio.run(main())
