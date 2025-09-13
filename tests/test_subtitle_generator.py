import pytest
from src.subtitle_generator import SubtitleGenerator
from src.script_generator import VideoScript


def test_subtitle_generator_initialization():
    """SubtitleGeneratorクラスが正しく初期化できることをテスト"""
    # 準備・実行
    generator = SubtitleGenerator()
    
    # 検証
    assert generator is not None


def test_generate_subtitle_text_from_script():
    """台本から字幕用テキストが生成されることをテスト"""
    # 準備
    script = VideoScript(
        title="テストタイトル",
        overview="これは本の概要です",
        comments=["重要なポイント1", "重要なポイント2"],
        conclusion="まとめの文章です"
    )
    generator = SubtitleGenerator()
    
    # 実行
    subtitle_text = generator.generate_subtitle_text(script)
    
    # 検証
    assert isinstance(subtitle_text, str)
    assert len(subtitle_text) > 0
    assert "テストタイトル" in subtitle_text
    assert "これは本の概要です" in subtitle_text
    assert "重要なポイント1" in subtitle_text
    assert "まとめの文章です" in subtitle_text


def test_generate_subtitle_with_timing():
    """字幕のタイミング情報が適切に設定されることをテスト"""
    # 準備
    script = VideoScript(
        title="短いタイトル",
        overview="短い概要",
        comments=["短いコメント"],
        conclusion="短いまとめ"
    )
    generator = SubtitleGenerator()
    audio_duration = 60.0  # 60秒の音声
    
    # 実行
    subtitle_with_timing = generator.generate_subtitle_with_timing(script, audio_duration)
    
    # 検証
    assert isinstance(subtitle_with_timing, list)
    assert len(subtitle_with_timing) > 0
    
    # 各字幕セグメントの検証
    for segment in subtitle_with_timing:
        assert "text" in segment
        assert "start_time" in segment
        assert "end_time" in segment
        assert isinstance(segment["start_time"], float)
        assert isinstance(segment["end_time"], float)
        assert segment["start_time"] >= 0
        assert segment["end_time"] <= audio_duration
        assert segment["start_time"] < segment["end_time"]


def test_format_text_with_line_breaks():
    """文字数制限に応じた改行処理が行われることをテスト"""
    # 準備
    generator = SubtitleGenerator()
    long_text = "これは非常に長い文章で、字幕として表示する際には適切な位置で改行する必要があります。文字数制限を超える場合は自動的に改行されるべきです。"
    max_chars_per_line = 20
    
    # 実行
    formatted_text = generator.format_text_with_line_breaks(long_text, max_chars_per_line)
    
    # 検証
    lines = formatted_text.split('\n')
    assert len(lines) > 1  # 複数行に分割されている
    
    # 各行の文字数チェック
    for line in lines:
        assert len(line) <= max_chars_per_line
    
    # 元のテキストの内容が保持されている
    reconstructed_text = formatted_text.replace('\n', '')
    assert reconstructed_text == long_text


def test_escape_special_characters():
    """特殊文字の適切なエスケープが行われることをテスト"""
    # 準備
    generator = SubtitleGenerator()
    text_with_special_chars = 'これは"特殊"文字<>を&含むテキストです'
    
    # 実行
    escaped_text = generator.escape_special_characters(text_with_special_chars)
    
    # 検証
    assert '"' not in escaped_text
    assert '<' not in escaped_text
    assert '>' not in escaped_text
    
    # エスケープされた文字が正しく変換されている
    assert '&quot;' in escaped_text  # "
    assert '&lt;' in escaped_text  # <
    assert '&gt;' in escaped_text  # >
    assert '&amp;' in escaped_text  # &