from google import genai
import os
import json
from typing import Optional
from dataclasses import dataclass, asdict
from decouple import config

try:
    from src.amazon_scraper import BookInfo
except ImportError:
    from amazon_scraper import BookInfo


@dataclass
class VideoScript:
    """動画台本を表すデータクラス"""
    title: str
    overview: str
    comments: list[str] 
    conclusion: str
    
    def to_dict(self) -> dict:
        """辞書形式に変換"""
        return asdict(self)
    
    def to_json(self, indent=2) -> str:
        """JSON文字列に変換"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)
    
    def to_text(self) -> str:
        """台本テキスト形式に変換"""
        script_parts = []
        script_parts.append(f"【タイトル】\n{self.title}\n")
        script_parts.append(f"【概要】\n{self.overview}\n")
        
        for i, comment in enumerate(self.comments, 1):
            script_parts.append(f"【コメント{i}】\n{comment}\n")
        
        script_parts.append(f"【締め】\n{self.conclusion}")
        
        return "\n".join(script_parts)


class GeminiScriptGeneratorError(Exception):
    """Gemini台本生成関連のエラー"""
    pass


class GeminiScriptGenerator:
    """Gemini APIを使用した動画台本生成クラス"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        GeminiScriptGeneratorを初期化
        
        Args:
            api_key: Gemini APIキー。未指定の場合は環境変数から取得
        """
        self.api_key = api_key or config('GEMINI_API_KEY', default='')
        if not self.api_key:
            raise GeminiScriptGeneratorError("GEMINI_API_KEYが設定されていません")
        
        # Gemini APIクライアントを設定
        self.client = genai.Client(api_key=self.api_key)
    
    def generate_script_from_book_info(self, book_info: BookInfo) -> VideoScript:
        """
        書籍情報から動画台本を生成
        
        Args:
            book_info: 書籍情報
            
        Returns:
            VideoScript: 生成された動画台本
        """
        try:
            # レビューテキストを文字列に変換
            reviews_text = ""
            if book_info.reviews:
                reviews_text = "\n".join([
                    f"・{review.title}: {review.text[:200]}..." 
                    for review in book_info.reviews[:3]  # 最初の3つのレビューのみ使用
                ])
            
            prompt = self._create_prompt(book_info, reviews_text)
            
            # Gemini APIで台本生成
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            
            if not response.text:
                raise GeminiScriptGeneratorError("Gemini APIからの応答が空です")
            
            # レスポンスをパースしてVideoScriptオブジェクトに変換
            return self._parse_response_to_script(response.text, book_info)
            
        except Exception as e:
            raise GeminiScriptGeneratorError(f"台本生成中にエラーが発生しました: {e}")
    
    def _create_prompt(self, book_info: BookInfo, reviews_text: str) -> str:
        """台本生成用のプロンプトを作成"""
        return f"""
あなたはYouTubeショート動画の台本作成の専門家です。
以下の書籍情報を基に、60秒程度のショート動画用台本を作成してください。

# 書籍情報
- タイトル: {book_info.title}
- 著者: {book_info.author}
- 価格: {book_info.price}
- 評価: {book_info.rating}
- 説明: {book_info.description}

# カスタマーレビュー
{reviews_text}

# 台本構成要件
1. 【タイトル】: キャッチーで興味を引く動画タイトル（例：「50年前に書かれた伝説の予言書がヤバすぎた・・・！」）
2. 【概要】: 本の内容を1-2文で魅力的に紹介
3. 【コメント1】: レビューや書籍内容から印象的なポイントを1つ（30文字程度）
4. 【コメント2】: 別の角度からの魅力的なポイント（30文字程度）  
5. 【コメント3】: さらに別の興味深い点（30文字程度、オプション）
6. 【締め】: 視聴者の行動を促す一言（購入意欲を高める）

# 出力形式
以下の形式で出力してください：
タイトル: [ここに動画タイトル]
概要: [ここに本の概要]
コメント1: [ここにコメント1]
コメント2: [ここにコメント2]
コメント3: [ここにコメント3]（オプション）
締め: [ここに締めの一言]

# 注意事項
- YouTube視聴者（20-40代）に響く表現を使用
- 感情に訴える言葉選び
- 短時間で伝わる簡潔な表現
- 書籍の魅力を最大限に引き出す
"""
    
    def _parse_response_to_script(self, response_text: str, book_info: BookInfo) -> VideoScript:
        """Geminiの応答をVideoScriptオブジェクトに変換"""
        lines = response_text.strip().split('\n')
        
        script_data = {
            'title': '',
            'overview': '', 
            'comments': [],
            'conclusion': ''
        }
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line.startswith('タイトル:'):
                script_data['title'] = line.replace('タイトル:', '').strip()
            elif line.startswith('概要:'):
                script_data['overview'] = line.replace('概要:', '').strip()
            elif line.startswith('コメント1:'):
                script_data['comments'].append(line.replace('コメント1:', '').strip())
            elif line.startswith('コメント2:'):
                script_data['comments'].append(line.replace('コメント2:', '').strip())
            elif line.startswith('コメント3:'):
                script_data['comments'].append(line.replace('コメント3:', '').strip())
            elif line.startswith('締め:'):
                script_data['conclusion'] = line.replace('締め:', '').strip()
        
        # 必須フィールドのチェックとデフォルト値設定
        if not script_data['title']:
            script_data['title'] = f"{book_info.title}が面白すぎる件について"
        if not script_data['overview']:
            script_data['overview'] = book_info.description or "この本、めちゃくちゃ面白いんです！"
        if not script_data['comments']:
            script_data['comments'] = ["読者からの評価も高い！", "この内容は必見です"]
        if not script_data['conclusion']:
            script_data['conclusion'] = "気になった方はぜひチェックしてみてください！"
        
        return VideoScript(
            title=script_data['title'],
            overview=script_data['overview'],
            comments=script_data['comments'],
            conclusion=script_data['conclusion']
        )


if __name__ == "__main__":
    import sys
    import argparse
    try:
        from src.amazon_scraper import AmazonScraper
    except ImportError:
        from amazon_scraper import AmazonScraper
    
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
            # TODO: JSONからBookInfoオブジェクトを作成する処理を追加
            print("JSON読み込み機能は今後実装予定です", file=sys.stderr)
            sys.exit(1)
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
                sample_file = os.path.join(os.path.dirname(__file__), "..", "amazon_page_sample.html")
                if os.path.exists(sample_file):
                    print(f"サンプルファイルから書籍情報を取得中: {sample_file}", file=sys.stderr)
                    book_info = scraper.scrape_book_info_from_html_file(sample_file)
                else:
                    print("エラー: --url, --file, または --book-json を指定してください", file=sys.stderr)
                    sys.exit(1)
        
        # 台本生成
        print("Gemini APIで台本生成中...", file=sys.stderr)
        generator = GeminiScriptGenerator()
        script = generator.generate_script_from_book_info(book_info)
        
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