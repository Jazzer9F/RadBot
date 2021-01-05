import pickle
from typing import Dict, List

from eth_utils import keccak, event_abi_to_log_topic
from web3._utils.events import get_event_data

from balanceStore import BalanceStore
from constants import *
from utils import *

w3 = initWeb3()

eXRD_Contract = readContract(w3, './eXRD_token.json', eXRD)
USDC_Contract = readContract(w3, './USDC_token.json', USDC)
poolContract = readContract(w3, './UniSwap_pair.json', pool)

TRANSFER_TOPIC = keccak(text='Transfer(address,address,uint256)')
TOKENS = {eXRD, USDC, pool}


class UniswapInfo:
    debug = False

    def __init__(self, debug=False):
        self.debug = debug
        self.updateTransactions()

    def updateTransactions(self) -> Dict[str, List[Dict[str, int]]]:
        uniInfo, lastBlock = self.loadDataBase()

        if uniInfo is None:
            uniInfo = {}
            lastBlock = STARTING_BLOCK

        addresses, newLastBlock = self.updateBalances(uniInfo, lastBlock + 1)

        if newLastBlock == lastBlock:  # nothing changed yet
            return uniInfo

        self.writeDataBase(uniInfo, newLastBlock)
        return uniInfo

    def getBalances(self, wallets: [str]) -> List[Dict[str, int]]:
        addresses = self.updateTransactions()
        store = BalanceStore(addresses)
        results = []
        for addr in wallets:
            balances = store.getBalances(addr)
            for balance in balances:
                if 'LP' in balance and balance['LP'] > 100 and 'eXRD' in balance and 'USDC' in balance:
                    results.append(balance)
        return results

    def updateBalances(self, addresses, fromBlockNr):
        entries = poolContract.events.Transfer.getLogs(fromBlock=int(fromBlockNr))
        lastBlock = int(fromBlockNr) - 1

        if len(entries) == 0:
            return addresses, lastBlock

        # calculate balances of added eXRD, USDC (in the pool), and LP tokens (received from the pool) for each address
        store = BalanceStore(addresses)

        transactions = {}
        for s in entries:
            lastBlock = s.blockNumber
            transactions[s.transactionHash] = None

        event_abi = self.getTransferAbi()

        for tx in transactions:
            receipt = w3.eth.getTransactionReceipt(tx)
            if self.debug:
                print('Block: ' + str(receipt['blockNumber']))
            stake_USDC = 0
            stake_eXRD = 0
            stake_LP = 0
            user_address = receipt['from']
            # Go through the log starting from last transfer. Stop if transfers of all 3 tokens was observed. (Zapper.fi transactions)
            seenTokens = set()
            for log in reversed(receipt.logs):
                if log.topics[0] == TRANSFER_TOPIC:
                    s = get_event_data(poolContract.events.Transfer.web3.codec, event_abi, log)
                    args = s['args']
                    source = args['from']
                    to = args['to']
                    address = s['address']
                    value = args['value']
                    if address == pool and source == VOID:  # LP tokens created and transferred to user
                        seenTokens.add(address)
                        stake_LP += value
                    elif address == pool and to == pool:  # LP tokens burned
                        seenTokens.add(address)
                        stake_LP -= value
                    elif address != pool and to == pool and source != pool:  # eXRD/USDC added
                        seenTokens.add(address)
                        if address == eXRD:
                            stake_eXRD += value
                        elif address == USDC:
                            stake_USDC += value
                    elif address != pool and source == pool and to != pool:  # eXRD/USDC removed
                        seenTokens.add(address)
                        pass  # ignore - track by LP tokens only
                    else:  # transactions between Uniswap router and the Pool?
                        if self.debug:
                            print('FROM: ' + source + ' TO: ' + to + ' Address: ' + address + ' Amount: ' + str(value))
                    if seenTokens.issuperset(TOKENS):
                        break
            if stake_LP > 0:
                store.addStake(user_address, stake_USDC, stake_eXRD, stake_LP)
            elif stake_LP < 0:
                store.removeStake(user_address, -stake_LP)

        updatedAddresses = store.addresses

        if self.debug:
            print('Total addresses: ' + str(len(updatedAddresses)))
            for address in updatedAddresses:
                print(str(address) + ' -> ' + str(updatedAddresses[address]))

        return updatedAddresses, lastBlock

    @staticmethod
    def getTransferAbi():
        event_abi = None
        for abi in poolContract.events.abi:
            if 'name' in abi:
                topic = event_abi_to_log_topic(abi)
                if topic == TRANSFER_TOPIC:
                    event_abi = abi
        return event_abi

    @staticmethod
    def loadDataBase():
        try:
            with open('uniInfo.p', 'rb') as fp:
                data = pickle.load(fp)
                return data['addresses'], data['lastBlock']
        except FileNotFoundError:
            return None, None

    @staticmethod
    def writeDataBase(addresses, lastBlock):
        with open('uniInfo.p', 'wb') as fp:
            data = {'addresses': addresses, 'lastBlock': lastBlock}
            pickle.dump(data, fp, protocol=pickle.HIGHEST_PROTOCOL)


if __name__ == "__main__":
    info = UniswapInfo()

    print('Done')
