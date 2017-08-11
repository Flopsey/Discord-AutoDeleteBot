import asyncio
import configparser
import logging
import os
import sys
import time

import discord
import instapush

config = configparser.ConfigParser(interpolation=None)
config.read('config.txt')

debug = config['DEBUGGING'].getboolean('debug')
debug_level = {True: logging.DEBUG}.get(debug, logging.INFO)
logging.basicConfig(level=debug_level)

d_config = config['DISCORD']
prefixes = tuple(d_config['command prefixes'].split())
bot_token = d_config['bot token']
command_channel_ids = set(d_config['command channels'].split())
delete_all = d_config.getboolean('delete all messages')

i_config = config['INSTAPUSH']
use_Instapush = i_config.getboolean('use Instapush')
if use_Instapush:
    instapush_app_id = i_config['app id']
    instapush_secret = i_config['secret']
    instapush_app = instapush.App(appid=instapush_app_id, secret=instapush_secret)
    exception_event = i_config['event name']
    exception_tracker = i_config['tracker']

client = discord.Client()

command_channels = set()


@client.event
async def on_ready():
    for id_ in command_channel_ids:
        command_channels.add(discord.utils.get(client.get_all_channels(), id=id_))


async def delete_message_if_not_pinned(message: discord.Message):
    if message.pinned is not True:
        try:
            await client.delete_message(message)
        except discord.errors.NotFound:
            pass


@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return
    if message.channel in command_channels:
        if not delete_all:
            return
        await asyncio.sleep(15)
        await delete_message_if_not_pinned(message)
    elif message.content.startswith(prefixes):
        channels = set(message.server.channels) & command_channels
        if len(channels) == 0:
            text = '{user} no bot commands here, please!'.format(user=message.author.mention)
        else:
            channels_text = str()
            count = 0
            for channel in channels:
                if count != 0:
                    channels_text += ', '
                channels_text += channel.mention
                count += 1
            text = '{user} \N{RIGHTWARDS ARROW} {channels}'.format(user=message.author.mention, channels=channels_text)
        reply = await client.send_message(message.channel, text)
        await delete_message_if_not_pinned(message)
        await asyncio.sleep(15)
        await client.delete_message(reply)


@client.event
async def on_message_edit(before: discord.Message, after: discord.Message):
    await on_message(after)


try:
    client.run(bot_token)
except Exception as e:
    try:
        if use_Instapush:
            instapush_app.notify(event_name=exception_event, trackers={exception_tracker: str(e)})
    finally:
        client.logout()
        time.sleep(10)
        os.execv(sys.executable, [sys.executable] + sys.argv)
