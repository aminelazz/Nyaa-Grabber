import json
import os

import random
import requests
import subprocess
from bs4 import BeautifulSoup
from interactions import AutoArchiveDuration, Client, Intents
from interactions import listen, slash_command, slash_option, SlashContext, OptionType, SlashCommandChoice, Activity, ActivityType, Embed, File
from interactions import BaseChannel, ThreadChannel, Webhook, WebhookMixin
from interactions import Activity, ActivityType, Embed, File
from interactions import Modal, ModalContext, ParagraphText, ShortText
from interactions import Button, ButtonStyle, ComponentContext, component_callback
from interactions.ext.paginators import Paginator
from dotenv import load_dotenv
import re

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
APP_ID = os.getenv('APP_ID')

bot = Client(token=TOKEN, intents=Intents.ALL)

grabber_subprocess = None
check_mark = ":white_check_mark:"
red_square = ":red_square:"
information_source = ":information_source:"
link_emoji = "🔗"
magnet_emoji = "🧲"
torrent_emoji = "📥"

# Get commands
def get_commands():
    """Get commands through GET request"""
    bot_token = TOKEN
    app_id = APP_ID

    # URL to make the GET request to
    url = f'https://discord.com/api/v9/applications/{app_id}/commands'

    # Construct the headers with the authorization token
    headers = {
        'Authorization': f'Bot {bot_token}'
    }

    # Perform the GET request with the headers
    response = requests.get(url, headers=headers).json()

    return response

# On start
@listen()
async def on_startup():
    print(
        f'{bot.user} is connected to the following guilds:\n'
    )

    for guild in bot.guilds:
        print(
            f'{guild.name} (id: {guild.id})'
        )
    await bot.change_presence(activity=Activity(type=ActivityType.WATCHING,name="One Piece"))


# Display all cmds
@slash_command(
        name='cmds', 
        description='Display avaible commands',
        )
async def cmds(ctx: SlashContext):
    if ctx.author == bot.user:  # Ignore bot's own messages
        return

    embed = Embed(
        title="All Nyaa Grabber Commands",
        description="Here is all the available commands for Nyaa Grabber:",
        color="#3498db"  # You can set the color of the embed
    )

    cmds = get_commands()

    embed.set_thumbnail(url=bot.user.avatar.url)
    # embed.set_author(name='Available commands', icon_url=bot.user.avatar.url)
    for cmd in cmds:
        embed.add_field(name=f'/{cmd["name"]}', value=cmd["description"], inline=False)
    # embed.set_footer(text="This is the footer of the embed.")

    await ctx.send(content=None, embeds=[embed])
    
# Get raws cmd
@slash_command(
        name="get_raws", 
        description="A command that get raws from nyaa.si based on parameters",
        )
@slash_option(
    name="raw_provider",
    description="Raw provider name (erai-raws, subsplease, ember...)",
    required=True,
    opt_type=OptionType.STRING,
)
@slash_option(
    name="anime_name",
    description="Anime name",
    required=True,
    opt_type=OptionType.STRING,
)
@slash_option(
    name="nbr_raws",
    description="Number of raws",
    required=False,
    opt_type=OptionType.INTEGER,
    min_value=1,
    max_value=6,
)
@slash_option(
    name="offset",
    description="Number of raws to skip",
    required=False,
    opt_type=OptionType.INTEGER,
)
@slash_option(
    name="ep_number",
    description="Episode number",
    required=False,
    opt_type=OptionType.INTEGER,
)
async def get_raws(ctx: SlashContext, raw_provider:str, anime_name:str, ep_number:int = "", offset:int = 0, nbr_raws:int = 1):
    # Add typing effect
    await ctx.defer()

    # message = await ctx.send(f"Please wait...")

    url = f"https://nyaa.si/?f=0&c=0_0&q={raw_provider}+{anime_name}+{ep_number}+1080&s=id&o=asc"
    nyaa_request = requests.get(url)
    nyaa_soup = BeautifulSoup(nyaa_request.content, 'html.parser')

    # Get tbody
    nyaa_tbody = nyaa_soup.find('tbody')
    if not nyaa_tbody:
        await ctx.send(f"No raws found for **{anime_name}** episode **{ep_number}**.")
        return
    
    # Get rows
    nyaa_rows = nyaa_tbody.find_all('tr')[offset : offset + nbr_raws] # The offset is the number of raws to skip

    raws = []

    # Iterate over rows
    for row in nyaa_rows:
        # Get link
        cell = row.find_all('td')[1]
        a = cell.find_all('a')

        # Check if there is 2 a attributes
        if len(a) > 1:
            link = a[1]['href']
            title = a[1]['title']
        else:
            link = a[0]['href']
            title = a[0]['title']

        # Get magnet and torrent link
        second_cell = row.find_all('td')[2]

        # Links
        link = f"https://nyaa.si{link}"
        torrent_link = f"https://nyaa.si{second_cell.find_all('a')[0]['href']}"
        magnet_link = second_cell.find_all('a')[1]['href']

        # Replace the magnet link
        magnet_link = magnet_link.replace("magnet:?xt=", "https://nyaasi-to-magnet.up.railway.app/nyaamagnet/")
        magnet_link = re.sub(r"&dn=.+", "", magnet_link)

        # Print the title and the link
        raws.append(f"""
***{title}***:
[{link_emoji} Link]({link}) | [{torrent_emoji} Torrent]({torrent_link}) | [{magnet_emoji} Magnet]({magnet_link})""")
        # await ctx.send(f"You input {integer_option}")

    # for raw in raws:
    #     await ctx.send(content=raw, suppress_embeds=True)

    await ctx.send(content="\n".join(raws), suppress_embeds=True)

