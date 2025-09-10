import os
import tempfile
from PIL import Image
from typing import List, Dict
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeVideoClip, ImageClip
from src.subtitle_image_generator import SubtitleImageGenerator, SubtitleStyle


class VideoGenerator:
    """音声と字幕情報から動画を生成する純粋ライブラリ"""
    
    # デフォルト設定（ハードコーディング）
    DEFAULT_SETTINGS = {
        'subtitle': {
            'font_size': 64,                    # 字幕フォントサイズ（ピクセル）
            'font_color': (255, 255, 255),      # 字幕色（RGB: 白）
            'background_color': (0, 0, 0, 140), # 字幕背景色（RGBA: 半透明黒）
            'outline_color': (0, 0, 0),         # 文字縁取り色（RGB: 黒）
            'outline_width': 3,                 # 縁取りの太さ（ピクセル）
            'margin': 60,                       # 画面端からの余白（ピクセル）
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
            width: 動画の幅（デフォルト: 1080 - YouTubeショーツ）
            height: 動画の高さ（デフォルト: 1920 - YouTubeショーツ）
        """
        self.width = width
        self.height = height
        
        # 字幕画像生成器を初期化
        self.subtitle_image_generator = SubtitleImageGenerator(width, height)
        
        # デフォルト設定からスタイルオブジェクトを作成
        self.default_subtitle_style = SubtitleStyle(
            font_size=self.DEFAULT_SETTINGS['subtitle']['font_size'],
            font_color=self.DEFAULT_SETTINGS['subtitle']['font_color'],
            background_color=self.DEFAULT_SETTINGS['subtitle']['background_color'],
            outline_color=self.DEFAULT_SETTINGS['subtitle']['outline_color'],
            outline_width=self.DEFAULT_SETTINGS['subtitle']['outline_width'],
            margin=self.DEFAULT_SETTINGS['subtitle']['margin'],
            line_spacing=self.DEFAULT_SETTINGS['subtitle']['line_spacing'],
            max_width_ratio=self.DEFAULT_SETTINGS['subtitle']['max_width_ratio']
        )
        
        self.default_video_settings = self.DEFAULT_SETTINGS['video']
    
    
    def create_video(
        self, 
        audio_path: str, 
        subtitle_segments: List[Dict], 
        output_path: str,
        subtitle_style: SubtitleStyle = None
    ) -> str:
        """
        音声、字幕から動画を作成する（背景色はデフォルト設定を使用）
        
        Args:
            audio_path: 音声ファイルパス
            subtitle_segments: 字幕セグメントのリスト [{"text": str, "start_time": float, "end_time": float}, ...]
            output_path: 出力動画ファイルパス
            subtitle_style: 字幕スタイル設定
            
        Returns:
            作成された動画ファイルのパス
        """
        if subtitle_style is None:
            subtitle_style = self.default_subtitle_style
        
        # 音声クリップを読み込み
        audio_clip = AudioFileClip(audio_path)
        
        # 背景画像をインラインで作成（デフォルト設定使用）
        background_color = self.default_video_settings['background_color']
        background_image = Image.new('RGB', (self.width, self.height), background_color)
        
        # 一時的に背景画像を保存
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_bg:
            background_image.save(tmp_bg.name, 'JPEG')
            temp_bg_path = tmp_bg.name
        
        try:
            # 背景画像から動画クリップを作成
            video_clip = ImageClip(temp_bg_path, duration=audio_clip.duration)
            video_clip = video_clip.resize((self.width, self.height))
            
            clips = [video_clip]
            temp_subtitle_paths = []
            
            # 字幕セグメントから字幕クリップを作成
            for segment in subtitle_segments:
                # 字幕画像をPILで直接作成（一時ファイル保存なし）
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_sub:
                    subtitle_image_path = self.subtitle_image_generator.create_subtitle_image(
                        segment["text"], 
                        subtitle_style,
                        tmp_sub.name
                    )
                    temp_subtitle_paths.append(subtitle_image_path)
                
                # 字幕クリップを作成
                subtitle_clip = ImageClip(subtitle_image_path)
                subtitle_clip = subtitle_clip.set_position(('center', 'bottom'))
                subtitle_clip = subtitle_clip.set_duration(
                    segment["end_time"] - segment["start_time"]
                )
                subtitle_clip = subtitle_clip.set_start(segment["start_time"])
                
                clips.append(subtitle_clip)
            
            # 全てのクリップを合成
            final_video = CompositeVideoClip(clips)
            final_video = final_video.set_audio(audio_clip)
            final_video = final_video.set_duration(audio_clip.duration)
            
            # 動画を出力
            final_video.write_videofile(
                output_path,
                fps=self.default_video_settings['fps'],
                codec=self.default_video_settings['codec'],
                audio_codec=self.default_video_settings['audio_codec'],
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
            # 一時ファイルをクリーンアップ
            if os.path.exists(temp_bg_path):
                os.unlink(temp_bg_path)
            
            for temp_path in temp_subtitle_paths:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)


if __name__ == "__main__":
    import sys
    import json
    import argparse
    
    parser = argparse.ArgumentParser(description='純粋動画生成ライブラリ')
    parser.add_argument('--demo', action='store_true', help='デモ動画を生成')
    parser.add_argument('--script-json', type=str, help='JSONスクリプトファイルパス')
    parser.add_argument('--output', type=str, required=True, help='出力動画ファイルパス')
    
    args = parser.parse_args()
    
    try:
        generator = VideoGenerator()
        
        if args.demo:
            # デモ動画生成
            print("=== デモ動画生成 ===")
            
            # 注意: 背景色はデフォルト設定で自動設定されます
            
            # デモ用の字幕セグメント
            demo_segments = [
                {"text": "これはデモ動画です", "start_time": 0.0, "end_time": 2.0},
                {"text": "字幕付きの動画生成をテストしています", "start_time": 2.0, "end_time": 5.0},
                {"text": "VideoGeneratorライブラリのテスト完了！", "start_time": 5.0, "end_time": 8.0}
            ]
            
            # デモ音声ファイルが必要（実際の使用では外部で用意）
            print("注意: 音声ファイルが必要です。実際の使用では音声ファイルパスを指定してください。")
            print("デモではスキップしました。")
            
        elif args.script_json:
            # JSONファイルから台本を読み込んで動画生成
            with open(args.script_json, 'r', encoding='utf-8') as f:
                script_data = json.load(f)
            
            print(f"JSONスクリプトから動画生成中: {args.script_json}")
            print("注意: 実際の使用では背景画像、音声ファイル、字幕セグメントを外部で準備してください。")
            
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
            sys.exit(1)
    
    except Exception as e:
        print(f"エラー: 動画生成中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)