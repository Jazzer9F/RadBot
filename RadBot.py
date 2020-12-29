# -*- coding: utf-8 -*-
"""
RadBot.py

Telegram bot tracking some Radix metrics
"""
import numpy as np
import pandas as pd
from web3 import Web3
import time
import json
import requests
from telebot import TeleBot
from myRadixPortfolio import RadixPortfolio
from rewards import RewardTrender


eXRD = '0x6468e79A80C0eaB0F9A2B574c8d5bC374Af59414'
eXRD_vault = '0x2b988eE889C3049104C1A5F87AF0f522790CF5F6'
eXRD_rewards = '0xDF191bFbdE2e3E178e3336E63C18DD20d537c421'
USDC = '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'
pool = '0x684B00a5773679f88598A19976fBeb25a68E9a5f'

locked_1 = '0x872BCC6C36b512c5FEd0BF947BA574B1cDC0eDD8'
locked_2 = '0x6521b13F91171e0798f0feAE8b48Fb74957E2F2b'
locked_3 = '0xb1c4D9aF8b0aD40A46561f4451354C1Dee8DcE25'
locked_4 = '0x2083810A80924F82B112a0d957C51DeB06888106'
locked_5 = '0x66BF61d5F1a77147ff0011020759726843a006d9'
locked_6 = '0x4B71EB9fC60c438d1E6e7844273f7a369CD188e7'
locked_7 = '0x2b988eE889C3049104C1A5F87AF0f522790CF5F6'
locked_8 = '0xD1d59397abCCFD06d238b12AA95C50A17598b515'
locked_9 = '0xDF191bFbdE2e3E178e3336E63C18DD20d537c421'
locked_10 = '0x6553F21aE00ff0731d9e7da300D2beFE8D38eA4F'
locked_11 = '0xf9f1804D7680F02A8C50af47794eaDB36AdF98db'
locked_12 = '0xE371469D2B557F72aCE9ed15d8A2c856c2C78606'
locked_13 = '0x6468e79A80C0eaB0F9A2B574c8d5bC374Af59414'
locked_14 = '0x10Bc34f232980929Dcf91909E6746034B453b029'
locked_15 = '0x17e00383A843A9922bCA3B280C0ADE9f8BA48449'
locked_16 = '0x684B00a5773679f88598A19976fBeb25a68E9a5f'
locked_17 = '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'
locked_18 = '0xf9cc02b750c2d22FE57F1b8B9c545A311Bf5bC99'


locked = [locked_1, locked_2, locked_3, locked_4, locked_5, locked_6,
          locked_7, locked_8, locked_9, locked_10, locked_11, locked_12,
          locked_13, locked_14, locked_15, locked_16, locked_17, locked_18]

with open('./infura.json') as f:
    INFURA_URL = json.load(f)['url']

w3 = Web3(Web3.HTTPProvider(INFURA_URL))
with open('./eXRD_token.json') as f:
    ABI = json.load(f)['result']
eXRD_Contract = w3.eth.contract(address=eXRD, abi=ABI)

with open('./eXRD_vault.json') as f:
    ABI = json.load(f)['result']
vaultContract = w3.eth.contract(address=eXRD_vault, abi=ABI)

with open('./eXRD_rewards.json') as f:
    ABI = json.load(f)['result']
rewardsContract = w3.eth.contract(address=eXRD_rewards, abi=ABI)

with open('./USDC_token.json') as f:
    ABI = json.load(f)
USDC_Contract = w3.eth.contract(address=USDC, abi=ABI)

with open('./UniSwap_pair.json') as f:
    ABI = json.load(f)['result']
poolContract = w3.eth.contract(address=pool, abi=ABI)

with open('./RadBotToken.json') as f:
    RADBOT_TOKEN = json.load(f)['token']