# Start grabber command
@slash_command(
        name="start_grabber", 
        description="A command to start the grabber subprocess",    
)
async def start_grabber(ctx: SlashContext):
    # Add typing effect
    await ctx.defer()

    # Check first if "grabber_data.json" exists
    try:
        with open('grabber_data.json', 'r+') as f:
            grabber_data = json.load(f)
    except FileNotFoundError:
        await ctx.send("Please configure at least one channel to start the proccess.")
        print("Please configure at least one channel to start the proccess.")
        return

    message = await ctx.send(f"Starting the grabber subprocess...")
    global grabber_subprocess
    global check_mark
    global red_square
    global information_source

    if grabber_subprocess is None:
        # Start the processing script using subprocess and capture its output
        # with open('output.txt', 'w') as output:
        #     grabber_subprocess = subprocess.Popen('python3.10 -u grabber.py > output.txt 2>&1 &', stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        
        grabber_subprocess = subprocess.Popen(['python3.10', '-u', 'grabber.py'], stdout=open('output.txt', 'w'), stderr=subprocess.STDOUT, preexec_fn=os.setpgrp)
        # grabber_subprocess = subprocess.Popen(['python', '-u', 'grabber.py'])

        await message.edit(content=f"{check_mark} The grabber subprocess **started successfully**")
    else:
        await message.edit(content=f"{information_source} The grabber subprocess is **already running**")
        return

# Stop grabber command
@slash_command(
        name="stop_grabber", 
        description="A command to stop the grabber subprocess",    
)
async def stop_grabber(ctx: SlashContext):
    # Add typing effect
    await ctx.defer()

    message = await ctx.send("Stopping the grabber subprocess...")
    global grabber_subprocess
    global check_mark
    global red_square
    global information_source

    if grabber_subprocess:
        grabber_subprocess.kill()  # Terminate the subprocess
        grabber_subprocess = None

        await message.edit(content=f"{red_square} The grabber subprocess **stopped**")
    else:
        await message.edit(content=f"{information_source} The grabber subprocess is **not running**")

# Check grabber command
@slash_command(
        name="check_grabber",
        description="A command to check if the grabber subprocess is running",
        )
async def check_grabber(ctx: SlashContext):
    # Add typing effect
    await ctx.defer()

    message = await ctx.send("Checking...")
    global grabber_subprocess
    global check_mark
    global red_square
    global information_source

    if grabber_subprocess:
        running = grabber_subprocess.poll()
        if running is None:
            await message.edit(content=f"{check_mark} The grabber subprocess is **running**")
        else:
            grabber_subprocess = None
            await message.edit(content=f"{red_square} The grabber subprocess is **not running**")
    else:
        await message.edit(content=f"{red_square} The grabber subprocess is **not running**")


