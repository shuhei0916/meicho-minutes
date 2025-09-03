import pytest
from src.amazon_scraper import AmazonScraper
import os


def test_amazon_scraper_initialization():
    """Amazonスクレイピングクライアントが正しく初期化できることをテスト"""
    # 準備
    request_delay = 2.0
    max_retries = 3
    
    # 実行
    scraper = AmazonScraper(
        request_delay=request_delay,
        max_retries=max_retries
    )
    
    # 検証
    assert scraper.request_delay == request_delay
    assert scraper.max_retries == max_retries
    assert scraper.session is not None


def test_scrape_book_basic_info_from_html():
    """ローカルHTMLファイルから書籍基本情報をスクレイピングできることをテスト"""
    # 準備
    scraper = AmazonScraper()
    html_file_path = os.path.join(os.path.dirname(__file__), "..", "amazon_page_sample.html")
    
    # 実行
    book_info = scraper.scrape_book_info_from_html_file(html_file_path)
    
    # 検証
    assert book_info is not None
    assert book_info["title"] == "団塊の世代 〈新版〉 (文春文庫 さ 1-20)"
    assert book_info["author"] == "堺屋 太一"
    assert book_info["price"] == "￥534"
    assert book_info["image_url"] == "https://m.media-amazon.com/images/I/51wZYgJf7oL._SY385_.jpg"