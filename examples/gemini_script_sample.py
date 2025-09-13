#!/usr/bin/env python3
"""
Gemini Script Generator CLI Sample
書籍情報から動画台本を生成するサンプルスクリプト
"""

import sys
import os
import json
import argparse

# src/ モジュールへのパスを追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from script_generator import ScriptGenerator
from amazon_scraper import AmazonScraper


def book_info_to_dict(book_info):
    """BookInfoオブジェクトを辞書に変換"""
    return {
        "title": book_info.title or "",
        "author": book_info.author or "",
        "price": book_info.price or "",
        "rating": book_info.rating or "",
        "description": book_info.description or "",
        "reviews": [
            {"title": review.title or "", "text": review.text or ""}
            for review in book_info.reviews
        ] if book_info.reviews else []
    }


def main():
    parser = argparse.ArgumentParser(description='書籍情報から動画台本を生成')
    parser.add_argument('--url', type=str, help='Amazon商品ページのURL')
    parser.add_argument('--file', type=str, help='ローカルHTMLファイルパス')
    parser.add_argument('--book-json', type=str, help='書籍情報JSONファイルパス')
    parser.add_argument('--output', type=str, help='台本出力ファイルパス')
    parser.add_argument('--format', choices=['json', 'text'], default='text', 
                        help='出力形式 (json/text)')
    
    args = parser.parse_args()
    
    try:
        # 書籍情報の取得
        if args.book_json:
            # JSONファイルから読み込み
            with open(args.book_json, 'r', encoding='utf-8') as f:
                book_data = json.load(f)
        else:
            # スクレイピングで取得
            scraper = AmazonScraper()
            if args.url:
                print(f"URLから書籍情報を取得中: {args.url}", file=sys.stderr)
                book_info = scraper.scrape_book_info_from_url(args.url)
            elif args.file:
                print(f"ファイルから書籍情報を取得中: {args.file}", file=sys.stderr)
                book_info = scraper.scrape_book_info_from_html_file(args.file)
            else:
                # デフォルトでサンプルファイルを使用
                sample_file = os.path.join(os.path.dirname(__file__), "..", "data", "amazon_page_sample.html")
                if os.path.exists(sample_file):
                    print(f"サンプルファイルから書籍情報を取得中: {sample_file}", file=sys.stderr)
                    book_info = scraper.scrape_book_info_from_html_file(sample_file)
                else:
                    print("エラー: --url, --file, または --book-json を指定してください", file=sys.stderr)
                    sys.exit(1)
            
            # BookInfoを辞書に変換
            book_data = book_info_to_dict(book_info)
        
        # 台本生成
        print("Gemini APIで台本生成中...", file=sys.stderr)
        generator = ScriptGenerator()
        script = generator.generate_script(book_data)
        
        # 出力
        if args.format == 'json':
            output_content = script.to_json()
        else:
            output_content = script.to_text()
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output_content)
            print(f"台本をファイルに保存しました: {args.output}", file=sys.stderr)
        else:
            print(output_content)
        
        print(f"\n✅ 台本生成完了!", file=sys.stderr)
        print(f"   タイトル: {script.title}", file=sys.stderr)
        print(f"   コメント数: {len(script.comments)}", file=sys.stderr)
        
    except Exception as e:
        print(f"エラー: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()