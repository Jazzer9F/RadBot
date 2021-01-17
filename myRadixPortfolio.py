# -*- coding: utf-8 -*-
"""
RadBot.py

Telegram bot tracking some Radix metrics
"""
import pandas as pd
import time

from utils import *
from constants import *

w3 = initWeb3()

eXRD_Contract = readContract(w3, './eXRD_token.json', eXRD)
vaultContract = readContract(w3, './eXRD_vault.json', eXRD_vault)
rewardsContract = readContract(w3, './eXRD_rewards.json', eXRD_rewards)
USDC_Contract = readContract(w3, './USDC_token.json', USDC)
poolContract = readContract(w3, './UniSwap_pair.json', pool)


class RadixPortfolio:
    # Emission rate (hardcoded for now)
    E = int(25e24/30/24/60/60)

    def __init__(self, wallets):
        self.wallets = [Web3.toChecksumAddress(w) for w in wallets]

        self.loadPortfolio()
        self.loadRewardsInfo()
        self.loadPoolInfo()
        self.calculateRewards()
        self.calculateAssetValue()

    def walletCheck(self, wallet):
        balanceOf = USDC_Contract.functions.balanceOf(wallet)
        my_USDC = balanceOf.call()

        balanceOf = eXRD_Contract.functions.balanceOf(wallet)
        my_eXRD = balanceOf.call()

        balanceOf = poolContract.functions.balanceOf(wallet)
        myLP = balanceOf.call()

        stakeCount = rewardsContract.functions.stakeCount(wallet)
        n = stakeCount.call()

        stakes = []
        for i in range(n):
            _userStakes = rewardsContract.functions._userStakes(wallet, i)
            (stake, t) = _userStakes.call()
            stakes.append((wallet, stake, t))

        return (my_USDC, my_eXRD, myLP, stakes)


    def loadRewardsInfo(self):
        totalStaked = rewardsContract.functions.totalStaked()
        self.totalStake = totalStaked.call()

        totalStakingShareSeconds = rewardsContract.functions._totalStakingShareSeconds()
        self.totalStakeSecs = totalStakingShareSeconds.call()

        totalUnlocked = rewardsContract.functions.totalUnlocked()
        self.unlocked = totalUnlocked.call()

        lastAccountingTimestampSec = rewardsContract.functions._lastAccountingTimestampSec()
        self.t1 = lastAccountingTimestampSec.call()


    def loadPoolInfo(self):
        getReserves = poolContract.functions.getReserves()
        (pool_eXRD, pool_USDC, t) = getReserves.call()
        self.pool_eXRD = pool_eXRD
        self.pool_USDC = pool_USDC

        totalSupply = poolContract.functions.totalSupply()
        self.totalLPs = totalSupply.call()
        self.spot_price = pool_USDC*1e12/pool_eXRD


    def loadPortfolio(self):
        all_stakes = []
        assets = []
        for wallet in self.wallets:
            (my_USDC, my_eXRD, my_LP, stakes) = self.walletCheck(wallet)
            rewards = sum([s[1] for s in stakes])
            assets.append((wallet, my_USDC, my_eXRD, my_LP, rewards))
            all_stakes += stakes

        self.assets = pd.DataFrame(assets, columns=['wallet', 'USDC', 'eXRD', 'naked LP', 'staked LP']).set_index('wallet')
        self.stakes = pd.DataFrame(all_stakes, columns=['wallet','stake','t0'])

    def calculateAssetValue(self):
        eXRD_price = (self.pool_USDC*1e12)/(self.pool_eXRD)
        LP_value = 2*self.pool_USDC/self.totalLPs/1e6
        self.assets['value'] = self.assets['USDC']/1e6 + self.assets['eXRD']*eXRD_price/1e18 + self.assets['rewards']*eXRD_price + (self.assets['naked LP']+self.assets['staked LP'])*LP_value

    def updateAccounting(self):
        t = int(time.time())
        self.unlocked = self.unlocked + self.E*(t-self.t1)
        self.totalStakeSecs = self.totalStakeSecs + self.totalStake*(t-self.t1)
        self.totalStakeDays = self.totalStakeSecs/(60*60*24)
        self.t1 = t

    def calculateRewards(self):
        self.updateAccounting()
        self.stakes['t1'] = self.t1
        self.stakes['bonus'] = (1/6 + 5/6*((self.stakes['t1']-self.stakes['t0'])/90/24/60/60)**2).clip(1/6,1)
        self.stakes['stakeSecs'] = self.stakes['stake']/1e12*(self.stakes['t1']-self.stakes['t0'])
        self.stakes['rewards'] = (self.stakes['stakeSecs']/self.totalStakeSecs*self.unlocked/1e6*self.stakes.bonus).astype(float)

        T0 = (self.stakes.t1 - self.stakes.t0)/(60*60*24)
        green = self.stakes.stake/self.totalStakeDays*(self.unlocked/1e12)*self.stakes['bonus']
        red = self.totalStake/self.totalStakeDays*self.stakes.stake*T0/self.totalStakeDays*(self.unlocked/1e12)*self.stakes['bonus']
        orange = self.stakes.stake*T0/self.totalStakeDays*(self.E/1e12)*(60*60*24)*self.stakes['bonus']
        blue = 10/6*self.stakes.stake*T0/self.totalStakeDays*(self.unlocked/1e12)*T0/90**2

        eXRD_per_LP = 2*self.pool_eXRD/self.totalLPs
        annual_reward_per_LP = (green-red+orange+blue)/(self.stakes.stake/1e12)*365
        self.stakes['APY_current'] = (100*annual_reward_per_LP/eXRD_per_LP).astype(float)
        self.stakes['APY_realized'] = 100*self.stakes.rewards*1e18*(60*60*24*365/(self.stakes.t1-self.stakes.t0))/self.stakes.stake/eXRD_per_LP
        self.nominal_APY = 100*self.E*(60*60*24*365)/self.totalStake/eXRD_per_LP/6
        self.initial_APY = 100*self.unlocked/self.totalStakeSecs*(60*60*24*365)/eXRD_per_LP/6

        self.stakes['green'] = green/(green-red+orange+blue)*self.stakes.APY_current
        self.stakes['red'] = -red/(green-red+orange+blue)*self.stakes.APY_current
        self.stakes['orange'] = orange/(green-red+orange+blue)*self.stakes.APY_current
        self.stakes['blue'] = blue/(green-red+orange+blue)*self.stakes.APY_current

        self.assets['rewards'] = self.stakes.groupby('wallet').sum().rewards
        self.assets['rewards'] = self.assets['rewards'].fillna(0)


    def report(self):
        if not hasattr(self, 'nominal_APY'):
            self.calculateRewards()

        msg = f"Total USDC equivalent value of these accounts is ${round(self.assets.value.sum(),2)}\n"
        msg += f"Liquidity rewards value is included. Current rewards stand at {round(self.stakes.rewards.sum(),2)} eXRD."

        print(msg)


if __name__ == "__main__":
    wallets = pd.read_csv('myWallets.csv',header=None)[0].to_list()
    portfolio = RadixPortfolio(wallets)
    portfolio.report()