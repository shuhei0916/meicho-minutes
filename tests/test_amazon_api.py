import pytest
from src.amazon_scraper import AmazonScraper


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