import feedparser
import json

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