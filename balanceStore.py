from typing import Dict, List


class BalanceStore:
    addresses: Dict[str, List[Dict[str, int]]] = {}

    def __init__(self, addresses: Dict[str, List[Dict[str, int]]]):
        self.addresses = addresses

    def getBalances(self, address: str) -> List[Dict[str, int]]:
        addr = address.lower()
        return self.addresses[addr] if addr in self.addresses else []

    def addStake(self, address: str, value_USDC: int, value_eXRD: int, value_LP: int):
        """
            Adds values to the token balances.
        """
        addr = address.lower()
        balances = self.addresses[addr] if addr in self.addresses else []
        balances.append({
            'USDC': value_USDC,
            'eXRD': value_eXRD,
            'LP': value_LP
        })
        self.addresses[addr] = balances

    def removeStake(self, address: str, value_LP: int):
        """
            Removes a value from the token balance. If LP tokens are removed - removes proportional amount from USDC/eXRD balances
        """
        addr = address.lower()
        balances = self.addresses[addr] if addr in self.addresses else []
        if len(balances) > 0:
            while len(balances) > 0 and value_LP > 0:
                balance = balances[-1]
                initial_LP = balance['LP']
                if value_LP >= initial_LP:
                    del balances[-1]
                    value_LP -= initial_LP
                else:
                    new_LP = initial_LP - value_LP
                    remaining_percent = new_LP / initial_LP if initial_LP != 0 else 1
                    balance['LP'] = new_LP
                    balance['USDC'] = int(balance['USDC'] * remaining_percent)
                    balance['eXRD'] = int(balance['eXRD'] * remaining_percent)
                    balances[-1] = balance
                    value_LP = 0
        else:
            # Just log such cases - deal with them later
            balances.append({
                'USDC': 0,
                'eXRD': 0,
                'LP': -value_LP
            })
        self.addresses[addr] = balances
