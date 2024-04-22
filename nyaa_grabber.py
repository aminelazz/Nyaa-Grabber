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
cross_mark = "❌"

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

# Get Anime infos embed
def get_embed(grabber):
    """Get the anime infos in an embed"""
    # Create the titles list
    titles = []
    for title in grabber["anime"]["titles"]:
        titles.append(title)

    # Create the embed
    embed = Embed(
        title="Current channel configuration",
        # description="Here are all the available grabbers:",
        color="#3498db",  # You can set the color of the embed
        thumbnail=grabber["anime"]["image_url"]
    )

    # Check if raw_providers is empty
    # Note that the list may have one entry which can be empty
    # In that case, the list is considered empty too
    if len(grabber["raw_providers"]) != 0 and grabber["raw_providers"][0] != "":
        raw_providers = ', '.join(grabber["raw_providers"])
    else:
        raw_providers = "None"

    # Debug
    # print(f"Length: {len(grabber['raw_providers'])}")
    # print(f"Raw providers: {raw_providers}")

    # Add the fields to the embed
    embed.add_field(name="Title", value=grabber["anime"]["title"], inline=False)
    embed.add_field(name="Titles", value="- " + "\n- ".join(titles), inline=False)
    embed.add_field(name="Episodes", value=grabber["anime"]["episodes"], inline=True)
    embed.add_field(name="Season", value=grabber["anime"]["season"], inline=True)
    embed.add_field(name="Year", value=grabber["anime"]["year"], inline=True)
    embed.add_field(name="Status", value=grabber["anime"]["status"], inline=True)
    embed.add_field(name="Score", value=grabber["anime"]["score"], inline=True)
    embed.add_field(name="Type", value=grabber["anime"]["type"], inline=True)
    embed.add_field(name="Duration", value=grabber["anime"]["duration"], inline=True)
    embed.add_field(name="Broadcast", value=grabber["anime"]["broadcast"], inline=True)
    embed.add_field(name="MAL ID", value=grabber["anime"]["mal_id"], inline=True)
    embed.add_field(name="URL", value=grabber["anime"]["url"], inline=False)
    embed.add_field(name="Raws chosen", value=raw_providers, inline=True)
    embed.add_field(name="Fetch", value=grabber["fetch"] if ("fetch" in grabber.keys()) else "True", inline=True)
    embed.add_field(name="Thread", value=f"<#{grabber['thread_id']}>", inline=True)

    return embed

# Set anime buttons
def get_buttons(fetch: bool):
    """Set the buttons for the embed"""
    # Create an edit button to send with the message
    edit_button = Button(
        style=ButtonStyle.PRIMARY,
        label="Edit",
        custom_id="edit",
    )

    # Create an enable/disable button to send with the message
    enable_button = Button(
        style=ButtonStyle.GREEN if not fetch else ButtonStyle.DANGER,
        label="Enable" if not fetch else "Disable",
        custom_id="enable",
    )

    # Create a delete button to send with the message
    delete_button = Button(
        style=ButtonStyle.DANGER,
        label="Delete",
        custom_id="delete",
    )

    return [edit_button, enable_button, delete_button]

# Set grabber subprocess buttons
def get_grabber_buttons(is_running: bool):
    """Set the buttons for the embed"""
    # Create a start button to send with the message
    start_button = Button(
        style=ButtonStyle.PRIMARY,
        label="Start",
        custom_id="start_grabber",
        disabled=is_running,
    )

    # Create a stop button to send with the message
    stop_button = Button(
        style=ButtonStyle.DANGER,
        label="Stop",
        custom_id="stop_grabber",
        disabled=not is_running,
    )

    return [start_button, stop_button]

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

# Get grabber status
@slash_command(
        name="grabber_status",
        description="A command to display grabber status",
        )
