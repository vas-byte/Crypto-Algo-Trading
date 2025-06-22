import asyncio
from concurrent.futures import ThreadPoolExecutor
from twikit import Client
import requests
import re
import numpy as np
import datetime
import os
import time

class SentimentScraper:

    def __init__(self, deepseek_api_key):

        self.client =  Client('en-US')
        self.client._user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
        self.client.proxy = ""

        self.client2 = Client('en-US')
        self.client2._user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3.1 Safari/605.1.15"
        self.client2.proxy = ""

        self.client3 = Client('en-US')
        self.client3._user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
        self.client3.proxy = ""

        self.deepseek_api_key = deepseek_api_key
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        self.model = "deepseek-chat"

        self.username = ""
        self.email = ""
        self.password = ""

        self.username2 = ""
        self.email2 = ""
        self.password2 = ""

        self.username3 = ""
        self.email3 = ""
        self.password3 = ""
    
    
    async def login(self):
        
        if os.path.exists("1.json"):
            print("Auth file '1.json' found. Loading cookies...")
            self.client.load_cookies("1.json")
        else:
            await self.client.login(auth_info_1=self.username, auth_info_2=self.email, password=self.password, enable_ui_metrics=True)
            print(f"Logged in as {self.username} with email {self.email}")
            self.client.save_cookies("1.json")
        
        time.sleep(10)

        if os.path.exists("2.json"):
            print("Auth file '2.json' found. Loading cookies...")
            self.client2.load_cookies("2.json")
        else:
            await self.client2.login(auth_info_1=self.username2, auth_info_2=self.email2, password=self.password2, enable_ui_metrics=True)
            print(f"Logged in as {self.username2} with email {self.email2}")
            self.client2.save_cookies("2.json")

        time.sleep(10)
        
        if os.path.exists("3.json"):
            print("Auth file '3.json' found. Loading cookies...")
            self.client3.load_cookies("3.json")
        else:
            await self.client3.login(auth_info_1=self.username3, auth_info_2=self.email3, password=self.password3, enable_ui_metrics=True)
            print(f"Logged in as {self.username3} with email {self.email3}")
            self.client3.save_cookies("3.json")


    async def check_auth(self):
        for fname in ["1", "2", "3"]:
            if os.path.exists(fname):
                print(f"Auth file '{fname}' found.")
                with open(fname, "r") as f:
                    lines = [line.strip() for line in f.readlines()]
                    if len(lines) < 3:
                        raise ValueError(f"File '{fname}' does not contain enough lines.")
                    
                    # Line 1: username, Line 2: password, Line 3: email
                    username, password, email = lines[:3]
                    username = username.replace(" ", "").replace("\n", "")
                    password = password.replace(" ", "").replace("\n", "")
                    email = email.replace(" ", "").replace("\n", "")

                    print(f"New Username: {username}, Email: {email}, Password: {password}")

                    try:
                        if fname == "1":
                            await self.client.logout()
                            self.client = Client('en-US')
                            self.client._user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
                            self.client.proxy = "http://a5e86ce0c1e21742285c__cr.au:2b0b199ca04148d3@gw.dataimpulse.com:10000"
                            await self.client.login(auth_info_1=username, auth_info_2=email, password=password)

                        elif fname == "2":
                            await self.client2.logout()
                            self.client2 = Client('en-US')
                            self.client2._user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3.1 Safari/605.1.15"
                            self.client2.proxy = "http://a5e86ce0c1e21742285c__cr.au:2b0b199ca04148d3@gw.dataimpulse.com:10001"
                            await self.client2.login(auth_info_1=username, auth_info_2=email, password=password)
                        
                        elif fname == "3":
                            await self.client3.logout()
                            self.client3 = Client('en-US')
                            self.client3._user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
                            self.client3.proxy = "http://a5e86ce0c1e21742285c__cr.au:2b0b199ca04148d3@gw.dataimpulse.com:10002"
                            await self.client3.login(auth_info_1=username, auth_info_2=email, password=password)
                    except Exception as e:
                        print(f"Error logging in with {fname}: {e}")


    async def __get_latest_tweets(self, ticker, cryptoname, start_date, end_date):

        print(f"(${ticker} OR {cryptoname}) since:{start_date}")

        tweet_data = []

        minfavs = 20
        loops = 0

        if "BTC" in ticker:
            minfavs = 120
            client = self.client
            loops = 35
        
        elif "DOGE" in ticker:
            minfavs = 10
            client = self.client2
            loops = 25
        
        elif "TRUMP" in ticker:
            minfavs = 5
            client = self.client2
            loops = 20
        
        elif "ADA" in ticker:
            minfavs = 20
            client = self.client3
            loops = 22
        
        elif "XRP" in ticker:
            minfavs = 30
            client = self.client3
            loops = 22

        tried = 0

        while True:
    
            try:
                tweets = await client.search_tweet(f'(${ticker} OR {cryptoname}) -giveaway -prize min_faves:{minfavs} since:{start_date}', 'Latest')
                break

            except Exception as e:
                print(f"⚠️ Error fetching tweets: {e}")
                print("Retrying in 3 seconds...")
                await asyncio.sleep(3)
                tried += 1
                if tried >= 3:
                    print("Failed to fetch tweets after multiple attempts. Exiting.")
                    return []
                continue

        for tweet in tweets:
            tweet_data.append({
                'id': tweet.id,
                'text': tweet.text,
                'created_at': tweet.created_at,
                'user_followers_count': tweet.user.followers_count,
                'retweet_count': tweet.retweet_count,
                'like_count': tweet.favorite_count,
                'reply_count': tweet.reply_count,
                'text': tweet.full_text
            })
        
        next_tweets = tweets

        for _ in range(loops):
            tried = 0

            while True:
                
                try:  
                    next_tweets = await next_tweets.next()
                    break
                except Exception as e:

                    if tried >= 3:
                        print("Failed to fetch next tweets after multiple attempts. Exiting.")
                        break
                    tried += 1
                    await asyncio.sleep(3)
                    continue

            if next_tweets is None or len(next_tweets) == 0:
                break

            for tweet in next_tweets:
                tweet_data.append({
                    'id': tweet.id,
                    'text': tweet.text,
                    'created_at': tweet.created_at,
                    'user_followers_count': tweet.user.followers_count,
                    'retweet_count': tweet.retweet_count,
                    'like_count': tweet.favorite_count,
                    'reply_count': tweet.reply_count,
                    'text': tweet.full_text
                })


        print(f"Found {len(tweet_data)} tweets for {ticker} or {cryptoname} from {start_date} to {end_date}.")

        return tweet_data
    
    
    def __clean_text(self, text):
        if text is None:
            return ""
        text = re.sub(r"http\S+|www\S+|https\S+", "", str(text))
        text = text.encode('ascii', 'ignore').decode('ascii')
        text = re.sub(r"#\w+", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        text = re.sub(r'@\w+', '', text)
        return text
    
    def __get_relevance(self, text):
       
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
                "Authorization": f"Bearer {self.deepseek_api_key}",
                "Content-Type": "application/json"
            }

            try:
                response = requests.post(self.api_url, json=payload, headers=headers, timeout=10)
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"].strip().lower()
                return content.startswith("yes")
            except Exception as e:
                print(f"⚠️ DeepSeek error: {e}")
                return False
            
    def __deepseek_sentiment(self, text, crypto_name):
        try:
            headers = {
                "Authorization": f"Bearer {self.deepseek_api_key}",
                "Content-Type": "application/json"
            }

            prompt = f"Classify the sentiment of {crypto_name}:\n{text}\n\nRespond only with one word: Positive, Negative, or Neutral."

            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "Classify text as Positive, Negative, or Neutral."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.2,
                "max_tokens": 10
            }

            response = requests.post(self.api_url, headers=headers, json=payload)
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
    
    def __analyze_sentiment(self, tweets, crypto_name):

        # Clean text
        for tweet in tweets:
            tweet['text'] = self.__clean_text(tweet['text'])
            if not tweet['text']:
                continue
            
        # Filter relevant tweets
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Map calls is_market_relevant on tweet texts, returns boolean results in same order
            relevance_results = list(executor.map(self.__get_relevance, [t['text'] for t in tweets]))
        
        relevant_tweets = []

        for i, tweet in enumerate(tweets):
         
            if not relevance_results[i]:
                continue
            
            relevant_tweets.append(tweet)
        
        print(f"Filtered down to {len(relevant_tweets)} relevant tweets for {crypto_name}.")
        
        # Analyze sentiment
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Map calls __deepseek_sentiment on relevant tweet texts, returns sentiment results in same order
            sentiment_results = list(executor.map(self.__deepseek_sentiment, [t['text'] for t in relevant_tweets], [crypto_name] * len(relevant_tweets)))
        
        # Combine results
        for i, tweet in enumerate(relevant_tweets):
            tweet['sentiment'] = sentiment_results[i]
        
        print(f"Sentiment analysis complete for {len(relevant_tweets)} relevant tweets.")
        
        return relevant_tweets
    
    def tanh_scale(self, x, k=0.000001):
        return np.tanh(k * x)
    
    async def get_sentiment(self, ticker, cryptoname):
        """
        Get the sentiment of the latest tweets for a given ticker or cryptocurrency name.
        
        :param ticker: Stock ticker symbol (e.g., 'AAPL').
        :param cryptoname: Cryptocurrency name (e.g., 'Bitcoin').
        :return: List of tweet data with sentiment information.
        """
        start_date = datetime.datetime.now().strftime('%Y-%m-%d')
        end_date = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')

        tweet_data = await self.__get_latest_tweets(ticker, cryptoname, start_date, end_date)
        sentiment_results = self.__analyze_sentiment(tweet_data, cryptoname)

        # Calculate overall sentiment
        sentiment_score = 0

        for tweet in sentiment_results:
            retweets = tweet['retweet_count']
            likes = tweet['like_count']
            followers = tweet['user_followers_count']
            weight = followers * ((likes+1)/(followers+1)) * (retweets+1)
            if tweet['sentiment'] == 'Positive':
                sentiment_score += weight
            elif tweet['sentiment'] == 'Negative':
                sentiment_score -= weight
        
        # Scale sentiment score using tanh
        k=0.000001

        if ticker == "BTC":
            k=0.0000005
        elif ticker == "DOGE":
            k=0.00001
        elif ticker == "TRUMP":
            k=0.00002
        elif ticker == "ADA":
            k=0.000005
        elif ticker == "XRP":
            k=0.000001

        scaled_sentiment = self.tanh_scale(sentiment_score, k)
        print(f"Overall sentiment for {ticker} or {cryptoname}: {scaled_sentiment:.4f}")

        return scaled_sentiment
