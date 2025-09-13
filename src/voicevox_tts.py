import requests
import os
import json
from typing import Dict, Optional
from pathlib import Path

# VideoScriptクラスのインポート（モジュール実行時の互換性対応）
try:
    from src.script_generator import VideoScript
    from src.ass_subtitle_generator import ASSSubtitleGenerator
except ImportError:
    from script_generator import VideoScript
    from ass_subtitle_generator import ASSSubtitleGenerator


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
    
    def __init__(self, server_url: str = "127.0.0.1:50021", speaker_id: int = 1, speed_scale: float = 1.0):
        """
        VoiceVoxTTSを初期化
        
        Args:
            server_url: VOICEVOXエンジンのサーバーURL（ハードコーディング推奨）
            speaker_id: 話者ID（デフォルト: 1）
            speed_scale: 話者スピード倍率（0.5〜2.0、デフォルト: 1.0）
        """
        self.server_url = server_url
        self.speaker_id = speaker_id
        self.speed_scale = speed_scale
        self.base_url = f"http://{server_url}"
        
        # ASS字幕生成器を初期化
        self.ass_generator = ASSSubtitleGenerator()
    
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
    
    def _modify_audio_query(self, query: Dict, speed_scale: float = None) -> Dict:
        """
        音声クエリのパラメータを調整
        
        Args:
            query: 音声クエリの辞書
            speed_scale: 話者スピード倍率（指定されない場合はインスタンスのデフォルト値を使用）
        
        Returns:
            調整された音声クエリの辞書
        """
        if speed_scale is None:
            speed_scale = self.speed_scale
        
        # スピード調整（0.5〜2.0の範囲に制限）
        speed_scale = max(0.5, min(2.0, speed_scale))
        query["speedScale"] = speed_scale
        
        return query
    
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
        
        # 台本を音声読み上げ用テキストに変換（見出しなし）
        script_text = script.to_speech_text()
        
        # 音声クエリ生成
        query = self._create_audio_query(script_text, speaker_id)
        
        # 音声クエリのパラメータ調整（スピード等）
        query = self._modify_audio_query(query)
        
        # 音声合成
        audio_data = self._synthesize_audio(query, speaker_id)
        
        # ファイル保存
        with open(output_path, 'wb') as f:
            f.write(audio_data)
        
        return output_path
    
    def generate_audio_with_ass_subtitle(
        self, 
        script: VideoScript, 
        audio_output_path: str, 
        ass_output_path: str,
        speaker_id: Optional[int] = None
    ) -> tuple[str, str]:
        """
        VideoScriptから音声ファイルとASS字幕ファイルを同時生成
        
        Args:
            script: 動画台本
            audio_output_path: 音声ファイル出力パス
            ass_output_path: ASS字幕ファイル出力パス
            speaker_id: 話者ID（指定されない場合はデフォルト値を使用）
            
        Returns:
            (音声ファイルパス, ASS字幕ファイルパス) のタプル
        """
        # 話者IDのデフォルト値設定
        if speaker_id is None:
            speaker_id = self.speaker_id
        
        # 台本を音声読み上げ用テキストに変換
        script_text = script.to_speech_text()
        
        # 音声クエリ生成
        query = self._create_audio_query(script_text, speaker_id)
        
        # 音声クエリのパラメータ調整
        query = self._modify_audio_query(query)
        
        # ASS字幕生成（音声合成前に実行）
        accent_phrases = query.get('accent_phrases', [])
        ass_content = self.ass_generator.generate_ass_from_accent_phrases(
            accent_phrases, ass_output_path, script_text
        )
        
        # 音声合成
        audio_data = self._synthesize_audio(query, speaker_id)
        
        # 音声ファイル保存
        with open(audio_output_path, 'wb') as f:
            f.write(audio_data)
        
        return audio_output_path, ass_output_path
    
    def generate_ass_subtitle_from_text(
        self, 
        text: str, 
        ass_output_path: str,
        speaker_id: Optional[int] = None
    ) -> str:
        """
        テキストから直接ASS字幕ファイルを生成（音声ファイルは生成しない）
        
        Args:
            text: 読み上げテキスト
            ass_output_path: ASS字幕ファイル出力パス
            speaker_id: 話者ID（指定されない場合はデフォルト値を使用）
            
        Returns:
            ASS字幕ファイルのパス
        """
        # 話者IDのデフォルト値設定
        if speaker_id is None:
            speaker_id = self.speaker_id
        
        # 音声クエリ生成（音声は合成しない）
        query = self._create_audio_query(text, speaker_id)
        query = self._modify_audio_query(query)
        
        # ASS字幕生成
        accent_phrases = query.get('accent_phrases', [])
        self.ass_generator.generate_ass_from_accent_phrases(
            accent_phrases, ass_output_path, text
        )
        
        return ass_output_path
    
    def save_audio_query(self, text: str, query_output_path: str, speaker_id: Optional[int] = None) -> str:
        """
        音声クエリをJSONファイルとして保存（デバッグ用）
        
        Args:
            text: 読み上げテキスト
            query_output_path: audio_query JSONファイル出力パス
            speaker_id: 話者ID
            
        Returns:
            保存されたJSONファイルのパス
        """
        if speaker_id is None:
            speaker_id = self.speaker_id
        
        query = self._create_audio_query(text, speaker_id)
        query = self._modify_audio_query(query)
        
        with open(query_output_path, 'w', encoding='utf-8') as f:
            json.dump(query, f, ensure_ascii=False, indent=2)
        
        return query_output_path


