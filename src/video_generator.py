import requests
import os
from PIL import Image
from io import BytesIO
from typing import List, Dict
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeVideoClip, ImageClip
from src.amazon_scraper import BookInfo
from src.gemini_script_generator import VideoScript
# from src.subtitle_generator import SubtitleGenerator  # 依存関係問題を回避するためコメントアウト
from src.subtitle_image_generator import SubtitleImageGenerator, SubtitleStyle


class VideoGenerator:
    """動画生成機能を提供するクラス"""
    
    # デフォルト設定（ハードコーディング）
    DEFAULT_SETTINGS = {
        'subtitle': {
            'font_size': 45,                    # 字幕フォントサイズ（ピクセル）
            'font_color': (255, 255, 255),      # 字幕色（RGB: 白）
            'background_color': (0, 0, 0, 140), # 字幕背景色（RGBA: 半透明黒）
            'outline_color': (0, 0, 0),         # 文字縁取り色（RGB: 黒）
            'outline_width': 3,                 # 縁取りの太さ（ピクセル）
            'margin': 25,                       # 画面端からの余白（ピクセル）
            'line_spacing': 8,                  # 行間のスペース（ピクセル）
            'max_width_ratio': 0.85             # 画面幅に対する字幕最大幅の比率
        },
        'video': {
            'background_color': (25, 25, 112),  # ネイビーブルー
            'fps': 24,
            'codec': 'libx264',
            'audio_codec': 'aac'
        }
    }
    
    def __init__(self, width: int = 1080, height: int = 1920):
        """
        VideoGeneratorを初期化
        
        Args:
            width: 動画の幅（デフォルト: 1080px、YouTubeショート推奨）
            height: 動画の高さ（デフォルト: 1920px、YouTubeショート推奨）
        """
        self.width = width
        self.height = height
        self.subtitle_image_generator = SubtitleImageGenerator(width, height)
        
        # デフォルト字幕スタイルを作成
        subtitle_config = self.DEFAULT_SETTINGS['subtitle']
        self.default_subtitle_style = SubtitleStyle(
            font_size=subtitle_config['font_size'],
            font_color=subtitle_config['font_color'],
            background_color=subtitle_config['background_color'],
            outline_color=subtitle_config['outline_color'],
            outline_width=subtitle_config['outline_width'],
            margin=subtitle_config['margin'],
            line_spacing=subtitle_config['line_spacing'],
            max_width_ratio=subtitle_config['max_width_ratio']
        )
    
    def process_book_cover_image(self, book_info: BookInfo, output_path: str) -> str:
        """
        書影画像を取得し、動画用に処理する
        
        Args:
            book_info: 書籍情報
            output_path: 出力ファイルパス
            
        Returns:
            処理された画像ファイルのパス
        """
        # 画像をダウンロード
        response = requests.get(book_info.image_url)
        response.raise_for_status()
        
        # PILで画像を開く
        image = Image.open(BytesIO(response.content))
        
        # 動画サイズに合わせてリサイズ（アスペクト比を保持）
        image.thumbnail((self.width, self.height), Image.Resampling.LANCZOS)
        
        # RGB形式に変換（JPEG保存のため）
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # 保存
        image.save(output_path, 'JPEG')
        
        return output_path
    
    def create_background_image(self, output_path: str, color: tuple = (25, 25, 112)) -> str:
        """
        背景画像を作成する
        
        Args:
            output_path: 出力ファイルパス
            color: 背景色（RGB）デフォルトはダークブルー
            
        Returns:
            作成された背景画像ファイルのパス
        """
        # 指定サイズの背景画像を作成
        background = Image.new('RGB', (self.width, self.height), color)
        
        # 保存
        background.save(output_path, 'JPEG')
        
        return output_path
    
    def create_video_with_pil_subtitles(
        self, 
        background_image_path: str, 
        audio_path: str, 
        subtitle_segments: List[Dict], 
        output_path: str,
        subtitle_style: SubtitleStyle = None,
        temp_dir: str = "/tmp"
    ) -> str:
        """
        PIL字幕を使用して動画を作成する（ImageMagick依存を回避）
        
        Args:
            background_image_path: 背景画像ファイルパス
            audio_path: 音声ファイルパス
            subtitle_segments: 字幕セグメントのリスト
            output_path: 出力動画ファイルパス
            subtitle_style: 字幕スタイル設定
            temp_dir: 一時ファイルディレクトリ
            
        Returns:
            作成された動画ファイルのパス
        """
        if subtitle_style is None:
            subtitle_style = SubtitleStyle(font_size=40)
        
        # 音声クリップを読み込み
        audio_clip = AudioFileClip(audio_path)
        
        # 背景画像から動画クリップを作成
        video_clip = ImageClip(background_image_path, duration=audio_clip.duration)
        video_clip = video_clip.resize((self.width, self.height))
        
        clips = [video_clip]
        temp_subtitle_files = []
        
        try:
            # PIL字幕画像を生成
            subtitle_images = self.subtitle_image_generator.create_subtitle_images_from_segments(
                subtitle_segments, 
                subtitle_style, 
                temp_dir
            )
            
            # 字幕画像をImageClipとして追加
            for subtitle_info in subtitle_images:
                temp_subtitle_files.append(subtitle_info["image_path"])
                
                subtitle_clip = ImageClip(subtitle_info["image_path"])
                subtitle_clip = subtitle_clip.set_position(('center', 'bottom'))
                subtitle_clip = subtitle_clip.set_duration(
                    subtitle_info["end_time"] - subtitle_info["start_time"]
                )
                subtitle_clip = subtitle_clip.set_start(subtitle_info["start_time"])
                
                clips.append(subtitle_clip)
            
            # 全てのクリップを合成
            final_video = CompositeVideoClip(clips)
            final_video = final_video.set_audio(audio_clip)
            final_video = final_video.set_duration(audio_clip.duration)
            
            # 動画を出力
            temp_audiofile = os.path.join(temp_dir, f"temp_audio_{os.getpid()}.m4a")
            final_video.write_videofile(
                output_path,
                fps=24,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile=temp_audiofile,
                verbose=False,
                logger=None
            )
            
            # メモリ解放
            audio_clip.close()
            video_clip.close()
            final_video.close()
            
            for clip in clips[1:]:  # 背景以外のクリップを解放
                clip.close()
            
            return output_path
            
        finally:
            # 一時字幕ファイルをクリーンアップ
            for temp_file in temp_subtitle_files:
                if os.path.exists(temp_file):
                    try:
                        os.unlink(temp_file)
                    except:
                        pass  # ファイル削除エラーは無視
    
    def create_video_without_subtitles(
        self, 
        background_image_path: str, 
        audio_path: str, 
        output_path: str
    ) -> str:
        """
        字幕なしで動画を作成する（フォールバック機能）
        
        Args:
            background_image_path: 背景画像ファイルパス
            audio_path: 音声ファイルパス
            output_path: 出力動画ファイルパス
            
        Returns:
            作成された動画ファイルのパス
        """
        # 音声クリップを読み込み
        audio_clip = AudioFileClip(audio_path)
        
        # 背景画像から動画クリップを作成
        video_clip = ImageClip(background_image_path, duration=audio_clip.duration)
        video_clip = video_clip.resize((self.width, self.height))
        
        # 音声付きの動画を作成
        final_video = video_clip.set_audio(audio_clip)
        
        # 動画を出力  
        temp_audiofile = os.path.join("/tmp", f"temp_audio_simple_{os.getpid()}.m4a")
        final_video.write_videofile(
            output_path,
            fps=24,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile=temp_audiofile,
            verbose=False,
            logger=None
        )
        
        # メモリ解放
        audio_clip.close()
        video_clip.close()
        final_video.close()
        
        return output_path
    
    def create_youtube_shorts_video(
        self, 
        book_info: BookInfo, 
        script, # VideoScript型だが依存関係を避けるため型ヒント省略
        output_path: str, 
        temp_dir: str = "/tmp",
        subtitle_style: SubtitleStyle = None,
        enable_subtitles: bool = True
    ) -> str:
        """
        書籍情報と台本からYouTubeショート向けの縦型動画を生成する（v2対応）
        
        Args:
            book_info: 書籍情報
            script: 動画台本
            output_path: 出力動画ファイルパス
            temp_dir: 一時ファイル用ディレクトリ
            subtitle_style: 字幕スタイル設定
            enable_subtitles: 字幕を有効にするか
            
        Returns:
            作成された動画ファイルのパス
        """
        import tempfile
        import os
        from src.voicevox_tts import VoiceVoxTTS
        
        # 一時ファイル用のパスを作成
        temp_background = os.path.join(temp_dir, f"background_{os.getpid()}.jpg")
        temp_cover = os.path.join(temp_dir, f"cover_{os.getpid()}.jpg") 
        temp_audio = os.path.join(temp_dir, f"audio_{os.getpid()}.wav")
        
        try:
            # 1. 背景画像を作成
            self.create_background_image(temp_background)
            
            # 2. 書影画像を取得・処理
            if book_info.image_url:
                self.process_book_cover_image(book_info, temp_cover)
            
            # 3. 音声を生成（VoiceVoxTTS使用）
            tts = VoiceVoxTTS()
            tts.generate_audio_from_script(script, temp_audio)
            
            if enable_subtitles:
                # 4. PIL字幕付き動画を生成
                try:
                    from src.subtitle_generator import SubtitleGenerator
                    subtitle_generator = SubtitleGenerator()
                    
                    # 音声ファイルの長さを取得
                    audio_clip = AudioFileClip(temp_audio)
                    audio_duration = audio_clip.duration
                    audio_clip.close()
                    
                    subtitle_segments = subtitle_generator.generate_subtitle_with_timing(script, audio_duration)
                    
                    # PIL字幕付き動画を作成
                    result = self.create_video_with_pil_subtitles(
                        temp_background,
                        temp_audio, 
                        subtitle_segments,
                        output_path,
                        subtitle_style,
                        temp_dir
                    )
                    
                    return result
                    
                except Exception as e:
                    print(f"⚠️ 字幕付き動画生成に失敗、字幕なしにフォールバック: {e}")
                    
                    # フォールバックとして字幕なし動画を生成
                    return self.create_video_without_subtitles(
                        temp_background,
                        temp_audio,
                        output_path
                    )
            else:
                # 5. 字幕なし動画を生成
                return self.create_video_without_subtitles(
                    temp_background,
                    temp_audio,
                    output_path
                )
            
        finally:
            # 一時ファイルをクリーンアップ
            for temp_file in [temp_background, temp_cover, temp_audio]:
                if os.path.exists(temp_file):
                    try:
                        os.unlink(temp_file)
                    except:
                        pass  # ファイル削除エラーは無視


