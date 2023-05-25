import unittest
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

if __name__ == '__main__':
    unittest.main()