import pytest
from src.amazon_scraper import AmazonScraper, BookInfo, Review, AmazonScrapingError, NetworkError, PageNotFoundError
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
    html_file_path = os.path.join(os.path.dirname(__file__), "..", "data", "amazon_page_sample.html")
    
    # 実行
    book_info = scraper.scrape_book_info_from_html_file(html_file_path)
    
    # 検証
    assert isinstance(book_info, BookInfo)
    assert book_info.title == "団塊の世代 〈新版〉 (文春文庫 さ 1-20)"
    assert book_info.author == "堺屋 太一"
    assert book_info.price == "￥534"
    assert book_info.image_url == "https://m.media-amazon.com/images/I/51wZYgJf7oL._SY385_.jpg"
    assert book_info.description == "「団塊の世代」が日本の経済社会になにをもたらすのかを予言した名著。今後の大量定年、老齢化問題への対策を新たに加えた新装版"
    assert book_info.rating == "5つ星のうち3.8"
    assert book_info.reviews is not None
    assert len(book_info.reviews) >= 2
    
    # 最初のレビューをチェック
    first_review = book_info.reviews[0]
    assert isinstance(first_review, Review)
    assert first_review.title == "読んでて切ない団塊世代サラリーマン譚"
    assert "ちょっと前に著者である堺屋氏の訃報を知ったのを機に" in first_review.text
    assert "団塊世代サラリーマンの短編が4本収録されてます" in first_review.text
    
    # 2番目のレビューをチェック  
    second_review = book_info.reviews[1]
    assert isinstance(second_review, Review)
    assert second_review.title == "なんだ、分かってたんじゃねえか"
    assert "本書の優れたところは、「団塊」という人口のアンバランス" in second_review.text


def test_book_info_to_json():
    """BookInfoオブジェクトがJSONに正しく変換できることをテスト"""
    # 準備
    review = Review(title="テストレビュー", text="テストレビューの内容")
    book_info = BookInfo(
        title="テスト書籍",
        author="テスト著者", 
        price="￥1000",
        rating="5つ星のうち4.5",
        reviews=[review]
    )
    
    # 実行
    json_str = book_info.to_json()
    json_dict = book_info.to_dict()
    
    # 検証
    assert '"title": "テスト書籍"' in json_str
    assert json_dict["title"] == "テスト書籍"
    assert json_dict["reviews"][0]["title"] == "テストレビュー"


def test_error_handling_file_not_found():
    """存在しないファイルに対する適切なエラーハンドリングをテスト"""
    # 準備
    scraper = AmazonScraper()
    
    # 実行・検証
    with pytest.raises(PageNotFoundError):
        scraper.scrape_book_info_from_html_file("non_existent_file.html")