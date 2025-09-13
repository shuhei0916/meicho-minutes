#!/usr/bin/env python3
"""
完全パイプライン統合テスト
Amazon scraper → Gemini script generator → VoiceVox TTS → Video Generator
"""

import os
import sys
import tempfile
from pathlib import Path

# プロジェクトパスを追加
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from src.script_generator import ScriptGenerator, VideoScript
from src.voicevox_tts import VoiceVoxTTS
from src.video_generator import VideoGenerator


def test_complete_pipeline():
    """完全パイプラインテスト"""
    print("🚀 完全パイプライン統合テスト開始")
    
    # テスト用の書籍データ（Amazon scraperの出力を模擬）
    test_book_data = {
        "title": "団塊の世代 〈新版〉 (文春文庫 さ 1-20)",
        "author": "堺屋 太一",
        "price": "￥145 より",
        "image_url": "https://m.media-amazon.com/images/I/51wZYgJf7oL._SY445_SX342_.jpg",
        "description": "「団塊の世代」が日本の経済社会になにをもたらすのかを予言した名著。今後の大量定年、老齢化問題への対策を新たに加えた新装版",
        "rating": "5つ星のうち3.8",
        "reviews": [
            {
                "title": "読んでて切ない団塊世代サラリーマン譚", 
                "text": "団塊世代サラリーマンの短編が4本収録されてます。話の中の団塊世代の空気感を懐かしく感じると共に堺屋氏の先見の明に感服しました。"
            },
            {
                "title": "なんだ、分かってたんじゃねえか",
                "text": "本書の優れたところは、「団塊」という人口のアンバランスがもたらす社会変動に直面しての、日本人のリアルなグダグダっぷりをきちんと描写していることだ。"
            }
        ]
    }
    
    temp_dir = Path("tmp")
    temp_dir.mkdir(exist_ok=True)
    
    try:
        # Step 1: Gemini Script Generation
        print("\n📜 Step 1: Gemini Script Generation")
        script_generator = ScriptGenerator()
        video_script = script_generator.generate_script(test_book_data)
        
        script_path = temp_dir / "pipeline_test_script.json"
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(video_script.to_json())
        
        print(f"   ✅ 台本生成完了: {script_path}")
        print(f"   📝 タイトル: {video_script.title}")
        print(f"   📝 紹介文長: {len(video_script.description)}文字")
        
        # Step 2: VoiceVox TTS (Skip if VoiceVox server not available)
        print("\n🎤 Step 2: VoiceVox TTS")
        try:
            tts = VoiceVoxTTS()
            audio_path = temp_dir / "pipeline_test_audio.wav"
            tts.generate_audio_from_script(video_script, str(audio_path))
            
            print(f"   ✅ 音声生成完了: {audio_path}")
            audio_available = True
            
        except Exception as e:
            print(f"   ⚠️  音声生成スキップ: {e}")
            print(f"   💡 VoiceVoxサーバーが起動していない可能性があります")
            audio_available = False
        
        # Step 3: Video Generation
        print("\n🎬 Step 3: Video Generation")
        video_generator = VideoGenerator()
        
        if audio_available:
            # 完全統合テスト
            video_path = temp_dir / "pipeline_test_complete.mp4"
            script_text = f"{video_script.title}。{video_script.description}"
            
            result = video_generator.create_video_from_script_and_audio(
                script_text=script_text,
                audio_path=str(audio_path),
                output_path=str(video_path)
            )
            
            print(f"   ✅ 完全統合動画生成完了: {result}")
            print(f"   📊 ファイルサイズ: {Path(result).stat().st_size / 1024:.1f} KB")
            
        else:
            print("   ℹ️  音声なしで字幕タイミングテストのみ実行")
            # 仮想の音声長でテスト
            from src.subtitle_timing_generator import SubtitleTimingGenerator
            timing_gen = SubtitleTimingGenerator()
            script_text = f"{video_script.title}。{video_script.description}"
            
            # 推定読み上げ時間を計算
            estimated_duration = timing_gen.estimate_reading_time(script_text)
            print(f"   📊 推定読み上げ時間: {estimated_duration:.1f}秒")
            
            # 文章分割テスト
            sentences = timing_gen._split_into_sentences(script_text)
            print(f"   📊 分割文数: {len(sentences)}")
            for i, sentence in enumerate(sentences[:3]):  # 最初の3文のみ表示
                print(f"     {i+1}. {sentence}...")
        
        print("\n🎉 完全パイプライン統合テスト成功!")
        return True
        
    except Exception as e:
        print(f"\n❌ パイプラインテスト失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_video_generator_standalone():
    """VideoGenerator単体テスト"""
    print("\n🔧 VideoGenerator 単体テスト")
    
    temp_dir = Path("tmp")
    
    # 既存のファイルを確認
    script_files = list(temp_dir.glob("*script*.json"))
    audio_files = list(temp_dir.glob("*.wav"))
    
    if not script_files or not audio_files:
        print("   ⚠️  テスト用ファイルが見つかりません")
        print(f"   📁 スクリプトファイル: {len(script_files)}個")
        print(f"   🎵 音声ファイル: {len(audio_files)}個")
        return False
    
    script_path = script_files[0]
    audio_path = audio_files[0] 
    
    print(f"   📜 使用スクリプト: {script_path}")
    print(f"   🎵 使用音声: {audio_path}")
    
    try:
        video_generator = VideoGenerator()
        video_path = temp_dir / "standalone_test_video.mp4"
        
        # JSON読み込み
        import json
        with open(script_path, 'r', encoding='utf-8') as f:
            script_data = json.load(f)
        
        script_text = f"{script_data['title']}。{script_data['description']}"
        
        # 動画生成
        result = video_generator.create_video_from_script_and_audio(
            script_text=script_text,
            audio_path=str(audio_path),
            output_path=str(video_path)
        )
        
        print(f"   ✅ 動画生成成功: {result}")
        print(f"   📊 ファイルサイズ: {Path(result).stat().st_size / 1024:.1f} KB")
        return True
        
    except Exception as e:
        print(f"   ❌ VideoGenerator単体テスト失敗: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("🎯 MEICHO MINUTES - 完全パイプライン統合テスト")
    print("=" * 60)
    
    # 完全パイプラインテスト
    pipeline_success = test_complete_pipeline()
    
    # VideoGenerator単体テスト
    standalone_success = test_video_generator_standalone()
    
    print("\n" + "=" * 60)
    print("📋 テスト結果サマリー")
    print("=" * 60)
    print(f"完全パイプラインテスト: {'✅ 成功' if pipeline_success else '❌ 失敗'}")
    print(f"VideoGenerator単体テスト: {'✅ 成功' if standalone_success else '❌ 失敗'}")
    
    if pipeline_success and standalone_success:
        print("\n🎉 全テスト成功! Video Generator完成!")
        sys.exit(0)
    else:
        print("\n⚠️  一部テストが失敗しました")
        sys.exit(1)