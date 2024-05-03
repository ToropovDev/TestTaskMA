import time
import json
import requests
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions

# создание базового url
base_url = "https://online.metro-cc.ru"
category_url = base_url + "/category/chaj-kofe-kakao/kofe"
category_url = category_url + "?in_stock=1"

# настройка драйвера selenium
chrome_options = Options()
chrome_options.add_argument("--headless")
driver = webdriver.Chrome(options=chrome_options)


def get_product_links(count) -> list:
    """
    Функция проходится по всем страницам категории,
    собирает с каждой список продуктов и возвращает список ссылок
    """
    links = []
    for page in range(1, count + 1):
        page_url = category_url + "&page=" + str(page)
        page_html = BeautifulSoup(requests.get(page_url).text, "html.parser")
        products_on_page = page_html.find_all("div", class_="product-card")

        for product in products_on_page:
            product_link = product.find("a", class_="product-card-photo__link").attrs['href']
            links.append(product_link)
    return links


def get_dynamic_info(url) -> BeautifulSoup | str:
    """
    Функция открывает страницу товара, ждет пока загрузится динамическая информация о цене,
    после чего раскрывает полный список характеристик товара и возвращает информацию
    """
    driver.get(url)
    try:
        WebDriverWait(driver, 10).until(
            expected_conditions.visibility_of_element_located((By.CLASS_NAME, "product-unit-prices__trigger"))
        )

        fixed_bottom = driver.find_element(By.CLASS_NAME, "fixed-bottom-mobile-block")
        driver.execute_script("arguments[0].style.visibility = 'hidden'", fixed_bottom)

        full_attrs_btn = driver.find_element(by=By.CLASS_NAME, value="product-page-content__button-to-full-attributes")
        full_attrs_btn.click()

        all_attrs_btn = driver.find_element(by=By.CLASS_NAME, value="product-page-content__button-show-all-attributes ")
        all_attrs_btn.click()

        time.sleep(5)
        result = BeautifulSoup(driver.page_source, "html.parser")
        return result
    except:
        return ""


def get_product_brand(html) -> str:
    """
    Функция получает информацию о производителе товара из его характеристик
    """
    product_attrs = (html
                     .find('ul', class_="product-attributes__list")
                     .find_all("li", class_="product-attributes__list-item"))

    brand = "-"
    for attr in product_attrs:
        attr_name = (attr
                     .find("span", class_="product-attributes__list-item-name")
                     .find("span", class_="product-attributes__list-item-name-text").text.strip())
        if attr_name == "Бренд":
            brand = attr.find("a", class_='product-attributes__list-item-link').text.strip()
    return brand


def get_product_prices(html) -> (int, int):
    """
    Функция получает информацию о цене товара, проверяет, есть ли старая цена,
    возвращает старую и новую цены
    """
    actual_price = int((html.find("div", class_="product-unit-prices__actual-wrapper")
                        .find("span", class_="product-price__sum-rubles")
                        .text
                        .strip()
                        .replace("\xa0", "")))
    old_price = (html.find("div", class_="product-unit-prices__old-wrapper")
                 .find("span", class_="product-price__sum-rubles"))

    if old_price is None:
        old_price = actual_price
    else:
        old_price = int(old_price
                     .text
                     .strip()
                     .replace("\xa0", ""))
    return old_price, actual_price


def get_product_dict(links) -> dict:
    """
    Функция проходится по ссылкам, собирает все необходимые данные и собирает словарь
    """
    product_dict = {}
    for link in links:
        product_url = base_url + link
        product_html = get_dynamic_info(product_url)
        if product_html == "":
            continue

        product_id = product_html.find('p', class_='product-page-content__article').text.split()[1]
        product_name = product_html.find("h1", class_="product-page-content__product-name").find("span").text.strip()
        product_brand = get_product_brand(product_html)
        regular_price, discount_price = get_product_prices(product_html)

        product_dict[product_id] = {
            "product_name": product_name,
            "product_url": product_url,
            "product_regular_price": regular_price,
            "product_discount_price": discount_price,
            "product_brand": product_brand
        }
    return product_dict


def scraper(soup):
    pages = soup.find('ul', class_='v-pagination')
    pages = [int(page.text) for page in pages if page.text not in ["", "..."]]
    pages_count = max(pages)

    product_count = soup.find('span', class_='heading-products-count')
    product_count = int(product_count.text.split()[0])

    products_links = get_product_links(pages_count)
    products_links = products_links[:product_count]

    product_dict = get_product_dict(products_links)
    return product_dict


def main():
    driver.get(category_url)
    select_city_btn = driver.find_element(by=By.CLASS_NAME, value='header-address__receive-address')
    select_city_btn.click()

    div = driver.find_element(by=By.XPATH, value="//div[@class='delivery__tab']")
    driver.execute_script("arguments[0].click();", div)

    change_city = driver.find_element(by=By.CLASS_NAME, value='pickup-content__city')
    change_city_btn = change_city.find_element(by=By.CLASS_NAME, value='active-blue-text')
    driver.execute_script("arguments[0].click();", change_city_btn)

    modal_city = driver.find_element(by=By.CLASS_NAME, value='modal-city')
    city_div = modal_city.find_elements(by=By.CLASS_NAME, value="city-item")[22]
    driver.execute_script("arguments[0].click();", city_div)

    apply_btn = driver.find_element(by=By.CLASS_NAME, value="delivery__btn-apply")
    apply_btn.click()

    time.sleep(5)
    beautiful_soup = BeautifulSoup(driver.page_source, "html.parser")
    result = scraper(beautiful_soup)

    with open(f"result_Saint-Petersburg.json", "w") as file:
        json.dump(result, file, ensure_ascii=False, indent=4)


if __name__ == '__main__':
    main()
