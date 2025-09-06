#!/usr/bin/env python3
"""
ImageMagick依存問題を特定するための統合テスト
最小限の依存関係でTextClipエラーを再現
"""

import os
import sys
import tempfile
from dataclasses import dataclass
from typing import List

# MoviePyをインポートしてTextClipエラーを再現
try:
    from moviepy.editor import AudioFileClip, ImageClip, CompositeVideoClip, TextClip
    print("✅ MoviePy インポート成功")
except ImportError as e:
    print(f"❌ MoviePy インポートエラー: {e}")
    sys.exit(1)

# 最小限のVideoScriptクラス定義
@dataclass
class VideoScript:
    title: str
    overview: str
    comments: List[str]
    conclusion: str

def test_textclip_creation():
    """TextClip作成でImageMagick依存問題を再現"""
    print("\n=== TextClip作成テスト ===")
    
    try:
        # 基本的なTextClipを作成してみる
        text_clip = TextClip(
            "テスト字幕",
            fontsize=40,
            color='white',
            font='Arial',  # これがImageMagickを要求する可能性
            size=(864, None),  # 1080 * 0.8 = 864
            method='caption'
        )
        print("✅ TextClip作成成功")
        text_clip.close()
        
    except OSError as e:
        if "ImageMagick" in str(e) or "unset" in str(e):
            print(f"🔍 ImageMagick依存エラーを検出: {e}")
            return False
        else:
            print(f"❌ 予期しないOSエラー: {e}")
            raise
    except Exception as e:
        print(f"❌ 予期しないエラー: {type(e).__name__}: {e}")
        raise
    
    return True

def test_simple_video_composition():
    """字幕なしのシンプルな動画合成テスト"""
    print("\n=== シンプル動画合成テスト ===")
    
    # 1. 一時的な背景画像を作成
    from PIL import Image
    bg_path = "temp_bg.jpg"
    background = Image.new('RGB', (1080, 1920), (50, 50, 150))  # 青い背景
    background.save(bg_path, 'JPEG')
    print(f"✅ 背景画像作成: {bg_path}")
    
    # 2. ダミー音声を作成（pydubが必要ない方法）
    import wave
    import struct
    
    audio_path = "temp_audio.wav"
    duration = 5  # 5秒
    sample_rate = 22050
    
    with wave.open(audio_path, 'w') as wav_file:
        wav_file.setnchannels(1)  # モノラル
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        
        # 無音のダミーデータ
        for _ in range(int(sample_rate * duration)):
            wav_file.writeframes(struct.pack('<h', 0))
    
    print(f"✅ ダミー音声作成: {audio_path}")
    
    # 3. 字幕なしで動画を合成
    try:
        audio_clip = AudioFileClip(audio_path)
        video_clip = ImageClip(bg_path, duration=audio_clip.duration)
        video_clip = video_clip.resize((1080, 1920))
        
        # 音声付きの動画を作成（字幕なし）
        final_video = video_clip.set_audio(audio_clip)
        
        output_path = "imagemagick_test_video.mp4"
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
        
        print(f"✅ 字幕なし動画生成成功: {output_path}")
        
        # ファイルサイズ確認
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"   ファイルサイズ: {file_size} bytes")
            return True
        
    except Exception as e:
        print(f"❌ 動画合成エラー: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # 一時ファイルをクリーンアップ
        for temp_file in [bg_path, audio_path]:
            if os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                except:
                    pass
    
    return False

def main():
    print("🧪 ImageMagick依存問題の統合テスト開始")
    
    # Phase 1: TextClip単体テスト
    textclip_success = test_textclip_creation()
    
    # Phase 2: 字幕なし動画合成テスト
    video_success = test_simple_video_composition()
    
    # 結果の報告
    print(f"\n📋 テスト結果:")
    print(f"   TextClip作成: {'✅ 成功' if textclip_success else '❌ 失敗 (ImageMagick問題)'}")
    print(f"   字幕なし動画: {'✅ 成功' if video_success else '❌ 失敗'}")
    
    if not textclip_success and video_success:
        print("\n🔍 結論: TextClip（字幕機能）でImageMagick依存問題あり")
        print("💡 解決策: PIL/Pillowベースの字幕画像生成システムの実装が必要")
    elif not textclip_success and not video_success:
        print("\n❌ 結論: MoviePy全体に問題がある可能性")
    elif textclip_success and video_success:
        print("\n✅ 結論: ImageMagick問題は解決済み")
    else:
        print("\n⚠️ 結論: 予期しない結果パターン")

if __name__ == "__main__":
    main()