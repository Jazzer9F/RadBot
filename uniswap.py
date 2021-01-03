import pickle
from typing import Dict

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


class UniswapInfo:
    debug = False

    def __init__(self, debug=False):
        self.debug = debug
        self.updateTransactions()

    def updateTransactions(self) -> Dict[str, Dict[str, int]]:
        uniInfo, lastBlock = self.loadDataBase()

        if uniInfo is None:
            uniInfo = {}
            lastBlock = STARTING_BLOCK

        addresses, newLastBlock = self.getBalances(uniInfo, lastBlock + 1)

        if newLastBlock == lastBlock:  # nothing changed yet
            return uniInfo

        self.writeDataBase(uniInfo, newLastBlock)
        return uniInfo

    def getBalance(self, wallets: [str]) -> (int, int):
        addresses = self.updateTransactions()
        store = BalanceStore(addresses)
        bal_USDC = 0
        bal_eXRD = 0
        for addr in wallets:
            balances = store.getBalances(addr)
            if 'LP' in balances and balances['LP'] > 100 and 'eXRD' in balances and 'USDC' in balances:
                bal_USDC += balances['USDC']
                bal_eXRD += balances['eXRD']
        return bal_USDC, bal_eXRD

    def getBalances(self, addresses, fromBlockNr):
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
            for log in receipt.logs:
                if log.topics[0] == TRANSFER_TOPIC:
                    s = get_event_data(poolContract.events.Transfer.web3.codec, event_abi, log)
                    args = s['args']
                    source = args['from']
                    to = args['to']
                    address = s['address']
                    value = args['value']
                    if address == pool and source == VOID:  # LP tokens created and transferred to user
                        store.addBalance(to, 'LP', value)
                    elif address == pool and to == pool:  # LP tokens burned
                        store.addBalance(source, 'LP', -value)
                    elif to == pool and source != pool:  # eXRD/USDC added
                        token = 'eXRD' if address == eXRD else 'USDC'
                        store.addBalance(source, token, value)
                    elif source == pool and to != pool:  # eXRD/USDC removed
                        # ignore - track by LP tokens only
                        pass
                        # token = 'eXRD' if address == eXRD else 'USDC'
                        # store.addBalance(to, token, -value)
                    else:  # transactions between Uniswap router and the Pool?
                        if self.debug:
                            print('FROM: ' + source + ' TO: ' + to + ' Address: ' + address + ' Amount: ' + str(value))

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
