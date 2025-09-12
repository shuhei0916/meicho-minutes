import os
import tempfile
import re
import ffmpeg
from typing import List, Dict, Optional
from pathlib import Path


class VideoGenerator:
    """FFmpegベースのASS字幕焼き込み動画生成ライブラリ"""
    
    # デフォルト設定
    DEFAULT_SETTINGS = {
        'video': {
            'width': 1080,                      # YouTubeショーツ対応
            'height': 1920,
            'fps': 24,
            'background_color': '#191970',      # ネイビーブルー
            'codec': 'libx264',
            'audio_codec': 'aac',
            'crf': 23,                          # 品質設定
            'preset': 'medium'                  # エンコード速度
        }
    }
    
    def __init__(self, width: int = 1080, height: int = 1920):
        """
        VideoGeneratorを初期化
        
        Args:
            width: 動画の幅（デフォルト: 1080）
            height: 動画の高さ（デフォルト: 1920）
        """
        self.width = width
        self.height = height
        self.settings = self.DEFAULT_SETTINGS.copy()
        self.settings['video']['width'] = width
        self.settings['video']['height'] = height
    
    def create_background_video(self, audio_path: str, output_path: str) -> str:
        """
        音声ファイルから背景色のみの動画を作成
        
        Args:
            audio_path: 音声ファイルパス
            output_path: 出力動画ファイルパス
            
        Returns:
            作成された動画ファイルのパス
        """
        video_settings = self.settings['video']
        
        try:
            # 音声情報を取得
            audio_info = ffmpeg.probe(audio_path)
            duration = float(audio_info['format']['duration'])
            
            # 背景動画生成（色のみ）
            background_stream = ffmpeg.input(
                'color=c={}:size={}x{}:duration={}:rate={}'.format(
                    video_settings['background_color'],
                    video_settings['width'],
                    video_settings['height'],
                    duration,
                    video_settings['fps']
                ),
                f='lavfi'
            )
            
            # 音声ストリーム
            audio_stream = ffmpeg.input(audio_path)
            
            # 動画と音声を結合
            output = ffmpeg.output(
                background_stream,
                audio_stream,
                output_path,
                vcodec=video_settings['codec'],
                acodec=video_settings['audio_codec'],
                crf=video_settings['crf'],
                preset=video_settings['preset'],
                pix_fmt='yuv420p'
            )
            
            # 既存ファイルを上書き
            output = ffmpeg.overwrite_output(output)
            
            # 実行
            ffmpeg.run(output, quiet=True)
            
            return output_path
            
        except ffmpeg.Error as e:
            error_message = e.stderr.decode() if e.stderr else str(e)
            raise RuntimeError(f"背景動画生成に失敗: {error_message}")
    
    def create_video_with_ass_subtitle(
        self,
        audio_path: str,
        ass_subtitle_path: str,
        output_path: str
    ) -> str:
        """
        音声ファイルとASS字幕ファイルから動画を作成（FFmpeg字幕焼き込み）
        
        Args:
            audio_path: 音声ファイルパス
            ass_subtitle_path: ASS字幕ファイルパス
            output_path: 出力動画ファイルパス
            
        Returns:
            作成された動画ファイルのパス
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"音声ファイルが見つかりません: {audio_path}")
        
        if not os.path.exists(ass_subtitle_path):
            raise FileNotFoundError(f"ASS字幕ファイルが見つかりません: {ass_subtitle_path}")
        
        video_settings = self.settings['video']
        
        try:
            # 音声情報を取得
            audio_info = ffmpeg.probe(audio_path)
            duration = float(audio_info['format']['duration'])
            
            # 背景動画生成（色のみ）
            background_stream = ffmpeg.input(
                'color=c={}:size={}x{}:duration={}:rate={}'.format(
                    video_settings['background_color'],
                    video_settings['width'],
                    video_settings['height'],
                    duration,
                    video_settings['fps']
                ),
                f='lavfi'
            )
            
            # ASS字幕フィルターを適用
            # Windows環境でのパス対応（バックスラッシュをエスケープ）
            ass_path_escaped = ass_subtitle_path.replace('\\', '\\\\').replace(':', '\\:')
            
            video_with_subtitles = background_stream.filter(
                'subtitles',
                filename=ass_path_escaped
            )
            
            # 音声ストリーム
            audio_stream = ffmpeg.input(audio_path)
            
            # 動画と音声を結合
            output = ffmpeg.output(
                video_with_subtitles,
                audio_stream,
                output_path,
                vcodec=video_settings['codec'],
                acodec=video_settings['audio_codec'],
                crf=video_settings['crf'],
                preset=video_settings['preset'],
                pix_fmt='yuv420p'
            )
            
            # 既存ファイルを上書き
            output = ffmpeg.overwrite_output(output)
            
            # 実行
            ffmpeg.run(output, quiet=True)
            
            return output_path
            
        except ffmpeg.Error as e:
            error_message = e.stderr.decode() if e.stderr else str(e)
            raise RuntimeError(f"ASS字幕付き動画生成に失敗: {error_message}")
    
    def parse_ass_subtitle_file(self, ass_file_path: str) -> List[Dict[str, any]]:
        """
        ASS字幕ファイルを解析して字幕セグメントを抽出（検証用）
        
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


