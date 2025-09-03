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
                reviews.append({
                    "title": review_title,
                    "text": review_text
                })
        
        return {
            "title": title,
            "author": author,
            "price": price,
            "image_url": image_url,
            "description": description,
            "rating": rating,
            "reviews": reviews
        }