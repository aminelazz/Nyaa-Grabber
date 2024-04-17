import schedule
import feedparser
import time
import os
import requests
import json
from fuzzywuzzy import fuzz
from bs4 import BeautifulSoup
import re

link_emoji = "🔗"
magnet_emoji = "🧲"
torrent_emoji = "📥"

def job(send):
    # Load previously fetched feed data
    try:
        with open('previous_feed_data.json', 'r+') as f:
            previous_feed_data = json.load(f)
    except FileNotFoundError:
        previous_feed_data = []

    # Get the feed from https://nyaa.si/rss using feedparser package
    feed = feedparser.parse('https://nyaa.si/rss?c=1_0')

    # Get only entries that have "Anime" in nyaa_category
    # anime_entries = [entry for entry in feed.entries if "Anime" in entry.nyaa_category]

    # Check if the feed is new
    new_items = []
    for entry in feed.entries:
        raw = {
            "title": entry.title,
            "link": entry.id
        }
        if raw not in previous_feed_data:
            new_items.append(raw)

    # Process the new feed items here (e.g., print or save to a database)
    for item in new_items:
        print("New Feed Title:", item["title"])
        print("New Feed Link:", item["link"])
        print()

    # Update the previous feed data with the new data
    previous_feed_data = new_items + previous_feed_data

    # Save the updated feed data for the next run
    with open('previous_feed_data.json', 'w+') as f:
        json.dump(previous_feed_data[:100], f, indent=4)
    # Perform loop on "grabber_data.json" and match strings
    # with "previous_feed_data.json" and download the torrent
    # if the string matches
    with open('grabber_data.json', 'r+') as f:
        grabber_data:dict = json.load(f)

    for grabber in grabber_data.values():
        anime = grabber["anime"]
        raw_providers = grabber["raw_providers"]
        webhook_url = f"{grabber['webhook_url']}?thread_id={grabber['thread_id']}"

        matched_torrents = []
        # loop over titles to check if the torrent name matches
        for title in anime["titles"]:
            for item in new_items:
                if fuzz.token_set_ratio(title, item["title"]) > 70:
                    if not raw_providers:
                        matched_torrents.append(item)
                        continue
                    else:
                        # match raw providers
                        for raw_provider in raw_providers:
                            if str.lower(raw_provider) in str.lower(item["title"]):
                                # Add the torrent to the matched torrents
                                matched_torrents.append(item)
                                # break the loop
                                # break

        # Remove duplicates
        unique_list = []
        for item in matched_torrents:
            if item not in unique_list:
                unique_list.append(item)
        
        # Send the message to the channel
        if send:
            # Send it to the channel
            if unique_list:
                # Send the message to the channel
                message = f"New episode of {anime['title']} is out!\n\n"
                for torrent in unique_list:
                    # Get the magnet link
                    magnet_link, torrent_link = get_magnet_link(torrent["link"])
                    raw = f"""
***{torrent['title']}***:
[{link_emoji} Link]({torrent['link']})   |   [{torrent_emoji} Torrent]({torrent_link})   |   [{magnet_emoji} Magnet]({magnet_link})"""
                    message += f"{raw}\n\n"
                    
                    # Log
                    print(f"Sending {torrent['title']} with magnet...")

                # Send the message to the channel
                requests.post(webhook_url, json={"content": message})


# Function to scrap the link and get magnet link
def get_magnet_link(link):
    try:
        # Get the page content
        page = requests.get(link)
        soup = BeautifulSoup(page.content, 'html.parser')
        # Get the magnet link
        panel_footer = soup.find('div', {'class': 'panel-footer clearfix'})
        torrent_link = f"https://nyaa.si{panel_footer.findAll('a')[0]['href']}"
        # Get the magnet link
        magnet_link = panel_footer.findAll('a')[1]['href']
        # Replace the magnet link
        magnet_link = magnet_link.replace("magnet:?xt=", "https://nyaasi-to-magnet.up.railway.app/nyaamagnet/")
        magnet_link = re.sub(r"&dn=.+", "", magnet_link)
        return magnet_link, torrent_link
    except Exception as e:
        print(f"An error occured while getting magnet link: {e}")
        return None, None

# Only fetch without sending
job(False)

# Schedule the job to run every 5 minutes
schedule.every(5).minutes.do(lambda: job(True))

# Keep the script running
while True:
    schedule.run_pending()
    time.sleep(1)