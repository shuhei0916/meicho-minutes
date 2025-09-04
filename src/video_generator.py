import requests
from PIL import Image
from io import BytesIO
from typing import List, Dict
from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip, ImageClip
from src.amazon_scraper import BookInfo
from src.gemini_script_generator import VideoScript
from src.subtitle_generator import SubtitleGenerator


class VideoGenerator:
    """動画生成機能を提供するクラス"""
    
    def __init__(self, width: int = 1080, height: int = 1920):
        """
        VideoGeneratorを初期化
        
        Args:
            width: 動画の幅（デフォルト: 1080px、YouTubeショート推奨）
            height: 動画の高さ（デフォルト: 1920px、YouTubeショート推奨）
        """
        self.width = width
        self.height = height
    
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
    
    def create_video_with_audio_and_subtitles(
        self, 
        background_image_path: str, 
        audio_path: str, 
        subtitle_segments: List[Dict], 
        output_path: str
    ) -> str:
        """
        背景画像、音声、字幕を合成して動画を作成する
        
        Args:
            background_image_path: 背景画像ファイルパス
            audio_path: 音声ファイルパス
            subtitle_segments: 字幕セグメントのリスト
            output_path: 出力動画ファイルパス
            
        Returns:
            作成された動画ファイルのパス
        """
        # 音声クリップを読み込み
        audio_clip = AudioFileClip(audio_path)
        
        # 背景画像から動画クリップを作成
        video_clip = ImageClip(background_image_path, duration=audio_clip.duration)
        video_clip = video_clip.resize((self.width, self.height))
        
        # 字幕クリップを作成
        text_clips = []
        for segment in subtitle_segments:
            text_clip = TextClip(
                segment['text'],
                fontsize=40,
                color='white',
                font='Arial',
                size=(self.width * 0.8, None),
                method='caption'
            ).set_position(('center', 'bottom')).set_duration(
                segment['end_time'] - segment['start_time']
            ).set_start(segment['start_time'])
            
            text_clips.append(text_clip)
        
        # 全てのクリップを合成
        final_video = CompositeVideoClip([video_clip] + text_clips)
        final_video = final_video.set_audio(audio_clip)
        final_video = final_video.set_duration(audio_clip.duration)
        
        # 動画を出力
        final_video.write_videofile(
            output_path,
            fps=24,
            codec='libx264',
            audio_codec='aac',
            verbose=False,
            logger=None
        )
        
        # メモリ解放
        audio_clip.close()
        video_clip.close()
        final_video.close()
        for clip in text_clips:
            clip.close()
        
        return output_path
    
    def create_youtube_shorts_video(
        self, 
        book_info: BookInfo, 
        script: VideoScript, 
        output_path: str, 
        temp_dir: str = "/tmp"
    ) -> str:
        """
        書籍情報と台本からYouTubeショート向けの縦型動画を生成する
        
        Args:
            book_info: 書籍情報
            script: 動画台本
            output_path: 出力動画ファイルパス
            temp_dir: 一時ファイル用ディレクトリ
            
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
            
            # 4. 字幕を生成
            subtitle_generator = SubtitleGenerator()
            
            # 音声ファイルの長さを取得
            audio_clip = AudioFileClip(temp_audio)
            audio_duration = audio_clip.duration
            audio_clip.close()
            
            subtitle_segments = subtitle_generator.generate_subtitle_with_timing(script, audio_duration)
            
            # 5. 動画を合成
            result = self.create_video_with_audio_and_subtitles(
                temp_background,
                temp_audio, 
                subtitle_segments,
                output_path
            )
            
            return result
            
        finally:
            # 一時ファイルをクリーンアップ
            for temp_file in [temp_background, temp_cover, temp_audio]:
                if os.path.exists(temp_file):
                    try:
                        os.unlink(temp_file)
                    except:
                        pass  # ファイル削除エラーは無視