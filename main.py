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
    publisher: str


# オライリー書籍一覧ページ
OREILLY_BASE_URL = "https://www.oreilly.co.jp/catalog/"

# 翔泳社書籍一覧ページ
SHOEISHA_BASE_URL = "https://www.shoeisha.co.jp/"


def main():
    """エントリーポイント"""
    try:
        result: list[Book] = []
        # オライリー
        response = get(OREILLY_BASE_URL, timeout=30)
        result.append(analyze_oreilly_books(response.text))

        # 翔泳社
        for page in range(1, 501):
            url = urljoin(SHOEISHA_BASE_URL, f"book/list?p={page}")
            response = get(url, timeout=30)
            if no_shoeisha_items_found(response.text):
                # ページングがこれ以上見つからなかった場合はbreak
                break
            result.append(analyze_shoeisha_books(response.text))
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
                publisher="オライリー・ジャパン",
            )
        )
    return books


def analyze_shoeisha_books(html_text: str) -> list[Book]:
    """翔泳社の発行書籍一覧ページを解析します

    Args:
        html_text (str): HTMLテキスト

    Returns:
        list[Book]: 解析した本の一覧
    """
    books: list[Book] = []
    soup = BeautifulSoup(html_text, "html.parser")
    for row in soup.select("#cx_contents_block > div > section > div.row.list"):
        for book_div in row.find_all("div", class_="textWrapper"):
            title = book_div.find("h3").get_text(strip=True)
            release_date = (
                book_div.find("dt", string="発売：")
                .find_next_sibling("dd")
                .get_text(strip=True)
            )
            isbn = book_div.find("dd", class_="isbn").get_text(strip=True)
            price = (
                book_div.find("dt", string="定価：")
                .find_next_sibling("dd")
                .get_text(strip=True)
            )
            url = book_div.find("h3").find("a")["href"]

            books.append(
                Book(
                    title=title,
                    release_date=release_date,
                    isbn=isbn,
                    price=price,
                    url=urljoin(SHOEISHA_BASE_URL, url),
                    publisher="翔泳社",
                )
            )
    return books


def no_shoeisha_items_found(html_text: str) -> bool:
    """翔泳社の書籍が存在しているか

    Args:
        html_text (str): HTMLテキスト

    Returns:
        bool: 存在してないときはTrue、それ以外はFalse
    """
    soup = BeautifulSoup(html_text, "html.parser")
    return (
        soup.find(lambda tag: tag.name == "p" and "該当の書籍は見つかりませんでした。" in tag.get_text())
        is not None
    )


if __name__ == "__main__":
    main()