@slash_command(name="add_anime", description="Add anime to grabber")
async def add_anime(ctx: SlashContext): 
    try:
        # Create a modal
        anime_modal = Modal(
            ShortText(
                label="Anime ID",
                custom_id="mal_id",
                placeholder="Enter the anime ID",
                min_length=1,
                max_length=8
            ),
            ParagraphText(
                label="Raw providers (optional)",
                custom_id="raw_providers",
                placeholder="Enter the raw providers, every provider in line",
                required=False
            ),
            title="Add anime to grabber",
        )

        # Send the modal
        await ctx.send_modal(modal=anime_modal)

        # Wait for the modal response
        modal_ctx:ModalContext = await ctx.bot.wait_for_modal(anime_modal)
        # Extract the responses
        mal_id:int = modal_ctx.responses["mal_id"]
        raw_providers:list = modal_ctx.responses["raw_providers"].split("\n")

        # Add typing effect
        await modal_ctx.defer()

        # Check if grabber_data.json exists and read it
        if os.path.isfile("grabber_data.json"):
            with open("grabber_data.json", "r") as f:
                grabber_data = json.load(f)
                # Check if mal_id already exists
                if mal_id in grabber_data:
                    channel_id:str = grabber_data[mal_id]["channel_id"]
                    await modal_ctx.send(content=f"Anime with id **{mal_id}** is already configured in <#{channel_id}>", suppress_embeds=True)
                    return

                # Check if the channel is already configured
                for grabber in grabber_data.values():
                    if str(grabber["channel_id"]) == str(ctx.channel_id):
                        await modal_ctx.send(content=f"This channel is already configured to grab **{grabber['anime']['mal_id']}** - **{grabber['anime']['title']}**.", suppress_embeds=True)
                        return

        # Create grabber_data.json if not exists
        elif not os.path.isfile("grabber_data.json"):
            with open("grabber_data.json", "w") as f:
                json.dump({}, f)
        # Read the file and put its data in the grabber_data dictionnary
        with open("grabber_data.json", "r") as f:
            grabber_data = json.load(f)

        # Send a get request to MAL using the Jikan API
        response = requests.get(f"https://api.jikan.moe/v4/anime/{mal_id}")

        # Check if the mal_id is valid
        status_code = response.status_code
        if status_code != 200:
            await modal_ctx.send(content=f"Error {status_code}: {response.reason}", suppress_embeds=True)
            return

        # Get the anime infos
        anime_infos = response.json()["data"]

        # Create the titles list
        titles = []
        for title in anime_infos["titles"]:
            titles.append(title["title"])

        # Create the anime object
        anime = {
            "title": anime_infos["title"],
            "titles": titles,
            # "synopsis": anime_infos["synopsis"],
            "episodes": anime_infos["episodes"],
            "season": anime_infos["season"],
            "year": anime_infos["year"],
            # "source": anime_infos["source"],
            "status": anime_infos["status"],
            "score": anime_infos["score"],
            # "rank": anime_infos["rank"],
            # "trailer_url": anime_infos["trailer"]["url"],
            # "background": anime_infos["background"],
            "mal_id": anime_infos["mal_id"],
            "url": anime_infos["url"],
            "image_url": anime_infos["images"]["webp"]["image_url"],
            "type": anime_infos["type"],
            "duration": anime_infos["duration"],
            # "rating": anime_infos["rating"],
            "broadcast": anime_infos["broadcast"]["string"],
        }



        # Create a thread
        thread = await ctx.channel.create_public_thread(name="Raws", auto_archive_duration=AutoArchiveDuration.ONE_WEEK)
        thread_id = thread.id

        # Send a message in the thread
        await thread.send(content = "This is the first message in the **Raws** thread.\n"
                                    "This thread will be used to send raws links so that it would be separated from the parent channel.")

        # Set the webhook name
        webhook_name = f"{anime['title'][:60]}..." if len(anime["title"]) > 60 else anime["title"]
    
        # Download the image
        try:
            image_request = requests.get(anime["image_url"])
            image = image_request.content
        except Exception as e:
            print(e)

        # Create the webhook
        # Try to create the webhook with the image
        # If it fails, create the webhook without the image
        try:
            webhook = await Webhook.create(client=bot, channel=ctx.channel, name=webhook_name, avatar=image)
        except Exception as e:
            print(e)
            webhook = await Webhook.create(client=bot, channel=ctx.channel, name=webhook_name)
        
        # Get the webhook url
        webhook_id = webhook.id
        webhook_url = webhook.url
        webhook_token = webhook.token

        # Delete the image from the memory
        try:
            del image
        except Exception as e:
            print(e)

        # Create the grabber object
        grabber_object = {
            "anime": anime,
            "raw_providers": raw_providers,
            "channel_id": ctx.channel_id,
            "thread_id": thread_id,
            "webhook_id": webhook_id,
            "webhook_url": webhook_url,
            "webhook_token": webhook_token,
        }

        # Add the anime to the grabber_data dictionnary
        grabber_data[anime["mal_id"]] = grabber_object
        # Write the grabber_data dictionnary to the file
        with open("grabber_data.json", "w") as f:
            json.dump(grabber_data, f, indent=4)

        # Create the content string
        content = f"""
**Title:** {anime['title']}
**Episodes:** {anime['episodes']}
**Season:** {anime['season']}
**Year:** {anime['year']}
**Status:** {anime['status']}
**Score:** {anime['score']}
**MAL ID:** {anime['mal_id']}
**URL:** {anime['url']}
**Type:** {anime['type']}
**Duration:** {anime['duration']}
**Broadcast:** {anime['broadcast']}
**Raws chosen:** {', '.join(raw_providers)}

The thread {thread.mention} and webhook **{webhook.name}** has been created successfully.
"""

        # Send the content in the modal
        await modal_ctx.send(content= content,
                            suppress_embeds=True)
    except Exception as e:
        print(e)
        await modal_ctx.send(content=f"Error: {e}", suppress_embeds=True)

