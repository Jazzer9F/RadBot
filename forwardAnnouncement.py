# -*- coding: utf-8 -*-
"""
Created on Wed 3 Feb 2021
@author: Jazzer

Will read the pinned messages from the announcements channel and post one of them in the main group.
"""
import json
import time
import asyncio
from telethon import TelegramClient, types

ann_channel = 'RadixAnnouncements'
main_group = 'radix_dlt'
period = 4     # Post once every this many hours

def loadCredentials():
    with open('./telegram_API_credentials.json') as f:
        creds = json.load(f)
        api_id = creds['api_id']
        api_hash = creds['api_hash']
    return (api_id, api_hash)

async def forwardAnnouncement():
    if time.time()%(period*3600) > 1800: return
    api_id, api_hash = loadCredentials()
    async with await TelegramClient('RadNews', api_id, api_hash).start() as client:
        channel = await client.get_entity(ann_channel)
        posts = []
        async for post in client.iter_messages(channel, filter=types.InputMessagesFilterPinned()):
            posts.append(post)
        n = len(posts)
        if n > 0:
            selected = (n-1)-int(time.time()/3600/period)%n
            group = await client.get_entity(main_group)
            await client.forward_messages(group, posts[selected])

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(forwardAnnouncement())
    loop.close()
