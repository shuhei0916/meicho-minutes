import os
import tempfile
import re
from PIL import Image
from typing import List, Dict, Optional
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeVideoClip, ImageClip
from src.subtitle_image_generator import SubtitleImageGenerator, SubtitleStyle
from src.subtitle_timing_generator import SubtitleTimingGenerator


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
        
        # 字幕タイミング生成器を初期化
        self.subtitle_timing_generator = SubtitleTimingGenerator()
        
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
    
    def create_video_from_script_and_audio(
        self,
        script_text: str,
        audio_path: str,
        output_path: str,
        subtitle_style: SubtitleStyle = None
    ) -> str:
        """
        台本テキストと音声ファイルから動画を作成（字幕タイミング自動生成）
        
        Args:
            script_text: 台本テキスト
            audio_path: 音声ファイルパス  
            output_path: 出力動画ファイルパス
            subtitle_style: 字幕スタイル設定
            
        Returns:
            作成された動画ファイルのパス
        """
        # 字幕タイミングを自動生成
        subtitle_segments = self.subtitle_timing_generator.generate_subtitle_segments(
            script_text, audio_path
        )
        
        # 既存のcreate_videoメソッドを呼び出し
        return self.create_video(
            audio_path=audio_path,
            subtitle_segments=subtitle_segments,
            output_path=output_path,
            subtitle_style=subtitle_style
        )
    
    def parse_ass_subtitle_file(self, ass_file_path: str) -> List[Dict[str, any]]:
        """
        ASS字幕ファイルを解析して字幕セグメントを抽出
        
        Args:
            ass_file_path: ASS字幕ファイルのパス
            
        Returns:
            字幕セグメント [{"text": str, "start_time": float, "end_time": float}, ...]
        """
        if not os.path.exists(ass_file_path):
            raise FileNotFoundError(f"ASS字幕ファイルが見つかりません: {ass_file_path}")
        
        segments = []
        
        try:
            with open(ass_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Dialogueライン抽出
            dialogue_pattern = r'^Dialogue:\s*(\d+),([^,]+),([^,]+),([^,]+),[^,]*,[^,]*,[^,]*,[^,]*,(.+)$'
            
            for line in content.split('\n'):
                line = line.strip()
                if not line.startswith('Dialogue:'):
                    continue
                
                match = re.match(dialogue_pattern, line)
                if match:
                    layer, start_time_str, end_time_str, style, text = match.groups()
                    
                    # ASS時間形式をfloatに変換
                    start_time = self._parse_ass_time(start_time_str)
                    end_time = self._parse_ass_time(end_time_str)
                    
                    # テキストからASS形式のエスケープを除去
                    clean_text = text.replace('\\N', '\n').replace('\\n', '\n')
                    
                    segments.append({
                        "text": clean_text,
                        "start_time": start_time,
                        "end_time": end_time
                    })
            
            # 開始時間でソート
            segments.sort(key=lambda x: x["start_time"])
            
        except Exception as e:
            raise ValueError(f"ASS字幕ファイルの解析に失敗: {e}")
        
        return segments
    
    def _parse_ass_time(self, time_str: str) -> float:
        """
        ASS時間形式（H:MM:SS.CC）を秒数（float）に変換
        
        Args:
            time_str: ASS時間形式の文字列
            
        Returns:
            秒数（float）
        """
        # H:MM:SS.CC形式をパース
        time_pattern = r'^(\d+):(\d{2}):(\d{2})\.(\d{2})$'
        match = re.match(time_pattern, time_str.strip())
        
        if not match:
            raise ValueError(f"無効なASS時間形式: {time_str}")
        
        hours, minutes, seconds, centiseconds = map(int, match.groups())
        total_seconds = hours * 3600 + minutes * 60 + seconds + centiseconds / 100.0
        
        return total_seconds
    
    def create_video_from_ass_subtitle(
        self,
        audio_path: str,
        ass_subtitle_path: str, 
        output_path: str,
        subtitle_style: SubtitleStyle = None
    ) -> str:
        """
        音声ファイルとASS字幕ファイルから動画を作成
        
        Args:
            audio_path: 音声ファイルパス
            ass_subtitle_path: ASS字幕ファイルパス
            output_path: 出力動画ファイルパス
            subtitle_style: 字幕スタイル設定
            
        Returns:
            作成された動画ファイルのパス
        """
        # ASS字幕ファイルを解析
        subtitle_segments = self.parse_ass_subtitle_file(ass_subtitle_path)
        
        # 既存のcreate_videoメソッドを使用
        return self.create_video(
            audio_path=audio_path,
            subtitle_segments=subtitle_segments,
            output_path=output_path,
            subtitle_style=subtitle_style
        )


if __name__ == "__main__":
    import sys
    import json
    import argparse
    
    parser = argparse.ArgumentParser(description='純粋動画生成ライブラリ')
    parser.add_argument('--demo', action='store_true', help='デモ動画を生成')
    parser.add_argument('--script-json', type=str, help='JSONスクリプトファイルパス')
    parser.add_argument('--audio', type=str, help='音声ファイルパス')
    parser.add_argument('--ass-subtitle', type=str, help='ASS字幕ファイルパス')
    parser.add_argument('--output', type=str, help='出力動画ファイルパス')
    parser.add_argument('--no-subtitles', action='store_true', help='字幕なしで動画生成')
    parser.add_argument('--subtitle-test', action='store_true', help='字幕タイミングテストモード')
    
    args = parser.parse_args()
    
    # --subtitle-test以外では--outputが必要
    if not args.subtitle_test and not args.output:
        parser.error("--output は --subtitle-test モード以外では必須です")
    
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
            
        elif args.audio and args.ass_subtitle:
            # 音声ファイル+ASS字幕ファイルから動画生成
            from pathlib import Path
            
            audio_path = Path(args.audio)
            ass_path = Path(args.ass_subtitle)
            
            if not audio_path.exists():
                print(f"❌ エラー: 音声ファイルが見つかりません: {args.audio}")
                sys.exit(1)
            
            if not ass_path.exists():
                print(f"❌ エラー: ASS字幕ファイルが見つかりません: {args.ass_subtitle}")
                sys.exit(1)
            
            print(f"🎵 音声読み込み: {audio_path}")
            print(f"📝 ASS字幕読み込み: {ass_path}")
            
            # 動画生成
            print("🎬 ASS字幕付き動画生成中...")
            result = generator.create_video_from_ass_subtitle(
                audio_path=str(audio_path),
                ass_subtitle_path=str(ass_path),
                output_path=args.output
            )
            
            print(f"✅ ASS字幕付き動画生成完了: {result}")
            
        elif args.script_json and args.audio:
            # JSONファイルと音声ファイルから動画生成
            from pathlib import Path
            
            script_path = Path(args.script_json)
            audio_path = Path(args.audio)
            
            if not script_path.exists():
                print(f"❌ エラー: スクリプトファイルが見つかりません: {args.script_json}")
                sys.exit(1)
            
            if not audio_path.exists():
                print(f"❌ エラー: 音声ファイルが見つかりません: {args.audio}")
                sys.exit(1)
            
            # JSONから台本テキストを抽出
            with open(script_path, 'r', encoding='utf-8') as f:
                script_data = json.load(f)
            
            # 新しい形式（title + description）に対応
            if 'description' in script_data:
                script_text = f"{script_data['title']}。{script_data['description']}"
            else:
                # 古い形式のフォールバック
                script_text = f"{script_data.get('title', '')}。{script_data.get('overview', '')}"
            
            print(f"📜 台本読み込み: {script_path}")
            print(f"🎵 音声読み込み: {audio_path}")
            
            if args.subtitle_test:
                # 字幕タイミングテストモード
                print("⏱️  字幕タイミング生成テスト...")
                timing_generator = SubtitleTimingGenerator()
                segments = timing_generator.generate_subtitle_segments(script_text, str(audio_path))
                
                print(f"✅ 字幕セグメント数: {len(segments)}")
                for i, seg in enumerate(segments):
                    print(f"  {i+1:2d}. [{seg['start_time']:6.1f}s - {seg['end_time']:6.1f}s] {seg['text'][:50]}...")
                    
            else:
                # 実際の動画生成
                print("🎬 動画生成中...")
                
                if args.no_subtitles:
                    # 字幕なしで動画生成（背景+音声のみ）
                    result = generator.create_video(
                        audio_path=str(audio_path),
                        subtitle_segments=[],  # 空の字幕セグメント
                        output_path=args.output
                    )
                else:
                    # 字幕ありで動画生成
                    result = generator.create_video_from_script_and_audio(
                        script_text=script_text,
                        audio_path=str(audio_path),
                        output_path=args.output
                    )
                
                print(f"✅ 動画生成完了: {result}")
            
        else:
            print("使用方法:")
            print("  --demo --output video.mp4                                          : デモ動画生成")
            print("  --script-json script.json --audio audio.wav --output video.mp4     : 台本+音声から動画生成")
            print("  --audio audio.wav --ass-subtitle subtitle.ass --output video.mp4   : 音声+ASS字幕から動画生成")
            print("  --script-json script.json --audio audio.wav --subtitle-test        : 字幕タイミングテスト")
            print("  --script-json script.json --audio audio.wav --no-subtitles --output video.mp4 : 字幕なし動画")
            print("\n設定:")
            print("  字幕・動画設定はコード内にハードコーディングされています")
            print("  設定変更は src/video_generator.py の DEFAULT_SETTINGS を編集してください")
            print("\n例:")
            print("  python src/video_generator.py --demo --output demo_video.mp4")
            print("  python src/video_generator.py --script-json tmp/script.json --audio tmp/audio.wav --output video.mp4")
            print("  python src/video_generator.py --audio tmp/audio.wav --ass-subtitle tmp/subtitle.ass --output video.mp4")
            print("  python src/video_generator.py --script-json tmp/script.json --audio tmp/audio.wav --subtitle-test")
            sys.exit(1)
    
    except FileNotFoundError as e:
        print(f"❌ ファイルエラー: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析エラー: {e}", file=sys.stderr)
        print("台本JSONファイルの形式を確認してください", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"❌ 設定エラー: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ 予期しないエラー: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)