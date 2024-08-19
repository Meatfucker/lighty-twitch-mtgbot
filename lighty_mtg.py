"""
lighty_mtg
"""
import io
from io import BytesIO
import sys
import asyncio
import gc
import re
import os
from datetime import datetime
import random
import warnings
import urllib.parse
import torch
import discord
from discord import app_commands
from discord.ui import Button, View
from twitchio.ext import pubsub
import twitchio
import requests

from loguru import logger
from modules.settings import SETTINGS
from modules.mtg_generator import MTGCardGenerator
from modules.chat_generator import ChatGenerator


warnings.filterwarnings("ignore")
logger.remove()  # Remove the default configuration
logger.add(
    sink=io.TextIOWrapper(sys.stdout.buffer, write_through=True),
    format="<light-black>{time:YYYY-MM-DD HH:mm:ss}</light-black> | <level>{level: <8}</level> | <light-yellow>{message: ^27}</light-yellow> | <light-red>{extra}</light-red>",
    level="INFO",
    colorize=True
)
logger.add(
    "bot.log",
    rotation="20 MB",
    format="<light-black>{time:YYYY-MM-DD HH:mm:ss}</light-black> | <level>{level: <8}</level> | <light-yellow>{message: ^27}</light-yellow> | <light-red>{extra}</light-red>",
    level="INFO",
    colorize=True
)