@slash_command(name="reset_channel", description="Reset current channel configuration")
async def reset_channel(ctx: SlashContext):
    try:
        # Add typing effect
        await ctx.defer()

        # Check if grabber_data.json exists and read it
        if os.path.isfile("grabber_data.json"):
            with open("grabber_data.json", "r") as f:
                grabber_data = json.load(f)
        else:
            await ctx.send(content="No channel is configured to be reset.", suppress_embeds=True)
            return
        
        # Check if grabber_data is an empty dict
        if not grabber_data:
            await ctx.send(content="No channel is configured to be reset.", suppress_embeds=True)
            return
        
        found_channel = False

        # Check if the channel is already configured
        for grabber in grabber_data.values():
            channel_id:str = grabber["channel_id"]
            thread_id:str = grabber["thread_id"]
            webhook_id:str = grabber["webhook_id"]
            webhook_token:str = grabber["webhook_token"]
            webhook_url:str = grabber["webhook_url"]

            # print(channel_id)
            # print(ctx.channel_id)
            if str(channel_id) == str(ctx.channel_id):
                found_channel = True

                # Delete the thread
                thread:ThreadChannel = await bot.fetch_channel(thread_id)
                await thread.delete()

                # Delete the webhook
                webhook:Webhook = Webhook.from_url(webhook_url, bot)
                await webhook.delete()

                # Delete the grabber from the grabber_data
                del grabber_data[str(grabber["anime"]["mal_id"])]

                # Write the grabber_data dictionnary to the file
                with open("grabber_data.json", "w") as f:
                    json.dump(grabber_data, f, indent=4)

                # Write in the channel the confirmation
                await ctx.send(content=f"The channel has been reset successfully.", suppress_embeds=True)
                return
            
        # In case the channel is not configured
        if not found_channel:
            # print("else")
            await ctx.send(content="This channel is no longer configured.", suppress_embeds=True)
    except Exception as e:
        print(e)
        await ctx.send(content=f"Error: {e}", suppress_embeds=True)

@slash_command(name="edit_channels_raws", description="Edit current channel configuration")
async def edit_channel(ctx: SlashContext):
    try:
        # Add typing effect
        await ctx.defer()

        # Check if grabber_data.json exists and read it
        if os.path.isfile("grabber_data.json"):
            with open("grabber_data.json", "r") as f:
                grabber_data = json.load(f)
        else:
            await ctx.send(content="The grabber file doesn't exist.", suppress_embeds=True)
            return
        
        # Check if grabber_data is an empty dict
        if not grabber_data:
            await ctx.send(content="The grabber file is empty.", suppress_embeds=True)
            return
        
        found_channel = False

        # Check if the channel is already configured
        for grabber in grabber_data.values():
            anime_title:str = grabber["anime"]["title"]
            mal_id:str = grabber["anime"]["mal_id"]
            url:str = grabber["anime"]["url"]
            channel_id:str = grabber["channel_id"]
            raw_providers:str = ', '.join(grabber["raw_providers"])

            # Get current channel entry
            if str(channel_id) == str(ctx.channel_id):
                found_channel = True
                # Create an edit button to send with the message
                edit_button = Button(
                    style=ButtonStyle.PRIMARY,
                    label="Edit",
                    custom_id="edit",
                )

                content = f"""
Current channel configuration:

**Title:** {anime_title}
**MAL ID:** {mal_id}
**URL:** {url}
**Raws chosen:** {raw_providers}
"""

                # Write in the channel the raws providers
                await ctx.send(content=content, components=edit_button, suppress_embeds=True)
                return

        # In case the channel is not configured
        if not found_channel:
            await ctx.send(content="The current channel isn't configured.", suppress_embeds=True)
    except Exception as e:
        print(e)
        await ctx.send(content=f"Error: {e}", suppress_embeds=True)

