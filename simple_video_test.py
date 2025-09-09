#!/usr/bin/env python3
"""
シンプルな動画生成テスト
字幕なしで背景画像と音声のみを合成
"""

import os
import sys
sys.path.append('/mnt/c/Users/Ito/projects/meicho-minutes')

from moviepy.editor import AudioFileClip, ImageClip, CompositeVideoClip
from src.video_generator import VideoGenerator
from src.gemini_script_generator import VideoScript
from src.voicevox_tts import VoiceVoxTTS

def create_simple_video():
    """字幕なしのシンプルな動画を生成"""
    
    # 1. 背景画像を生成
    generator = VideoGenerator()
    bg_path = "simple_background.jpg"
    generator.create_background_image(bg_path, (50, 50, 150))  # 青い背景
    print(f"✅ 背景画像生成完了: {bg_path}")
    
    # 2. 音声を生成
    script = VideoScript(
        title="テスト動画",
        overview="これはシンプルな動画テストです。",
        comments=["音声と背景画像のテストを行います。"],
        conclusion="テスト完了です。"
    )
    
    tts = VoiceVoxTTS()
    audio_path = "simple_audio.wav"
    
    try:
        tts.generate_audio_from_script(script, audio_path)
        print(f"✅ 音声生成完了: {audio_path}")
    except Exception as e:
        print(f"⚠️ 音声生成をスキップ: {e}")
        # ダミー音声ファイルを作成（無音）
        from pydub import AudioSegment
        silence = AudioSegment.silent(duration=10000)  # 10秒の無音
        silence.export(audio_path, format="wav")
        print(f"✅ 無音ダミー音声作成: {audio_path}")
    
    # 3. 動画を合成（字幕なし）
    audio_clip = AudioFileClip(audio_path)
    video_clip = ImageClip(bg_path, duration=audio_clip.duration)
    video_clip = video_clip.resize((1080, 1920))
    
    # 音声付きの動画を作成
    final_video = video_clip.set_audio(audio_clip)
    
    output_path = "simple_test_video.mp4"
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
    
    print(f"✅ シンプル動画生成完了: {output_path}")
    return output_path

if __name__ == "__main__":
    try:
        result = create_simple_video()
        print(f"\n🎬 動画ファイル: {result}")
        print("動画プレーヤーで再生して確認してください！")
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()