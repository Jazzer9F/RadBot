# Common utility functions
import json
from web3 import Web3


def initWeb3():
    with open('./infura.json') as f:
        infuraUrl = json.load(f)['url']
    return Web3(Web3.HTTPProvider(infuraUrl))


def readContract(w3, file, address):
    with open(file) as f:
        abi = json.load(f)
        if 'result' in abi:
            abi = abi['result']
    return w3.eth.contract(address=address, abi=abi)