async def grabber_status(ctx: SlashContext):
    # Add typing effect
    await ctx.defer()

    global grabber_subprocess
    global check_mark
    global red_square
    global information_source

    is_running = False

    if grabber_subprocess:
        running = grabber_subprocess.poll()
        if running is None:
            is_running = True
            content=f"{check_mark} The grabber subprocess is **running**"
        else:
            grabber_subprocess = None
            content=f"{red_square} The grabber subprocess is **not running**"
    else:
        content=f"{red_square} The grabber subprocess is **not running**"

    # Get the buttons
    buttons = get_grabber_buttons(is_running)

    await ctx.send(content=content, components=buttons)

# Start grabber button event
@component_callback("start_grabber")
async def start_grabber_button(ctx: ComponentContext):
    # Add typing effect
    # await ctx.defer()

    # Check first if "grabber_data.json" exists
    try:
        with open('grabber_data.json', 'r+') as f:
            grabber_data = json.load(f)
    except FileNotFoundError:
        await ctx.message.delete()
        await ctx.send("Please configure at least one channel to start the proccess.")
        print("Please configure at least one channel to start the proccess.")
        return

    global grabber_subprocess
    global check_mark
    global red_square
    global information_source

    is_running = False

    if grabber_subprocess is None:
        # Start the processing script using subprocess and capture its output
        # with open('output.txt', 'w') as output:
        #     grabber_subprocess = subprocess.Popen('python3.10 -u grabber.py > output.txt 2>&1 &', stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        
        # grabber_subprocess = subprocess.Popen(['python3.10', '-u', 'grabber.py'], stdout=open('output.txt', 'w'), stderr=subprocess.STDOUT, preexec_fn=os.setpgrp)
        grabber_subprocess = subprocess.Popen(['python', '-u', 'grabber.py'])

        is_running = True
        content=f"{check_mark} The grabber subprocess **started successfully**"
    else:
        content=f"{information_source} The grabber subprocess is **already running**"

    # Get the buttons
    buttons = get_grabber_buttons(is_running)

    await ctx.edit_origin(content=content, components=buttons)

# Stop grabber button event
@component_callback("stop_grabber")
async def stop_grabber_button(ctx: ComponentContext):
    # Add typing effect
    # await ctx.defer()

    global grabber_subprocess
    global check_mark
    global red_square
    global information_source

    is_running = False

    if grabber_subprocess:
        grabber_subprocess.kill()
        grabber_subprocess = None

        content=f"{red_square} The grabber subprocess **stopped**"
    else:
        content=f"{information_source} The grabber subprocess is **not running**"

    # Get the buttons
    buttons = get_grabber_buttons(is_running)

    await ctx.edit_origin(content=content, components=buttons)

# Add anime command
@slash_command(name="add_anime", description="Add anime to grabber")
async def add_anime(ctx: SlashContext): 
    try:
        # Get current guild id
        guild_id = str(ctx.guild_id)

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

                if guild_id in grabber_data.keys():
                    guild_data = grabber_data[guild_id]
                else:
                    guild_data = {}

                # Check if mal_id already exists
                if mal_id in guild_data:
                    channel_id:str = guild_data[mal_id]["channel_id"]
                    await modal_ctx.send(content=f"Anime with id **{mal_id}** is already configured in <#{channel_id}>", suppress_embeds=True)
                    return

                # Check if the channel is already configured
                for grabber in guild_data.values():
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
            "fetch": True,
        }

        # Add the anime to the grabber_data dictionnary
        if guild_id not in grabber_data.keys():
            grabber_data[guild_id] = {}

        grabber_data[guild_id][anime["mal_id"]] = grabber_object
        # Write the grabber_data dictionnary to the file
        with open("grabber_data.json", "w") as f:
            json.dump(grabber_data, f, indent=4)

        # Get embed
        embed = get_embed(grabber_object)

        # Create the buttons
        buttons = get_buttons(True)

        # Create the content string
        content = f"\n\nThe thread {thread.mention} and webhook **{webhook.name}** has been created successfully."

        # Send the content in the modal
        await modal_ctx.send(content= content,
                            embeds=[embed],
                            components=buttons,
                            suppress_embeds=False)
    except Exception as e:
        print(e)
        await modal_ctx.send(content=f"Error: {e}", suppress_embeds=True)

