import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock
from src.voicevox_tts import VoiceVoxTTS, VoiceVoxError, ServerConnectionError, AudioGenerationError
from src.gemini_script_generator import VideoScript


def test_voicevox_tts_initialization():
    """VoiceVoxTTSクラスが正しく初期化できることをテスト"""
    # 準備・実行
    tts = VoiceVoxTTS(server_url="127.0.0.1:50021", speaker_id=1)
    
    # 検証
    assert tts.server_url == "127.0.0.1:50021"
    assert tts.speaker_id == 1


def test_voicevox_tts_default_initialization():
    """VoiceVoxTTSクラスがデフォルト値で初期化できることをテスト"""
    # 準備・実行
    tts = VoiceVoxTTS()
    
    # 検証
    assert tts.server_url == "127.0.0.1:50021"
    assert tts.speaker_id == 1


@patch('src.voicevox_tts.requests.get')
def test_create_audio_query(mock_get):
    """テキストから音声クエリが正しく生成されることをテスト"""
    # 準備
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "accent_phrases": [
            {
                "moras": [{"text": "コ", "vowel": "o", "pitch": 5.5}],
                "accent": 1
            }
        ],
        "speedScale": 1.0,
        "pitchScale": 0.0,
        "intonationScale": 1.0
    }
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response
    
    tts = VoiceVoxTTS()
    
    # 実行
    query = tts._create_audio_query("こんにちは", speaker_id=1)
    
    # 検証
    assert "accent_phrases" in query
    assert query["speedScale"] == 1.0
    assert query["pitchScale"] == 0.0
    mock_get.assert_called_once_with(
        "http://127.0.0.1:50021/audio_query",
        params={"text": "こんにちは", "speaker": 1}
    )


@patch('src.voicevox_tts.requests.post')
def test_synthesize_audio(mock_post):
    """音声クエリから.wavファイルが生成されることをテスト"""
    # 準備
    mock_response = MagicMock()
    mock_response.content = b'fake_wav_data_here'
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response
    
    tts = VoiceVoxTTS()
    mock_query = {
        "accent_phrases": [{"moras": [{"text": "テ", "vowel": "e"}]}],
        "speedScale": 1.0
    }
    
    # 実行
    audio_data = tts._synthesize_audio(mock_query, speaker_id=1)
    
    # 検証
    assert isinstance(audio_data, bytes)
    assert audio_data == b'fake_wav_data_here'
    mock_post.assert_called_once_with(
        "http://127.0.0.1:50021/synthesis",
        json=mock_query,
        params={"speaker": 1}
    )


@patch('src.voicevox_tts.VoiceVoxTTS._synthesize_audio')
@patch('src.voicevox_tts.VoiceVoxTTS._create_audio_query')
def test_generate_audio_from_script(mock_create_query, mock_synthesize):
    """VideoScriptから音声ファイルが生成されることをテスト"""
    # 準備
    script = VideoScript(
        title="テストタイトル",
        overview="テスト概要",
        comments=["コメント1", "コメント2"],
        conclusion="テスト締め"
    )
    
    mock_query = {"accent_phrases": [], "speedScale": 1.0}
    mock_audio_data = b'fake_wav_audio_data'
    
    mock_create_query.return_value = mock_query
    mock_synthesize.return_value = mock_audio_data
    
    tts = VoiceVoxTTS()
    
    # 一時ファイルで出力先を指定
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
        output_path = temp_file.name
    
    try:
        # 実行
        result_path = tts.generate_audio_from_script(script, output_path)
        
        # 検証
        assert result_path == output_path
        assert os.path.exists(output_path)
        
        # ファイル内容の確認
        with open(output_path, 'rb') as f:
            assert f.read() == mock_audio_data
        
        # API呼び出しの確認
        mock_create_query.assert_called_once()
        mock_synthesize.assert_called_once_with(mock_query, 1)
        
    finally:
        # クリーンアップ
        if os.path.exists(output_path):
            os.unlink(output_path)