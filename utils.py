from typing import Any, Callable

from bs4 import BeautifulSoup
import requests


def scrap_and_process(soup: BeautifulSoup, many: bool, css_selector: str, process: Callable = None) -> Any:
    """ Scrap nodes from soup and return processed data """
    el = soup.select_one(css_selector) if not many else soup.select(css_selector)
    return (process(el) if not many else [process(e) for e in el]) if process else el


def download_file(url: str, save_path: str, verify: bool = False) -> None:
    """ Download a file using streaming to keep memory usage low """
    with requests.get(url=url, stream=True, verify=verify) as r:
        r.raise_for_status()
        with open(save_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