if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='FFmpegベースのASS字幕焼き込み動画生成')
    parser.add_argument('--audio', type=str, required=True, help='音声ファイルパス')
    parser.add_argument('--ass-subtitle', type=str, help='ASS字幕ファイルパス')
    parser.add_argument('--output', type=str, help='出力動画ファイルパス')
    parser.add_argument('--background-only', action='store_true', help='背景のみの動画を生成（字幕なし）')
    parser.add_argument('--verify-ass', action='store_true', help='ASS字幕ファイル内容を検証・表示')
    
    args = parser.parse_args()
    
    try:
        generator = VideoGenerator()
        
        # 音声ファイルの存在確認
        audio_path = Path(args.audio)
        if not audio_path.exists():
            print(f"❌ エラー: 音声ファイルが見つかりません: {args.audio}")
            sys.exit(1)
        
        print(f"🎵 音声ファイル: {audio_path}")
        
        # ASS字幕ファイル検証モード
        if args.verify_ass and args.ass_subtitle:
            print(f"📝 ASS字幕ファイル検証: {args.ass_subtitle}")
            try:
                segments = generator.parse_ass_subtitle_file(args.ass_subtitle)
                print(f"✅ 字幕セグメント数: {len(segments)}")
                for i, seg in enumerate(segments[:5]):  # 最初の5個のみ表示
                    print(f"  {i+1:2d}. [{seg['start_time']:6.2f}s - {seg['end_time']:6.2f}s] {seg['text'][:30]}...")
                if len(segments) > 5:
                    print(f"     ... その他{len(segments) - 5}セグメント")
            except Exception as e:
                print(f"❌ ASS字幕ファイル検証エラー: {e}")
                sys.exit(1)
        
        # 背景のみモード
        elif args.background_only:
            if not args.output:
                print("❌ エラー: --background-onlyモードでは--outputが必要です")
                sys.exit(1)
            
            print("🎬 背景のみ動画生成中...")
            result = generator.create_background_video(
                audio_path=str(audio_path),
                output_path=args.output
            )
            print(f"✅ 背景動画生成完了: {result}")
        
        # ASS字幕付き動画生成
        elif args.ass_subtitle and args.output:
            ass_path = Path(args.ass_subtitle)
            if not ass_path.exists():
                print(f"❌ エラー: ASS字幕ファイルが見つかりません: {args.ass_subtitle}")
                sys.exit(1)
            
            print(f"📝 ASS字幕ファイル: {ass_path}")
            print("🎬 ASS字幕付き動画生成中...")
            
            result = generator.create_video_with_ass_subtitle(
                audio_path=str(audio_path),
                ass_subtitle_path=str(ass_path),
                output_path=args.output
            )
            
            print(f"✅ ASS字幕付き動画生成完了: {result}")
        
        else:
            print("使用方法:")
            print("  --audio audio.wav --ass-subtitle subtitle.ass --output video.mp4   : ASS字幕付き動画生成")
            print("  --audio audio.wav --background-only --output video.mp4             : 背景のみ動画生成")
            print("  --audio audio.wav --ass-subtitle subtitle.ass --verify-ass         : ASS字幕検証")
            print("\n例:")
            print("  python src/video_generator.py --audio tmp/audio.wav --ass-subtitle tmp/subtitle.ass --output tmp/video.mp4")
            print("  python src/video_generator.py --audio tmp/audio.wav --background-only --output tmp/background.mp4")
            sys.exit(1)
    
    except FileNotFoundError as e:
        print(f"❌ ファイルエラー: {e}")
        sys.exit(1)
    except RuntimeError as e:
        print(f"❌ 動画生成エラー: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 予期しないエラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)