"""技術書のスクレイピングをします
"""
from dataclasses import dataclass
from urllib.parse import urljoin
from requests import get
from requests.exceptions import HTTPError, RequestException
from bs4 import BeautifulSoup


@dataclass
class Book:
    """技術書のモデル"""

    title: str
    isbn: str
    price: str
    url: str
    release_date: str


OREILLY_BASE_URL = "https://www.oreilly.co.jp/catalog/"


def main():
    """エントリーポイント"""
    try:
        response = get(OREILLY_BASE_URL, timeout=30)
        analyze_oreilly_books(response.text)
    except HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        exit(1)
    except RequestException as req_err:
        print(f"RequestException error occurred: {req_err}")
        exit(1)


def analyze_oreilly_books(html_text: str) -> list[Book]:
    """オライリー発行書籍一覧ページを解析します


    Args:
        html_text (str): HTMLテキスト

    Returns:
        list[Book]: 解析した本の一覧
    """
    books: list[Book] = []
    soup = BeautifulSoup(html_text, "html.parser")
    for tr in soup.select("#bookTable > tbody > tr"):
        isbn = tr.find("td").text.strip()
        title = tr.find("td", class_="title").get_text(strip=True)
        price = tr.find("td", class_="price").text.strip()
        release_date = tr.find_all("td")[-1].text.strip()
        url = tr.find("a")["href"]

        books.append(
            Book(
                title=title,
                isbn=isbn,
                price=price,
                # 相対パスのURLなので変換
                url=urljoin(OREILLY_BASE_URL, url),
                release_date=release_date,
            )
        )
    return books


if __name__ == "__main__":
    main()
