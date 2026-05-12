import asyncio, aiohttp, re, json, time, pandas as pd
from bs4 import BeautifulSoup
from seaborn.external.docscrape import header
from unidecode import unidecode
from selenium import webdriver
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from tqdm.asyncio import tqdm_asyncio
from tqdm import tqdm
from aiohttp import ClientTimeout
from food_parser.proxy import get_working_proxy, load_proxies
from food_parser.stealth import get_headers, USER_AGENTS
import random
from aiohttp_socks import ProxyType, ProxyConnector


timeout = ClientTimeout(
    total=30,        # общий таймаут (можно больше)
    connect=10,      # на соединение
    sock_read=20     # на чтение ответа
)
START_URL = "https://food.ru"
# Категории, ссылки и количество страниц для каждой категории
categories = ['первые блюда', 'вторые блюда', 'закуски', 'салаты', 'гарниры', 'десерты', 'выпечка', 'напитки']
category_links = ['/recipes/pervye-bliuda', '/recipes/vtorye-bliuda', '/recipes/zakuski', '/recipes/salaty', '/recipes/garniry', '/recipes/deserty', '/recipes/vypechka', '/recipes/napitki']
category_numbers = ['384', '2631', '775', '804', '90', '820', '700', '277']  # Количество страниц
HEADERS = {"User-Agent": "Mozilla/5.0"}



def make_driver(headless: bool = True) -> webdriver.Chrome:
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    return webdriver.Chrome(service=webdriver.chrome.service.Service(
                                ChromeDriverManager().install()),
                            options=options)


def infinite_scroll(url: str, target_count: int = 300, pause: float = 0.1, scroll_ratio=0.7) -> list[dict]:
    """Прокручиваем страницу, пока не соберём target_count карточек."""
    seen = set()
    records = []
    driver = make_driver()

    for page in range(1, target_count + 1):
        page_url = url if page == 1 else f"{url}?page={page}"
        driver.get(page_url)

        # ищем все listitem-карточки в секции "Лента публикаций"
        cards = driver.find_elements(
            By.CSS_SELECTOR,
            'section[aria-label="Лента публикаций"] div[role="listitem"] a.card_card__YG0I9'
        )
        print(f"Url {page_url}, Found {len(cards)} cards, total: {len(records)}")

        if not cards:
            print(f"Url {page_url}, No cards found, stopping.")
            break

        for a in cards:
            href = a.get_attribute("href")
            if href and href not in seen:
                img = a.find_element(By.CSS_SELECTOR, "img")
                title = img.get_attribute("alt") or img.get_attribute("title")
                print(f"Title: {title}, URL: {href}")
                records.append({"url": href, "title": title})
                seen.add(href)

        # прокручиваем дальше
        total_height = driver.execute_script("return document.body.scrollHeight")
        driver.execute_script("window.scrollTo(0, arguments[0]);", total_height * scroll_ratio)
        time.sleep(pause)

    driver.quit()
    return records


