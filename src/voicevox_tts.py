import requests
import os
from typing import Dict, Optional
from src.gemini_script_generator import VideoScript


class VoiceVoxError(Exception):
    """VOICEVOX関連のエラーの基底クラス"""
    pass


class ServerConnectionError(VoiceVoxError):
    """VOICEVOXサーバーへの接続エラー"""
    pass


class AudioGenerationError(VoiceVoxError):
    """音声生成時のエラー"""
    pass


class VoiceVoxTTS:
    """VOICEVOX Text-to-Speech クライアント"""
    
    def __init__(self, server_url: str = "127.0.0.1:50021", speaker_id: int = 1):
        """
        VoiceVoxTTSを初期化
        
        Args:
            server_url: VOICEVOXエンジンのサーバーURL
            speaker_id: 話者ID（デフォルト: 1）
        """
        self.server_url = server_url
        self.speaker_id = speaker_id
        self.base_url = f"http://{server_url}"
    
    def _create_audio_query(self, text: str, speaker_id: int) -> Dict:
        """
        テキストから音声クエリを生成
        
        Args:
            text: 音声合成するテキスト
            speaker_id: 話者ID
            
        Returns:
            音声クエリの辞書
            
        Raises:
            ServerConnectionError: サーバー接続エラー
        """
        try:
            response = requests.post(
                f"{self.base_url}/audio_query",
                params={"text": text, "speaker": speaker_id}
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise ServerConnectionError(f"音声クエリの生成に失敗しました: {e}")
    
    def _synthesize_audio(self, query: Dict, speaker_id: int) -> bytes:
        """
        音声クエリから音声データを合成
        
        Args:
            query: 音声クエリの辞書
            speaker_id: 話者ID
            
        Returns:
            音声データ（bytes）
            
        Raises:
            AudioGenerationError: 音声合成エラー
        """
        try:
            response = requests.post(
                f"{self.base_url}/synthesis",
                json=query,
                params={"speaker": speaker_id}
            )
            response.raise_for_status()
            return response.content
        except requests.RequestException as e:
            raise AudioGenerationError(f"音声合成に失敗しました: {e}")
    
    def generate_audio_from_script(self, script: VideoScript, output_path: str, speaker_id: Optional[int] = None) -> str:
        """
        VideoScriptから音声ファイルを生成
        
        Args:
            script: 動画台本
            output_path: 出力ファイルパス
            speaker_id: 話者ID（指定されない場合はデフォルト値を使用）
            
        Returns:
            生成された音声ファイルのパス
        """
        # 話者IDのデフォルト値設定
        if speaker_id is None:
            speaker_id = self.speaker_id
        
        # 台本をテキストに変換
        script_text = script.to_text()
        
        # 音声クエリ生成
        query = self._create_audio_query(script_text, speaker_id)
        
        # 音声合成
        audio_data = self._synthesize_audio(query, speaker_id)
        
        # ファイル保存
        with open(output_path, 'wb') as f:
            f.write(audio_data)
        
        return output_path


if __name__ == "__main__":
    import sys
    import argparse
    try:
        from src.amazon_scraper import AmazonScraper
        from src.gemini_script_generator import GeminiScriptGenerator
    except ImportError:
        from amazon_scraper import AmazonScraper
        from gemini_script_generator import GeminiScriptGenerator
    
    parser = argparse.ArgumentParser(description='VOICEVOX TTSを使用して音声ファイルを生成')
    parser.add_argument('--script', type=str, help='VideoScriptのJSONファイルパス')
    parser.add_argument('--text', type=str, help='直接テキストを指定')
    parser.add_argument('--url', type=str, help='Amazon商品ページのURL')
    parser.add_argument('--file', type=str, help='ローカルHTMLファイルパス')
    parser.add_argument('--output', type=str, required=True, help='出力する音声ファイルパス')
    parser.add_argument('--speaker', type=int, default=1, help='話者ID（デフォルト: 1）')
    parser.add_argument('--server', type=str, default='127.0.0.1:50021', help='VOICEVOXサーバーURL')
    
    args = parser.parse_args()
    
    try:
        tts = VoiceVoxTTS(server_url=args.server, speaker_id=args.speaker)
        
        if args.script:
            # JSONファイルからVideoScriptを読み込み
            import json
            with open(args.script, 'r', encoding='utf-8') as f:
                script_data = json.load(f)
            
            script = VideoScript(
                title=script_data['title'],
                overview=script_data['overview'],
                comments=script_data['comments'],
                conclusion=script_data['conclusion']
            )
            print(f"スクリプトファイルから音声生成中: {args.script}")
            result_path = tts.generate_audio_from_script(script, args.output, args.speaker)
            
        elif args.text:
            # 直接テキストから音声生成
            print(f"テキストから音声生成中: {args.text}")
            query = tts._create_audio_query(args.text, args.speaker)
            audio_data = tts._synthesize_audio(query, args.speaker)
            
            with open(args.output, 'wb') as f:
                f.write(audio_data)
            result_path = args.output
            
        elif args.url or args.file:
            # Amazon商品から台本生成して音声化
            scraper = AmazonScraper()
            
            if args.url:
                print(f"URLから書籍情報を取得中: {args.url}")
                book_info = scraper.scrape_book_info_from_url(args.url)
            else:
                print(f"ファイルから書籍情報を取得中: {args.file}")
                book_info = scraper.scrape_book_info_from_html_file(args.file)
            
            # Geminiで台本生成
            script_generator = GeminiScriptGenerator()
            script = script_generator.generate_script_from_book_info(book_info)
            
            print("Gemini APIで台本生成完了")
            print("VOICEVOX TTSで音声生成中...")
            
            result_path = tts.generate_audio_from_script(script, args.output, args.speaker)
        else:
            print("エラー: --script, --text, --url, --file のいずれかを指定してください")
            sys.exit(1)
        
        print(f"\n✅ 音声ファイル生成完了!")
        print(f"   出力先: {result_path}")
        print(f"   話者ID: {args.speaker}")
        
    except Exception as e:
        print(f"エラー: 音声生成中にエラーが発生しました: {e}")
        sys.exit(1)