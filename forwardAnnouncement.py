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
        posts =  await client(GetHistoryRequest(
            peer = channel,
            limit = 4,
            offset_date = None,
            offset_id = 0,
            max_id = 0,
            min_id = 0,
            add_offset = 0,
            hash = 0
            ))

        group = await client.get_entity(main_group)
        selected = int(time.time()/3600)%4
        await client.send_message(group, posts.messages[selected])

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(forwardAnnouncement())
    loop.close()