# Infos command
@slash_command(name="infos", description="Display current channel configuration")
async def infos(ctx: SlashContext):
    try:
        # Get current guild id
        guild_id = str(ctx.guild_id)

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

        # Check if current guild is in the grabber_data
        if guild_id not in grabber_data.keys():
            await ctx.send(content="No channel is configured to be reset.", suppress_embeds=True)
            return
        
        found_channel = False

        # Check if the channel is already configured
        for grabber in grabber_data[guild_id].values():
            anime_title:str = grabber["anime"]["title"]
            mal_id:str = grabber["anime"]["mal_id"]
            url:str = grabber["anime"]["url"]
            thumbnail:str = grabber["anime"]["image_url"]
            channel_id:str = grabber["channel_id"]
            raw_providers:str = ', '.join(grabber["raw_providers"])

            fetch:bool = grabber["fetch"] if ("fetch" in grabber.keys()) else True

            # Get current channel entry
            if str(channel_id) == str(ctx.channel_id):
                found_channel = True

                # Get embed
                embed = get_embed(grabber)

                # Create the buttons
                buttons = get_buttons(fetch)

                # Write in the channel the raws providers
                await ctx.send(embeds=[embed], components=buttons, suppress_embeds=False)
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
        # Get current guild id
        guild_id = str(ctx.guild_id)

        # Check if grabber_data.json exists and read it
        if os.path.isfile("grabber_data.json"):
            with open("grabber_data.json", "r") as f:
                grabber_data = json.load(f)
        else:
            await ctx.message.delete()
            await ctx.send(content="The grabber file doesn't exist.", suppress_embeds=True)
            return
        
        # Check if grabber_data is an empty dict
        if not grabber_data:
            await ctx.message.delete()
            await ctx.send(content="The grabber file is empty.", suppress_embeds=True)
            return

        # Check if current guild is in the grabber_data
        if guild_id not in grabber_data.keys():
            await ctx.message.delete()
            await ctx.send(content="No channel is configured to be reset.", suppress_embeds=True)
            return

        found_channel = False

        # Check if the channel is already configured
        for grabber in grabber_data[guild_id].values():
            anime_title:str = grabber["anime"]["title"]
            anime_titles:str = '\n'.join(grabber["anime"]["titles"])
            mal_id:str = grabber["anime"]["mal_id"]
            url:str = grabber["anime"]["url"]
            channel_id:str = grabber["channel_id"]
            raw_providers:str = '\n'.join(grabber["raw_providers"])
            fetch:bool = grabber["fetch"] if ("fetch" in grabber.keys()) else True

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
                    ParagraphText(
                        label="Titles",
                        custom_id="titles",
                        placeholder="Enter the titles, every title in line",
                        required=True,
                        value=anime_titles
                    ),
                    title="Edit anime configuration",
                )

                # Send the modal
                await ctx.send_modal(modal=anime_modal)

                # Wait for the modal response
                modal_ctx:ModalContext = await ctx.bot.wait_for_modal(anime_modal)
                # Extract the responses
                raw_providers:list = modal_ctx.responses["raw_providers"].split("\n")
                titles:list = modal_ctx.responses["titles"].split("\n")

                # Add typing effect
                await modal_ctx.defer()

                # Save the new raw_providers
                grabber["raw_providers"] = raw_providers
                grabber["anime"]["titles"] = titles

                # Write the grabber_data dictionnary to the file
                with open("grabber_data.json", "w") as f:
                    json.dump(grabber_data, f, indent=4)

                # Get the new embed
                embed = get_embed(grabber)

                # Create the buttons
                buttons = get_buttons(fetch)

                message = {
                    "content": f"The configuration has been updated successfully.",
                    "embeds": [embed],
                    "components": buttons,
                }

                # Delete the original message
                await ctx.message.delete()

                # Send the content in the modal
                await modal_ctx.send(**message)
                return
            
        # In case the channel is not configured
        if not found_channel:
            # print("else")
            await ctx.message.delete()
            await ctx.send(content="This channel is no longer configured.", suppress_embeds=True)
            return
    except Exception as e:
        print(e)
        await ctx.send(content=f"Error: {e}", suppress_embeds=True)

