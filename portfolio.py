from abc import ABC
from datetime import datetime
import time
import json

from selenium import webdriver
# Tyto tri spodni from nemazat. Je to skyte v kodu. Jinak to bude vyhazovat chyby.
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from bs4 import BeautifulSoup

from binance.client import Client
import config

from sqlalchemy import create_engine

from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
    Column,
    Integer,
    Text,
    Numeric,
    BigInteger
)

import os
# TODO - nechat tady nebo dat do 'if __name__ == "__main__":' ? Nebude to ovlivnovat dalsi soubory po importu
# do dalsiho souboru?
os.chdir(os.path.dirname(os.path.abspath(__file__)))


class Scraper:

    def __init__(self):
        self.assets = {}

    @staticmethod
    def _get_html_code_selenium(url_address: str, wait_till="1"):
        """
        Funkce stahne html kod z webu knihovnou Selenium.
        Vrati html kod ve formatu string, pripraveny k parsovani knihovnou beautifulsoup.

        " " "
        <html><body>
        ... telo ...
        </body></html>
        " " "

        :param url_address: "url_adresa"
        :return: "html_kod_ve_formatu_string"
        """

        print(f"Getting data from URL: {url_address}")

        browser = webdriver.Chrome()
        browser.get(url_address)
        # Když je okno malé, tak má jiný html kód, protože je jinak poskládané, proto je potřeba
        # ho zvětšit na maximum, aby mělo pořád stejný html kód
        browser.maximize_window()

        # element = WebDriverWait(browser, 15).until(
        #     EC.presence_of_element_located((By.CLASS_NAME, "TokenRow_value__1eEXO"))
        # )

        # Kdyz je potreba pockat, az se nacte nejaky tag. Wait_till je v tride ekosystemu.
        eval(wait_till)

        # time.sleep(1) je tam kvuli tomu, ze se nestiha nacist web a pote se spatne stahne html kod,
        # proto se ceka 1s, aby se vse spravne nacetlo
        time.sleep(1)

        # print(browser.page_source)

        return browser.page_source  # html kód ve formátu string

    def parse_html_code_from_string(self, url_address, wait_till) -> BeautifulSoup:
        """
        Funkce prevede html kod "str" na naparsovany objekt Beautifulsoup, ve kterem uz je mozno vyhledavat.

        Beautifulsoup =
        <html><body>
        ... telo ...
        </body></html>

        :return: objekt BeautifulSoup
        """

        bs_obj = BeautifulSoup(self._get_html_code_selenium(url_address, wait_till), "html.parser")
        # print(bs_obj)

        return bs_obj


class LoadFile(ABC):

    def load_file(self, file_name):
        pass


class LoadJsonFile(LoadFile):

    def __init__(self):
        self.data_file = None

    def load_file(self, file_name):
        """
        Metoda nacte JSON soubor do kolekce ve ktere je ulozen. Napr.:
        data = [{obj1}, {obj2}, {obj3}]

        :param file_name: "nazev_souboru.json"
        :return: kolekce (list, slovnik, ...)
        """

        with open(file_name) as f:
            self.data_file = json.load(f)

        return self.data_file


class UserInput:

    def __init__(self):
        self.data_file = None
        self.created_objects = []

    def load_file(self, loader, file_name):
        self.data_file = loader.load_file(file_name)
        return self.data_file

    def create_class_objects(self):
        for data in self.data_file:
            # print(data)
            ecosystem_cex = data["ecosystem_cex"]  # Vrati "Cosmos" nebo "Eth" nebo ...
            # print(ekosystem)

            created_object = eval(f"{ecosystem_cex}(**{data})")  # Trida se vygeneruje

            self.add_object(created_object)

    def add_object(self, created_object):
        self.created_objects.append(created_object)


class Tokens(ABC):

    def __init__(self, division, ecosystem_cex):
        self.division = division
        self.ecosystem_cex = ecosystem_cex

        self.assets = {}

    def get_assets(self):
        pass


