import unittest

import pytest

from main import *
from unittest.mock import patch, MagicMock
from io import StringIO


class TestBot(unittest.TestCase):

    def test_get_all_companies(self):
        # Mock the response from requests.get
        response = {
            'securities': {
                'data': [
                    ['AAPL', 0, 'Apple'],
                    ['GOOG', 0, 'Alphabet'],
                    ['MSFT', 0, 'Microsoft']
                ]
            }
        }
        with patch('requests.get') as mock_get:
            mock_get.return_value.text = json.dumps(response)
            companies_list = get_all_companies()
            expected = [('AAPL', 0), ('GOOG', 0), ('MSFT', 0)]
            self.assertEqual(companies_list, expected)

    def test_check_alg(self):
        test_cases = [(30, 'SUPER STRONG BUY'),  (0, 'SELL'), (10, 'BUY'), (-20, 'STRONG SELL')]
        for price, expected in test_cases:
            result = check_alg(price)
            assert result == expected, f"Expected: {expected}, Got: {result}"

    def test_alg_sell_buy(self):
        prices, difference_price, deptht_sell, deptht_buy, rsi, expected = [100, 110, 120, 130, 140], 10, 5, 5, 70, 'BUY'
        result = alg_sell_buy(prices, difference_price, deptht_sell, deptht_buy, rsi)
        assert result == expected, f"Expected: {expected}, Got: {result}"

    def test_own_recomendation(self):
        action, difference_price, difference_volume, deptht_sell, deptht_buy, rsi, cci, expected = 100, 0.4, 0.4, 0.4, 100, 20, 5, 'STRONG BUY'
        result = own_recommendetion(action, difference_price, difference_volume, deptht_sell, deptht_buy, rsi, cci)
        assert result == expected, f"Expected: {expected}, Got: {result}"

if __name__ == '__main__':
    unittest.main()