#!/usr/bin/env python3
"""
video_generator_v2の簡易テスト（依存関係を回避）
"""

import os
import sys
import tempfile
from dataclasses import dataclass
from typing import List, Optional

# プロジェクトパスを追加
sys.path.append('/mnt/c/Users/Ito/projects/meicho-minutes')

# 最小限のクラス定義
@dataclass
class BookInfo:
    title: Optional[str] = None
    author: Optional[str] = None
    price: Optional[str] = None
    image_url: Optional[str] = None
    description: Optional[str] = None
    reviews: List = None
    
    def __post_init__(self):
        if self.reviews is None:
            self.reviews = []

def test_video_generator_v2_basic():
    """VideoGeneratorV2の基本機能テスト"""
    print("=== VideoGeneratorV2 基本機能テスト ===")
    
    try:
        from src.video_generator_v2 import VideoGeneratorV2, SubtitleStyle
        
        # インスタンス作成
        generator = VideoGeneratorV2()
        print("✅ VideoGeneratorV2 インスタンス作成成功")
        
        # 背景画像作成テスト
        bg_path = "test_v2_bg.jpg"
        generator.create_background_image(bg_path, (100, 150, 200))
        
        if os.path.exists(bg_path):
            size = os.path.getsize(bg_path)
            print(f"✅ 背景画像作成成功: {bg_path} ({size} bytes)")
        else:
            print("❌ 背景画像作成失敗")
            return False
        
        # ダミー音声作成
        audio_path = "test_v2_audio.wav"
        import wave
        import struct
        
        with wave.open(audio_path, 'w') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(22050)
            
            for _ in range(22050 * 3):  # 3秒
                wav_file.writeframes(struct.pack('<h', 0))
        
        print("✅ ダミー音声作成成功")
        
        # 字幕なし動画生成テスト
        output_path = "test_v2_video.mp4"
        result = generator.create_video_without_subtitles(
            bg_path, audio_path, output_path
        )
        
        if os.path.exists(result):
            size = os.path.getsize(result)
            print(f"✅ 字幕なし動画生成成功: {result} ({size:,} bytes)")
        else:
            print("❌ 動画生成失敗")
            return False
        
        # クリーンアップ
        for temp_file in [bg_path, audio_path, output_path]:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
        
        return True
        
    except Exception as e:
        print(f"❌ テストエラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def compare_generators():
    """video_generatorとvideo_generator_v2の比較"""
    print("\\n=== video_generator vs video_generator_v2 比較 ===")
    
    try:
        # video_generator.py（修正版）
        from src.video_generator import VideoGenerator
        gen1 = VideoGenerator()
        print("✅ VideoGenerator (修正版) インポート成功")
        
        # video_generator_v2.py
        from src.video_generator_v2 import VideoGeneratorV2
        gen2 = VideoGeneratorV2()
        print("✅ VideoGeneratorV2 インポート成功")
        
        # メソッド比較
        gen1_methods = [method for method in dir(gen1) if method.startswith('create_')]
        gen2_methods = [method for method in dir(gen2) if method.startswith('create_')]
        
        print("\\n📋 メソッド比較:")
        print(f"   VideoGenerator: {gen1_methods}")
        print(f"   VideoGeneratorV2: {gen2_methods}")
        
        # 属性比較
        print("\\n🔧 主要な属性:")
        print(f"   VideoGenerator - width: {gen1.width}, height: {gen1.height}")
        print(f"   VideoGeneratorV2 - width: {gen2.width}, height: {gen2.height}")
        
        # subtitle_image_generator属性の確認
        has_subtitle_gen1 = hasattr(gen1, 'subtitle_image_generator')
        has_subtitle_gen2 = hasattr(gen2, 'subtitle_image_generator')
        
        print(f"\\n📝 字幕生成器:")
        print(f"   VideoGenerator - subtitle_image_generator: {has_subtitle_gen1}")
        print(f"   VideoGeneratorV2 - subtitle_image_generator: {has_subtitle_gen2}")
        
        return True
        
    except Exception as e:
        print(f"❌ 比較エラー: {e}")
        return False

def main():
    print("🧪 VideoGeneratorV2 動作確認テスト開始\\n")
    
    # 基本機能テスト
    basic_success = test_video_generator_v2_basic()
    
    # 比較テスト
    compare_success = compare_generators()
    
    print(f"\\n📋 テスト結果:")
    print(f"   VideoGeneratorV2基本機能: {'✅ 成功' if basic_success else '❌ 失敗'}")
    print(f"   ジェネレーター比較: {'✅ 成功' if compare_success else '❌ 失敗'}")
    
    if basic_success and compare_success:
        print("\\n🎉 VideoGeneratorV2は正常に動作します！")
        print("\\n💡 主要な違い:")
        print("   • video_generator.py: 既存クラスを修正してImageMagick依存を解消")
        print("   • video_generator_v2.py: 新しいクラス（VideoGeneratorV2）として独立実装")
        print("   • 両方ともPIL/Pillowベースの字幕システムを使用")
        print("   • create_youtube_shorts_video vs create_youtube_shorts_video_v2")
    else:
        print("\\n⚠️ 一部機能に問題があります")
        
    print("\\n❌ 注意: 指定された出力ファイル拡張子が.wavですが、これは動画ファイル(.mp4)を生成するスクリプトです")

if __name__ == "__main__":
    main()