# Enable/Disable button event
@component_callback("enable")
async def enable_disable_button(ctx: ComponentContext):
    try:
        # Get current guild id
        guild_id = str(ctx.guild_id)

        # Check if grabber_data.json exists and read it
        if os.path.isfile("grabber_data.json"):
            with open("grabber_data.json", "r") as f:
                grabber_data = json.load(f)
        else:
            await ctx.message.delete()
            await ctx.send(content="The grabber file doesn't exist.", suppress_embeds=True)
            return
        
        # Check if grabber_data is an empty dict
        if not grabber_data:
            await ctx.message.delete()
            await ctx.send(content="The grabber file is empty.", suppress_embeds=True)
            return

        # Check if current guild is in the grabber_data
        if guild_id not in grabber_data.keys():
            await ctx.message.delete()
            await ctx.send(content="No channel is configured to be reset.", suppress_embeds=True)
            return

        found_channel = False

        # Check if the channel is already configured
        for grabber in grabber_data[guild_id].values():
            anime_title:str = grabber["anime"]["title"]
            mal_id:str = grabber["anime"]["mal_id"]
            url:str = grabber["anime"]["url"]
            channel_id:str = grabber["channel_id"]
            raw_providers:str = ', '.join(grabber["raw_providers"])
            fetch:bool = grabber["fetch"] if ("fetch" in grabber.keys()) else True

            # Get current channel entry
            if str(channel_id) == str(ctx.channel_id):
                # print("found_channel")
                found_channel = True

                # Enable or disable the fetch
                grabber["fetch"] = not fetch

                # Write the grabber_data dictionnary to the file
                with open("grabber_data.json", "w") as f:
                    json.dump(grabber_data, f, indent=4)

                # Send to channel
                content = f"The fetch has been **{'enabled' if not fetch else 'disabled'}** successfully."
                
                # Get embed
                embed = get_embed(grabber)

                # Create the buttons
                buttons = get_buttons(not fetch)

                # Edit the original message
                await ctx.edit_origin(content=content, embeds=[embed], components=buttons)

        # In case the channel is not configured
        if not found_channel:
            # print("else")
            await ctx.message.delete()
            await ctx.send(content="This channel is no longer configured.", suppress_embeds=True)
            return
    except Exception as e:
        print(e)
        await ctx.send(content=f"Error: {e}", suppress_embeds=True)

