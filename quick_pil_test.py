#!/usr/bin/env python3
"""
PIL字幕機能の迅速なテスト
"""

import os
import sys
sys.path.append('/mnt/c/Users/Ito/projects/meicho-minutes')

def test_pil_subtitle_only():
    """PIL字幕画像生成のみをテスト"""
    print("=== PIL字幕画像生成テスト ===")
    
    try:
        # SubtitleImageGeneratorのインポートテスト
        from src.subtitle_image_generator import SubtitleImageGenerator, SubtitleStyle
        print("✅ SubtitleImageGenerator インポート成功")
        
        # インスタンス作成
        generator = SubtitleImageGenerator(1080, 1920)
        print("✅ SubtitleImageGenerator インスタンス作成成功")
        
        # 字幕スタイル設定
        style = SubtitleStyle(
            font_size=40,
            background_color=(0, 0, 0, 128),
            outline_width=2
        )
        print("✅ SubtitleStyle設定完了")
        
        # 字幕画像生成テスト
        test_texts = [
            "PIL字幕テスト",
            "長いテキストの改行処理テスト\n複数行テキスト対応確認"
        ]
        
        for i, text in enumerate(test_texts):
            output_path = f"pil_test_{i+1}.png"
            result = generator.create_subtitle_image(text, style, output_path)
            
            if os.path.exists(result):
                size = os.path.getsize(result)
                print(f"✅ 字幕画像 {i+1} 生成成功: {result} ({size} bytes)")
            else:
                print(f"❌ 字幕画像 {i+1} 生成失敗")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ PIL字幕テストエラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_moviepy_image_compositing():
    """MoviePyでのImageClip合成テスト"""
    print("\\n=== MoviePy ImageClip合成テスト ===")
    
    try:
        from moviepy.editor import ImageClip, CompositeVideoClip
        from PIL import Image
        
        # 1. 背景画像作成
        bg_path = "quick_bg.jpg"
        background = Image.new('RGB', (1080, 1920), (50, 100, 150))
        background.save(bg_path, 'JPEG')
        print("✅ 背景画像作成完了")
        
        # 2. 字幕画像作成（PILで）
        subtitle_path = "quick_subtitle.png"
        subtitle_img = Image.new('RGBA', (800, 100), (0, 0, 0, 128))
        subtitle_img.save(subtitle_path, 'PNG')
        print("✅ 字幕画像作成完了")
        
        # 3. MoviePyでImageClip作成テスト
        bg_clip = ImageClip(bg_path, duration=3)
        bg_clip = bg_clip.resize((1080, 1920))
        print("✅ 背景ImageClip作成成功")
        
        subtitle_clip = ImageClip(subtitle_path, duration=3)
        subtitle_clip = subtitle_clip.set_position(('center', 'bottom'))
        print("✅ 字幕ImageClip作成成功")
        
        # 4. 合成テスト
        composite = CompositeVideoClip([bg_clip, subtitle_clip])
        print("✅ CompositeVideoClip作成成功")
        
        # メモリ解放
        bg_clip.close()
        subtitle_clip.close()
        composite.close()
        
        # 一時ファイル削除
        for temp_file in [bg_path, subtitle_path]:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
        
        return True
        
    except Exception as e:
        print(f"❌ MoviePy合成テストエラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("🧪 PIL字幕機能クイックテスト開始\\n")
    
    # PIL字幕画像生成テスト
    pil_success = test_pil_subtitle_only()
    
    # MoviePy合成テスト
    moviepy_success = test_moviepy_image_compositing()
    
    # 結果報告
    print(f"\\n📋 クイックテスト結果:")
    print(f"   PIL字幕画像生成: {'✅ 成功' if pil_success else '❌ 失敗'}")
    print(f"   MoviePy ImageClip合成: {'✅ 成功' if moviepy_success else '❌ 失敗'}")
    
    if pil_success and moviepy_success:
        print("\\n🎉 PIL字幕システム基本機能テスト成功！")
        print("💡 PIL/Pillowベースの字幕画像生成システムが正常に動作します")
        print("🔧 次のステップ：VideoGeneratorV2への統合テスト")
    else:
        print("\\n⚠️ 一部機能に問題があります。詳細なデバッグが必要です。")

if __name__ == "__main__":
    main()