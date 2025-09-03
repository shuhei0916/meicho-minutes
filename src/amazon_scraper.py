import requests
from bs4 import BeautifulSoup
import os


class AmazonScraper:
    def __init__(self, request_delay=1.0, max_retries=3):
        self.request_delay = request_delay
        self.max_retries = max_retries
        self.session = requests.Session()
    
    def scrape_book_info_from_html_file(self, html_file_path):
        """ローカルHTMLファイルから書籍情報を取得"""
        with open(html_file_path, 'r', encoding='utf-8') as file:
            html_content = file.read()
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # タイトルを取得
        title_element = soup.find('span', id='productTitle')
        title = title_element.text.strip() if title_element else None
        
        # 著者を取得
        byline_info = soup.find('div', id='bylineInfo')
        author_element = byline_info.find('a', class_='a-link-normal') if byline_info else None
        author = author_element.text.strip() if author_element else None
        
        # 価格を取得
        price_element = soup.find('span', {'aria-label': '￥534'})
        price = price_element.text.strip() if price_element else None
        
        # 画像URLを取得
        image_element = soup.find('img', id='landingImage')
        image_url = image_element.get('src') if image_element else None
        
        return {
            "title": title,
            "author": author,
            "price": price,
            "image_url": image_url
        }