if __name__ == "__main__":
    import sys
    import argparse
    from pathlib import Path
    
    parser = argparse.ArgumentParser(
        description='VoiceVox TTS - 台本JSONから音声ファイルを生成',
        epilog="""
使用例:
  # 台本JSONから音声生成
  python src/voicevox_tts.py --script tmp/script.json --output tmp/audio.wav
  
  # デフォルト台本データでテスト実行
  python src/voicevox_tts.py --output test_audio.wav
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--script', type=str, help='台本JSONファイルのパス')
    parser.add_argument('--output', type=str, help='出力音声ファイルのパス（未指定時は標準エラー出力のみ）')
    parser.add_argument('--ass-subtitle', type=str, help='ASS字幕ファイル出力パス')
    parser.add_argument('--save-audio-query', type=str, help='audio_queryをJSONファイルに保存（デバッグ用）')
    parser.add_argument('--text', type=str, help='直接指定するテキスト')
    
    args = parser.parse_args()
    
    # ハードコーディングされた設定
    DEFAULT_SERVER = "127.0.0.1:50021"
    DEFAULT_SPEAKER = 13
    DEFAULT_SPEED = 1.2  # 標準スピード
    
    try:
        # VoiceVoxTTSを初期化
        tts = VoiceVoxTTS(server_url=DEFAULT_SERVER, speaker_id=DEFAULT_SPEAKER, speed_scale=DEFAULT_SPEED)
        
        # 台本データまたはテキストの準備
        script = None
        direct_text = None
        
        if args.script:
            # JSONファイルから台本を読み込み
            script_path = Path(args.script)
            if not script_path.exists():
                print(f"❌ エラー: ファイルが見つかりません: {args.script}", file=sys.stderr)
                sys.exit(1)
            
            with open(script_path, 'r', encoding='utf-8') as f:
                script_data = json.load(f)
            
            script = VideoScript(
                title=script_data['title'],
                description=script_data['description']
            )
            
            print(f"📜 台本を読み込み: {script_path}", file=sys.stderr)
            
        elif args.text:
            # 直接指定されたテキストを使用
            direct_text = args.text
            print(f"📝 直接テキスト使用: {direct_text[:50]}...", file=sys.stderr)
            
        else:
            # デフォルト台本データを使用
            script = VideoScript(
                title="【衝撃】50年前に日本の未来を予言した伝説の書がヤバすぎた…！",
                description="半世紀前に日本の未来を予言した伝説の名著。今まさに直面する社会問題のヒントがここに。50年前の描写が今の日本に刺さりまくり、働き方、人間関係の普遍的ヒントが満載。この国が迎える未来をすでに予言していたこの\"予言書\"を読んで、未来を生き抜くヒントを見つけよう！"
            )
            print("📜 デフォルト台本データを使用", file=sys.stderr)
        
        # audio_queryの保存（デバッグ用）
        if args.save_audio_query:
            query_path = Path(args.save_audio_query)
            query_path.parent.mkdir(parents=True, exist_ok=True)
            
            if script:
                text_to_process = script.to_speech_text()
            else:
                text_to_process = direct_text
            
            saved_query = tts.save_audio_query(text_to_process, str(query_path))
            print(f"💾 audio_queryを保存しました: {saved_query}", file=sys.stderr)
        
        # ASS字幕のみ生成
        if args.ass_subtitle and not args.output:
            ass_path = Path(args.ass_subtitle)
            ass_path.parent.mkdir(parents=True, exist_ok=True)
            
            if script:
                text_to_process = script.to_speech_text()
            else:
                text_to_process = direct_text
            
            print(f"📝 ASS字幕生成中... (話者ID: {DEFAULT_SPEAKER})", file=sys.stderr)
            ass_result = tts.generate_ass_subtitle_from_text(text_to_process, str(ass_path))
            
            print(f"✅ ASS字幕ファイルを生成しました: {ass_result}", file=sys.stderr)
            
        # 音声とASS字幕を同時生成
        elif args.output and args.ass_subtitle and script:
            audio_path = Path(args.output)
            ass_path = Path(args.ass_subtitle)
            audio_path.parent.mkdir(parents=True, exist_ok=True)
            ass_path.parent.mkdir(parents=True, exist_ok=True)
            
            print(f"🎤📝 音声+ASS字幕同時生成中... (話者ID: {DEFAULT_SPEAKER})", file=sys.stderr)
            audio_result, ass_result = tts.generate_audio_with_ass_subtitle(
                script, str(audio_path), str(ass_path)
            )
            
            print(f"✅ 音声+ASS字幕生成完了!", file=sys.stderr)
            print(f"   音声ファイル: {audio_result}", file=sys.stderr)
            print(f"   ASS字幕ファイル: {ass_result}", file=sys.stderr)
            print(f"   台本タイトル: {script.title}", file=sys.stderr)
            print(f"   話者ID: {DEFAULT_SPEAKER}", file=sys.stderr)
            
        # 音声のみ生成
        elif args.output:
            print(f"🎤 VOICEVOX音声生成中... (話者ID: {DEFAULT_SPEAKER})", file=sys.stderr)
            
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            if script:
                result_path = tts.generate_audio_from_script(script, str(output_path))
                print(f"✅ 音声ファイルを生成しました: {result_path}", file=sys.stderr)
                print(f"   台本タイトル: {script.title}", file=sys.stderr)
            else:
                # 直接テキストから音声生成（簡易実装）
                from src.script_generator import VideoScript
                temp_script = VideoScript(title="直接テキスト", description=direct_text)
                result_path = tts.generate_audio_from_script(temp_script, str(output_path))
                print(f"✅ 音声ファイルを生成しました: {result_path}", file=sys.stderr)
            
            print(f"   話者ID: {DEFAULT_SPEAKER}", file=sys.stderr)
            
        else:
            # 情報表示のみ
            if script:
                print(f"✅ 台本準備完了!", file=sys.stderr)
                print(f"   台本タイトル: {script.title}", file=sys.stderr)
                print(f"   紹介文長: {len(script.description)}文字", file=sys.stderr)
            else:
                print(f"✅ テキスト準備完了!", file=sys.stderr)
                print(f"   テキスト長: {len(direct_text)}文字", file=sys.stderr)
            print("注意: --output または --ass-subtitle を指定すると生成が実行されます", file=sys.stderr)
        
    except FileNotFoundError as e:
        print(f"❌ ファイルエラー: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析エラー: {e}", file=sys.stderr)
        print("台本JSONファイルの形式を確認してください", file=sys.stderr)
        sys.exit(1)
    except ServerConnectionError as e:
        print(f"❌ VOICEVOX接続エラー: {e}", file=sys.stderr)
        print(f"VOICEVOXエンジンが起動しているか確認してください (URL: {DEFAULT_SERVER})", file=sys.stderr)
        sys.exit(1)
    except (AudioGenerationError, VoiceVoxError) as e:
        print(f"❌ 音声生成エラー: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ 予期しないエラー: {e}", file=sys.stderr)
        sys.exit(1)