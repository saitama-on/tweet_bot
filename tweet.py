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
posted_titles = ["‘Tariffs here to stay’: Trump says 'big business' not worried as markets lose $5 trillion", 'Lawrence Bishnoi gang member Aditya Jain nabbed in Dubai', 'Watch: Speculations arise about Elon Musk leaving DOGE; Trump responds', 'Waqf Bill sparks rift within JD(U) as fifth leader quits party', "What is carbon monoxide poisoning- the gas that killed Brett Gardner's 14-year-old son: How to stay safe", "Indian origin Catholic priest killed at his parish rectory in US' Kansas", "KKR's Venkatesh Iyer deflects question on price-tag pressure with a smile", "Rishabh Pant's horror run continues with another cheap dismissal in IPL", 'Archaeologists uncover ancient garden at Church of the Holy Sepulchre, aligning with biblical accounts', 'What is the deadly antibiotic-resistant superbug spreading in Malaysia? Could it be a global threat?', 'Lok Sabha adopts resolution on Manipur well past 1am Thursday', 'IPL 2025: Venkatesh Iyer, Vaibhav Arora heroics lead KKR to dominating 80-run victory over SRH', 'Israel kills Hamas commander in Lebanon strike', 'Bengaluru CEO highlights unseen dangers of contemporary work culture', "'Witch hunt by European Leftists': Trump backs France's Le Pen after her conviction", "'No rocket science': Ashish Nehra reveals his coaching philosophy at Gujarat Titans", 'Doctor shares cancer warning against THIS viral no-carb diet form', "'Extremely unfortunate': LS Speaker Om Birla slams Sonia Gandhi over Waqf Bill 'bulldozed through' remark", 'Reciprocal Tariffs: Why Donald Trump is being trolled for saying Hank Tough', 'IPL 2025: Why Rohit Sharma not playing against Lucknow Super Giants', 'Donald Trump fires NSA chief Timothy Haugh amid cyber threats, sparking Democratic backlash', 'England suffer injury blow as Olly Stone set to miss India Test series', "UK court orders Donald Trump to pay $821,000 legal bill over 'Steele dossier' lawsuit", "Donald Trump says 'only the weak will fail' amid tariff chaos, Wall Street bloodbath", 'What is the best time to start morning walk', 'Parliament passes Waqf Amendment Bill 2025', 'Brace for hotter days ahead in Ahmedabad, maximum temperature to rise by 2-3 degrees', "'Will continue to resist all assaults of Modi govt': Congress to challenge Waqf Bill in SC", 'Airfares to Kochi & Thiruvananthapuram soar, domestic tourists look elsewhere', 'SC on Delhi HC ruling: Should courts be so touchy about criticism?', "Hardik Pandya breaks silence on Jasprit Bumrah: 'He should be ...'", 'From Lauren Sanchez to Katy Perry: Meet the 6 women who are all set to fly to space on Jeff Bezos’s New Shepard rocket', 'PM Narendra Modi meets Thai royalty: All about the current King and Queen of Thailand', 'J&K Police identifies 200 social media handles involved in radicalisation', 'Gali Surjan Singh: A historic street to be showcased at Mela Baharan in Lahore', 'Neither parent has right to tweak kid’s birth certificate to satisfy ego: Bombay HC', 'Study feasibility of trade in local currency, says PM Modi’s Bimstec action plan', "IPL 2025: Digvesh Rathi's tight spell trumps Hardik Pandya's all-round show as LSG down MI", "'Black badge protest, top court challenge': How DMK's M K Stalin is trying to make most of Waqf politics", 'Multivitamin to magnesium: 3 most common vitamin supplements that can land us in danger', 'Watch: Masked agitators trash Turning Point USA event at UC Davis, assault students', 'Madhya Pradesh youth falls into well, 7 jump one by one to save him, all die', "Trump's tariffs: Exporters seek restoration of benefits, bilateral deal push", 'Infra.Market eyes $1bn IPO, $5bn valuation', "'Not everyone can afford air purifier': Why SC refused to reconsider ban on crackers in NCR", '400 million gallons of sewage heading for US; Why won’t Mexico stop it?', 'Trump’s 2025 immigration update: Stricter Green Card rules for married couples announced', "April's Full Pink Moon: How, where and when to see the celestial event", 'India promises to support Myanmar towards switch to democratic future']

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
        for article in new_articles:
            tweets = create_tweet_thread(article)
            success = await post_tweet_thread(tweets,article['image_url'])
            if success:
                posted_titles.append(article['title'])
                # print(posted_titles)
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