class LightyMTGClient(discord.Client):
    """The discord client class for the bot"""
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.slash_command_tree = app_commands.CommandTree(self)
        self.generation_queue = asyncio.Queue()
        self.generation_queue_concurrency_list = {}
        self.currently_processing = False

    async def setup_hook(self):
        """This loads the various shit before logging in to discord"""
        self.loop.create_task(discord_client.process_queue())  # start queue

    async def on_ready(self):
        """Just prints the bots name to discord"""
        await self.slash_command_tree.sync()  # sync commands to discord
        ready_logger = logger.bind(user=discord_client.user.name, userid=discord_client.user.id)
        ready_logger.info("Discord Login Successful")

    @logger.catch()
    async def on_message(self, message):
        """This captures people talking to the bot in chat and responds."""
        if self.user.mentioned_in(message):
            if not await self.is_enabled_not_banned("enable_bot_actions", message.author):
                return
            prompt = re.sub(r'<[^>]+>', '', message.content).lstrip()  # this removes the user tag
            if await self.is_room_in_queue(message.author.id):
                self.generation_queue_concurrency_list[message.author.id] += 1
                chat_request = ChatGenerator(prompt, message.channel, message.author)
                await self.generation_queue.put(chat_request)
                chat_logger = logger.bind(user=message.author, prompt=prompt)
                chat_logger.info("Chat Queued")
            else:
                await message.channel.send("Queue limit has been reached, please wait for your previous gens to finish")

    @logger.catch()
    async def process_queue(self):
        """This is the primary queue for the bot. Anything that requires state be maintained goes through here"""
        while True:
            queue_request = await self.generation_queue.get()

            try:
                self.currently_processing = True
                if queue_request.action == "lightycard":

                    await queue_request.generate_card()

                    with io.BytesIO() as file_object:
                        queue_request.card.save(file_object, format="PNG")
                        file_object.seek(0)
                        filename = f'lighty_mtg_{queue_request.prompt[:20]}.png'
                        message = await queue_request.channel.send(
                            content=f"Twitch Card for `{queue_request.user}`: Prompt: `{queue_request.prompt}`",
                            file=discord.File(file_object, filename=filename, spoiler=True)
                        )

                    sanitized_prompt = re.sub(r'[<>:"/\\|?*\x00-\x1F]', '', queue_request.prompt)
                    dir_path = f'users/{queue_request.user}/{queue_request.card_type}.{sanitized_prompt[:20]}.{random.randint(1, 99999999)}.webp'
                    os.makedirs(os.path.dirname(dir_path), exist_ok=True)
                    queue_request.card.save(dir_path, format="WEBP")

                    message_link = f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}"
                    if queue_request.user.id == 666:
                        twitch_channel = twitch_client.get_channel("lighty")
                        await twitch_channel.send(f"@{queue_request.user}: Your card is ready at: {message_link}")

                    lightycard_logger = logger.bind(user=f'{queue_request.user}', prompt=queue_request.prompt, link=message_link)
                    lightycard_logger.info("Card Posted")

                if queue_request.action == "lightycard_three_pack":
                    now = datetime.now()
                    now_string = now.strftime("%Y%m%d%H%M%S")
                    sanitized_prompt = re.sub(r'[<>:"/\\|?*\x00-\x1F]', '', queue_request.prompt)

                    await queue_request.generate_card()
                    dir_path_1 = f'users/{queue_request.user}/{queue_request.card_type}.{sanitized_prompt[:20]}.{random.randint(1, 99999999)}.webp'
                    card_path_1 = f'users/{queue_request.user}/{now_string}/card1.webp'
                    os.makedirs(os.path.dirname(dir_path_1), exist_ok=True)
                    os.makedirs(os.path.dirname(card_path_1), exist_ok=True)
                    queue_request.card.save(dir_path_1, format="WEBP")
                    queue_request.card.save(card_path_1, format="WEBP")

                    await queue_request.generate_card()
                    dir_path_2 = f'users/{queue_request.user}/{queue_request.card_type}.{sanitized_prompt[:20]}.{random.randint(1, 99999999)}.webp'
                    card_path_2 = f'users/{queue_request.user}/{now_string}/card2.webp'
                    os.makedirs(os.path.dirname(dir_path_2), exist_ok=True)
                    os.makedirs(os.path.dirname(card_path_2), exist_ok=True)
                    queue_request.card.save(dir_path_2, format="WEBP")
                    queue_request.card.save(card_path_2, format="WEBP")

                    await queue_request.generate_card()
                    dir_path_3 = f'users/{queue_request.user}/{queue_request.card_type}.{sanitized_prompt[:20]}.{random.randint(1, 99999999)}.webp'
                    card_path_3 = f'users/{queue_request.user}/{now_string}/card3.webp'
                    os.makedirs(os.path.dirname(dir_path_1), exist_ok=True)
                    os.makedirs(os.path.dirname(card_path_3), exist_ok=True)
                    queue_request.card.save(dir_path_3, format="WEBP")
                    queue_request.card.save(card_path_3, format="WEBP")
                    logger.info(queue_request.user)
                    logger.info(f"# {queue_request.user} Open your pack here: http://theblackgoat.net/cardflip-dynamic.html?username={queue_request.user}&datetimestring={now_string}")
                    message = await queue_request.channel.send(f"# {queue_request.user} Open your pack here: [OPEN PACK](http://theblackgoat.net/cardflip-dynamic.html?username={queue_request.user}&datetimestring={now_string})")
                    await queue_request.channel.send(
                        content=f"Card Pack for `{queue_request.user}`: Prompt: `{queue_request.prompt}`",
                        files=[discord.File(dir_path_1, filename=f'lighty_mtg_{queue_request.prompt[:20]}.png', spoiler=True),
                              discord.File(dir_path_2, filename=f'lighty_mtg_{queue_request.prompt[:20]}.png', spoiler=True),
                              discord.File(dir_path_3, filename=f'lighty_mtg_{queue_request.prompt[:20]}.png', spoiler=True)]
                    )

                    if queue_request.user.id == 666:
                        message_link = f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}"
                        twitch_channel = twitch_client.get_channel("lighty")
                        await twitch_channel.send(f"@{queue_request.user}: Your pack is ready at: {message_link}")

                    logger.info("Pack created")


                if queue_request.action == "discord_chat":
                    await queue_request.generate_chat()
                    for i in range(0, len(queue_request.response), 2000):
                        chunk = queue_request.response[i:i + 2000]
                        await queue_request.channel.send(content=chunk, mention_author=True)
                    generate_chat_logger = logger.bind(user=queue_request.user, prompt=queue_request.prompt)
                    generate_chat_logger.info("Chat responded")


            except Exception as e:
                self.generation_queue_concurrency_list[queue_request.user.id] -= 1
                logger.error(f'EXCEPTION: {e}')
            finally:
                self.generation_queue_concurrency_list[queue_request.user.id] -= 1
                self.generation_queue.task_done()
                gc.collect()
                torch.cuda.empty_cache()
                self.currently_processing = False

    async def is_room_in_queue(self, user_id):
        """This checks the users current number of pending gens against the max,
         and if there is room, returns true, otherwise, false"""
        self.generation_queue_concurrency_list.setdefault(user_id, 0)
        user_queue_depth = int(SETTINGS.get("user_queue_depth", [1])[0])
        if self.generation_queue_concurrency_list[user_id] >= user_queue_depth:
            return False
        return True

    @staticmethod
    async def is_enabled_not_banned(module, user):
        """This only returns true if the module is both enabled and the user is not banned"""
        if SETTINGS[module][0] != "True":
            return False  # check if LLM generation is enabled
        if str(user.id) in SETTINGS.get("banned_users", [""])[0].split(','):
            return False  # Exit the function if the author is banned
        return True


