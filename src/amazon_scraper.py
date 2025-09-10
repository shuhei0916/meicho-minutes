import requests
from bs4 import BeautifulSoup
import os
import json
import time
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict


@dataclass
class Review:
    """カスタマーレビューを表すデータクラス"""
    title: str
    text: str


@dataclass
class BookInfo:
    """書籍情報を表すデータクラス"""
    title: Optional[str] = None
    author: Optional[str] = None
    price: Optional[str] = None
    image_url: Optional[str] = None
    description: Optional[str] = None
    rating: Optional[str] = None
    reviews: List[Review] = None
    
    def __post_init__(self):
        if self.reviews is None:
            self.reviews = []
    
    def to_dict(self) -> Dict:
        """辞書形式に変換"""
        return asdict(self)
    
    def to_json(self, indent=2) -> str:
        """JSON文字列に変換"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


class AmazonScrapingError(Exception):
    """Amazonスクレイピング関連のエラー"""
    pass


class NetworkError(AmazonScrapingError):
    """ネットワーク関連のエラー"""
    pass


class PageNotFoundError(AmazonScrapingError):
    """ページが見つからない場合のエラー"""
    pass


class AmazonScraper:
    def __init__(self, request_delay=1.0, max_retries=3):
        self.request_delay = request_delay
        self.max_retries = max_retries
        self.session = requests.Session()
        
        # レビュー取得に成功するUser-Agentのリスト（優先度順）
        self.user_agents = [
            # macOS Chrome（調査で8件レビュー取得成功）
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            # Windows Firefox（調査で8件レビュー取得成功）
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
            # Windows Chrome（最新版）
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            # macOS Safari
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15'
        ]
    
    def scrape_book_info_from_html_file(self, html_file_path) -> BookInfo:
        """ローカルHTMLファイルから書籍情報を取得"""
        try:
            if not os.path.exists(html_file_path):
                raise PageNotFoundError(f"HTMLファイルが見つかりません: {html_file_path}")
            
            with open(html_file_path, 'r', encoding='utf-8') as file:
                html_content = file.read()
            
            return self._parse_book_info_from_html(html_content)
            
        except PageNotFoundError:
            # PageNotFoundErrorはそのまま再発生
            raise
        except IOError as e:
            raise NetworkError(f"ファイル読み込みエラー: {e}")
        except Exception as e:
            raise AmazonScrapingError(f"HTMLパース中にエラーが発生しました: {e}")
    
    def scrape_book_info_from_url(self, url: str) -> BookInfo:
        """URLから書籍情報を取得（User-Agentローテーション機能付き）"""
        
        # User-Agentを順番に試行
        for ua_index, user_agent in enumerate(self.user_agents):
            for attempt in range(self.max_retries):
                try:
                    # リクエスト間隔制御
                    if attempt > 0 or ua_index > 0:
                        time.sleep(self.request_delay * (attempt + 1))
                    
                    headers = {'User-Agent': user_agent}
                    response = self.session.get(url, headers=headers, timeout=30)
                    
                    if response.status_code == 404:
                        raise PageNotFoundError(f"ページが見つかりません: {url}")
                    elif response.status_code == 403:
                        # 403の場合は次のUser-Agentを試す
                        break
                    elif response.status_code != 200:
                        raise NetworkError(f"HTTPエラー {response.status_code}: {url}")
                    
                    # レビュー取得を検証
                    book_info = self._parse_book_info_from_html(response.text)
                    
                    # レビューが取得できていない場合は次のUser-Agentを試す
                    if not book_info.reviews and ua_index < len(self.user_agents) - 1:
                        print(f"⚠️ User-Agent {ua_index + 1}でレビュー未取得、次を試行")
                        break
                    
                    # 成功した場合
                    if book_info.reviews:
                        print(f"✅ User-Agent {ua_index + 1}でレビュー{len(book_info.reviews)}件取得")
                    
                    return book_info
                    
                except requests.exceptions.Timeout:
                    if attempt == self.max_retries - 1:
                        break  # 次のUser-Agentを試す
                except requests.exceptions.ConnectionError:
                    if attempt == self.max_retries - 1:
                        break  # 次のUser-Agentを試す
                except requests.exceptions.RequestException:
                    if attempt == self.max_retries - 1:
                        break  # 次のUser-Agentを試す
        
        raise NetworkError(f"全てのUser-Agent（{len(self.user_agents)}個）で失敗しました: {url}")
    
    def _parse_book_info_from_html(self, html_content: str) -> BookInfo:
        """HTMLコンテンツから書籍情報をパースする"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # タイトルを取得
        title_element = soup.find('span', id='productTitle')
        title = title_element.text.strip() if title_element else None
        
        # 著者を取得
        byline_info = soup.find('div', id='bylineInfo')
        author_element = byline_info.find('a', class_='a-link-normal') if byline_info else None
        author = author_element.text.strip() if author_element else None
        
        # 価格を取得
        price_element = soup.find('span', {'aria-label': lambda label: label and '￥' in label})
        price = price_element.text.strip() if price_element else None
        
        # 画像URLを取得
        image_element = soup.find('img', id='landingImage')
        image_url = image_element.get('src') if image_element else None
        
        # 説明文を取得
        description_div = soup.find('div', id='bookDescription_feature_div')
        description_span = description_div.find('span') if description_div else None
        description = description_span.text.strip() if description_span else None
        
        # レビュー評価を取得
        rating_element = soup.find('span', {'title': lambda title: title and '5つ星のうち' in title})
        rating = rating_element.get('title') if rating_element else None
        
        # カスタマーレビューを取得
        reviews = []
        review_elements = soup.find_all('li', {'data-hook': 'review'})
        
        for review_element in review_elements:
            # レビュータイトル
            title_element = review_element.find('a', {'data-hook': 'review-title'})
            review_title = None
            if title_element:
                # レビュータイトル内のspan（星評価以外）を探す
                title_spans = title_element.find_all('span')
                for span in title_spans:
                    if span.text.strip() and '5つ星のうち' not in span.text:
                        review_title = span.text.strip()
                        break
            
            # レビュー本文
            body_element = review_element.find('span', {'data-hook': 'review-body'})
            review_text = None
            if body_element:
                text_span = body_element.find('span')
                if text_span:
                    # <br>タグを改行に変換
                    review_text = text_span.get_text(separator='\n').strip()
            
            if review_title and review_text:
                reviews.append(Review(title=review_title, text=review_text))
        
        return BookInfo(
            title=title,
            author=author,
            price=price,
            image_url=image_url,
            description=description,
            rating=rating,
            reviews=reviews
        )


