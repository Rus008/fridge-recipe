import asyncio
import logging
import random
from typing import Optional, List
import aiohttp

# Вместо обычного aiohttp используем aiohttp_socks
from aiohttp_socks import ProxyType, ProxyConnector, ChainProxyConnector
from food_parser.logger import setup_colored_logger

# Настройка логгера
logger = setup_colored_logger(__name__)

# Список тестовых URL
TEST_URLS = [
    "https://food.ru"
    # "https://ifconfig.me/ip",
    # "https://checkip.amazonaws.com",
    # "https://api.ipify.org?format=json",
    # "https://ident.me"
]


async def load_proxies(file_path: str) -> List[str]:
    """Загружает список прокси из файла."""
    logger.info(f"Загрузка прокси из файла: {file_path}")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            proxies = [line.strip() for line in f if line.strip()]
        logger.info(f"Успешно загружено {len(proxies)} прокси.")
        return proxies
    except FileNotFoundError:
        logger.error(f"Файл {file_path} не найден.")
        return []
    except Exception as e:
        logger.exception(f"Ошибка при чтении файла {file_path}: {e}")
        return []


async def is_proxy_working(proxy: str, timeout: int = 10) -> bool:
    """Проверяет работоспособность SOCKS5-прокси."""
    logger.debug(f"Проверка SOCKS5-прокси: {proxy}")

    proxy = proxy.removeprefix("socks5://").removeprefix("http://").removeprefix("https://")

    try:
        user = password = None
        host_port = proxy

        if "@" in proxy:
            auth_part, host_part = proxy.split("@", 1)
            user, password = auth_part.split(":", 1)
            host_part = host_part.strip()
            host_port = host_part

        host_port = host_port.strip()
        host, port = host_port.split(":", 1)
        port = int(port)

        connector = ProxyConnector(
            proxy_type=ProxyType.SOCKS5,
            host=host,
            port=port,
            username=user,
            password=password,
            ssl=False,
        )

        async def test_connection():
            async with aiohttp.ClientSession(connector=connector) as session:
                for url in TEST_URLS:
                    try:
                        async with session.get(url, ssl=False, allow_redirects=True) as response:
                            if response.status == 200:
                                logger.info(f"✅ Прокси работает: {proxy} (через {url})")
                                return True
                            else:
                                logger.warning(f"❌ {proxy} вернул статус {response.status} на {url}")
                    except Exception as e:
                        logger.warning(f"⚠ Ошибка при запросе к {url} через {proxy}: {e}")
                        continue
            return False

        result = await asyncio.wait_for(test_connection(), timeout=timeout)
        if not result:
            logger.warning(f"❌ Прокси {proxy} не прошёл ни одну проверку.")
        return result

    except asyncio.TimeoutError:
        logger.warning(f"⏱ Таймаут при проверке прокси {proxy}.")
        return False
    except Exception as e:
        logger.warning(f"🚫 Неизвестная ошибка при проверке прокси {proxy}: {e}")
        return False

async def get_working_proxy(proxies: List[str]) -> Optional[str]:
    """Возвращает первое рабочее SOCKS5-прокси после случайной перетасовки."""
    if not proxies:
        logger.warning("Список прокси пуст.")
        return None

    logger.debug(f"Начинаю проверку {len(proxies)} SOCKS5-прокси...")
    # Выбираем случайную стартовую позицию вместо полной перетасовки
    start_idx = random.randrange(len(proxies) - 10)
    for i in range(len(proxies)):
        proxy = proxies[(start_idx + i) % len(proxies)]
        logger.debug(f"Попытка использовать прокси: {proxy}")
        if await is_proxy_working(proxy):
            logger.debug(f"Используется рабочее прокси: {proxy}")
            return proxy

    logger.error("Не найдено ни одного рабочего SOCKS5-прокси.")
    return None