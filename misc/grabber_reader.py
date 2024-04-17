import json


with open('grabber_data.json', 'r+') as f:
    grabber_data:dict = json.load(f)

if "1108178912292376577" in grabber_data:
    print("Yes")

exists = False
for grabber in grabber_data.values():
    # print(grabber)
    anime = grabber["anime"]
    channel_id = grabber["channel_id"]
    print(channel_id)
    # print(anime)
    if str(channel_id) == "1108178912292376577":
        exists = True
        print("Yes")
        break
    for title in anime["titles"]:
        print(title)
