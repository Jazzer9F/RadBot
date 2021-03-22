# -*- coding: utf-8 -*-
"""
Created on Sun Nov  1 15:40:20 2020

@author: jaspe
"""
from datetime import timedelta
from timeloop import Timeloop
import json
import time
import _thread

from telebot import TeleBot

from constants import eXRD_vault
from utils import initWeb3, readContract

tl = Timeloop()
w3 = initWeb3()

vaultContract = readContract(w3, './eXRD_vault.json', eXRD_vault)

with open('./RadBotToken.json') as f:
    RADBOT_TOKEN = json.load(f)['token']

with open('./subscribers.json') as f:
    subscribers = json.load(f)['subscribers']

telegram = TeleBot(RADBOT_TOKEN)

seenUnlock = False
@tl.job(interval=timedelta(seconds=5))
def unlockTime():
    global seenUnlock

    if seenUnlock:
        _thread.interrupt_main()
        return
    else:
        method = vaultContract.functions.getUnlockedPercentages(0)
        unlocked = method.call()

        if unlocked > 35:
            seenUnlock = True

            for destination, dest_id in subscribers.items():
                try:
                    telegram.send_message(dest_id, "Heya RadBulls!\n\n* The *\n* eXRD *\n* token *\n* unlock *\n* just *\n* happened! *\n\nCheers from team RadBot!", parse_mode='Markdown')
                except:
                    print(f'Failed to send message to {destination}.')

            for destination, dest_id in subscribers.items():
                try:
                    sticker = open('./ItsRainingXRD.jfif','rb')
                    telegram.send_sticker(dest_id, sticker)
                except:
                    print(f'Failed to send sticker to {destination}.')


            print('Unlock completed!')
            _thread.interrupt_main()
        else:
            print(f'{time.strftime("%H:%M:%S", time.localtime())} -- No unlock yet')


if __name__ == '__main__':
    tl.start(block=True)