class RadBot():
    lastUnlockTrigger = 1607547600
    nextUnlockTarget = 0.11                     
       
    def __init__(self, token = RADBOT_TOKEN):
        self.telegram = TeleBot(token)
        self.portfolio = RadixPortfolio([])
        self.trender = RewardTrender()

    def getSMA(self):
        req = requests.get('http://api.coingecko.com/api/v3/coins/e-radix/market_chart?vs_currency=usd&days=7&interval=hourly')
        prices = pd.DataFrame(req.json()['prices'])
        prices = prices[prices[0]>1000*self.lastUnlockTrigger]
        return prices[1].mean()
               

    def nextUnlock(self):
        t = time.time()        
        self.updatePrice()
        SMA = self.getSMA()

        msg =  f"Current spot price: {round(self.price,4)} USDC/eXRD\n"
        
        timeLeft = (self.lastUnlockTrigger + 60*60*24*7) - t
        if timeLeft < 0:
            msg += "Minimum time to next unlock has passed.\n"
        else:
            days, r = divmod(timeLeft, 60*60*24)
            hours, r = divmod(r, 60*60)
            minutes = int(r/60)
            msg += f"Minimum time to next unlock: {int(days)}d, {int(hours)}h, {int(minutes)}m.\n"
        
        msg += f"Next unlock SMA target: {self.nextUnlockTarget} $\n"
        msg += f"Current CoinGecko SMA: {round(SMA,4)} $"
        return msg
        

    def updatePrice(self):
        getReserves = poolContract.functions.getReserves()
        (pool_eXRD, pool_USDC, t) = getReserves.call()
        self.pool_eXRD = pool_eXRD
        self.pool_USDC = pool_USDC
        
        self.price = self.pool_USDC*1e12/self.pool_eXRD
        return self.price
    
        
    def calcMarketCap(self):
        self.lockedAmount = 0
        for l in locked:
            balanceOf = eXRD_Contract.functions.balanceOf(l)
            self.lockedAmount += balanceOf.call()
        
        totalSupply = eXRD_Contract.functions.totalSupply()
        self.supply = totalSupply.call()
        self.unlocked = self.supply - self.lockedAmount

        self.updatePrice()        
        self.mcap = self.price*(self.unlocked)/1e18

        SMA7 = self.getSMA()
        
        msg =  f"Current spot price: {round(self.price,4)} USDC/eXRD\n"
        msg += f"Current 7-day SMA: ${round(SMA7,4)}\n"
        msg += f"Current Market Cap: {round(self.mcap/1e6,2)} MM USDC\n"
        msg += f"Percentage in LP: {round(100*self.pool_eXRD/self.unlocked,2)}%"

        return msg


    def analyseWallets(self, wallets, colors=False):
        try:
            self.portfolio = RadixPortfolio(wallets)
        except:
            return "Failed to retrieve wallet information"

        LPs = self.portfolio.assets['naked LP'].sum()+self.portfolio.assets['staked LP'].sum()
        pooled_USDC = LPs/self.portfolio.totalLPs*self.portfolio.pool_USDC/1e6
        pooled_eXRD = LPs/self.portfolio.totalLPs*self.portfolio.pool_eXRD/1e18
        totalRewards = self.portfolio.assets.rewards.sum()
        
        msg =   "Analysis of requested wallet(s)\n"
        msg += f"Unstaked USDC: {round(self.portfolio.assets.USDC.sum()/1e6,2)}\n"
        msg += f"Unstaked eXRD: {round(self.portfolio.assets.eXRD.sum()/1e18,2)}\n"
        msg += f"Pooled USDC: {round(pooled_USDC,2)}\n"
        msg += f"Pooled eXRD: {round(pooled_eXRD,2)}\n"
        msg += f"Total Rewards: {round(totalRewards,2)}\n"
        msg +=  "--------------------------------+\n"
        msg += f"Total value: {round(self.portfolio.assets.value.sum(),2)} USDC\n"

        for i in range(len(self.portfolio.stakes)):
            stake = self.portfolio.stakes.iloc[i]
            if colors:
                msg += f"\nStake {i} - age {round((stake.t1 - stake.t0)/(60*60*24),2)}d - current APY {round(stake.APY_current,2)}% - green {round(stake.green,2)}% - red {round(stake.red,2)}% - orange {round(stake.orange,2)}% - blue {round(stake.blue,2)}%"
            else:
                msg += f"\nStake {i} - age {round((stake.t1 - stake.t0)/(60*60*24),2)}d - rewards {round(stake.rewards,2)} - bonus {round(6*stake.bonus,2)} - current APY {round(stake.APY_current,2)}% - average APY {round(stake.APY_realized,2)}%"

        t = pd.Timestamp.now()
        trendDF = self.trender.calcRewardsOverTime(self.portfolio.stakes)
        d_columns = [c for c in trendDF.columns if 'donated ' in c]
        donated = trendDF[d_columns].sum(axis=1)*sum(self.portfolio.stakes.stake*self.portfolio.stakes.bonus)/sum(self.portfolio.stakes.stake)
        donated = donated.groupby(donated.index).last()
        donated[t] = np.NaN
        donated = donated.sort_index().interpolate(method='polynomial',order=2)[t]

        msg += f"\n\nRewards mined through staking: {round(totalRewards-donated,2)}"
        msg += f"\nRewards donated by early leavers: {round(donated,2)}"

        if len(self.portfolio.stakes) > 1:
            overallAPY = sum(self.portfolio.stakes.stake*self.portfolio.stakes.APY_current)/sum(self.portfolio.stakes.stake)
            overallBonus = 6*sum(self.portfolio.stakes.stake*self.portfolio.stakes.bonus)/sum(self.portfolio.stakes.stake)
            msg += f"\n\nWeighted average current APY: {round(overallAPY,2)}%"
            msg += f"\nWeighted average bonus factor: {round(overallBonus,2)}"
            msg += f"\nTotal unclaimed eXRD rewards: {round(self.portfolio.stakes.rewards.sum(),2)}"

        return msg
    
    
    def rewardsProjection(self, wallets):
        try:
            self.portfolio = RadixPortfolio(wallets)
        except:
            raise Exception("Failed")
        
        self.trender.updateEventList()
        return self.trender.plotRewards(self.portfolio.stakes)
    
    
    def calcAPY(self):
        WATS = self.portfolio.totalStakeSecs/self.portfolio.totalStake/60/60/24
        resupply_time = self.portfolio.unlocked/self.portfolio.E/60/60/24

        msg =  f"Current spot price: {round(self.updatePrice(),4)} USDC/eXRD\n"
        msg += f"Current initial APY: {round(self.portfolio.initial_APY,2)}%\n"
        msg += f"Current nominal APY: {round(self.portfolio.nominal_APY,2)}% ({round(6*self.portfolio.nominal_APY,2)}%)\n"
        msg += f"Average time staked: {round(WATS,2)} days\n"
        msg += f"Rewards resupply time: {round(resupply_time,2)} days\n"
        
        return msg


    def helpMessage(self):
        msg = "Welcome to RadBot!\n"
        msg += "\nCurrent commands:"
        msg += "\n  /a <address(es)> --> Analyse wallet(s)"
        msg += "\n  /apy --> Current LM APY"
        msg += "\n  /mcap --> eXRD market cap"
        msg += "\n  /projection <address> --> Rewards trend"
        msg += "\n  /unlock --> next unlock info"
        
        return msg


    def handleCommand(self, message):
        command = message.text.split()[0][1:]
        
        if command in ['start', 'help']:
            self.telegram.reply_to(message, self.helpMessage())
        elif command in ['apy', 'APY']:
            self.telegram.reply_to(message, self.calcAPY())
        elif command in ['a', 'analyse', 'analyze']:
            self.telegram.reply_to(message, self.analyseWallets(message.text.split()[1:]))
        elif command in ['mc', 'mcap']:
            self.telegram.reply_to(message, self.calcMarketCap())        
        elif command in ['projection']:
            try:
                with self.rewardsProjection(message.text.split()[1:]) as buffer:
                    self.telegram.reply_to(message, "The below is a graph of what your total rewards look like until now, and how they will develop if nobody (un/re)stakes from now on. Your actual future rewards will be less if more stake is added, and more if stake leaves before reaching 6x multiplier.")
                    self.telegram.send_photo(message.chat.id, buffer)
            except:
                self.telegram.reply_to(message, "Failed to analyze address(es).")
        elif command in ['u', 'unlock']:
            self.telegram.reply_to(message, self.nextUnlock())
        else:
            self.telegram.reply_to(message, "Unknown command. Try /help for command list.")        
            
            

if __name__ == "__main__":
    bot = RadBot() 

    validCommands = ['start','help','apy','APY','a','analyse','analyze','mc','mcap','projection','u','unlock']
    @bot.telegram.message_handler(commands = validCommands)
    def botCommand(message):
        try:
            bot.handleCommand(message)
        except:
            bot.telegram.reply_to(message, "Error during execution.")
    
    bot.telegram.polling()