# Edit button event
@component_callback("edit")
async def edit_button(ctx: ComponentContext):
    try:

        # Check if grabber_data.json exists and read it
        if os.path.isfile("grabber_data.json"):
            with open("grabber_data.json", "r") as f:
                grabber_data = json.load(f)
        else:
            await ctx.send(content="The grabber file doesn't exist.", suppress_embeds=True)
            return
        
        # Check if grabber_data is an empty dict
        if not grabber_data:
            await ctx.send(content="The grabber file is empty.", suppress_embeds=True)
            return

        # Check if the channel is already configured
        for grabber in grabber_data.values():
            anime_title:str = grabber["anime"]["title"]
            mal_id:str = grabber["anime"]["mal_id"]
            url:str = grabber["anime"]["url"]
            channel_id:str = grabber["channel_id"]
            raw_providers:str = '\n'.join(grabber["raw_providers"])

            found_channel = False

            # Get current channel entry
            if str(channel_id) == str(ctx.channel_id):
                found_channel = True

                # Create a modal
                anime_modal = Modal(
                    ParagraphText(
                        label="Raw providers (optional)",
                        custom_id="raw_providers",
                        placeholder="Enter the raw providers, every provider in line",
                        required=False,
                        value=raw_providers,
                    ),
                    title="Edit anime configuration",
                )

                # Send the modal
                await ctx.send_modal(modal=anime_modal)

                # Wait for the modal response
                modal_ctx:ModalContext = await ctx.bot.wait_for_modal(anime_modal)
                # Extract the responses
                raw_providers:list = modal_ctx.responses["raw_providers"].split("\n")

                # Add typing effect
                await modal_ctx.defer()

                # Save the new raw_providers
                grabber["raw_providers"] = raw_providers

                # Write the grabber_data dictionnary to the file
                with open("grabber_data.json", "w") as f:
                    json.dump(grabber_data, f, indent=4)

                # Send to channel
                content = f"""
The raws providers has been updated successfully.

**Raw providers:** {', '.join(raw_providers)}
"""

                # Send the content in the modal
                await modal_ctx.send(content= content,
                                    suppress_embeds=True)
                return
            
        # In case the channel is not configured
        if not found_channel:
            # print("else")
            await ctx.send(content="This channel is no longer configured.", suppress_embeds=True)
    except Exception as e:
        print(e)
        await ctx.send(content=f"Error: {e}", suppress_embeds=True)

# Display all grabbers cmd
@slash_command(
        name='grabbers', 
        description='Display all grabbers',
        )
async def grabbers(ctx: SlashContext):
    if ctx.author == bot.user:
        return
    
    # Add typing effect
    await ctx.defer()

    # Check if grabber_data.json exists and read it
    if os.path.isfile("grabber_data.json"):
        with open("grabber_data.json", "r") as f:
            grabber_data = json.load(f)
    else:
        await ctx.send(content="No channel is configured.", suppress_embeds=True)
        return

    # Check if grabber_data is an empty dict
    if not grabber_data:
        await ctx.send(content="No channel is configured.", suppress_embeds=True)
        return
    
    embeds = []

    # Iterate over grabbers
    for grabber in grabber_data.values():
        # Create an embed
        embed = Embed(
            title="All grabbers",
            description="Here is all the available grabbers:",
            color="#3498db",  # You can set the color of the embed
            thumbnail=grabber["anime"]["image_url"]
        )

        # Add a field for each grabber
        anime_title:str = grabber["anime"]["title"]
        mal_id:str = grabber["anime"]["mal_id"]
        url:str = grabber["anime"]["url"]
        channel_id:str = grabber["channel_id"]
        raw_providers:str = ', '.join(grabber["raw_providers"])

        embed.add_field(name=f'{anime_title}', value=f"**MAL ID:** {mal_id}\n**URL:** {url}\n**Raws chosen:** {raw_providers}\n**Channel:** <#{channel_id}>", inline=False)

        # Add the embed to the embeds list
        embeds.append(embed)

    # Create a paginator
    paginator = Paginator.create_from_embeds(bot, *embeds)

    # Send the paginator
    await paginator.send(ctx)



# Get Guild Id
# @slash_command(
#         name="guild_id",
#         description="Get the guild id",
#         )
# async def guild_id(ctx: SlashContext):
#     # Add typing effect
#     await ctx.defer()

#     await ctx.send(f"Guild id: {ctx.guild_id}")

bot.start()