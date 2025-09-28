#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API для получения цен криптовалют
"""

import logging
import asyncio
import aiohttp
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


class CryptoAPI:
    """API для получения цен криптовалют"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_duration = 60  # Кэш на 1 минуту
        
        # Поддерживаемые криптовалюты и их ID в CoinGecko
        self.crypto_ids = {
            # Топ-8
            'BTC': 'bitcoin',
            'ETH': 'ethereum',
            'BNB': 'binancecoin',
            'SOL': 'solana',
            'ADA': 'cardano',
            'XRP': 'ripple',
            'DOT': 'polkadot',
            'DOGE': 'dogecoin',
            
            # DeFi
            'USDT': 'tether',
            'USDC': 'usd-coin',
            'DAI': 'dai',
            'UNI': 'uniswap',
            'LINK': 'chainlink',
            'AAVE': 'aave',
            'COMP': 'compound-governance-token',
            'SUSHI': 'sushi',
            
            # Layer 1
            'MATIC': 'matic-network',
            'AVAX': 'avalanche-2',
            'FTM': 'fantom',
            'NEAR': 'near',
            'ALGO': 'algorand',
            'ATOM': 'cosmos',
            
            # GameFi
            'AXS': 'axie-infinity',
            'SAND': 'the-sandbox',
            'MANA': 'decentraland',
            'ENJ': 'enjincoin',
            
            # Meme
            'SHIB': 'shiba-inu',
            'PEPE': 'pepe',
            'FLOKI': 'floki',
            
            # Другие популярные
            'LTC': 'litecoin',
            'BCH': 'bitcoin-cash',
            'XLM': 'stellar',
            'VET': 'vechain',
            'FIL': 'filecoin',
            'ICP': 'internet-computer',
            'TRX': 'tron',
            'ETC': 'ethereum-classic',
            'XMR': 'monero',
            'ZEC': 'zcash',
            
            # Дополнительные криптовалюты
            'APEX': 'apex-coin',
            'APT': 'aptos',
            'ARB': 'arbitrum',
            'OP': 'optimism',
            'SUI': 'sui',
            'SEI': 'sei-network',
            'TIA': 'celestia',
            'INJ': 'injective-protocol',
            'JUP': 'jupiter-exchange-solana',
            'WIF': 'dogwifcoin',
            'BONK': 'bonk',
            'POPCAT': 'popcat',
            'MEW': 'cat-in-a-dogs-world',
            'BOME': 'book-of-meme',
            'SLERF': 'slerf',
            'MYRO': 'myro',
            'PNUT': 'peanut-the-squirrel',
            'ACT': 'achain',
            'ADX': 'adex',
            'AGI': 'singularitynet',
            'AKRO': 'akropolis',
            'ALCX': 'alchemix',
            'ALEPH': 'aleph',
            'ALPHA': 'alpha-finance',
            'AMP': 'amp-token',
            'ANKR': 'ankr',
            'ANT': 'aragon',
            'API3': 'api3',
            'AR': 'arweave',
            'AUDIO': 'audius',
            'BADGER': 'badger-dao',
            'BAL': 'balancer',
            'BAND': 'band-protocol',
            'BAT': 'basic-attention-token',
            'BETA': 'beta-finance',
            'BLZ': 'bluzelle',
            'BNT': 'bancor',
            'BOND': 'barnbridge',
            'BRD': 'bread',
            'BUSD': 'binance-usd',
            'C98': 'coin98',
            'CEL': 'celsius-degree-token',
            'CELO': 'celo',
            'CHR': 'chromaway',
            'CHZ': 'chiliz',
            'CKB': 'nervos-network',
            'CLV': 'clover-finance',
            'COCOS': 'cocos-bcx',
            'COMP': 'compound-governance-token',
            'COTI': 'coti',
            'CRO': 'crypto-com-chain',
            'CRV': 'curve-dao-token',
            'CTSI': 'cartesi',
            'CVC': 'civic',
            'CVX': 'convex-finance',
            'DASH': 'dash',
            'DENT': 'dent',
            'DGB': 'digibyte',
            'DIA': 'dia-data',
            'DNT': 'district0x',
            'DYDX': 'dydx',
            'EGLD': 'elrond-erd-2',
            'ELF': 'aelf',
            'ENJ': 'enjincoin',
            'ENS': 'ethereum-name-service',
            'EOS': 'eos',
            'ERN': 'ethernity-chain',
            'ETN': 'electroneum',
            'FARM': 'harvest-finance',
            'FET': 'fetch-ai',
            'FIS': 'stafi',
            'FLOW': 'flow',
            'FORTH': 'ampleforth-governance-token',
            'FTT': 'ftx-token',
            'FXS': 'frax-share',
            'GALA': 'gala',
            'GNO': 'gnosis',
            'GRT': 'the-graph',
            'GTC': 'gitcoin',
            'GUSD': 'gemini-dollar',
            'HBAR': 'hedera-hashgraph',
            'HNT': 'helium',
            'HOT': 'holo',
            'HT': 'huobi-token',
            'HUSD': 'husd',
            'IDEX': 'idex',
            'ILV': 'illuvium',
            'IMX': 'immutable-x',
            'IOST': 'iostoken',
            'IOTX': 'iotex',
            'JASMY': 'jasmycoin',
            'KAVA': 'kava',
            'KEEP': 'keep-network',
            'KLAY': 'klay-token',
            'KNC': 'kyber-network-crystal',
            'KSM': 'kusama',
            'LDO': 'lido-dao',
            'LEO': 'leo-token',
            'LINA': 'linear',
            'LPT': 'livepeer',
            'LRC': 'loopring',
            'LSK': 'lisk',
            'LUNC': 'terra-luna',
            'LUNA': 'terra-luna-2',
            'MASK': 'mask-network',
            'MCO': 'monaco',
            'MDT': 'measurable-data-token',
            'MIR': 'mirror-protocol',
            'MKR': 'maker',
            'MLN': 'melon',
            'MOVR': 'moonriver',
            'NANO': 'nano',
            'NKN': 'nkn',
            'NMR': 'numeraire',
            'NU': 'nucypher',
            'OCEAN': 'ocean-protocol',
            'OGN': 'origin-protocol',
            'OMG': 'omg',
            'ONE': 'harmony',
            'ONT': 'ontology',
            'OOKI': 'ooki',
            'ORN': 'orion-protocol',
            'OXT': 'orchid-protocol',
            'PAXG': 'pax-gold',
            'PERP': 'perpetual-protocol',
            'POND': 'marlin',
            'POWR': 'power-ledger',
            'QNT': 'quant-network',
            'QTUM': 'qtum',
            'RAD': 'radicle',
            'RARI': 'rarible',
            'REN': 'republic-protocol',
            'REP': 'augur',
            'REQ': 'request-network',
            'RLC': 'iexec-rlc',
            'ROSE': 'oasis-network',
            'RSR': 'reserve-rights-token',
            'RUNE': 'thorchain',
            'RVN': 'ravencoin',
            'SAND': 'the-sandbox',
            'SC': 'siacoin',
            'SCRT': 'secret',
            'SFP': 'safemoon',
            'SKL': 'skale',
            'SNX': 'havven',
            'SRM': 'serum',
            'STG': 'stargate-finance',
            'STORJ': 'storj',
            'STX': 'stacks',
            'SUN': 'sun-token',
            'SUSHI': 'sushi',
            'SWEAT': 'sweatcoin',
            'SXP': 'swipe',
            'SYN': 'synapse-2',
            'THETA': 'theta-token',
            'TLM': 'alien-worlds',
            'TWT': 'trust-wallet-token',
            'UMA': 'uma',
            'UNFI': 'unifi-protocol-dao',
            'UOS': 'ultra',
            'UTK': 'utrust',
            'VTHO': 'vethor-token',
            'WAXP': 'wax',
            'WAVES': 'waves',
            'WAX': 'wax',
            'WBTC': 'wrapped-bitcoin',
            'WING': 'wing-finance',
            'WNXM': 'wrapped-nxm',
            'WOO': 'woo-network',
            'XEC': 'ecash',
            'XEM': 'nem',
            'XNO': 'nano',
            'XTZ': 'tezos',
            'YFI': 'yearn-finance',
            'YFII': 'yfii-finance',
            'YGG': 'yield-guild-games',
            'ZEN': 'horizen',
            'ZIL': 'zilliqa',
            'ZRX': '0x'
        }
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10),
            headers={
                'User-Agent': 'TelegramBot/1.0',
                'Accept': 'application/json'
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def get_crypto_price(self, crypto: str) -> Optional[float]:
        """Получить текущую цену криптовалюты"""
        try:
            crypto = crypto.upper()
            
            # Проверяем кэш
            if crypto in self.cache:
                cached_data = self.cache[crypto]
                if datetime.now() - cached_data['timestamp'] < timedelta(seconds=self.cache_duration):
                    return cached_data['price']
            
            # Получаем цену из API
            price = await self._fetch_price_from_api(crypto)
            
            if price:
                # Сохраняем в кэш
                self.cache[crypto] = {
                    'price': price,
                    'timestamp': datetime.now()
                }
                return price
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка получения цены {crypto}: {e}")
            return None
    
    async def _fetch_price_from_api(self, crypto: str) -> Optional[float]:
        """Получить цену из CoinGecko API"""
        try:
            if crypto not in self.crypto_ids:
                logger.warning(f"Неподдерживаемая криптовалюта: {crypto}")
                return None
            
            crypto_id = self.crypto_ids[crypto]
            
            # Используем CoinGecko API
            url = f"https://api.coingecko.com/api/v3/simple/price"
            params = {
                'ids': crypto_id,
                'vs_currencies': 'usd',
                'include_24hr_change': 'true'
            }
            
            if not self.session:
                self.session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=10)
                )
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if crypto_id in data:
                        return data[crypto_id]['usd']
                    else:
                        logger.warning(f"Криптовалюта {crypto} не найдена в ответе API")
                        return None
                else:
                    logger.error(f"Ошибка API CoinGecko: {response.status}")
                    return None
                    
        except asyncio.TimeoutError:
            logger.error(f"Таймаут при получении цены {crypto}")
            return None
        except Exception as e:
            logger.error(f"Ошибка при запросе к API: {e}")
            return None
    
    async def get_multiple_prices(self, cryptos: list) -> Dict[str, float]:
        """Получить цены для нескольких криптовалют одновременно"""
        try:
            # Фильтруем поддерживаемые криптовалюты
            supported_cryptos = [c.upper() for c in cryptos if c.upper() in self.crypto_ids]
            
            if not supported_cryptos:
                return {}
            
            # Получаем ID для API
            crypto_ids = [self.crypto_ids[c] for c in supported_cryptos]
            
            # Запрос к CoinGecko API
            url = f"https://api.coingecko.com/api/v3/simple/price"
            params = {
                'ids': ','.join(crypto_ids),
                'vs_currencies': 'usd',
                'include_24hr_change': 'true'
            }
            
            if not self.session:
                self.session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=10)
                )
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Преобразуем ответ в нужный формат
                    result = {}
                    for crypto in supported_cryptos:
                        crypto_id = self.crypto_ids[crypto]
                        if crypto_id in data:
                            price = data[crypto_id]['usd']
                            result[crypto] = price
                            
                            # Обновляем кэш
                            self.cache[crypto] = {
                                'price': price,
                                'timestamp': datetime.now()
                            }
                    
                    return result
                else:
                    logger.error(f"Ошибка API CoinGecko: {response.status}")
                    return {}
                    
        except Exception as e:
            logger.error(f"Ошибка получения множественных цен: {e}")
            return {}
    
    def get_cached_price(self, crypto: str) -> Optional[float]:
        """Получить цену из кэша без запроса к API"""
        try:
            crypto = crypto.upper()
            if crypto in self.cache:
                cached_data = self.cache[crypto]
                if datetime.now() - cached_data['timestamp'] < timedelta(seconds=self.cache_duration):
                    return cached_data['price']
            return None
        except Exception:
            return None
    
    def clear_cache(self) -> None:
        """Очистить кэш"""
        self.cache.clear()
        logger.info("Кэш цен криптовалют очищен")


# Глобальный экземпляр API
crypto_api = CryptoAPI()


async def get_crypto_price(crypto: str) -> Optional[float]:
    """Удобная функция для получения цены криптовалюты"""
    async with crypto_api as api:
        return await api.get_crypto_price(crypto)


async def get_multiple_crypto_prices(cryptos: list) -> Dict[str, float]:
    """Удобная функция для получения цен нескольких криптовалют"""
    async with crypto_api as api:
        return await api.get_multiple_prices(cryptos)
