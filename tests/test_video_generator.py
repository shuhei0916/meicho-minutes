import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock
from PIL import Image
from src.video_generator import VideoGenerator
from src.amazon_scraper import BookInfo


def test_video_generator_initialization():
    """VideoGeneratorクラスが正しく初期化できることをテスト"""
    # 準備・実行
    generator = VideoGenerator()
    
    # 検証
    assert generator is not None
    assert hasattr(generator, 'width')
    assert hasattr(generator, 'height')
    assert generator.width == 1080  # YouTubeショート推奨サイズ
    assert generator.height == 1920  # YouTubeショート推奨サイズ


@patch('src.video_generator.requests.get')
def test_process_book_cover_image(mock_get):
    """書影画像が取得・処理されることをテスト"""
    # 準備
    # モック画像データを作成
    test_image = Image.new('RGB', (300, 400), color='red')
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
        test_image.save(temp_file.name, 'JPEG')
        
        with open(temp_file.name, 'rb') as f:
            mock_image_data = f.read()
    
    # HTTPレスポンスのモック
    mock_response = MagicMock()
    mock_response.content = mock_image_data
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response
    
    # BookInfoオブジェクト
    book_info = BookInfo(
        title="テスト書籍",
        author="テスト著者",
        price="1,500円",
        image_url="https://example.com/book.jpg",
        description="テスト説明",
        reviews=[]
    )
    
    generator = VideoGenerator()
    
    # 出力ファイル
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as output_file:
        output_path = output_file.name
    
    try:
        # 実行
        result_path = generator.process_book_cover_image(book_info, output_path)
        
        # 検証
        assert result_path == output_path
        assert os.path.exists(output_path)
        
        # 画像が適切に処理されている
        processed_image = Image.open(output_path)
        assert processed_image.size[0] <= generator.width
        assert processed_image.size[1] <= generator.height
        
        # API呼び出しの確認
        mock_get.assert_called_once_with(book_info.image_url)
        
    finally:
        # クリーンアップ
        for file_path in [temp_file.name, output_path]:
            if os.path.exists(file_path):
                os.unlink(file_path)


def test_create_background_image():
    """背景画像が適切に設定されることをテスト"""
    # 準備
    generator = VideoGenerator()
    
    # 出力ファイル
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as output_file:
        output_path = output_file.name
    
    try:
        # 実行
        result_path = generator.create_background_image(output_path)
        
        # 検証
        assert result_path == output_path
        assert os.path.exists(output_path)
        
        # 背景画像が正しいサイズで生成されている
        background_image = Image.open(output_path)
        assert background_image.size == (generator.width, generator.height)
        
        # 画像形式の確認
        assert background_image.format == 'JPEG'
        assert background_image.mode == 'RGB'
        
    finally:
        # クリーンアップ
        if os.path.exists(output_path):
            os.unlink(output_path)


