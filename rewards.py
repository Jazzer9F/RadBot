import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

import time
import threading
import io

from constants import *
from utils import *

plt.rc('figure', titleweight='bold')
plt.rc('axes', grid='True', linewidth=1.2, titlepad=20)
plt.rc('font', weight='bold', size=16)
plt.rc('lines', linewidth=3.5)

w3 = initWeb3()

rewardsContract = readContract(w3, './eXRD_rewards.json', eXRD_rewards)


emissionTimestamps = np.array([1605629336, 1608221336, 1608221858, 1610813858, 1610822511])

class RewardTrender():
    baseIndex = pd.date_range(start='17-11-2020 17:00', periods=270*4, freq='6H')
    emissionIndex = pd.DatetimeIndex(emissionTimestamps*1e9)
    lock = threading.Lock()
    store_cache = [None, None]

    def __init__(self):
        staked, unstaked = self.loadDataBase()
        if staked is not None:
            totalStake = self.calcTotalStake(staked, unstaked)
            totalStake = pd.concat([totalStake,pd.Series(index=self.baseIndex.append(self.emissionIndex),dtype=float)]).sort_index().fillna(method='ffill')
            totalStake.name = 'totalStake'

            totalStakeTime = self.calcTotalStakeTime(totalStake)
            (E, U) = self.calcEmission(totalStake.index)

            data = [totalStake, totalStakeTime, E, U]
            combined = pd.concat(data, axis=1, keys=[s.name for s in data])
            claimed = unstaked.set_index(pd.to_datetime(unstaked['timestamp']*1e9))['claimed']/1e18
            claimed =  claimed.groupby('timestamp').sum()
            combined = combined.join(claimed, how='outer')
            combined.claimed = combined.claimed.fillna(0).cumsum()
            combined['remainingU'] = combined.totalU - combined.claimed
            combined['destroyedST'] = self.calcDestroyedStakeTime(staked, unstaked)
            combined.destroyedST = combined.destroyedST.fillna(0).cumsum()
            combined['remainingST'] = combined.totalStakeTime - combined.destroyedST
            combined['donatedU'] = self.calcDonatedRewards(combined)

            self.stakeData = combined

    def loadDataBase(self):
        if self.store_cache[0] is not None:
            return self.store_cache[0], self.store_cache[1]

        with self.lock:
            store = pd.HDFStore('stake.h5')
            try:
                self.store_cache = [store['stakedDF'], store['unstakedDF']]
                return self.store_cache[0], self.store_cache[1]
            except KeyError:
                return None, None
            finally:
                store.close()


    def writeDataBase(self, stakedDF, unstakedDF):
        with self.lock:
            store = pd.HDFStore('stake.h5')
            try:
                del store['stakedDF']
                del store['unstakedDF']
            except KeyError:
                pass

            store['stakedDF'] = stakedDF
            store['unstakedDF'] = unstakedDF
            store.close()
            self.store_cache = [stakedDF, unstakedDF]


    def updateEventList(self):
        staked, unstaked = self.loadDataBase()

        if staked is None:
            staked = pd.DataFrame([])
            unstaked = pd.DataFrame([])
            lastBlock = STARTING_BLOCK
        else:
            lastBlock = max(staked.blockNumber.max(), unstaked.blockNumber.max())

        newStaked = self.getStakedEvents(lastBlock+1)
        newUnstaked = self.getUnstakedEvents(lastBlock+1)

        if (len(newStaked)==0) & (len(newUnstaked)==0):
            return

        self.setAllTimestamps([newStaked, newUnstaked])

        allStaked = pd.concat([staked, newStaked]).reset_index(drop=True)
        allUnstaked = pd.concat([unstaked, newUnstaked]).reset_index(drop=True)

        self.writeDataBase(allStaked, allUnstaked)
        RewardTrender.__init__(self)


    def getStakedEvents(self, fromBlockNr):
        stakedFilter = rewardsContract.events.Staked.createFilter(fromBlock=int(fromBlockNr))
        stakedEventList = stakedFilter.get_all_entries()

        stakedList = []
        for s in stakedEventList:
            stakedList.append({'user':s.args.user, 'amount':s.args.amount,
                               'total':s.args.total, 'event':'Staked',
                               'hash':s.transactionHash, 'blockNumber':s.blockNumber
                               })

        stakedDF = pd.DataFrame(stakedList)

        return stakedDF


    def getUnstakedEvents(self, fromBlockNr):
        unstakedFilter = rewardsContract.events.Unstaked.createFilter(fromBlock=int(fromBlockNr))
        unstakedEventList = unstakedFilter.get_all_entries()

        claimedFilter = rewardsContract.events.TokensClaimed.createFilter(fromBlock=int(fromBlockNr))
        claimedEventList = claimedFilter.get_all_entries()

        unstakedList = []
        for u,c in zip(unstakedEventList, claimedEventList):
            unstakedList.append({'user':u.args.user, 'amount':u.args.amount,
                               'total':u.args.total, 'event':'Unstaked',
                               'hash':u.transactionHash, 'blockNumber':u.blockNumber,
                               'claimed': c.args.amount
                               })

        unstakedDF = pd.DataFrame(unstakedList)

        return unstakedDF


    def setAllTimestamps(self, dataFrames):
        blockNrs = set()
        for df in dataFrames:
            if len(df):
                blockNrs = blockNrs.union(df.blockNumber)

        timestamps = {}
        for nr in blockNrs:
            timestamps[nr] = w3.eth.getBlock(nr).timestamp

        for df in dataFrames:
            if len(df):
                df['timestamp'] = df.blockNumber.map(timestamps)


    def calcTotalStake(self, stakedDF, unstakedDF):
        unstakedDF = unstakedDF.copy()
        unstakedDF.amount *= -1
        combined = pd.concat([stakedDF[['timestamp','amount']].copy(), unstakedDF[['timestamp','amount']]])
        combined['timestamp'] = pd.to_datetime(combined['timestamp']*1e9)
        combined = combined.sort_values(by='timestamp').set_index('timestamp',drop=True)['amount']
        combined.name = 'totalStake'
        combined /= 1e12

        return combined.cumsum()


    def calcTotalStakeTime(self, totalStake):
        diff = (totalStake.index.to_series().diff()//pd.Timedelta('1s')).fillna(0).astype(int)
        dStakeTime = (totalStake.shift()*diff).fillna(0)
        dStakeTime.name = 'totalStakeTime'

        return dStakeTime.cumsum()


    def calcDestroyedStakeTime(self, staked, unstaked):
        staked_ = staked.copy()
        unstaked_ = unstaked.copy()
        staked_['active'] = staked_.amount
        for ix, u in unstaked.iterrows():
            DST = 0
            user = u.user
            stake_to_remove = u.amount
            stakes = staked_[(staked_.user == user) & (staked_.active > 0) & (staked_.timestamp <= u.timestamp)]
            for ix_, s in stakes[::-1].iterrows():
                removed = min(stake_to_remove, s.active)
                staked_.loc[ix_,'active'] = s.active - removed
                stake_to_remove -= removed
                time = u.timestamp - s.timestamp
                DST += (removed/1e12)*time

                if stake_to_remove <= 0:
                    continue

            unstaked_.loc[ix,'destroyed'] = DST

        unstaked_ = unstaked_.groupby('timestamp').sum()
        unstaked_ = unstaked_.set_index(pd.to_datetime(unstaked_.index.values*1e9))
        return unstaked_.destroyed


    def calcDonatedRewards(self, stakeData):
        claimed = stakeData.claimed.diff()
        availableU = stakeData.remainingU + claimed
        destroyed = stakeData.destroyedST.diff()
        totalST = stakeData.remainingST + destroyed
        fullRewards = destroyed/totalST*availableU
        donatedRewards = (fullRewards-claimed).fillna(0)

        return donatedRewards


    def calcEmission(self, t):
        t0 = 1605629336
        t0_ = t0 + (24*60*60*30)
        t1 = 1608221858
        t1_ = t1 + (24*60*60*30)
        t2 = 1610822511
        t2_ = t2 + (24*60*60*60)

        t3 = t2_
        t3_ = t3 + (24*60*60*30)
        t4 = t3_
        t4_ = t4 + (24*60*60*30)

        if type(t) == pd.core.indexes.datetimes.DatetimeIndex:
            t_ = t.copy().astype(int)/1e9
        else:
            t_ = t

        E0 = pd.Series(75e6/(24*60*60*30)*(t_>=t0)*(t_<t0_), index=t)
        E1 = pd.Series(50e6/(24*60*60*30)*(t_>=t1)*(t_<t1_), index=t)
        E2 = pd.Series(50e6/(24*60*60*60)*(t_>=t2)*(t_<t2_), index=t)
        E3 = pd.Series(15e6/(24*60*60*30)*(t_>=t3)*(t_<t3_), index=t)
        E4 = pd.Series(10e6/(24*60*60*30)*(t_>=t4)*(t_<t4_), index=t)
        E = E0+E1+E2+E3+E4
        E.name = 'emission'

        diff = pd.Series(t_, index=t).diff()
        diff[0] = t_[0]-t0
        U = (diff*E).cumsum()
        U.name = 'totalU'

        return (E, U)


    def calcRewardsOverTime(self, stakesDF):
        def calcBonus(t, t0):
            t0_ = pd.Series(pd.Timestamp(t0*1e9), index=t)
            return 1/6 + 5/6*((((t-t0_)/pd.Timedelta('90d'))**2).clip(0,1))

        ix = self.stakeData.index
        trendDF = pd.DataFrame()
        for s in stakesDF.itertuples():
            stake = s.stake
            t0 = s.t0
            stake_ = pd.Series(stake/1e12*(ix>=pd.Timestamp(t0*1e9)), index=ix)
            stakeTime_ = self.calcTotalStakeTime(stake_)
            bonus = calcBonus(ix, t0)
            R = stakeTime_/self.stakeData.remainingST*self.stakeData.remainingU*bonus
            d = stakeTime_/self.stakeData.remainingST*self.stakeData.donatedU
            trendDF[f'staked {s.Index}'] = stake_
            trendDF[f'stakeTime {s.Index}'] = stakeTime_
            trendDF[f'stake {s.Index}'] = R
            trendDF[f'donated {s.Index}'] = d.cumsum()*bonus

        return trendDF


    def plotRewards(self, stakesDF):
        trendDF = self.calcRewardsOverTime(stakesDF)

        ix = self.baseIndex
        trendDF = trendDF.loc[self.baseIndex]
        past = (ix <= pd.Timestamp(time.time()*1e9))
        R_columns = [c for c in trendDF.columns if 'stake ' in c]
        trendDF = 216/172*trendDF[R_columns].sum(axis=1)

        fig = plt.figure(figsize=(12,8))
        plt.title('Rewards projection assuming nobody (un)stakes', fontsize=24, fontweight='bold')
        ax = fig.gca()
        potential = sns.lineplot(data=trendDF.loc[~past], legend=None)
        for l in potential.lines: l.set_linestyle("--")
        sns.lineplot(data=trendDF.loc[past])
        xmin = pd.Timestamp(stakesDF.t0.min()*1e9)-pd.Timedelta('10d')
        xmax = pd.Timestamp(stakesDF.t0.max()*1e9)+pd.Timedelta('180d')
        ax.set_xlim(xmin=xmin,xmax=xmax)
        ax.set_ylim(ymin=0)
        plt.xticks(rotation=60)

        buffer = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buffer, format='png', bbox='tight')
        plt.close()

        buffer.seek(0)
        return buffer


if __name__ == "__main__":
    stakes = pd.DataFrame([{'stake':1256060027644086, 't0':1605634336}])
    rT = RewardTrender()
    rT.updateEventList()

    from PIL import Image
    with rT.plotRewards(stakes) as buffer:
        im = Image.open(buffer)
        im.show()

#ix = rT.stakeData.index
#past = (ix <= pd.Timestamp(time.time()*1e9))
#fig = plt.figure(figsize=(12,8))
#ns.lineplot(data=rT.stakeData.donatedU.loc[past])
#plt.savefig('test.png', bbox='tight')

#staked, unstaked = rT.loadDataBase()
#unstaked.sort_values(by='amount').tail()
#unstaked.loc[702]