if __name__ == "__main__":
    import sys
    import argparse
    import json
    import tempfile
    
    parser = argparse.ArgumentParser(description='独立した動画生成ツール')
    parser.add_argument('--demo', action='store_true', help='デモ動画を生成')
    parser.add_argument('--script-json', type=str, help='VideoScriptのJSONファイルから動画生成')
    parser.add_argument('--output', type=str, required=True, help='出力動画ファイルパス')
    
    args = parser.parse_args()
    
    try:
        generator = VideoGenerator()  # デフォルト設定を使用
        
        if args.demo:
            # デモ動画生成
            print("=== デモ動画生成 ===")
            
            # サンプル書籍情報
            sample_book = BookInfo(
                title="効率的な学習法マスターガイド",
                author="学習博士",
                price="1,980円",
                image_url="https://m.media-amazon.com/images/I/51wZYgJf7oL.jpg",
                description="短時間で効果的に学習する方法を詳しく解説した実践的ガイドブック。",
                reviews=[]
            )
            
            # サンプル台本
            sample_script = VideoScript(
                title="【必見】勉強効率が10倍アップする方法",
                overview="この本では科学的に証明された学習テクニックを紹介します。",
                comments=[
                    "ポモドーロテクニックで集中力アップ！",
                    "アクティブリコールで記憶定着率向上！",
                    "間隔反復学習で長期記憶に残る！"
                ],
                conclusion="継続的な実践で必ず結果が出ます。今すぐ始めましょう！"
            )
            
            print("サンプル動画を生成中...")
            # デフォルト設定を使用
            result_path = generator.create_youtube_shorts_video(sample_book, sample_script, args.output, "/tmp", generator.default_subtitle_style)
            print(f"✅ デモ動画生成完了: {result_path}")
            
            
        elif args.script_json:
            # JSONファイルから台本を読み込んで動画生成
            with open(args.script_json, 'r', encoding='utf-8') as f:
                script_data = json.load(f)
            
            script = VideoScript(
                title=script_data['title'],
                overview=script_data['overview'],
                comments=script_data['comments'],
                conclusion=script_data['conclusion']
            )
            
            # サンプル書籍情報
            sample_book = BookInfo(
                title=script.title,
                author="不明",
                price="価格不明",
                image_url="https://via.placeholder.com/300x400/4ECDC4/FFFFFF?text=Book+Cover",
                description=script.overview,
                reviews=[]
            )
            
            print(f"スクリプトファイルから動画生成中: {args.script_json}")
            result_path = generator.create_youtube_shorts_video(sample_book, script, args.output, "/tmp", generator.default_subtitle_style)
            print(f"✅ 動画生成完了: {result_path}")
            
            
        else:
            print("使用方法:")
            print("  --demo --output video.mp4                    : デモ動画生成")
            print("  --script-json script.json --output video.mp4 : JSONスクリプトから動画生成")
            print("\n設定:")
            print("  字幕・動画設定はコード内にハードコーディングされています")
            print("  設定変更は src/video_generator.py の DEFAULT_SETTINGS を編集してください")
            print("\n例:")
            print("  python src/video_generator.py --demo --output demo_video.mp4")
            print("  python src/video_generator.py --script-json script.json --output video.mp4")
            print("  python src/video_generator.py --test-components --output test")
            sys.exit(1)
    
    except Exception as e:
        print(f"エラー: 動画生成中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)