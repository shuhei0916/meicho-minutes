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
            response = requests.get(
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