class Cosmos(Tokens):

    def __init__(self, division, ecosystem_cex, network, url_address):
        super().__init__(division, ecosystem_cex)
        self.network = network
        self.url_address = url_address

    def get_assets(self):

        wait_till = """WebDriverWait(browser, 20).until(
            EC.presence_of_element_located((By.CLASS_NAME, "TokenRow_value__1eEXO"))
        )"""

        scraper = Scraper()

        # Najde vsechny tokeny v tabulce assets
        found_assets = scraper.parse_html_code_from_string(self.url_address, wait_till).find_all(
            "div", {"class": "TokensTable_row__1DYIv"}
        )
        for asset in found_assets:
            # Najde nazev tokenu
            name = asset.find("div", {"class": "TokenRow_assetName__q1FOR"}).text
            # Najde mnozstvi tokenu
            amount = asset.find("div", {"data-for": "originDecimal"}).get("data-tip").lstrip("≈ $").replace(",", "")
            # Najde dolarovou hodnotu tokenu
            dollar_value = asset.find("div", {"data-for": "originTotalValue"}).get("data-tip").lstrip("≈ $")\
                .replace(",", "")
            self.assets[name] = {"amount": float(amount), "dollar_value": float(dollar_value)}

        print(self.assets)

        return self.assets


class Ethereum(Tokens):

    def __init__(self, division, ecosystem_cex, network, url_address):
        super().__init__(division, ecosystem_cex)
        self.network = network
        self.url_address = url_address

    def get_assets(self):

        wait_till = "1"  # 1 - neceka na nic

        scraper = Scraper()

        # Najde vsechny tokeny v tabulce assets
        found_assets = scraper.parse_html_code_from_string(self.url_address, wait_till)\
            .find("div", {"class": "card-body"})

        # print(found_assets)

        amount, name = found_assets.div.find_next_sibling().div.div.text.split()
        amount = float(amount)
        dollar_value = found_assets.div.find_next_sibling().find_next_sibling().span.text.lstrip("≈ $(@")\
            .rstrip("/ETH)").replace(",", "")
        dollar_value = amount * float(dollar_value)

        if name == "Ether":
            name = "ETH"

        self.assets[name] = {"amount": amount, "dollar_value": dollar_value}

        print(self.assets)

        return self.assets


class Binance(Tokens):

    def __init__(self, division, ecosystem_cex):
        super().__init__(division, ecosystem_cex)
        self.division = division
        self.ecosystem_cex = ecosystem_cex

        self.client = None
        self.spot_tokens = {}
        self.spot_prices = {}

    def _connection(self):

        # Pripojeni API
        self.client = Client(config.binance_api_key, config.binance_secret_key)

    def get_spot_asets(self):

        # vypise vsechny tokeny co jsou na binance a k nim moji hodnotu, ikdyz je 0.0
        spot = self.client.get_account()

        for token in spot["balances"]:  # Vybere ze ziskaneho slovniku jen info o tokenech
            if float(token["free"]) > 0.0:  # Vybere jen mnozstvi tokenu > 0.0
                # Ulozi do slovniku info o tokenu {'BTC': '0.5', 'ETH': '2.0'}
                self.spot_tokens[token['asset']] = token['free']

        # print(self.spot_tokens)

    def get_token_price(self):

        # TODO dodelat vsechny tokeny, ktere se nebudou ukladat
        not_count = ["LDBTC", "NFT"]

        # TODO dodelat vsechny tokeny, kde se nebude pridelavat "USDT" napr USDTUSDT
        stable_coins = ["USDT", "BUSD", "USDC"]

        # TODO dodelat logiku pro LDBTC (zastakovany BTC)

        for token in self.spot_tokens:
            if token not in not_count:
                if token not in stable_coins:
                    # if token not in not_count or token not in stable_coins:
                    # print(token)
                    # price vrati {'symbol': 'BTCUSDT', 'price': '24700.91000000'}
                    price = self.client.get_symbol_ticker(symbol=token+"USDT")
                    # print(price)
                    # print(type(price["price"]))
                    self.spot_prices[token] = price
                elif token in stable_coins:
                    self.spot_prices[token] = {"symbol": token, "price": 1}

        # print(self.spot_prices)

    def get_assets(self):

        self._connection()
        self.get_spot_asets()
        self.get_token_price()

        # self.assets[]

        for key, value in self.spot_tokens.items():  # Vytvori lovnik s amount
            self.assets[key] = {"amount": float(value), "dollar_value": 0}

        for key, value in self.spot_prices.items():  # do slovniku s amount doplni dollar value
            self.assets[key]["dollar_value"] = float(value["price"]) * float(self.assets[key]["amount"])

        print("Getting data from Binance")
        print(self.assets)


