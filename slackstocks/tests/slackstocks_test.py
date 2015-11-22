from ..components.slackstocks import SlackStocks
import unittest
from unittest.mock import MagicMock


class TestSlackStocks(unittest.TestCase):

    def test_constructor_should_throw_exception_if_no_token(self):
        self.assertRaises(Exception, SlackStocks, None)


if __name__ == '__main__':
    unittest.main()
