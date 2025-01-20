import json
from datetime import datetime
import requests
import logging

class TronManager:
    TRON_API_URL = 'https://api.codesazan.ir/AutoTron'
    API_KEY = '6729827551:L1QWp943xhky@CodeSazan_APIManager_Bot'

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def create_tron_account(self):
        """
        Creates a new TRON wallet by calling the API
        Returns dict with address and private key
        """
        try:
            params = {
                'key': self.API_KEY,
                'type': 'createAccount' 
            }
            response = requests.get(self.TRON_API_URL + '/', params=params)
            if response.status_code == 200:
                data = response.json()
                return data
            else:
                self.logger.error('خطا در دریافت پاسخ از وب سرویس')
                raise Exception('Error receiving response from web service')
        except Exception as e:
            self.logger.error(f'Error creating Tron account: {str(e)}')
            raise Exception('Unable to create Tron account')

    def get_trx_balance(self, address):
        """
        Gets TRX balance for a TRON wallet address
        Returns balance as float
        """
        try:
            params = {
                'key': self.API_KEY,
                'type': 'balancetrx',  
                'address': address 
            }
            response = requests.get(self.TRON_API_URL + '/', params=params)
            if response.status_code == 200:
                data = response.json()
                print(data['result']['balance'])
                return float(data['result']['balance'])
            else:
                self.logger.error('خطا در دریافت پاسخ از وب سرویس')
                raise Exception('Error receiving response from web service')
        except Exception as e:
            self.logger.error(f'Error getting Tron balance: {str(e)}')
            raise Exception('Unable to get Tron balance')

    def send_trx(self, from_address, private_key, to_address, amount):
        """
        Sends TRX from one address to another
        Returns transaction response data
        """
        try:
            params = {
                'key': self.API_KEY,
                'type': 'sendtrx',
                'address': from_address,
                'backup_key': private_key,
                'to': to_address,
                'amount': str(amount)
            }
            response = requests.get(self.TRON_API_URL, params=params)
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"API request failed with status {response.status_code}")
        except Exception as e:
            self.logger.error(f'Error sending TRX: {str(e)}')
            raise Exception('Unable to send TRX')