class CustomDiscordUser:
    """Allows setting arbitrary discord user ids for the queue to work with since twitch has none"""
    def __init__(self, user):
        self.id = 666
        self.user = user

    def __str__(self):
        return self.user


class MyPubSubPool(pubsub.PubSubPool):
    """Watches for auth token failures and attempts to get new tokens"""
    async def auth_fail_hook(self, topics):
        auth_logger = logger.bind(channel=topics[0])
        auth_logger.info(f"Auth Failed")
        new_token = await self.refresh_token()
        for topic in topics:
            topic.token = new_token
        await self.subscribe_topics(topics)

    @staticmethod
    async def refresh_token():
        """Refreshes auth tokens, reauthorizes with twitch, and saves them to the settings.cfg file"""
        client_id = SETTINGS["twitch_client_id"][0]
        client_secret = SETTINGS["twitch_client_secret"][0]
        refresh_token = SETTINGS["twitch_channel_refresh_token"][0]
        encoded_refresh_token = urllib.parse.quote(refresh_token)
        url = 'https://id.twitch.tv/oauth2/token'
        data = {
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'refresh_token',
            'refresh_token': encoded_refresh_token
        }
        response = requests.post(url, data=data)
        new_access_token = None
        if response.status_code == 200:
            logger.info('Access token refreshed')
            response_data = response.json()
            new_access_token = response_data.get('access_token')
            new_refresh_token = response_data.get('refresh_token')

            with open('settings.cfg', 'r') as settings_file:
                lines = settings_file.readlines()

            # Replace the old access token with the new one
            for i, line in enumerate(lines):
                if line.startswith('twitch_channel_auth='):
                    lines[i] = f'twitch_channel_auth={new_access_token}\n'
                    break

            for i, line in enumerate(lines):
                if line.startswith('twitch_channel_refresh_token='):
                    lines[i] = f'twitch_channel_refresh_token={new_refresh_token}\n'
                    break

            # Write the updated contents back to the settings.cfg file
            with open('settings.cfg', 'w') as settings_file:
                settings_file.writelines(lines)

        else:
            logger.info('Failed to refresh access token.')
            logger.info('Status Code:', response.status_code)
            logger.info('Response:', response.json())

        return new_access_token


discord_client = LightyMTGClient(intents=discord.Intents.all())  # client intents

twitch_client = twitchio.Client(
    token=SETTINGS["twitch_app_token"][0],
    client_secret=SETTINGS["twitch_client_secret"][0],
    initial_channels=[SETTINGS["twitch_channel"][0]]
)


