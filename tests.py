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
        test_cases = [(30, 'SUPER STRONG BUY'),  (0, 'SELL'), (10, 'STRONG BUY'), (-20, 'STRONG SELL')]
        for price, expected in test_cases:
            result = check_alg(price)
            assert result == expected, f"Expected: {expected}, Got: {result}"

    def test_alg_sell_buy(self):
        difference_price, deptht_sell, deptht_buy, rsi, expected = 0.9, 0, 100, 60, 'STRONG BUY'
        result = alg_sell_buy('YNDX', difference_price, deptht_sell, deptht_buy, rsi)
        assert result == expected, f"Expected: {expected}, Got: {result}"

    def test_own_recomendation(self):
        action, difference_price, difference_volume, deptht_sell, deptht_buy, rsi, cci, expected = 'YNDX', 0.7, 0.8, 10, 90, 10, -101, 'SUPER STRONG BUY'
        result = own_recommendetion(action, difference_price, difference_volume, deptht_sell, deptht_buy, rsi, cci)
        assert result == expected, f"Expected: {expected}, Got: {result}"

    def test_process(self):
        action = "YNDX"
        response = requests.get(
            f"https://iss.moex.com/iss/engines/stock/markets/shares/boards/tqbr/securities/{action}.json")
        assert response.status_code == 200, f"Expected: {200}, Got: {response.status_code}"

    def test_check(self):
        action = "YNDX"
        response = requests.get(
            f"https://iss.moex.com/iss/engines/stock/markets/shares/boards/tqbr/securities/{action}.json")
        assert response.status_code == 200
        assert len(check(response, action)) == 4, f"Expected: {4}, Got: {len(check(response, action))}"

if __name__ == '__main__':
    unittest.main()