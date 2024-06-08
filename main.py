"""技術書のスクレイピングをします
"""

from dataclasses import dataclass, fields
from datetime import datetime, timezone, timedelta
import json
from urllib.parse import urljoin
from csv import writer
from re import search as regex_search
from argparse import ArgumentParser
from requests import get, post
from requests.exceptions import HTTPError, RequestException
from bs4 import BeautifulSoup
from babel.numbers import format_currency


@dataclass
class Book:
    """技術書のモデル"""

    title: str
    isbn: str
    price: str | None
    url: str
    published_at: datetime
    publisher: str


# オライリー書籍一覧ページ
OREILLY_BASE_URL = "https://www.oreilly.co.jp/catalog/"

# 翔泳社書籍一覧ページ
SHOEISHA_BASE_URL = "https://www.shoeisha.co.jp/"

# 技術評論社書籍一覧ページ
GIHYO_BASE_URL = "https://gihyo.jp/"

# 技術評論社のカテゴリのクエリパラメーター
gihyo_category_params: set[str] = {
    "0602",  # Java
    "0611",  # JavaScript
    "0603",  # Python・PHP・Ruby・Perlなど
    "0601",  # C・C++
    "0604",  # C#・VB・.NETなど
    "0605",  # iOS・Androidなど
    "0612",  # 機械学習・AI・データ分析
    "0607",  # Webアプリケーション開発
    "0608",  # SE仕事術・SE読み物
    "0609",  # 開発技法・ソフトウェアテスト・UML
    "0701",  # サーバ・インフラ・ネットワーク
    "0704",  # UNIX・Linux・FreeBSD
    "0705",  # データベース・SQLなど
}


def main():
    """エントリーポイント"""
    try:
        parser = ArgumentParser(
            description="出版社のサイトから技術書の情報を取得します"
        )
        parser.add_argument("-p", "--post", help="POSTする先のURL")
        args = parser.parse_args()
        result: list[Book] = []
        # オライリー
        response = get(OREILLY_BASE_URL, timeout=30)
        result.extend(analyze_oreilly_books(response.text))
        print(f"DONE: {OREILLY_BASE_URL}")

        # 翔泳社
        for page in range(0, 501):
            url = urljoin(SHOEISHA_BASE_URL, f"book/list?p={page}")
            response = get(url, timeout=30)
            if no_shoeisha_items_found(response.text):
                # ページングがこれ以上見つからなかった場合はbreak
                break
            result.extend(analyze_shoeisha_books(response.text))
            print(f"DONE: {url}")

        # 技術評論社
        for category in gihyo_category_params:
            for page in range(0, 101):
                url = urljoin(GIHYO_BASE_URL, f"book/genre?s={category}&page={page}")
                response = get(url, timeout=30)
                res = analyze_gihyo_books(response.text)
                if len(res) == 0:
                    break
                result.extend(res)
                print(f"DONE: {url}")

        if args.post is None:
            # CSV出力
            write_csv(result)
        else:
            post_books(args.post, result)
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
        dateStr = tr.find_all("td")[-1].text.strip()
        url = tr.find("a")["href"]
        # オライリーのページそのままだと文字化けするのでUTF8に直す
        title = title.encode("iso-8859-1").decode("utf-8", errors="ignore")

        books.append(
            Book(
                title=title,
                isbn=isbn,
                price=format_price(price, r"(\d{1,3}(,\d{3})*)"),
                # 相対パスのURLなので変換
                url=urljoin(OREILLY_BASE_URL, url),
                published_at=datetime.strptime(dateStr, "%Y/%m/%d").replace(
                    tzinfo=timezone(timedelta(hours=9))
                ),
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
            dateStr = (
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
                    published_at=datetime.strptime(dateStr, "%Y年%m月%d日").replace(
                        tzinfo=timezone(timedelta(hours=9))
                    ),
                    isbn=isbn,
                    price=format_price(price, r"(\d{1,3}(,\d{3})*)円"),
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
        soup.find(
            lambda tag: tag.name == "p"
            and "該当の書籍は見つかりませんでした。" in tag.get_text()
        )
        is not None
    )


def analyze_gihyo_books(html_text: str) -> list[Book]:
    """技術評論社の発行書籍一覧ページを解析します

    Args:
        html_text (str): HTMLテキスト

    Returns:
        list[Book]: 解析した本の一覧
    """
    books: list[Book] = []
    soup = BeautifulSoup(html_text, "html.parser")
    for row in soup.select("#mainbook > ul.magazineList01.bookList01 > li.clearfix"):
        title = row.find("h3").find("a").get_text(strip=True)
        price = row.find("p", class_="price").get_text(strip=True)
        dateStr = row.find("p", class_="sellingdate").get_text(strip=True)

        # リンクを抽出
        book_link_tag = row.find("a", href=True)
        book_link = book_link_tag["href"]

        # ISBN番号をリンクから抽出（URLの最後の部分）
        isbn = book_link.split("/")[-1]

        books.append(
            Book(
                title=title,
                price=format_price(price, r"(\d{1,3}(,\d{3})*)円"),
                published_at=datetime.strptime(dateStr, "%Y年%m月%d日発売").replace(
                    tzinfo=timezone(timedelta(hours=9))
                ),
                isbn=isbn,
                url=urljoin(GIHYO_BASE_URL, book_link),
                publisher="技術評論社",
            )
        )
    return books


def write_csv(books: list[Book]):
    """CSV出力します

    Args:
        books (list[Book]): 技術書一覧
    """
    csv_header = [f.name for f in fields(Book)]
    with open("tech-books.csv", "w", encoding="utf-8") as file:
        csv_writer = writer(file, lineterminator="\n")
        csv_writer.writerow(csv_header)
        for book in books:
            record: list[str] = [
                book.title,
                book.isbn,
                book.price,
                book.url,
                book.published_at.strftime("%Y-%m-%d"),
                book.publisher,
            ]
            csv_writer.writerow(record)


def format_price(currency: str, pattern: str) -> str | None:
    """価格をフォーマットします

    Args:
        currency (str): 価格の元の文字列
        pattern (str): currencyのパターン

    Returns:
        str | None: 価格情報を抽出出来たらその文字列、それ以外はNone
    """
    matched = regex_search(pattern, currency)
    if matched is not None:
        formatted_currency = matched.group(1).replace(",", "")
        return format_currency(int(formatted_currency), "JPY", locale="ja_JP")
    else:
        print(f"価格のフォーマットに失敗: {currency}")
    return None


def post_books(url: str, books: list[Book]):
    """技術書データをPOSTします

    Args:
        url (str): POST先のURL
        books (list[Book]): POSTする対象の技術書データ
    """
    for book in books:
        response = post(
            url,
            data=json.dumps(
                {
                    "title": book.title,
                    "isbn": book.isbn,
                    "price": book.price,
                    "url": book.url,
                    "publisher": book.publisher,
                    "publishedAt": book.published_at.isoformat(),
                }
            ),
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        if response.status_code == 409:
            print("already created")
        elif response.status_code != 201:
            print(f"post failed: {response.status_code}")
            print(response.content)
            break


if __name__ == "__main__":
    main()
