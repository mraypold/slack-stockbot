#!/usr/bin/python
import time
import json
import re

from slackclient import SlackClient
from googlefinance import getQuotes


class SlackStocks():
    def __init__(self, token):
        self.user_id = ""
        self.user = ""

        self.client = self._set_client(token)
        self._set_properties()
        self._open_socket()

    def _set_client(self, token):
        """Returns a SlackClient when given a token string.

        Args:
            token: The token to connect to the client.
        Returns:
            A slack client.
        Raise:
            Exception: If token not valid.
        """
        if token:
            return SlackClient(token)
        else:
            raise Exception("A token is required to connect to Slack")

    def _open_socket(self):
        """Opens a socket connection with the slack server.

        This remains as its own method to allow easy mocking for testing.
        """
        self.client.rtm_connect()

    def _set_properties(self):
        """"Sets/overrides the existing bot's properties.

        api_call returns bytes, which must be converted to a dictionary.

        Should only be called after the SlackClient has been setup.
        """
        result = self.client.api_call("auth.test").decode("utf-8")

        result = json.loads(result)

        if not result['ok']:
            raise Exception("Authentication failure!")

        self.user_id = result['user_id'] if 'user_id' in result else ""
        self.user = result['user'] if 'user' in result else ""

    def display_message(self, message, channel):
        """Displays a given message in the specified channel.

        Args:
            message: A message to stream to the channel.
            channel: A channel available to the slack client.
        Raises:
            Exception: If a problem sending a message to the channel.
        """
        try:
            self.client.rtm_send_message(channel, message)
        except Exception as e:
            # Silently fail for now
            print(e)

    def _ismessage(self, event):
        """Returns true if the given event is a text event.

        Args:
            event: A slack even dictionary.
        """
        if 'text' in event and len(event['text'].strip()) > 0:
            return True

        return False

    def _contains_stock(self, message):
        """Returns true if the given message contains a stock symbol.

        Args:
            message: Thje given text message.
        """
        r = re.search(r'\$\w+', message)
        return True if r else False

    def _get_stocks(self, message):
        """Returns the stock tickers for the given message

        Args:
            message: A string containing a stock ticker prefaced by $.
        """
        return re.findall(r'\$\w+', message)

    def _is_stock_bot(self, user_id):
        """Returns true if the given user_id is stockbot

        Args:
            user_id: A user id to check against.
        """
        return user_id == self.user_id

    def _strip_non_alphabet(self, stock):
        """Returns a stock containing only alphabet characters.

        If returns nothing, then the given stock contained non-alphabet
        characters.

        Args:
            stock: A proposed stock which was written in a slack channel.
        """
        return re.sub("[^a-zA-Z]+", "", stock.upper())

    def _parse_events(self, events):
        """Returns a list of stocks for the given list of slack events.

        Args:
            events: A list of slack event dictionary objects.
        """
        stocks = []

        for event in events:
            if self._ismessage(event) and self._contains_stock(event['text']):
                stocks.extend(self._get_stocks(event['text']))

        return stocks

    def _parse_and_respond(self, event):
        """Streams stock data to the channel for the given event.

        Args:
            event: Slack event dictionary
        """
        if self._ismessage(event) and self._contains_stock(event['text']):
            stocks = self._get_stocks(event['text'])

            for stock in stocks:
                ticker = self._strip_non_alphabet(stock)

                # Do not respond if ticker is invalid.
                if not ticker:
                    continue

                channel = event['channel']

                # Lookup ticker data with google finance
                try:
                    gfin = getQuotes(ticker)[0]

                    # We want to display the ticker and the price
                    symbol = gfin.get("StockSymbol")
                    price = gfin.get("LastTradePrice")
                    date = gfin.get("LastTradeDateTimeLong")

                    # We aren't going to bother with localization...
                    response = "{} traded at ${} on {}".format(symbol, price, date)
                    self.client.rtm_send_message(channel, response)
                except Exception:
                    msg = "I was unable to find data on {}.".format(ticker)
                    self.client.rtm_send_message(channel, msg)

    def run(self):
        """Runs the SlackStocks bot until interrupted"""
        print("Connected as {}:{}.".format(self.user, self.user_id))
        print("Press ctrl-c to exit.")

        while True:
            result = self.client.rtm_read()

            if(len(result) > 0):
                for event in result:
                    self._parse_and_respond(event)

            time.sleep(1)
