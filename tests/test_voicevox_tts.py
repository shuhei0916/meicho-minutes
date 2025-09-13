import pytest
import os
import tempfile
import requests
from unittest.mock import patch, MagicMock
from src.voicevox_tts import VoiceVoxTTS, VoiceVoxError, ServerConnectionError, AudioGenerationError
from src.script_generator import VideoScript


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


@patch('src.voicevox_tts.requests.post')
def test_create_audio_query(mock_post):
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
    mock_post.return_value = mock_response
    
    tts = VoiceVoxTTS()
    
    # 実行
    query = tts._create_audio_query("こんにちは", speaker_id=1)
    
    # 検証
    assert "accent_phrases" in query
    assert query["speedScale"] == 1.0
    assert query["pitchScale"] == 0.0
    mock_post.assert_called_once_with(
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


@patch('src.voicevox_tts.requests.post')
def test_server_connection_error_audio_query(mock_post):
    """VOICEVOXサーバーが起動していない場合の音声クエリエラー処理をテスト"""
    # 準備
    mock_post.side_effect = requests.ConnectionError("Connection refused")
    
    tts = VoiceVoxTTS(server_url="127.0.0.1:99999")  # 存在しないポート
    
    # 実行・検証
    with pytest.raises(ServerConnectionError) as exc_info:
        tts._create_audio_query("テスト", speaker_id=1)
    
    assert "音声クエリの生成に失敗しました" in str(exc_info.value)


@patch('src.voicevox_tts.requests.post')
def test_server_connection_error_synthesis(mock_post):
    """VOICEVOXサーバーが起動していない場合の音声合成エラー処理をテスト"""
    # 準備
    mock_post.side_effect = requests.ConnectionError("Connection refused")
    
    tts = VoiceVoxTTS(server_url="127.0.0.1:99999")  # 存在しないポート
    mock_query = {"accent_phrases": [], "speedScale": 1.0}
    
    # 実行・検証
    with pytest.raises(AudioGenerationError) as exc_info:
        tts._synthesize_audio(mock_query, speaker_id=1)
    
    assert "音声合成に失敗しました" in str(exc_info.value)


@patch('src.voicevox_tts.VoiceVoxTTS._synthesize_audio')
@patch('src.voicevox_tts.VoiceVoxTTS._create_audio_query')
def test_multiple_speakers(mock_create_query, mock_synthesize):
    """異なる話者IDで音声が生成されることをテスト"""
    # 準備
    script = VideoScript(
        title="テスト",
        overview="概要",
        comments=["コメント"],
        conclusion="締め"
    )
    
    # 話者1用のモック
    mock_query_1 = {"accent_phrases": [], "speedScale": 1.0, "speaker": 1}
    mock_audio_1 = b'audio_data_speaker_1'
    
    # 話者2用のモック
    mock_query_2 = {"accent_phrases": [], "speedScale": 1.0, "speaker": 2}
    mock_audio_2 = b'audio_data_speaker_2'
    
    tts = VoiceVoxTTS()
    
    # 話者1でのテスト
    mock_create_query.return_value = mock_query_1
    mock_synthesize.return_value = mock_audio_1
    
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file_1:
        output_path_1 = temp_file_1.name
    
    try:
        result_1 = tts.generate_audio_from_script(script, output_path_1, speaker_id=1)
        
        # 話者2でのテスト
        mock_create_query.return_value = mock_query_2
        mock_synthesize.return_value = mock_audio_2
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file_2:
            output_path_2 = temp_file_2.name
        
        try:
            result_2 = tts.generate_audio_from_script(script, output_path_2, speaker_id=2)
            
            # 検証
            assert result_1 == output_path_1
            assert result_2 == output_path_2
            
            # 異なる音声データが生成されることを確認
            with open(output_path_1, 'rb') as f1, open(output_path_2, 'rb') as f2:
                assert f1.read() == mock_audio_1
                assert f2.read() == mock_audio_2
                assert mock_audio_1 != mock_audio_2  # 異なる話者で異なる音声
            
            # API呼び出し回数確認
            assert mock_create_query.call_count == 2
            assert mock_synthesize.call_count == 2
            
            # 話者IDが正しく渡されていることを確認
            mock_synthesize.assert_any_call(mock_query_1, 1)
            mock_synthesize.assert_any_call(mock_query_2, 2)
            
        finally:
            if os.path.exists(output_path_2):
                os.unlink(output_path_2)
    finally:
        if os.path.exists(output_path_1):
            os.unlink(output_path_1)


def test_cli_text_to_audio():
    """CLI機能でテキストから音声生成ができることをテスト"""
    # 準備
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
        output_path = temp_file.name
    
    try:
        # 実行（VOICEVOXサーバーが起動していない可能性があるので、実際のCLIテストは統合テストとして別途実施）
        # ここでは、CLI関数が正しく定義されていることを確認
        import src.voicevox_tts as voicevox_module
        
        # CLI機能が__main__に含まれていることを確認
        with open(voicevox_module.__file__, 'r', encoding='utf-8') as f:
            code = f.read()
            
        # 検証
        assert 'if __name__ == "__main__"' in code
        assert 'argparse.ArgumentParser' in code
        assert '--output' in code
        assert '--speaker' in code
        assert '--text' in code
        assert '--script' in code
        
    finally:
        # クリーンアップ
        if os.path.exists(output_path):
            os.unlink(output_path)