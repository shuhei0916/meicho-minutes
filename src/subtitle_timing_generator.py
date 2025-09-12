"""
字幕タイミング生成器
音声ファイルと台本テキストから字幕表示タイミングを自動生成
"""

import os
import re
from typing import List, Dict, Tuple
from moviepy.editor import AudioFileClip


class SubtitleTimingGenerator:
    """音声長と台本から字幕タイミングを生成"""
    
    def __init__(self):
        """字幕タイミング生成器を初期化"""
        # 日本語の句読点と区切り文字
        self.sentence_delimiters = r'[。！？\n]'
        # 1文字あたりの標準読み上げ時間（秒）
        self.chars_per_second = 8.0
        # 字幕間の最小間隔（秒）
        self.min_subtitle_gap = 0.3
        # 字幕の最小表示時間（秒）
        self.min_display_time = 1.2
        # 字幕の最大表示時間（秒）
        self.max_display_time = 5.0
    
    def generate_subtitle_segments(
        self, 
        text: str, 
        audio_path: str
    ) -> List[Dict[str, any]]:
        """
        テキストと音声ファイルから字幕セグメントを生成
        
        Args:
            text: 台本テキスト
            audio_path: 音声ファイルパス
            
        Returns:
            字幕セグメント [{"text": str, "start_time": float, "end_time": float}, ...]
        """
        # 音声ファイルの存在確認
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"音声ファイルが見つかりません: {audio_path}")
        
        # 音声の長さを取得
        try:
            with AudioFileClip(audio_path) as audio_clip:
                total_duration = audio_clip.duration
        except Exception as e:
            raise ValueError(f"音声ファイルの読み込みに失敗: {e}")
        
        if total_duration <= 0:
            raise ValueError("音声ファイルの長さが無効です")
        
        # テキストを文単位に分割
        sentences = self._split_into_sentences(text)
        
        if not sentences:
            return []
        
        # 各文の文字数を計算
        sentence_lengths = [len(sentence.strip()) for sentence in sentences]
        total_chars = sum(sentence_lengths)
        
        if total_chars == 0:
            return []
        
        # タイミングを計算
        segments = []
        current_time = 0.0
        
        for i, (sentence, length) in enumerate(zip(sentences, sentence_lengths)):
            if length == 0:
                continue
            
            # この文の表示時間を計算（文字数ベース + 調整）
            raw_duration = length / self.chars_per_second
            # 全体の時間に比例して調整
            duration_ratio = total_duration / (total_chars / self.chars_per_second)
            adjusted_duration = raw_duration * duration_ratio
            
            # 最小・最大時間で制限
            display_duration = max(
                self.min_display_time,
                min(adjusted_duration, self.max_display_time)
            )
            
            # 終了時間を計算
            end_time = current_time + display_duration
            
            # 音声の長さを超えないように調整
            if end_time > total_duration:
                end_time = total_duration
                # 最後の字幕は音声終了まで表示
                if i == len(sentences) - 1:
                    display_duration = end_time - current_time
            
            segments.append({
                "text": sentence.strip(),
                "start_time": current_time,
                "end_time": end_time
            })
            
            # 次の字幕開始時間（間隔を空ける）
            current_time = end_time + self.min_subtitle_gap
            
            # 音声終了時間を超えた場合は終了
            if current_time >= total_duration:
                break
        
        # 最後の調整：音声時間内に収める
        if segments:
            last_segment = segments[-1]
            if last_segment["end_time"] > total_duration:
                segments[-1]["end_time"] = total_duration
        
        return segments
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """
        テキストを文単位に分割
        
        Args:
            text: 分割するテキスト
            
        Returns:
            文のリスト
        """
        # 改行を句点に統一
        text = text.replace('\n', '。')
        
        # 句読点で分割
        sentences = re.split(self.sentence_delimiters, text)
        
        # 空文字列を除去し、短すぎる文は前の文と結合
        processed_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # 短すぎる文は前の文と結合（5文字未満）
            if len(sentence) < 5 and processed_sentences:
                processed_sentences[-1] += sentence
            else:
                processed_sentences.append(sentence)
        
        return processed_sentences
    
    def estimate_reading_time(self, text: str) -> float:
        """
        テキストの推定読み上げ時間を計算
        
        Args:
            text: 対象テキスト
            
        Returns:
            推定時間（秒）
        """
        char_count = len(text.strip())
        return char_count / self.chars_per_second


if __name__ == "__main__":
    import argparse
    import json
    import sys
    from pathlib import Path
    
    parser = argparse.ArgumentParser(
        description='字幕タイミング生成器 - 音声と台本から字幕タイミングを生成'
    )
    
    parser.add_argument('--text', type=str, help='台本テキスト（直接指定）')
    parser.add_argument('--script-json', type=str, help='台本JSONファイルパス')
    parser.add_argument('--audio', type=str, required=True, help='音声ファイルパス')
    parser.add_argument('--output', type=str, help='出力JSONファイルパス（未指定時は標準出力）')
    
    args = parser.parse_args()
    
    try:
        # テキスト取得
        if args.script_json:
            script_path = Path(args.script_json)
            if not script_path.exists():
                print(f"❌ エラー: ファイルが見つかりません: {args.script_json}", file=sys.stderr)
                sys.exit(1)
            
            with open(script_path, 'r', encoding='utf-8') as f:
                script_data = json.load(f)
            
            # 新しい形式（title + description）に対応
            if 'description' in script_data:
                text = f"{script_data['title']}。{script_data['description']}"
            else:
                # 古い形式のフォールバック
                text = f"{script_data.get('title', '')}。{script_data.get('overview', '')}"
            
            print(f"📜 台本を読み込み: {script_path}", file=sys.stderr)
            
        elif args.text:
            text = args.text
        else:
            print("❌ エラー: --text または --script-json を指定してください", file=sys.stderr)
            sys.exit(1)
        
        # 音声ファイル確認
        if not Path(args.audio).exists():
            print(f"❌ エラー: 音声ファイルが見つかりません: {args.audio}", file=sys.stderr)
            sys.exit(1)
        
        # 字幕タイミング生成
        print("⏱️  字幕タイミング生成中...", file=sys.stderr)
        generator = SubtitleTimingGenerator()
        segments = generator.generate_subtitle_segments(text, args.audio)
        
        if not segments:
            print("❌ エラー: 字幕セグメントを生成できませんでした", file=sys.stderr)
            sys.exit(1)
        
        # 結果を出力
        result = {
            "subtitle_segments": segments,
            "total_segments": len(segments),
            "total_duration": segments[-1]["end_time"] if segments else 0
        }
        
        output_json = json.dumps(result, ensure_ascii=False, indent=2)
        
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(output_json)
            
            print(f"✅ 字幕タイミングを保存: {output_path}", file=sys.stderr)
            print(f"   セグメント数: {len(segments)}", file=sys.stderr)
            print(f"   総時間: {segments[-1]['end_time']:.1f}秒", file=sys.stderr)
        else:
            print(output_json)
        
    except Exception as e:
        print(f"❌ エラー: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)