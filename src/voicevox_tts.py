import requests
import os
import json
from typing import Dict, Optional

# VideoScriptクラスのインポート（モジュール実行時の互換性対応）
try:
    from src.gemini_script_generator import VideoScript
except ImportError:
    from gemini_script_generator import VideoScript


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
    
    args = parser.parse_args()
    
    # ハードコーディングされた設定
    DEFAULT_SERVER = "127.0.0.1:50021"
    DEFAULT_SPEAKER = 13
    DEFAULT_SPEED = 1.2  # 標準スピード
    
    try:
        # VoiceVoxTTSを初期化
        tts = VoiceVoxTTS(server_url=DEFAULT_SERVER, speaker_id=DEFAULT_SPEAKER, speed_scale=DEFAULT_SPEED)
        
        # 台本データの準備
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
                overview=script_data['overview'],
                comments=script_data['comments'],
                conclusion=script_data['conclusion']
            )
            
            print(f"📜 台本を読み込み: {script_path}", file=sys.stderr)
        else:
            # デフォルト台本データを使用
            script = VideoScript(
                title="【衝撃】50年前に日本の未来を予言した伝説の書がヤバすぎた…！",
                overview="半世紀前に日本の未来を予言した伝説の名著。今まさに直面する社会問題のヒントがここに。",
                comments=[
                    "50年前の描写が今の日本に刺さりまくる",
                    "働き方、人間関係の普遍的ヒントが満載",
                    "この国が迎える未来をすでに予言していた"
                ],
                conclusion="この\"予言書\"を読んで、未来を生き抜くヒントを見つけよう！"
            )
            print("📜 デフォルト台本データを使用", file=sys.stderr)
        
        # 音声生成
        if args.output:
            print(f"🎤 VOICEVOX音声生成中... (話者ID: {DEFAULT_SPEAKER})", file=sys.stderr)
            
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            result_path = tts.generate_audio_from_script(script, str(output_path))
            
            print(f"✅ 音声ファイルを生成しました: {result_path}", file=sys.stderr)
            print(f"   台本タイトル: {script.title}", file=sys.stderr)
            print(f"   話者ID: {DEFAULT_SPEAKER}", file=sys.stderr)
        else:
            # 出力ファイルが指定されていない場合はテキスト表示のみ
            print(f"✅ 台本準備完了!", file=sys.stderr)
            print(f"   台本タイトル: {script.title}", file=sys.stderr)
            print(f"   コメント数: {len(script.comments)}", file=sys.stderr)
            print("注意: --output を指定すると音声ファイルが生成されます", file=sys.stderr)
        
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