@twitch_client.event()
async def event_pubsub_channel_points(event: pubsub.PubSubChannelPointsMessage):
    """Watches for channel rewards matching the reward title, and adds a card to the queue when it sees one"""
    if event.reward.title == SETTINGS['twitch_reward_name'][0]:
        channel = discord_client.get_channel(int(SETTINGS['discord_channel_id'][0]))

        custom_user = CustomDiscordUser(event.user.name)
        mtg_card_request = MTGCardGenerator('lightycard_three_pack', event.input, channel, custom_user)
        pubsub_logger = logger.bind(user=event.user.name, prompt=event.input)
        pubsub_logger.info(f'Twitch card reward redeemed')
        if await discord_client.is_room_in_queue(666):
            discord_client.generation_queue_concurrency_list[666] += 1
            await discord_client.generation_queue.put(mtg_card_request)


@twitch_client.event()
async def event_ready():
    """Prints stuff to the console when logged into twitch"""
    twitch_ready_logger = logger.bind(user=twitch_client.nick, channel=twitch_client.connected_channels)
    twitch_ready_logger.info(f'Twitch Login Successful')
    twitch_channel = twitch_client.get_channel("lighty")
    await twitch_channel.send("Lighty CCG Redemption Bot Online")


@discord_client.slash_command_tree.command(description="This generates lighty mtg cards")
async def lighty_mtg(interaction: discord.Interaction, prompt: str):
    """This is the slash command to generate a card."""
    if not await discord_client.is_enabled_not_banned("enable_bot_actions", interaction.user):
        await interaction.response.send_message("Disabled or user banned", ephemeral=True, delete_after=5)
        return

    mtg_card_request = MTGCardGenerator('lightycard', prompt, interaction.channel, interaction.user)

    if await discord_client.is_room_in_queue(interaction.user.id):
        card_queue_logger = logger.bind(user=interaction.user.name, prompt=prompt)
        card_queue_logger.info(f'Card Queued')
        discord_client.generation_queue_concurrency_list[interaction.user.id] += 1
        await discord_client.generation_queue.put(mtg_card_request)
        await interaction.response.send_message('Card Being Created:', ephemeral=True, delete_after=5)
    else:
        await interaction.response.send_message("Queue limit reached, please wait until your current gen or gens finish")

@discord_client.slash_command_tree.command(description="This generates lighty mtg cards")
async def lighty_mtg_three_pack(interaction: discord.Interaction, prompt: str):
    """This is the slash command to generate a card."""
    if not await discord_client.is_enabled_not_banned("enable_bot_actions", interaction.user):
        await interaction.response.send_message("Disabled or user banned", ephemeral=True, delete_after=5)
        return

    mtg_card_request = MTGCardGenerator('lightycard_three_pack', prompt, interaction.channel, interaction.user)

    if await discord_client.is_room_in_queue(interaction.user.id):
        card_queue_logger = logger.bind(user=interaction.user.name, prompt=prompt)
        card_queue_logger.info(f'Card Queued')
        discord_client.generation_queue_concurrency_list[interaction.user.id] += 1
        await discord_client.generation_queue.put(mtg_card_request)
        await interaction.response.send_message('Card Being Created:', ephemeral=True, delete_after=5)
    else:
        await interaction.response.send_message("Queue limit reached, please wait until your current gen or gens finish")

async def start_clients():
    """Spin off clients to threads and start them"""
    twitch_client.pubsub = MyPubSubPool(twitch_client)
    topics = [pubsub.channel_points(SETTINGS["twitch_channel_auth"][0])[int(SETTINGS["twitch_channel_id"][0])]]

    await asyncio.gather(
        discord_client.start(SETTINGS["discord_token"][0]),  # Start the bot
        twitch_client.pubsub.subscribe_topics(topics),
        twitch_client.start()
    )

async def twitch_exit_notice():
    """Notifies Twitch the bot is shutting down"""
    twitch_channel = twitch_client.get_channel("lighty")
    await twitch_channel.send("Lighty CCG Redemption Bot Offline")

def run_program():
    """Main startup loop"""
    loop = asyncio.get_event_loop()

    try:
        loop.run_until_complete(start_clients())
    except KeyboardInterrupt:
        loop.run_until_complete(twitch_exit_notice())

    finally:
        loop.close()


if __name__ == "__main__":
    run_program()
