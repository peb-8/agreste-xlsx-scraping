import requests
from bs4 import BeautifulSoup
from urllib3.exceptions import InsecureRequestWarning

from typing import Dict, Tuple, List
import time
import os
import pathlib

from utils import download_file, scrap_and_process


BASE_DOMAIN = "agreste.agriculture.gouv.fr"
BASE_URL = "https://" + BASE_DOMAIN
INDEX_URL = BASE_URL + "/agreste-web"
SEARCH_URL = INDEX_URL + "/disaron/!searchurl/searchUiid/search/"

COOKIE_NAME = "JSESSIONID"

CONTEXT_SELECTOR = r"#mainform > input[type=hidden]:nth-child(8)"
PAGE_SEQ_SELECTOR = r"#mainform > input[type=hidden]:nth-child(7)"
VIEW_STATE_SELECTOR = r"#javax\.faces\.ViewState"
ARTICLE_TITLE_SELECTOR = r"#mainform h4 > a"
ARTICLE_DESC_SELECTOR = r"#mainform tbody > tr div"
ARTICLE_ID_SELECTOR = r"#mainform h4 > a"
DOCS_SELECTOR = r"#docDonneeGroup1 a"

ARTICLE_ID_PROCESSOR = lambda x: x['onclick'].replace(" ", "").split("':'")[1][:-18]
ARTICLE_DESC_PROCESSOR = lambda x: x.text.replace("\n", "").strip()
ARTICLE_TITLE_PROCESSOR = lambda x: x['title']

SSL_CERT_PATH = False  # /!\ Replace in prod
if not SSL_CERT_PATH:
    requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

TITLE_STARTS_WITH = "Grandes cultures."
CATEGORIES = ("Publications nationales",)
SUB_CATEGORIES = ("Conjoncture – Infos Rapides",)

SAVE_DIR = "data"


def scrap_session_state(res_content: str) -> Dict[str, str]:
    """ Get the current session state """
    soup = BeautifulSoup(res_content, "html.parser")
    scrap_map = {
        "orion.navigation.context": (False, CONTEXT_SELECTOR,    lambda x: x.get('value')),
        "orion.navigation.pageSeq": (False, PAGE_SEQ_SELECTOR,   lambda x: x.get('value')),
        "javax.faces.ViewState":    (False, VIEW_STATE_SELECTOR, lambda x: x.get('value')),
    }
    return {prop: scrap_and_process(soup, *params) for prop, params in scrap_map.items()}


def get_cookie_and_session_state() -> Tuple[str, Dict[str, str]]:
    """ Get the cookie and session state (useful for next POST requests) """
    res = requests.get(url=SEARCH_URL, verify=SSL_CERT_PATH)
    assert res.status_code == 200
    return res.cookies.get_dict().get(COOKIE_NAME), scrap_session_state(res.content)


def filter_result(title: str, desc: str, id: str) -> Dict[str, str] | None:
    """ Get the article or None if the article doesn't meet the filter conditions """
    # TODO: refactor here
    part1, part2, part3 = desc.split("|")
    sub_cat, nb = part1[:27].strip(), part1[30:].strip()
    cat = part2.strip()
    maj_date = part3[15:]
    if title.startswith(TITLE_STARTS_WITH) and cat in CATEGORIES and sub_cat in SUB_CATEGORIES:
        return {"title": title, "cat": cat, "sub_cat": sub_cat, "nb": nb, "maj_date": maj_date, "id": id}
    return None


def get_article_URL(cookie: str, session_state: Dict[str, str], id: str) -> str:
    """ Get article URL from article """
    res = requests.post(
        url=SEARCH_URL,
        verify=SSL_CERT_PATH,
        data={
            "mainform": "mainform",
            "mainform:textInput-out": "",
            "orion.navigation.pageSeq": session_state.get("orion.navigation.pageSeq"),
            "orion.navigation.context": session_state.get("orion.navigation.context"),
            "orion.navigation.immediateRender": "",
            "javax.faces.ViewState": session_state.get("javax.faces.ViewState"),
            id: id
        },
        headers={
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "fr",
            "Cache-Control": "max-age=0",
            "Connection": "keep-alive",
            "Content-Length": "344",
            "Content-Type": "application/x-www-form-urlencoded",
            "Cookie": "JSESSIONID=" + cookie,
            "Host": "agreste.agriculture.gouv.fr",
            "Origin": BASE_URL,
            "Referer": SEARCH_URL,
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
            "sec-ch-ua": '"Microsoft Edge";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"'
        },
        allow_redirects=False
    )

    return res.headers["Location"] if res.status_code == 302 else None


