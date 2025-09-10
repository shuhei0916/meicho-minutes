import google.generativeai as genai
import os
import json
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from decouple import config


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
                raise GeminiScriptGeneratorError("Gemini APIからの応答が空です")
            
            # レスポンスをパースしてVideoScriptオブジェクトに変換
            return self._parse_response_to_script(response.text, book_data)
            
        except Exception as e:
            raise GeminiScriptGeneratorError(f"台本生成中にエラーが発生しました: {e}")
    
    def _create_prompt(self, book_data: Dict[str, Any], reviews_text: str) -> str:
        """台本生成用のプロンプトを作成"""
        return f"""
あなたはYouTubeショート動画の台本作成の専門家です。
以下の書籍情報を基に、60秒程度のショート動画用台本を作成してください。

# 書籍情報
- タイトル: {book_data.get('title', '')}
- 著者: {book_data.get('author', '')}
- 価格: {book_data.get('price', '')}
- 評価: {book_data.get('rating', '')}
- 説明: {book_data.get('description', '')}

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
    
    def _parse_response_to_script(self, response_text: str, book_data: Dict[str, Any]) -> VideoScript:
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
            script_data['title'] = f"{book_data.get('title', '未知の書籍')}が面白すぎる件について"
        if not script_data['overview']:
            script_data['overview'] = book_data.get('description', '') or "この本、めちゃくちゃ面白いんです！"
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
    # 純粋ライブラリとしてのデモンストレーション
    print("このファイルは純粋なライブラリです。")
    print("CLI機能は examples/gemini_script_sample.py を使用してください。")
    
    # 簡単なデモ
    demo_book_data = {
        "title": "デモ書籍",
        "author": "デモ著者",
        "price": "￥1000",
        "rating": "5つ星のうち4.0",
        "description": "これはデモ用の書籍説明です。",
        "reviews": [
            {"title": "面白い", "text": "とても面白かったです"},
            {"title": "おすすめ", "text": "みんなにおすすめしたい本です"}
        ]
    }
    
    try:
        generator = GeminiScriptGenerator()
        script = generator.generate_script(demo_book_data)
        print("\n=== 生成された台本 ===\n")
        print(script.to_text())
        print("\n=== JSON形式 ===\n")
        print(script.to_json())
    except Exception as e:
        print(f"エラー: {e}")
        print("注意: GEMINI_API_KEY環境変数が設定されているか確認してください。")