class AssetsCounter:

    def __init__(self):

        # Pripravene seznamy pro zapis do databaze
        self.all_assets_list = []
        self.blockchain_assets_list = []
        self.cex_assets_list = []

        # Assets
        self.all_assets = {}
        self.blockchain_assets = {}
        self.cex_assets = {}

        # Dollar value
        self.blockchain_dollar_value = 0
        self.cex_dollar_value = 0

    def count_all_assets(self, objects):
        """

        Příklad výstupu:

        [{'name': 'ATOM', 'amount': 214.78, 'dollar_value': 2908},
         {'name': 'JUNO', 'amount': 62.22, 'dollar_value': 79},
         {'name': 'OSMO', 'amount': 55.69, 'dollar_value': 56},
         {'name': 'ETH', 'amount': 2.83, 'dollar_value': 4655}]

        :param objects:
        :return:
        """

        for obj in objects.created_objects:

            for key, value in obj.assets.items():
                # print(f"key: {key}, value: {value}")

                if key not in self.all_assets:
                    value_part = {"amount": value["amount"], "dollar_value": value["dollar_value"]}
                    self.all_assets[key] = value_part
                else:
                    self.all_assets[key]["amount"] += value["amount"]
                    self.all_assets[key]["dollar_value"] += value["dollar_value"]

        for key, value in self.all_assets.items():
            slovnik = {"name": key, "amount": round(value["amount"], 2), "dollar_value": round(value["dollar_value"])}
            self.all_assets_list.append(slovnik)

    def count_blockchain_cex_assets(self, objects):

        for obj in objects.created_objects:

            if obj.division == "Blockchain":
                for key, value in obj.assets.items():
                    # print(f"key: {key}, value: {value}")

                    if key not in self.blockchain_assets:
                        value_part = {"division": "Blockchain", "amount": value["amount"],
                                      "dollar_value": value["dollar_value"]}
                        self.blockchain_assets[key] = value_part
                        self.blockchain_dollar_value += value["dollar_value"]
                    else:
                        self.blockchain_assets[key]["amount"] += value["amount"]
                        self.blockchain_assets[key]["dollar_value"] += value["dollar_value"]
                        self.blockchain_dollar_value += value["dollar_value"]
            elif obj.division == "Cex":
                for key, value in obj.assets.items():
                    # print(f"key: {key}, value: {value}")

                    if key not in self.cex_assets:
                        value_part = {"division": "Cex", "amount": value["amount"], "dollar_value": value["dollar_value"]}
                        self.cex_assets[key] = value_part
                        self.cex_dollar_value += value["dollar_value"]
                    else:
                        self.cex_assets[key]["amount"] += value["amount"]
                        self.cex_assets[key]["dollar_value"] += value["dollar_value"]
                        self.cex_dollar_value += value["dollar_value"]

        for key, value in self.blockchain_assets.items():
            # TODO hodit usera jinam
            slovnik = {"user_id": 2, "division": "Blockchain", "name": key, "amount": round(value["amount"], 2),
                       "dollar_value": round(value["dollar_value"])}
            self.blockchain_assets_list.append(slovnik)

        for key, value in self.cex_assets.items():
            # TODO hodit usera jinam
            slovnik = {"user_id": 2, "division": "Cex", "name": key, "amount": round(value["amount"], 2),
                       "dollar_value": round(value["dollar_value"])}
            self.cex_assets_list.append(slovnik)

        print("Blockchain assets: ", self.blockchain_assets)
        print("Cex assets: ", self.cex_assets)

        print("Blockchain assets database: ", self.blockchain_assets_list)
        print("Cex assets database: ", self.cex_assets_list)

        print(self.blockchain_dollar_value)
        print(self.cex_dollar_value)

    def count_assets(self, objects):

        self.count_all_assets(objects)
        self.count_blockchain_cex_assets(objects)


