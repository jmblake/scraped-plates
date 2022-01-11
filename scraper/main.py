"""
Simple script to scrape the Michelin guide website for information on
restaurants.
"""
from dataclasses import dataclass

import pymongo
import requests
from lxml import html

import config


award_mapping = {"m": "ONE_STAR",
                 "n": "TWO_STARS",
                 "o": "THREE_STARS",
                 "=": "BIB_GOURMAND"}


@dataclass
class Restaurant:
    name: str
    award: str
    lat: str
    lng: str
    data_id: str
    url: str
    edition: str

    @staticmethod
    def from_restaurant_page_items(elem: html.HtmlElement) -> 'Restaurant':
        # TODO: Tidy up this error handling
        try:
            award = award_mapping.get(elem
                                      .find_class("card__menu-content")[0]
                                      .find("div")
                                      .find("i")
                                      .text
                                      .strip(), "")
        except AttributeError:
            award = ""

        restaurant = Restaurant(
            name=(elem
                  .find_class("card__menu-content")[0]
                  .find("h3")
                  .find("a")
                  .text
                  .strip()),
            award=award,
            lat=elem.get("data-lat"),
            lng=elem.get("data-lng"),
            data_id=elem.get("data-id"),
            url=url_base + (elem
                            .find_class("card__menu-content")[0]
                            .find("h3")
                            .find("a")
                            .get("href")),
            edition=(elem
                     .find_class("card__menu-content")[0]
                     .find("div")
                     .find("span")
                     .text
                     .strip()),
        )
        return restaurant

# TODO: Make purpose of filters/location more explicit
# filters = [
#     "3-stars-michelin",
#     "2-stars-michelin",
#     "1-star-michelin",
#     "bib-gourmand",
# ]

# location = [
#     "gb",
#     "greater-london",
#     "london",
# ]

location = []
filters = []

url_base = "https://guide.michelin.com"
location_string = "/".join(location)
filter_query_suffix = "/".join(filters)

url = f"{url_base}/en/{location_string}/restaurants/{filter_query_suffix}"


def get_number_of_pages(url_with_filter: str) -> int:
    page: requests.Response = requests.get(url_with_filter)
    tree: html.HtmlElement = html.fromstring(page.content)
    # The -2'th element gives us the last element in the list of pagination
    # buttons that isn't the next/right arrow button - this contains the
    # total number of pages of results
    num_pages = int(
        tree
        .xpath("/html/body/main/section[1]/div[1]/div/div[4]/div/ul")[0][-2]
        .find("a")
        .text
    )
    return num_pages


def collect_restaurant_elements(max_pages: int) -> list[html.HtmlElement]:
    restaurant_elements: list[html.HtmlElement] = []
    for i in range(1, max_pages + 1):
        results_page_url = f"{url}/page/{i}"
        results_page: requests.Response = requests.get(results_page_url)
        results_html: html.HtmlElement = html.fromstring(results_page.content)
        restaurant_elements_on_page: list[html.HtmlElement] = (
            results_html
            .find_class("js-restaurant__list_item")
        )
        restaurant_elements.extend(restaurant_elements_on_page)
        # TODO: Set up proper logging
        if i % 10 == 0:
            print(f"Collected {i}/{max_pages} pages")
    return restaurant_elements


def write_to_mongodb(objs: list):
    # TODO: Figure out flags to remove from the connection string
    connection_string = (f"mongodb+srv://{config.user}:{config.password}"
                         f"@{config.cluster}/{config.db_name}?"
                         f"retryWrites=true&w=majority&ssl=true"
                         f"&ssl_cert_reqs=CERT_NONE")

    client = pymongo.MongoClient(connection_string,
                                 serverSelectionTimeoutMS=2000)
    db = client[config.db_name]
    collection = db[config.collection_name]
    collection.insert_many([obj.__dict__ for obj in objs])


def main():
    max_pages = get_number_of_pages(url)
    restaurant_xml_elements = collect_restaurant_elements(max_pages)
    restaurants = [Restaurant.from_restaurant_page_items(item) for item in
                   restaurant_xml_elements]
    write_to_mongodb(restaurants)


if __name__ == '__main__':
    main()
