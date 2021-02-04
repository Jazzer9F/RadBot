# -*- coding: utf-8 -*-
"""
Created on Wed 3 Feb 2021
@author: Jazzer

Will read the last 4 announcements from the announcements channel and post one of them in the main group.
"""
import json
import time
import asyncio
from telethon import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest

ann_channel = 'RadixAnnouncements'
main_group = 'radix_dlt'

def loadCredentials():
    with open('./telegram_API_credentials.json') as f:
        creds = json.load(f)
        api_id = creds['api_id']
        api_hash = creds['api_hash']
    return (api_id, api_hash)

async def forwardAnnouncement():
    api_id, api_hash = loadCredentials()
    async with TelegramClient('RadNews', api_id, api_hash) as client:
        await client.start()
        channel = await client.get_entity(ann_channel)
        posts =  await client.get_messages(channel, 4)
        group = await client.get_entity(main_group)
        selected = 3-int(time.time()/3600)%4
        await client.forward_messages(group, posts[0])

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(forwardAnnouncement())
    loop.close()
