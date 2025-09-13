import google.generativeai as genai
import os
import json
import re
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from decouple import config


@dataclass
class VideoScript:
    """動画台本を表すデータクラス"""
    title: str
    description: str
    
    def to_json(self, indent=2) -> str:
        """JSON文字列に変換"""
        return json.dumps(asdict(self), ensure_ascii=False, indent=indent)
    
    def to_text(self) -> str:
        """台本テキスト形式に変換"""
        return f"【タイトル】\n{self.title}\n\n【紹介文】\n{self.description}"
    
    def to_speech_text(self) -> str:
        """音声読み上げ用テキスト（見出しなし）"""
        return f"{self.title}。{self.description}"


class ScriptGeneratorError(Exception):
    """台本生成関連のエラー"""
    pass


class ScriptGenerator:
    """AI APIを使用した動画台本生成クラス"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        ScriptGeneratorを初期化
        
        Args:
            api_key: AI APIキー。未指定の場合は環境変数から取得
        """
        self.api_key = api_key or config('GEMINI_API_KEY', default='')
        if not self.api_key:
            raise ScriptGeneratorError("GEMINI_API_KEYが設定されていません")
        
        # Gemini APIクライアントを設定
        genai.configure(api_key=self.api_key)
        self.client = genai.GenerativeModel("gemini-2.5-flash")
    
    def generate_script(self, book_data: Dict[str, Any]) -> VideoScript:
        """
        書籍情報から動画台本を生成
        
        Args:
            book_data: 書籍情報の辞書
            {
                "title": str,
                "author": str,
                "price": str,
                "rating": str,
                "description": str,
                "reviews": [{"title": str, "text": str}, ...]
            }
            
        Returns:
            VideoScript: 生成された動画台本
        """
        try:
            # レビューテキストを文字列に変換
            reviews_text = ""
            if book_data.get('reviews'):
                reviews_text = "\n".join([
                    f"・{review.get('title', '')}: {review.get('text', '')[:200]}..." 
                    for review in book_data['reviews'][:3]  # 最初の3つのレビューのみ使用
                ])
            
            prompt = self._create_prompt(book_data, reviews_text)
            
            # Gemini APIで台本生成
            response = self.client.generate_content(prompt)
            
            if not response.text:
                raise ScriptGeneratorError("AI APIからの応答が空です")
            
            # レスポンスをパースしてVideoScriptオブジェクトに変換
            return self._parse_response_to_script(response.text, book_data)
            
        except Exception as e:
            raise ScriptGeneratorError(f"台本生成中にエラーが発生しました: {e}")
    
    def _create_prompt(self, book_data: Dict[str, Any], reviews_text: str) -> str:
        """台本生成用のプロンプトを作成"""
        return f"""
以下の書籍情報をもとに、YouTubeショート動画用の台本を作成してください。

# 書籍情報
- タイトル: {book_data.get('title', '')}
- 著者: {book_data.get('author', '')}
- 価格: {book_data.get('price', '')}
- 評価: {book_data.get('rating', '')}
- 説明: {book_data.get('description', '')}

# カスタマーレビュー
{reviews_text}

# 出力形式
以下のJSON形式のみで回答してください。他の文字は含めないでください：

{{
  "title": "キャッチーな動画タイトル（20文字以内）",
  "description": "本の魅力を端的にまとめた紹介文（240〜280文字）。"
}}

# 制約
- 読者の興味を引く言葉選び
- 短く、感情に訴える表現
- titleとdescriptionにはエスケープ文字や余計な引用符を含めない
- 純粋なJSON形式のみで回答
"""
    
    def _extract_json_from_response(self, response_text: str) -> str:
        """Geminiの応答から最初の有効なJSONブロックを抽出"""
        # JSONブロック開始と終了を検索
        start_idx = response_text.find('{')
        if start_idx == -1:
            raise ValueError("JSONブロックが見つかりません")
        
        brace_count = 0
        for i in range(start_idx, len(response_text)):
            if response_text[i] == '{':
                brace_count += 1
            elif response_text[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    return response_text[start_idx:i+1]
        
        raise ValueError("JSONブロックが完全ではありません")
    
    def _parse_response_to_script(self, response_text: str, book_data: Dict[str, Any]) -> VideoScript:
        """Geminiの応答をVideoScriptオブジェクトに変換"""
        try:
            # 応答から純粋なJSONブロックを抽出
            json_text = self._extract_json_from_response(response_text)
            script_data = json.loads(json_text)
            
            # 必須フィールドの確認
            title = script_data.get('title', '').strip()
            description = script_data.get('description', '').strip()
            
            # バリデーション
            if not title:
                title = f"{book_data.get('title', '未知の書籍')}が面白すぎる件"
            if not description:
                description = book_data.get('description', '') or "この本、めちゃくちゃ面白いんです！読者からの評価も高く、現代に必要な知識が詰まった必読の一冊です。"
            
            # 文字数制限チェック
            if len(title) > 20:
                title = title[:17] + "..."
            if len(description) > 280:
                description = description[:277] + "..."
            elif len(description) < 240:
                # 短すぎる場合は補足
                if len(description) < 200:
                    description += "ぜひ一度手に取ってみてください。"
            
            return VideoScript(
                title=title,
                description=description
            )
            
        except json.JSONDecodeError:
            # JSON解析に失敗した場合はフォールバック処理
            lines = response_text.strip().split('\n')
            title = ""
            description = ""
            
            for line in lines:
                line = line.strip()
                if line.startswith('"title":'):
                    title = line.split(':', 1)[1].strip().strip('"').strip("'").strip(',')
                elif line.startswith('"description":'):
                    description = line.split(':', 1)[1].strip().strip('"').strip("'").strip(',')
            
            # デフォルト値設定
            if not title:
                title = f"{book_data.get('title', '未知の書籍')}が面白すぎる件"
            if not description:
                description = book_data.get('description', '') or "この本、めちゃくちゃ面白いんです！読者からの評価も高く、現代に必要な知識が詰まった必読の一冊です。"
            
            return VideoScript(
                title=title[:20] if len(title) > 20 else title,
                description=description[:280] if len(description) > 280 else description
            )


if __name__ == "__main__":
    import sys
    import argparse
    import os
    from pathlib import Path
    
    parser = argparse.ArgumentParser(
        description='Script Generator - 書籍情報から動画台本を生成',
        epilog="""
使用例:
  # JSONファイルから台本生成
  python src/script_generator.py --book-json tmp/bookinfo.json
  
  # 出力をファイルに保存
  python src/script_generator.py --book-json tmp/bookinfo.json --output script.json
  
  # デフォルト書籍データでテスト実行
  python src/script_generator.py --output script.json
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--book-json', type=str, help='書籍情報JSONファイルのパス')
    parser.add_argument('--output', type=str, help='出力ファイルのパス（指定しない場合は標準出力）')
    
    args = parser.parse_args()
    
    try:
        # 書籍データの準備
        if args.book_json:
            # JSONファイルから読み込み
            book_json_path = Path(args.book_json)
            if not book_json_path.exists():
                print(f"❌ エラー: ファイルが見つかりません: {args.book_json}", file=sys.stderr)
                sys.exit(1)
            
            with open(book_json_path, 'r', encoding='utf-8') as f:
                book_data = json.load(f)
            
            print(f"📚 書籍情報を読み込み: {book_json_path}", file=sys.stderr)
        else:
            # デフォルト書籍データを使用
            book_data = {
                "title": "団塊の世代 〈新版〉 (文春文庫 さ 1-20)",
                "author": "堺屋 太一",
                "price": "￥145 より",
                "image_url": "https://m.media-amazon.com/images/I/51wZYgJf7oL._SY445_SX342_.jpg",
                "description": "「団塊の世代」が日本の経済社会になにをもたらすのかを予言した名著。今後の大量定年、老齢化問題への対策を新たに加えた新装版",
                "rating": "5つ星のうち3.8",
                "reviews": [
                    {"title": "読んでて切ない団塊世代サラリーマン譚",
                    "text": "ちょっと前に著者である堺屋氏の訃報を知ったのを機に、気になっていた本書を購読。\n団塊世代サラリーマンの短編が4本収録されてます。\n話の中の団塊世代の空気感を懐かしく感じると共に堺屋氏の先見の明に感服しました。\n令和時代となった現在ではちょっとした史料になるのではないでしょうか。"},
                    {"title": "なんだ、分かってたんじゃねえか",
                    "text": "本書の優れたところは、「団塊」という人口のアンバランスがもたらす社会変動に直面しての、日本人のリアルなグダグダっぷりをきちんと描写していることだ。おそらくモデルは第二次大戦時の有様なのだろう。\n付け焼き刃な対応、「オレ以外の誰か」への恨み言、結局何もしないで溜飲が下がればそれでいい、というのがちゃんと描かれていた。\nよくできた小説だと思う。本書が書かれた70年代に、単に統計にすぎない社会問題から、未来の人の心の動きが見えていたなんて。"}
                ]
            }
            print("📚 デフォルト書籍データを使用", file=sys.stderr)
        
        # 台本生成
        print("🤖 AI APIで台本生成中...", file=sys.stderr)
        generator = ScriptGenerator()
        script = generator.generate_script(book_data)
        
        # JSON形式で出力（固定）
        output_content = script.to_json()
        
        # 出力
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(output_content)
            
            print(f"✅ 台本を保存しました: {output_path}", file=sys.stderr)
            print(f"   タイトル: {script.title}", file=sys.stderr)
            print(f"   紹介文長: {len(script.description)}文字", file=sys.stderr)
        else:
            print(output_content)
            print(f"\n✅ 台本生成完了!", file=sys.stderr)
            print(f"   タイトル: {script.title}", file=sys.stderr)
            print(f"   紹介文長: {len(script.description)}文字", file=sys.stderr)
        
    except FileNotFoundError as e:
        print(f"❌ ファイルエラー: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析エラー: {e}", file=sys.stderr)
        print("書籍情報JSONファイルの形式を確認してください", file=sys.stderr)
        sys.exit(1)
    except ScriptGeneratorError as e:
        print(f"❌ 台本生成エラー: {e}", file=sys.stderr)
        print("注意: GEMINI_API_KEY環境変数が設定されているか確認してください", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ 予期しないエラー: {e}", file=sys.stderr)
        sys.exit(1)