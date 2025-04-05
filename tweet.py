import os
import time
import schedule
import tweepy
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO
import json
from datetime import datetime
from requests_html import HTMLSession
from requests_html import AsyncHTMLSession
import re
import aiohttp
import asyncio
import base64
from flask import Flask
import threading
# Global variable to store the last posted news title
posted_titles = set()

# API for media uploads
# twitter_api = tweepy.API(auth)
app = Flask(__name__)
app.route('/')
def home():
    return "home"


IMGBB_API_KEY = '5017c200616967582033ebdc22a22535'  # <-- Replace this

async def convert_and_upload_image(image_url):
    try:
        # Step 1: Download image
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as response:
                if response.status != 200:
                    raise Exception("Failed to download image")
                image_data = await response.read()

        # Step 2: Convert to PNG
        image = Image.open(BytesIO(image_data)).convert("RGBA")
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)

        # Step 3: Base64 encode the image
        b64_image = base64.b64encode(buffer.read()).decode('utf-8')

        # Step 4: Upload to imgbb
        upload_url = f"https://api.imgbb.com/1/upload?key={IMGBB_API_KEY}"
        payload = {
            'image': b64_image,
            'name': 'converted_image',
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(upload_url, data=payload) as upload_response:
                data = await upload_response.json()
                if not data.get("success"):
                    raise Exception("Upload failed")
                return data['data']['url']

    except Exception as e:
        print(f"Error: {e}")
        return None


async def scrape_inshorts():
    """Scrape news articles from Inshorts"""
    url = "https://timesofindia.indiatimes.com/briefs"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:

        session = AsyncHTMLSession()
        response = await session.get(url, headers=headers)
        await response.html.arender(timeout=20)
        # response.html.render()
        soup = BeautifulSoup(response.html.html, 'html.parser')
        
        # Find all news articles
        articles = []
        news_cards = soup.find_all('div', class_='brief_box')
        
        for card in news_cards:
            title = card.find('h2').text.strip()
            body = card.find('p').text.strip()
            
            # Try to find image from style attribute first
            image_div = card.find('div', class_='posrel')
            
            img_tag = image_div.find('img')
            image_url = img_tag['src']
            news_url = card.find('a')['href']
            articles.append({
                'title': title,
                'body': body,
                'image_url': image_url,
                'news_url': news_url
            })
        
        return articles
    except Exception as e:
        print(f"Error scraping Inshorts: {e}")
        return []

def create_tweet_thread(article):
   
    tweets = []
    
    # First tweet with title and image
    title_tweet = f"📰 {article['title']}"
    tweets.append(title_tweet + " " + "https://timesofindia.indiatimes.com"+article['news_url'])
    
    # Split body into sentences
    sentences = re.split(r'(?<=[.!?])\s+', article['body'])
    
    current_tweet = ""
    for sentence in sentences:
        # If adding this sentence would exceed the limit, start a new tweet
        if len(current_tweet + " " + sentence) > 280:
            if current_tweet:
                tweets.append(current_tweet.strip())
            current_tweet = sentence
        else:
            if current_tweet:
                current_tweet += " " + sentence
            else:
                current_tweet = sentence
    
    # Add the last tweet if there's anything left
    if current_tweet:
        tweets.append(current_tweet.strip())
    
    return tweets


async def post_tweet_thread(tweets, image_url):
    """Post a thread of tweets with images"""
    # new_url = await convert_and_upload_image(image_url) ;
    try:
        body = {
            'value1': tweets[0],
            'value2': tweets[1] if len(tweets) > 1 else '',
            
        }

        async with aiohttp.ClientSession() as session:
            async with session.post('https://maker.ifttt.com/trigger/final_tweet/with/key/lszsmG-T_wqPQ_CyN6yHRilptinm0slShiees30nlLw', json=body) as response:
                print(await response.text())
                return True
                

        # async with aiohttp.ClientSession() as session:
        #     async with session.post('https://maker.ifttt.com/trigger/upload1/with/key/lszsmG-T_wqPQ_CyN6yHRilptinm0slShiees30nlLw', json={'value1' : tweets[1]}) as response:
        #         print(await response.text())
        #         return True
                

        return False
        
    except Exception as e:
        print(f"Error posting thread: {e}")
        return False


async def post_news():
    """Scrape news and post as threads if unique"""
    global posted_titles
    articles = await scrape_inshorts()
    new_articles = [a for a in articles if a['title'] not in posted_titles]

    if new_articles:
        for article in new_articles[:20]:
            tweets = create_tweet_thread(article)
            success = await post_tweet_thread(tweets,article['image_url'])
            if success:
                posted_titles.add(article['title'])
                print(f"Posted new article: {article['title']}")
            else:
                print("Failed to post article")
    else:
        print("No new unique article to post")

async def main():
    while True:
        await post_news()
        # res = await scrape_inshorts()
        # print(res)
        await asyncio.sleep(600)  # Wait for 10 minutes before checking again


if __name__ == "__main__":
    flask_thread = threading.Thread(target=lambda: app.run(host='127.0.0.1', port=3000))
    flask_thread.start()
    asyncio.run(main()) 