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

from web3 import Web3

eXRD_vault = '0x2b988eE889C3049104C1A5F87AF0f522790CF5F6'

with open('./infura.json') as f:
    INFURA_URL = json.load(f)['url']

tl = Timeloop()
w3 = Web3(Web3.HTTPProvider(INFURA_URL))

with open('./eXRD_vault.json') as f:
  ABI = json.load(f)['result']
vaultContract = w3.eth.contract(address=eXRD_vault, abi=ABI)

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
    
        if unlocked > 15:
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