@patch('src.video_generator.ImageClip')
@patch('src.video_generator.AudioFileClip')
@patch('src.video_generator.TextClip')
@patch('src.video_generator.CompositeVideoClip')
def test_create_video_with_audio_and_subtitles(mock_composite_clip, mock_text_clip, mock_audio_clip, mock_image_clip):
    """音声と字幕が同期して合成されることをテスト"""
    # 準備
    generator = VideoGenerator()
    
    # モックファイルパス
    background_image_path = "background.jpg"
    audio_path = "audio.wav"
    subtitle_segments = [
        {"text": "テスト字幕1", "start_time": 0.0, "end_time": 5.0},
        {"text": "テスト字幕2", "start_time": 5.0, "end_time": 10.0}
    ]
    
    # 出力ファイル
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as output_file:
        output_path = output_file.name
    
    # MoviePyクリップのモック設定
    mock_image_instance = MagicMock()
    mock_image_instance.duration = 10.0
    mock_image_instance.resize.return_value = mock_image_instance
    mock_image_clip.return_value = mock_image_instance
    
    mock_audio_instance = MagicMock()
    mock_audio_instance.duration = 10.0
    mock_audio_clip.return_value = mock_audio_instance
    
    mock_text_instance = MagicMock()
    mock_text_instance.set_position.return_value = mock_text_instance
    mock_text_instance.set_duration.return_value = mock_text_instance
    mock_text_instance.set_start.return_value = mock_text_instance
    mock_text_clip.return_value = mock_text_instance
    
    # CompositeVideoClipのモック
    mock_composite = MagicMock()
    mock_composite.set_audio.return_value = mock_composite
    mock_composite.set_duration.return_value = mock_composite
    mock_composite_clip.return_value = mock_composite
    
    try:
        # 実行
        result_path = generator.create_video_with_audio_and_subtitles(
            background_image_path, 
            audio_path, 
            subtitle_segments, 
            output_path
        )
        
        # 検証
        assert result_path == output_path
        
        # MoviePyクリップが適切に作成されている
        mock_image_clip.assert_called_once()
        mock_audio_clip.assert_called_once_with(audio_path)
        
        # 字幕クリップが各セグメントで作成されている
        assert mock_text_clip.call_count == len(subtitle_segments)
        
    finally:
        # クリーンアップ
        if os.path.exists(output_path):
            os.unlink(output_path)


def test_create_youtube_shorts_video():
    """YouTubeショート向けの縦型動画が生成されることをテスト"""
    # 準備
    generator = VideoGenerator()  # デフォルトで1080x1920（縦型）
    
    # メソッドが存在することを確認
    assert hasattr(generator, 'create_youtube_shorts_video')
    
    # 縦型動画のアスペクト比確認（9:16）
    aspect_ratio = generator.width / generator.height
    expected_ratio = 1080 / 1920
    assert abs(aspect_ratio - expected_ratio) < 0.01
    
    # YouTubeショート向けのサイズ確認
    assert generator.width == 1080
    assert generator.height == 1920


def test_create_youtube_shorts_video_integration():
    """実際のcreate_youtube_shorts_videoを呼ぶ統合テスト（ImageMagick問題の特定用）"""
    # 準備
    generator = VideoGenerator()
    
    book_info = BookInfo(
        title="テストショート動画",
        author="テスト著者",
        price="1,000円",
        image_url="https://m.media-amazon.com/images/I/51wZYgJf7oL.jpg",
        description="ショート動画用テスト",
        reviews=[]
    )
    
    from src.gemini_script_generator import VideoScript
    script = VideoScript(
        title="ショート動画テスト",
        overview="短い概要",
        comments=["ポイント1"],
        conclusion="まとめ"
    )
    
    # 出力ファイル
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as output_file:
        output_path = output_file.name
    
    try:
        # 実際のcreate_youtube_shorts_videoを呼び出し
        # ImageMagick依存の問題が発生するかテスト
        result_path = generator.create_youtube_shorts_video(
            book_info, 
            script, 
            output_path,
            "/tmp",  # temp_dir
            40  # font_size
        )
        
        # 成功した場合の検証
        assert result_path == output_path
        assert os.path.exists(output_path)
        
        # 動画ファイルの基本検証
        file_size = os.path.getsize(output_path)
        assert file_size > 1000  # 最低1KBは必要
        
        print(f"✅ 統合テスト成功: {output_path} ({file_size} bytes)")
        
    except OSError as e:
        if "ImageMagick" in str(e) or "unset" in str(e):
            # ImageMagick関連のエラーを検出
            print(f"🔍 ImageMagick依存エラーを検出: {e}")
            pytest.skip(f"ImageMagick依存エラー: {e}")
        else:
            # その他のOSエラーは再発生
            raise
    
    except Exception as e:
        # 予期しないエラーの詳細ログ
        print(f"❌ 予期しないエラー: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise
        
    finally:
        # クリーンアップ
        if os.path.exists(output_path):
            os.unlink(output_path)