if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Amazon書籍情報スクレイピングツール',
        epilog="""
使用例:
  # ローカルHTMLファイルから取得
  python src/amazon_scraper.py --file data/amazon_page_sample.html
  
  # Amazon URLから取得（URLは必ずクォートで囲む）
  python src/amazon_scraper.py --url "https://www.amazon.co.jp/dp/B01234567X/?ref=abc&other=123"
  
  # 結果をファイルに保存
  python src/amazon_scraper.py --file data/sample.html --output result.json
  
注意事項:
  - URLに & が含まれる場合は、必ずダブルクォートまたはシングルクォートで囲んでください
  - そうしないとシェルがURLを複数のコマンドとして解釈します
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--url', type=str, help='Amazon商品ページのURL（クォートで囲むこと）')
    parser.add_argument('--file', type=str, help='ローカルHTMLファイルパス')
    parser.add_argument('--output', type=str, help='出力JSONファイルパス（指定しない場合は標準出力）')
    
    args = parser.parse_args()
    
    if not args.url and not args.file:
        print("エラー: --url または --file を指定してください", file=sys.stderr)
        sys.exit(1)
    
    scraper = AmazonScraper()
    
    try:
        if args.url:
            print(f"URLから情報を取得中: {args.url}", file=sys.stderr)
            book_info = scraper.scrape_book_info_from_url(args.url)
        else:
            print(f"ローカルファイルから情報を取得中: {args.file}", file=sys.stderr)
            book_info = scraper.scrape_book_info_from_html_file(args.file)
        
        # JSON出力
        json_output = book_info.to_json()
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(json_output)
            print(f"結果をファイルに保存しました: {args.output}", file=sys.stderr)
        else:
            print(json_output)
            
        # 取得できた項目の概要をstderrに出力
        print(f"\n✅ 取得完了:", file=sys.stderr)
        print(f"   タイトル: {book_info.title or 'N/A'}", file=sys.stderr)
        print(f"   著者: {book_info.author or 'N/A'}", file=sys.stderr)
        print(f"   価格: {book_info.price or 'N/A'}", file=sys.stderr)
        print(f"   評価: {book_info.rating or 'N/A'}", file=sys.stderr)
        print(f"   レビュー数: {len(book_info.reviews)}", file=sys.stderr)
        
    except AmazonScrapingError as e:
        print(f"スクレイピングエラー: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"予期しないエラー: {e}", file=sys.stderr)
        sys.exit(1)