async def parse_recipe(url: str, title: str, sem: asyncio.Semaphore) -> dict:
    PROXY = await get_working_proxy(await load_proxies("proxies.txt"))
    proxy_url = PROXY.removeprefix("socks5://").removeprefix("http://").removeprefix("https://")
    auth_part, host_part = proxy_url.split("@", 1)
    login, pwd = auth_part.split(":", 1)
    host, port_str = host_part.split(":", 1)
    port = int(port_str)
    connector = ProxyConnector(
        proxy_type=ProxyType.SOCKS5, host=host, port=port,
        username=login, password=pwd, ssl=False
    )
    user_agent = random.choice(USER_AGENTS)
    headers = await get_headers(user_agent)

    recipe_data = {"title": title, "url": url}
    async with aiohttp.ClientSession(connector=connector) as session:
        try:
            async with sem, session.get(url, headers=headers, timeout=timeout) as r:
                html = await r.text()
        except (asyncio.TimeoutError, aiohttp.ClientError):
            recipe_data.update({
                "recipe": "Ошибка",
                "time": 0,
                "count": 0,
                "ingredients": [],
                "nutrients": {},
                "allergy": "Ошибка"
            })
            return recipe_data

    soup = BeautifulSoup(html, "lxml")

    # рецепт
    section = soup.find('section', id='step-by-step-recipe')
    if section:
        spans = section.find_all('span', class_='markup_text__F9WKe')

        if spans and len(spans) > 1:
            # Пропускаем первый элемент и собираем текст из оставшихся
            combined_text = '\n'.join([span.text.strip() for span in spans[1:]])
            recipe_data['recipe'] = combined_text.strip()  # Убираем лишние пробелы
        else:
            recipe_data['recipe'] = "Описание не найдено"
    else:
        recipe_data['recipe'] = "Секция с рецептом не найдена"

    # время
    ready_time = soup.find('meta', itemprop='totalTime')
    ready_minutes = ready_time['content'] if ready_time else 'PT0M'
    ready_minutes_value = int(ready_minutes.replace('PT', '').replace('M', '')) if ready_minutes else 0
    recipe_data['time'] = ready_minutes_value

    # количество порций
    servings_input = soup.find('input', class_='input yield default yield')
    if servings_input:
        servings_value = servings_input.get('value')
        if servings_value.isdigit():
            servings_value = int(servings_value)
            recipe_data['count'] = servings_value
        else:
            recipe_data['count'] = 1

    # ингридиенты
    ing_rows = []
    for tr in soup.find_all("tr", {"itemprop": "recipeIngredient"}):
        name_tag = tr.find("span", class_="name")
        value_tag = tr.find("span", class_="value")  # число в граммах

        # qty + ед. измерения в исходном правом столбце:
        #   '4 ... шт. = 240 г'
        qty_block = tr.find("span", class_="ingredientsTable_text__3ILFA")
        qty_text = qty_block.get_text(" ", strip=True) if qty_block else ""
        qty_match = re.search(r"^([\d,\.]+)", qty_text)  # первые цифры

        ing_rows.append({
            "name": name_tag.get_text(strip=True) if name_tag else None,
            "qty": qty_match.group(1).replace(",", ".") if qty_match else None,
            "grams": value_tag.get_text(strip=True) if value_tag else None,
        })
    recipe_data['ingredients'] = ing_rows

    # БЖУ
    nutrient_info = {}
    nutrients = soup.find_all('span', class_='nutrient_title__JDSmX')
    values = soup.find_all('span', class_='nutrient_value__dd48k')
    if len(nutrients) == len(values):
        for nutrient, value in zip(nutrients, values):
            nutrient_info[nutrient.text.strip()] = value.text.strip()
    recipe_data['nutrients'] = nutrient_info

    # аллергены
    properties = soup.find_all('div', class_='properties_value__kAeD9')
    if properties:
        last_property = properties[-1].text.strip()  # Получаем последний элемент
        recipe_data['allergy'] = last_property
    else:
        recipe_data['allergy'] = "Аллергии не найдены"

    return recipe_data


async def crawl_async(max_conn: int = 20):
    df = pd.DataFrame()
    sem = asyncio.Semaphore(max_conn)

    for cnt, url, cat in zip(category_numbers, category_links, categories):
        cur_url = START_URL + url
        cards = infinite_scroll(cur_url, target_count=int(cnt))  # получаем карточки рецептов

        tasks = [parse_recipe(card["url"], card["title"], sem) for card in cards]

        recipes = []
        for recipe in await tqdm_asyncio.gather(*tasks):
            recipe['category'] = cat
            recipes.append(recipe)

        df_cur = pd.DataFrame(recipes)
        df_cur.to_csv(f"recipes_foodru_{cat}.csv", encoding="utf-8")
        df = pd.concat([df, df_cur], ignore_index=True)

    return df


if __name__ == "__main__":
    df = asyncio.run(crawl_async(max_conn=50))
    print(df.head(10))
    df.to_csv("recipes_foodru_вторые блюда.csv", encoding="utf-8")