class Database:

    def __init__(self):

        self.engine = None
        self.metadata = None

        # Tabulky
        self.viewer_portfolio_assets = None
        self.viewer_blockchain_cex_assets = None
        self.viewer_hodl_staking_farming_stable_assets = None
        self.viewer_networks_assets = None
        self.viewer_dollar_value = None

        # Users
        self.my_user = []
        self.demo_user_all_assets = []
        self.demo_live_user = []

        self.demo_user_blockchain_cex_assets = []
        self.demo_user_hodl_staking_farming_stable_assets = []
        self.demo_user_networks_assets = []
        self.demo_user_dollar_value = []

    def connection(self):

        # engine = create_engine(config.postgresql_engine, echo=True)   =>   echo=True  = debug mod
        self.engine = create_engine(config.postgresql_engine)

        self.metadata = MetaData()

    def add_tables(self):

        self.viewer_portfolio_assets = Table(
            "viewer_portfolio_assets",
            self.metadata,
            Column("id", BigInteger),
            Column("user_id", Integer),
            Column("date_and_time", Text),
            Column("name", Text),
            Column("amount", Numeric),
            Column("dollar_value", Numeric)
        )

        self.viewer_blockchain_cex_assets = Table(
            "viewer_blockchain_cex_assets",
            self.metadata,
            Column("id", BigInteger),
            Column("user_id", Integer),
            Column("date_and_time", Text),
            Column("division", Text),
            Column("name", Text),
            Column("amount", Numeric),
            Column("dollar_value", Numeric)
        )

        self.viewer_hodl_staking_farming_stable_assets = Table(
            "viewer_hodl_staking_farming_stable_assets",
            self.metadata,
            Column("id", BigInteger),
            Column("user_id", Integer),
            Column("date_and_time", Text),
            Column("division", Text),
            Column("name", Text),
            Column("amount", Numeric),
            Column("dollar_value", Numeric)
        )

        self.viewer_networks_assets = Table(
            "viewer_networks_assets",
            self.metadata,
            Column("id", BigInteger),
            Column("user_id", Integer),
            Column("date_and_time", Text),
            Column("division", Text),
            Column("name", Text),
            Column("amount", Numeric),
            Column("dollar_value", Numeric)
        )

        self.viewer_dollar_value = Table(
            "viewer_dollar_value",
            self.metadata,
            Column("id", BigInteger),
            Column("user_id", Integer),
            Column("date_and_time", Text),
            Column("category", Text),
            Column("division", Text),
            Column("dollar_value", Numeric)
        )

    def fill_my_user(self):

        self.add_other_informations()

        self.a = vypocet.blockchain_assets_list
        self.b = vypocet.cex_assets_list

    def fill_demo_user(self):

        self.demo_user_all_assets = [
            {'user_id': 3, 'name': 'wETH', 'amount': 0.125, 'dollar_value': 200},
            {'user_id': 3, 'name': 'ETH', 'amount': 0.73, 'dollar_value': 950},
            {'user_id': 3, 'name': 'BTC', 'amount': 0.01, 'dollar_value': 250},
            {'user_id': 3, 'name': 'ATOM', 'amount': 57.14, 'dollar_value': 800},
            {'user_id': 3, 'name': 'JUNO', 'amount': 153, 'dollar_value': 200},
            {'user_id': 3, 'name': 'DOT', 'amount': 27, 'dollar_value': 150},
            {'user_id': 3, 'name': 'USDT', 'amount': 300, 'dollar_value': 300}
        ]

        self.demo_user_blockchain_cex_assets = [
            {'user_id': 3, 'division': "Blockchain", 'name': 'ETH', 'amount': 0.73, 'dollar_value': 950},
            {'user_id': 3, 'division': "Blockchain", 'name': 'wETH', 'amount': 0.125, 'dollar_value': 200},
            {'user_id': 3, 'division': "Blockchain", 'name': 'ATOM', 'amount': 57.14, 'dollar_value': 800},
            {'user_id': 3, 'division': "Blockchain", 'name': 'JUNO', 'amount': 153, 'dollar_value': 200},
            {'user_id': 3, 'division': "Cex", 'name': 'BTC', 'amount': 0.01, 'dollar_value': 250},
            {'user_id': 3, 'division': "Cex", 'name': 'DOT', 'amount': 27, 'dollar_value': 150},
            {'user_id': 3, 'division': "Cex", 'name': 'USDT', 'amount': 300, 'dollar_value': 300}
        ]

        self.demo_user_hodl_staking_farming_stable_assets = [
            {'user_id': 3, 'division': "Hodl", 'name': 'ATOM', 'amount': 21.43, 'dollar_value': 300},
            {'user_id': 3, 'division': "Hodl", 'name': 'JUNO', 'amount': 76.10, 'dollar_value': 100},
            {'user_id': 3, 'division': "Hodl", 'name': 'ETH', 'amount': 0.53, 'dollar_value': 850},
            {'user_id': 3, 'division': "Hodl", 'name': 'wETH', 'amount': 0.125, 'dollar_value': 200},
            {'user_id': 3, 'division': "Hodl", 'name': 'BTC', 'amount': 0.006, 'dollar_value': 150},
            {'user_id': 3, 'division': "Hodl", 'name': 'DOT', 'amount': 27, 'dollar_value': 150},
            {'user_id': 3, 'division': "Staking", 'name': 'ATOM', 'amount': 35.71, 'dollar_value': 500},
            {'user_id': 3, 'division': "Staking", 'name': 'JUNO', 'amount': 76.90, 'dollar_value': 100},
            {'user_id': 3, 'division': "Farming", 'name': 'ETH', 'amount': 0.0625, 'dollar_value': 100},
            {'user_id': 3, 'division': "Farming", 'name': 'BTC', 'amount': 0.004, 'dollar_value': 100},
            {'user_id': 3, 'division': "Stable", 'name': 'USDT', 'amount': 300, 'dollar_value': 300}
        ]

        self.demo_user_networks_assets = [
            {'user_id': 3, 'division': "Cosmos", 'name': 'ATOM', 'amount': 57.14, 'dollar_value': 800},
            {'user_id': 3, 'division': "Cosmos", 'name': 'JUNO', 'amount': 153, 'dollar_value': 200},
            {'user_id': 3, 'division': "Ethereum", 'name': 'ETH', 'amount': 0.73, 'dollar_value': 950},
            {'user_id': 3, 'division': "Ethereum", 'name': 'wETH', 'amount': 0.125, 'dollar_value': 200},
            {'user_id': 3, 'division': "Binance", 'name': 'BTC', 'amount': 0.01, 'dollar_value': 250},
            {'user_id': 3, 'division': "Binance", 'name': 'DOT', 'amount': 27, 'dollar_value': 150},
            {'user_id': 3, 'division': "Binance", 'name': 'USDT', 'amount': 300, 'dollar_value': 300}
        ]

        self.demo_user_dollar_value = [
            {'user_id': 3, 'category': 'blockchain_cex', 'division': "Blockchain", 'dollar_value': 2150},
            {'user_id': 3, 'category': 'blockchain_cex', 'division': "Cex", 'dollar_value': 700},
            {'user_id': 3, 'category': 'hodl_staking_farming_stable', 'division': "Hodl", 'dollar_value': 1750},
            {'user_id': 3, 'category': 'hodl_staking_farming_stable', 'division': "Staking", 'dollar_value': 600},
            {'user_id': 3, 'category': 'hodl_staking_farming_stable', 'division': "Farming", 'dollar_value': 200},
            {'user_id': 3, 'category': 'hodl_staking_farming_stable', 'division': "Stable", 'dollar_value': 300},
            {'user_id': 3, 'category': 'network', 'division': "Cosmos", 'dollar_value': 1000},
            {'user_id': 3, 'category': 'network', 'division': "Ethereum", 'dollar_value': 1150},
            {'user_id': 3, 'category': 'network', 'division': "Binance", 'dollar_value': 700},
        ]

    def fill_demo_live_user(self):

        self.demo_live_user = [
            {'user_id': 4, 'name': 'SOL', 'amount': 5, 'dollar_value': 100},
            {'user_id': 4, 'name': 'NEAR', 'amount': 20, 'dollar_value': 50},
            {'user_id': 4, 'name': 'DOT', 'amount': 10, 'dollar_value': 40},
            {'user_id': 4, 'name': 'ATOM', 'amount': 15, 'dollar_value': 250}
        ]

    def add_other_informations(self):

        date_and_time = str(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        for asset in vypocet.all_assets_list:
            asset["user_id"] = 2
            asset["date_and_time"] = date_and_time

        self.my_user = vypocet.all_assets_list

    def database_execution(self):

        # Pocatecni inicializace databaze
        self.connection()

        # Vlozi vzor prazdne tabulky
        self.add_tables()

        self.metadata.drop_all(self.engine, checkfirst=True)  # vymaže včechny tabulky
        self.metadata.create_all(self.engine, checkfirst=True)  # vytvoří všechny tabulky

        connection = self.engine.connect()

        self.fill_my_user()  # Vlozi data pro tabulky pro muj account
        self.fill_demo_user()  # Vlozi data pro tabulky pro demo account
        self.fill_demo_live_user()  # Vlozi data pro tabulky pro demo_live account

        connection.execute(self.viewer_portfolio_assets.insert(), self.my_user)
        connection.execute(self.viewer_portfolio_assets.insert(), self.demo_user_all_assets)
        connection.execute(self.viewer_portfolio_assets.insert(), self.demo_live_user)

        connection.execute(self.viewer_blockchain_cex_assets.insert(), self.a)
        connection.execute(self.viewer_blockchain_cex_assets.insert(), self.b)
        connection.execute(self.viewer_blockchain_cex_assets.insert(), self.demo_user_blockchain_cex_assets)

        connection.execute(self.viewer_hodl_staking_farming_stable_assets.insert(),
                           self.demo_user_hodl_staking_farming_stable_assets)

        connection.execute(self.viewer_networks_assets.insert(), self.demo_user_networks_assets)

        connection.execute(self.viewer_dollar_value.insert(), self.demo_user_dollar_value)

        connection.commit()


if __name__ == "__main__":

    ###########################################################################
    # Nacteni adres z json souboru a vytvoreni objektu trid
    ###########################################################################

    obj_addresses = LoadJsonFile()
    obj_input = UserInput()

    # obj_input.nacti_soubor(obj_adresy, "adresy.json")
    obj_input.load_file(obj_addresses, "adresy_test.json")
    obj_input.create_class_objects()

    # print(obj_input.created_objects)

    ###########################################################################
    # Stahnuti assets
    ###########################################################################

    for objekt in obj_input.created_objects:  # obj_input.created_objects - vsechny objekty v listu na dalsi praci
        objekt.get_assets()

    ###########################################################################
    # Spocitani assets
    ###########################################################################

    vypocet = AssetsCounter()
    vypocet.count_assets(obj_input)
    # print(vypocet.all_assets)
    # print(vypocet.all_assets_list)

    ###########################################################################
    # Prace s databazi
    ###########################################################################

    database = Database()
    database.database_execution()