# Delete button event
@component_callback("delete")
async def delete_button(ctx: ComponentContext):
    try:
        # Get current guild id
        guild_id = str(ctx.guild_id)

        # Add typing effect
        # await ctx.defer()

        # Check if grabber_data.json exists and read it
        if os.path.isfile("grabber_data.json"):
            with open("grabber_data.json", "r") as f:
                grabber_data: dict = json.load(f)
        else:
            await ctx.message.delete()
            await ctx.send(content="No channel is configured to be reset.", suppress_embeds=True)
            return

        # Check if grabber_data is an empty dict
        if not grabber_data:
            await ctx.message.delete()
            await ctx.send(content="No channel is configured to be reset.", suppress_embeds=True)
            return

        # Check if current guild is in the grabber_data
        if guild_id not in grabber_data.keys():
            await ctx.message.delete()
            await ctx.send(content="No channel is configured to be reset.", suppress_embeds=True)
            return

        found_channel = False

        # Check if the channel is already configured
        for grabber in grabber_data[guild_id].values():
            channel_id:str = grabber["channel_id"]
            thread_id:str = grabber["thread_id"]
            webhook_id:str = grabber["webhook_id"]
            webhook_token:str = grabber["webhook_token"]
            webhook_url:str = grabber["webhook_url"]

            # print(channel_id)
            # print(ctx.channel_id)
            if str(channel_id) == str(ctx.channel_id):
                found_channel = True

                # Create confirmation modal
                confirmation_modal = Modal(
                    ShortText(
                        label="Confirmation (yes/y)",
                        custom_id="confirmation",
                        placeholder="Type 'yes' or 'y' to confirm",
                        min_length=1,
                        max_length=3
                    ),
                    title="Delete channel configuration",
                )

                # Send the modal
                await ctx.send_modal(modal=confirmation_modal)

                # Wait for the modal response
                modal_ctx:ModalContext = await ctx.bot.wait_for_modal(confirmation_modal)

                # Extract the responses
                confirmation:str = modal_ctx.responses["confirmation"]

                # Add typing effect
                # await modal_ctx.defer()

                # Check if the confirmation is correct
                if confirmation.lower() != "yes" and confirmation.lower() != "y":
                    await modal_ctx.send(content="The confirmation is incorrect. The channel configuration won't be deleted.", suppress_embeds=True)
                    return

                # Delete the thread
                thread:ThreadChannel = await bot.fetch_channel(thread_id)
                await thread.delete()

                # Delete the webhook
                webhook:Webhook = Webhook.from_url(webhook_url, bot)
                await webhook.delete()

                # Delete the grabber from the grabber_data
                del grabber_data[guild_id][str(grabber["anime"]["mal_id"])]

                # Write the grabber_data dictionnary to the file
                with open("grabber_data.json", "w") as f:
                    json.dump(grabber_data, f, indent=4)

                # Write in the channel the confirmation
                await ctx.message.delete()
                await modal_ctx.send(content=f"The channel has been reset successfully.", embed=None, components=[])
                return

        # In case the channel is not configured
        if not found_channel:
            await ctx.message.delete()
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
    
    try:
        # Get current guild id
        guild_id = str(ctx.guild_id)

        # Add typing effect
        await ctx.defer()

        # Check if grabber_data.json exists and read it
        if os.path.isfile("grabber_data.json"):
            with open("grabber_data.json", "r") as f:
                grabber_data = json.load(f)
        else:
            await ctx.send(content="No channel is configured in the current guild.", suppress_embeds=True)
            return

        # Check if grabber_data is an empty dict
        if not grabber_data:
            await ctx.send(content="No channel is configured in the current guild.", suppress_embeds=True)
            return

        # Check if current guild is in the grabber_data
        if guild_id not in grabber_data.keys():
            await ctx.send(content="No channel is configured in the current guild.", suppress_embeds=True)
            return
        
        # Check if the guild has no grabbers
        if not grabber_data[guild_id]:
            await ctx.send(content="No channel is configured in the current guild.", suppress_embeds=True)
            return

        embeds = []

        # Iterate over grabbers
        for grabber in grabber_data[guild_id].values():
            # Create an embed
            embed = Embed(
                title="All grabbers",
                description="Here are all the available grabbers:",
                color="#3498db",  # You can set the color of the embed
                thumbnail=grabber["anime"]["image_url"]
            )

            # Add a field for each grabber
            anime_title:str = grabber["anime"]["title"]
            mal_id:str = grabber["anime"]["mal_id"]
            url:str = grabber["anime"]["url"]
            channel_id:str = grabber["channel_id"]
            raw_providers:str = ', '.join(grabber["raw_providers"])
            fetch:str = grabber["fetch"] if ("fetch" in grabber.keys()) else "True"

            embed.add_field(name=f'{anime_title}', value=
                            f"**MAL ID:** {mal_id}\n"
                            f"**URL:** {url}\n"
                            f"**Raws chosen:** {raw_providers}\n"
                            f"**Channel:** <#{channel_id}>\n"
                            f"**Fetch:** {fetch}", inline=False)

            # Add the embed to the embeds list
            embeds.append(embed)

        # Create a paginator
        paginator = Paginator.create_from_embeds(bot, *embeds)

        # Send the paginator
        await paginator.send(ctx)
    except Exception as e:
        print(e)
        await ctx.send(content=f"Error: {e}", suppress_embeds=True)



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