def get_search_results(cookie: str, session_state: Dict[str, str]) -> List[Dict[str, str]]:
    """ Get articles from search page """
    res = requests.post(
        url=SEARCH_URL,
        verify=SSL_CERT_PATH,
        data={
            "mainform": "mainform",
            "mainform:textInput-out": "",
            "mainform:j_idt223:6:j_idt226-act-wrp-cmd": "",
            "mainform:j_idt139:4:j_idt145:0:filterCheckbox": "on",
            "mainform:j_idt173:0:j_idt179:3:filterCheckbox": "on",
            "orion.navigation.pageSeq": session_state.get("orion.navigation.pageSeq"),
            "orion.navigation.context": session_state.get("orion.navigation.context"),
            "orion.navigation.immediateRender": "",
            "javax.faces.ViewState": session_state.get("javax.faces.ViewState")
        },
        headers={
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "fr",
            "Cache-Control": "max-age=0",
            "Connection": "keep-alive",
            "Content-Length": "300",
            "Content-Type": "application/x-www-form-urlencoded",
            "Cookie": "JSESSIONID=" + cookie,
            "Host": "agreste.agriculture.gouv.fr",
            "Origin": BASE_URL,
            "Referer": SEARCH_URL,
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
            "sec-ch-ua": '"Microsoft Edge";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"'
        },
        allow_redirects=False
    )
    assert res.status_code == 200
    scrap_map = {
        "title": (True, ARTICLE_TITLE_SELECTOR, ARTICLE_TITLE_PROCESSOR),
        "desc": (True, ARTICLE_DESC_SELECTOR, ARTICLE_DESC_PROCESSOR),
        "id": (True, ARTICLE_ID_SELECTOR, ARTICLE_ID_PROCESSOR)
    }
    soup = BeautifulSoup(res.content, "html.parser")
    data = {prop: scrap_and_process(soup, *params) for prop, params in scrap_map.items()}
    results = [{"title": title, "desc": desc, "id": id} for title, desc, id in zip(data["title"], data["desc"], data["id"])]
    filtered_results = []
    for result in results:
        filtered_result = filter_result(result["title"], result["desc"], result["id"])
        if filtered_result:
            filtered_results.append(filtered_result)
    return filtered_results, scrap_session_state(res.content)


def get_documents_URLs(article_URL: str) -> List[str]:
    """ Get doc URLs from article page """
    if article_URL:
        res = requests.get(url=article_URL, verify=SSL_CERT_PATH)
        assert res.status_code == 200
        soup = BeautifulSoup(res.content, "html.parser")
        return scrap_and_process(soup, True, "#docDonneeGroup1 a", lambda x: BASE_URL + x["href"])


def main() -> None:
    """ Entry point of the application """
    start = time.time()
    # create save directory
    root = pathlib.Path(__file__).parent.absolute()
    save_dir = os.path.join(root, SAVE_DIR)
    if not os.path.exists(save_dir):
        os.mkdir(save_dir)
    # find existing documents
    saved_documents = [f.name for f in pathlib.Path(save_dir).iterdir() if f.is_file()]
    # initialize session
    cookie, session_state = get_cookie_and_session_state()
    # find articles
    print("Scraping documents...")
    articles, session_state = get_search_results(cookie, session_state)
    print(f"{len(articles)} article(s) found :")
    for article in articles:
        # find article URL
        article_URL = get_article_URL(cookie, session_state, article["id"])  # TODO: correct bug here (sometimes, URL not found)
        if not article_URL:
            print("[Error] No URL found for article " + article["title"])
            continue
        # find documents URLs
        documents_URLs = get_documents_URLs(article_URL)
        print("\t-", article["title"])
        for document_URL in documents_URLs:
            document_name = document_URL[88:]  # TODO: use parthlib to shorten path
            print("\t\t-", document_URL[76:])
            # download and save document
            if document_name not in saved_documents:
                try:
                    # TODO: correct bug here (file sometimes can't be saved due to forbidden access)
                    download_file(url=document_URL, save_path=os.path.join(save_dir, document_name), verify=SSL_CERT_PATH)
                except PermissionError as e:
                    print(e)
    print(f"Scraping done in {time.time() - start} seconds")


if __name__ == "__main__":
    main()
