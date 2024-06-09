# scraping-tech-books

技術書をスクレイピングします。

次の出版社のページをスクレイピングします。

- オライリージャパン
- 翔泳社
- 技術評論社

## Getting Started

Dev Containers をインストールし、次の手順を実施してください。

1. VSCode で本プロジェクトを開き、コマンドパレットから[Dev Containers: Reopen in Container...]を実行してください。
1. スクリプトを実行してください。
   ```bash
   python main.py
   ```

### 取得したデータを POST する

POST する先の URL を指定し、次のように実行してください。

```bash
python main.py --post http://localhost:8091/api/v1/books
```
