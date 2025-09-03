import pytest
from unittest.mock import patch, MagicMock
from src.gemini_script_generator import GeminiScriptGenerator, VideoScript, GeminiScriptGeneratorError
from src.amazon_scraper import BookInfo, Review


def test_video_script_creation():
    """VideoScriptオブジェクトの作成と変換をテスト"""
    # 準備
    script = VideoScript(
        title="テスト動画タイトル",
        overview="これはテスト概要です",
        comments=["コメント1", "コメント2"],
        conclusion="締めの言葉です"
    )
    
    # 検証
    assert script.title == "テスト動画タイトル"
    assert len(script.comments) == 2
    
    # JSON変換テスト
    json_str = script.to_json()
    assert '"title": "テスト動画タイトル"' in json_str
    
    # テキスト変換テスト
    text_str = script.to_text()
    assert "【タイトル】" in text_str
    assert "【概要】" in text_str
    assert "【コメント1】" in text_str
    assert "【締め】" in text_str


def test_gemini_script_generator_initialization():
    """GeminiScriptGeneratorの初期化をテスト"""
    # API keyが無い場合のエラーテスト
    with patch('src.gemini_script_generator.config', return_value=''):
        with pytest.raises(GeminiScriptGeneratorError):
            GeminiScriptGenerator()
    
    # API keyがある場合の正常初期化テスト
    with patch('google.genai.Client') as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        generator = GeminiScriptGenerator(api_key="test_api_key")
        
        mock_client_class.assert_called_once_with(api_key="test_api_key")
        assert generator.client == mock_client


@patch('google.genai.Client')
def test_script_generation_from_book_info(mock_client_class):
    """書籍情報から台本生成をテスト"""
    # モックのセットアップ
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = """タイトル: 団塊世代の真実が衝撃すぎる...！
概要: 50年前に予言された日本の未来がまさに現実となっていた驚愕の書籍
コメント1: 著者の先見の明に鳥肌が立つ
コメント2: 現代の問題を予測していた
コメント3: レビューでも絶賛の嵐
締め: この予言書、今読まないと後悔します！"""
    
    mock_client.models.generate_content.return_value = mock_response
    mock_client_class.return_value = mock_client
    
    # テストデータの準備
    reviews = [
        Review(title="すごい本", text="とても参考になりました"),
        Review(title="面白い", text="読み応えがある内容でした")
    ]
    book_info = BookInfo(
        title="団塊の世代",
        author="堺屋太一",
        price="￥1000",
        description="団塊世代について書かれた本",
        rating="5つ星のうち4.0",
        reviews=reviews
    )
    
    # 実行
    generator = GeminiScriptGenerator(api_key="test_key")
    script = generator.generate_script_from_book_info(book_info)
    
    # 検証
    assert isinstance(script, VideoScript)
    assert script.title == "団塊世代の真実が衝撃すぎる...！"
    assert script.overview == "50年前に予言された日本の未来がまさに現実となっていた驚愕の書籍"
    assert len(script.comments) == 3
    assert script.comments[0] == "著者の先見の明に鳥肌が立つ"
    assert script.conclusion == "この予言書、今読まないと後悔します！"
    
    # Gemini APIが呼ばれたことを確認
    mock_client.models.generate_content.assert_called_once()
    
    # API呼び出しの引数を確認
    call_args = mock_client.models.generate_content.call_args
    assert call_args[1]['model'] == "gemini-2.5-flash"
    assert 'contents' in call_args[1]


@patch('google.genai.Client')
def test_script_generation_with_empty_response(mock_client_class):
    """空の応答に対するエラーハンドリングをテスト"""
    # モックのセットアップ（空の応答）
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = ""
    
    mock_client.models.generate_content.return_value = mock_response
    mock_client_class.return_value = mock_client
    
    # テストデータの準備
    book_info = BookInfo(title="テスト本")
    
    # 実行・検証
    generator = GeminiScriptGenerator(api_key="test_key")
    with pytest.raises(GeminiScriptGeneratorError):
        generator.generate_script_from_book_info(book_info)


@patch('google.genai.Client')
def test_script_generation_with_incomplete_response(mock_client_class):
    """不完全な応答に対するデフォルト値設定をテスト"""
    # モックのセットアップ（不完全な応答）
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "タイトル: テストタイトル\n概要: テスト概要"
    
    mock_client.models.generate_content.return_value = mock_response
    mock_client_class.return_value = mock_client
    
    # テストデータの準備
    book_info = BookInfo(
        title="テスト本",
        description="テスト説明"
    )
    
    # 実行
    generator = GeminiScriptGenerator(api_key="test_key")
    script = generator.generate_script_from_book_info(book_info)
    
    # 検証（デフォルト値が設定されていることを確認）
    assert script.title == "テストタイトル"
    assert script.overview == "テスト概要"
    assert len(script.comments) >= 1  # デフォルトのコメントが設定される
    assert script.conclusion  # デフォルトの締めが設定される


def test_prompt_creation():
    """プロンプト作成の内容をテスト"""
    with patch('google.genai.Client') as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        generator = GeminiScriptGenerator(api_key="test_key")
        
        book_info = BookInfo(
            title="テスト本",
            author="テスト著者",
            description="テスト説明"
        )
        
        prompt = generator._create_prompt(book_info, "テストレビュー")
        
        # プロンプトに必要な情報が含まれていることを確認
        assert "テスト本" in prompt
        assert "テスト著者" in prompt
        assert "テスト説明" in prompt
        assert "テストレビュー" in prompt
        assert "60秒程度" in prompt
        assert "【タイトル】" in prompt
        assert "【概要】" in prompt