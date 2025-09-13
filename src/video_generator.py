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
    


if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='FFmpegベースのASS字幕焼き込み動画生成')
    parser.add_argument('--audio', type=str, required=True, help='音声ファイルパス')
    parser.add_argument('--ass-subtitle', type=str, required=True, help='ASS字幕ファイルパス')
    parser.add_argument('--output', type=str, required=True, help='出力動画ファイルパス')
    
    args = parser.parse_args()
    
    try:
        generator = VideoGenerator()
        
        # ファイル存在確認
        audio_path = Path(args.audio)
        ass_path = Path(args.ass_subtitle)
        
        if not audio_path.exists():
            print(f"❌ エラー: 音声ファイルが見つかりません: {args.audio}")
            sys.exit(1)
        
        if not ass_path.exists():
            print(f"❌ エラー: ASS字幕ファイルが見つかりません: {args.ass_subtitle}")
            sys.exit(1)
        
        print(f"🎵 音声ファイル: {audio_path}")
        print(f"📝 ASS字幕ファイル: {ass_path}")
        print("🎬 ASS字幕付き動画生成中...")
        
        # ASS字幕付き動画生成
        result = generator.create_video_with_ass_subtitle(
            audio_path=str(audio_path),
            ass_subtitle_path=str(ass_path),
            output_path=args.output
        )
        
        print(f"✅ ASS字幕付き動画生成完了: {result}")
    
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