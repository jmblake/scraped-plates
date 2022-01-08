"""
Simple script to scrape the Michelin guide website for information on
restaurants.
"""
from dataclasses import dataclass

import requests
from lxml import html


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
        restaurant = Restaurant(
            name=(elem
                  .find_class("card__menu-content")[0]
                  .find("h3")
                  .find("a")
                  .text
                  .strip()),
            award=award_mapping.get(elem
                                    .find_class("card__menu-content")[0]
                                    .find("div")
                                    .find("i")
                                    .text
                                    .strip(), ""),
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


filters = [
    "3-stars-michelin",
    "2-stars-michelin",
    "1-star-michelin",
    "bib-gourmand",
]

location = [
    "gb",
    "greater-london",
    "london",
]

url_base = "https://guide.michelin.com"
location_string = "/".join(location)
filter_query_suffix = "/".join(filters)

url = f"{url_base}/en/{location_string}/restaurants/{filter_query_suffix}"


def get_number_pages(url_with_filter: str) -> int:
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
    )  # TODO: Error handling for None case
    return num_pages


award_mapping = {"m": "ONE_STAR",
                 "n": "TWO_STARS",
                 "o": "THREE_STARS",
                 "=": "BIB_GOURMAND"}


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
        # results_html.find_class("card__menu-footer d-flex")
        restaurant_elements.extend(restaurant_elements_on_page)
    return restaurant_elements


def main():
    max_pages = get_number_pages(url)
    restaurant_xml_elements = collect_restaurant_elements(max_pages)
    restaurants = [Restaurant.from_restaurant_page_items(item)for item in
                   restaurant_xml_elements]



if __name__ == '__main__':
    main()
