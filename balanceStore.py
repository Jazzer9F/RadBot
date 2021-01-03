from typing import Dict


class BalanceStore:
    addresses: Dict[str, Dict[str, int]] = {}

    def __init__(self, addresses: Dict[str, Dict[str, int]]):
        self.addresses = addresses

    def getBalances(self, address: str) -> Dict[str, int]:
        addr = address.lower()
        return self.addresses[addr] if addr in self.addresses else {}

    def addBalance(self, address: str, token: str, value: int):
        """
            Adds value to the token balance. If LP tokens are removed - removes proportional amount from USDC/eXRD balances
        """
        # print('Adding ' + token + ' to ' + address)
        addr = address.lower()
        balances = self.addresses[addr] if addr in self.addresses else {}
        if token in balances:
            initial_value = balances[token]
            new_value = initial_value + value
            if token == 'LP' and value < 0:
                remaining_percent = new_value / initial_value if initial_value != 0 else 1
                if 'USDC' in balances:
                    balances['USDC'] = int(balances['USDC'] * remaining_percent)
                if 'eXRD' in balances:
                    balances['eXRD'] = int(balances['eXRD'] * remaining_percent)
            balances[token] = new_value
        else:
            balances[token] = value
        self.addresses[addr] = balances
