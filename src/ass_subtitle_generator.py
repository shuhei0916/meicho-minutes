"""
ASS字幕生成器
VoiceVoxのaudio_queryから精密なタイミング情報を抽出してASS字幕ファイルを生成
"""

import math
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass


@dataclass
class MoraTiming:
    """モーラのタイミング情報"""
    text: str
    start_time: float
    end_time: float
    consonant_length: float
    vowel_length: float
    pitch: float


@dataclass  
class SubtitleChunk:
    """字幕チャンクの情報"""
    text: str
    start_time: float
    end_time: float
    moras: List[MoraTiming]


class ASSSubtitleGenerator:
    """VoiceVoxのaudio_queryから高精度ASS字幕を生成"""
    
    def __init__(self):
        """ASS字幕生成器を初期化"""
        # チャンク化パラメータ
        self.max_chars_per_chunk = 20         # 1チャンクの最大文字数
        self.max_duration_per_chunk = 3.0     # 1チャンクの最大時間（秒）
        self.min_chunk_duration = 0.5        # 1チャンクの最小時間（秒）
        
        # 結合判定用キーワード
        self.connection_particles = ['の', 'に', 'を', 'が', 'は', 'で', 'と', 'や', 'か']
        self.pause_punctuation = ['。', '！', '？', '、']
        
    def extract_mora_timings(self, accent_phrases: List[Dict], original_text: str = "") -> List[MoraTiming]:
        """
        VoiceVoxのaccent_phrasesからモーラタイミング情報を抽出
        
        Args:
            accent_phrases: VoiceVoxのaudio_queryから取得したaccent_phrases
            
        Returns:
            モーラタイミング情報のリスト
        """
        mora_timings = []
        cumulative_time = 0.0
        
        for phrase in accent_phrases:
            # 通常のモーラを処理
            for mora in phrase.get('moras', []):
                consonant_length = mora.get('consonant_length', 0.0) or 0.0
                vowel_length = mora.get('vowel_length', 0.0) or 0.0
                
                start_time = cumulative_time
                end_time = start_time + consonant_length + vowel_length
                
                mora_timing = MoraTiming(
                    text=mora.get('text', ''),
                    start_time=start_time,
                    end_time=end_time,
                    consonant_length=consonant_length,
                    vowel_length=vowel_length,
                    pitch=mora.get('pitch', 0.0)
                )
                
                mora_timings.append(mora_timing)
                cumulative_time = end_time
            
            # ポーズモーラを処理
            pause_mora = phrase.get('pause_mora')
            if pause_mora:
                consonant_length = pause_mora.get('consonant_length', 0.0) or 0.0
                vowel_length = pause_mora.get('vowel_length', 0.0) or 0.0
                
                if consonant_length > 0 or vowel_length > 0:
                    start_time = cumulative_time
                    end_time = start_time + consonant_length + vowel_length
                    
                    pause_timing = MoraTiming(
                        text='',  # ポーズは空文字
                        start_time=start_time,
                        end_time=end_time,
                        consonant_length=consonant_length,
                        vowel_length=vowel_length,
                        pitch=pause_mora.get('pitch', 0.0)
                    )
                    
                    mora_timings.append(pause_timing)
                    cumulative_time = end_time
        
        return mora_timings
    
    def create_subtitle_chunks(self, mora_timings: List[MoraTiming]) -> List[SubtitleChunk]:
        """
        モーラタイミングから適切な字幕チャンクを作成
        
        Args:
            mora_timings: モーラタイミング情報のリスト
            
        Returns:
            字幕チャンクのリスト
        """
        if not mora_timings:
            return []
        
        chunks = []
        current_chunk_moras = []
        current_text = ""
        
        for i, mora in enumerate(mora_timings):
            # ポーズは飛ばす（テキストなし）
            if not mora.text:
                continue
            
            # 現在のチャンクに追加した場合の判定
            new_text = current_text + mora.text
            new_chunk_moras = current_chunk_moras + [mora]
            
            # チャンク分割判定
            should_split = self._should_split_chunk(
                current_text, new_text, current_chunk_moras, mora, i, mora_timings
            )
            
            if should_split and current_chunk_moras:
                # 現在のチャンクを完成させる
                chunk = self._create_chunk_from_moras(current_chunk_moras, current_text)
                chunks.append(chunk)
                
                # 新しいチャンクを開始
                current_chunk_moras = [mora]
                current_text = mora.text
            else:
                # 現在のチャンクに追加
                current_chunk_moras = new_chunk_moras
                current_text = new_text
        
        # 最後のチャンクを追加
        if current_chunk_moras:
            chunk = self._create_chunk_from_moras(current_chunk_moras, current_text)
            chunks.append(chunk)
        
        return self._optimize_chunks(chunks)
    
    def _should_split_chunk(
        self, 
        current_text: str, 
        new_text: str, 
        current_moras: List[MoraTiming],
        new_mora: MoraTiming,
        index: int,
        all_moras: List[MoraTiming]
    ) -> bool:
        """
        チャンク分割判定
        
        Args:
            current_text: 現在のチャンクテキスト
            new_text: 追加後のテキスト
            current_moras: 現在のモーラリスト
            new_mora: 追加予定のモーラ
            index: 現在のインデックス
            all_moras: 全モーラリスト
            
        Returns:
            分割するかどうか
        """
        # 最初のモーラは分割しない
        if not current_moras:
            return False
        
        # 文字数制限チェック
        if len(new_text) > self.max_chars_per_chunk:
            return True
        
        # 時間制限チェック
        duration = new_mora.end_time - current_moras[0].start_time
        if duration > self.max_duration_per_chunk:
            return True
        
        # 句読点での分割
        if current_text and current_text[-1] in self.pause_punctuation:
            return True
        
        # 接続助詞での結合優先（分割を避ける）
        if new_mora.text in self.connection_particles:
            return False
        
        # 自然な区切りでの分割（助詞の後など）
        if (current_text and 
            current_text[-1] in self.connection_particles and 
            len(current_text) >= 3):  # 最小長を確保
            return True
        
        return False
    
    def _create_chunk_from_moras(self, moras: List[MoraTiming], text: str) -> SubtitleChunk:
        """モーラリストからチャンクを作成"""
        if not moras:
            return SubtitleChunk("", 0.0, 0.0, [])
        
        start_time = moras[0].start_time
        end_time = moras[-1].end_time
        
        return SubtitleChunk(
            text=text,
            start_time=start_time,
            end_time=end_time,
            moras=moras
        )
    
    def _optimize_chunks(self, chunks: List[SubtitleChunk]) -> List[SubtitleChunk]:
        """
        チャンクを最適化（短すぎるものを結合など）
        
        Args:
            chunks: 最適化前のチャンクリスト
            
        Returns:
            最適化後のチャンクリスト
        """
        if not chunks:
            return chunks
        
        optimized = []
        i = 0
        
        while i < len(chunks):
            current_chunk = chunks[i]
            duration = current_chunk.end_time - current_chunk.start_time
            
            # 短すぎるチャンクは次のものと結合
            if (duration < self.min_chunk_duration and 
                i + 1 < len(chunks) and
                len(current_chunk.text) + len(chunks[i + 1].text) <= self.max_chars_per_chunk):
                
                next_chunk = chunks[i + 1]
                merged_chunk = SubtitleChunk(
                    text=current_chunk.text + next_chunk.text,
                    start_time=current_chunk.start_time,
                    end_time=next_chunk.end_time,
                    moras=current_chunk.moras + next_chunk.moras
                )
                optimized.append(merged_chunk)
                i += 2  # 2つのチャンクをスキップ
            else:
                optimized.append(current_chunk)
                i += 1
        
        return optimized
    
    def generate_ass_content(self, subtitle_chunks: List[SubtitleChunk], style_name: str = "Default") -> str:
        """
        字幕チャンクからASS形式の文字列を生成
        
        Args:
            subtitle_chunks: 字幕チャンクのリスト
            style_name: ASS スタイル名
            
        Returns:
            ASS形式の文字列
        """
        # ASSヘッダー
        header = """[Script Info]
Title: VoiceVox Generated Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.601
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Noto Sans CJK JP,64,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,3,0,2,60,60,60,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        
        # ダイアログ行を生成
        dialogues = []
        for chunk in subtitle_chunks:
            start_time = self._format_ass_time(chunk.start_time)
            end_time = self._format_ass_time(chunk.end_time)
            text = chunk.text.replace('\n', '\\N')  # 改行をASS形式にエスケープ
            
            dialogue = f"Dialogue: 0,{start_time},{end_time},{style_name},,0,0,0,,{text}"
            dialogues.append(dialogue)
        
        return header + "\n".join(dialogues)
    
    def _format_ass_time(self, seconds: float) -> str:
        """
        秒をASS時間形式（H:MM:SS.CC）に変換
        
        Args:
            seconds: 秒数
            
        Returns:
            ASS時間形式の文字列
        """
        total_centiseconds = int(seconds * 100)
        hours = total_centiseconds // 360000
        minutes = (total_centiseconds % 360000) // 6000
        secs = (total_centiseconds % 6000) // 100
        centiseconds = total_centiseconds % 100
        
        return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"
    
    def create_subtitle_chunks_from_text_and_timings(
        self,
        original_text: str,
        mora_timings: List[MoraTiming]
    ) -> List[SubtitleChunk]:
        """
        元のテキストとモーラタイミングから適切な字幕チャンクを作成
        
        Args:
            original_text: 元のテキスト（読める形）
            mora_timings: モーラタイミング情報
            
        Returns:
            字幕チャンクのリスト
        """
        if not mora_timings:
            return []
        
        # テキストを句読点で大まかに分割
        sentences = []
        current_sentence = ""
        
        for char in original_text:
            current_sentence += char
            if char in self.pause_punctuation:
                sentences.append(current_sentence.strip())
                current_sentence = ""
        
        if current_sentence.strip():
            sentences.append(current_sentence.strip())
        
        # 各文に対してタイミングを割り当て
        chunks = []
        total_duration = mora_timings[-1].end_time if mora_timings else 0
        total_chars = len(original_text)
        current_time = 0.0
        
        for sentence in sentences:
            if not sentence:
                continue
            
            # この文の推定時間を計算
            char_ratio = len(sentence) / total_chars if total_chars > 0 else 0
            estimated_duration = total_duration * char_ratio
            
            # 適切な長さでチャンクに分割
            if len(sentence) <= self.max_chars_per_chunk:
                # そのまま1チャンクに
                chunks.append(SubtitleChunk(
                    text=sentence,
                    start_time=current_time,
                    end_time=current_time + estimated_duration,
                    moras=[]
                ))
                current_time += estimated_duration + 0.2  # 少し間隔を空ける
            else:
                # 長い文は分割
                words = sentence
                chunk_size = self.max_chars_per_chunk
                for i in range(0, len(words), chunk_size):
                    chunk_text = words[i:i + chunk_size]
                    chunk_duration = estimated_duration * len(chunk_text) / len(sentence)
                    
                    chunks.append(SubtitleChunk(
                        text=chunk_text,
                        start_time=current_time,
                        end_time=current_time + chunk_duration,
                        moras=[]
                    ))
                    current_time += chunk_duration + 0.1
        
        return chunks
    
    def generate_ass_from_accent_phrases(
        self, 
        accent_phrases: List[Dict], 
        output_path: str = None,
        original_text: str = ""
    ) -> str:
        """
        VoiceVoxのaccent_phrasesから直接ASS字幕を生成
        
        Args:
            accent_phrases: VoiceVoxのaudio_queryから取得したaccent_phrases
            output_path: 出力ファイルパス（Noneの場合は文字列のみ返す）
            original_text: 元のテキスト（読める形）
            
        Returns:
            ASS形式の文字列
        """
        # モーラタイミング抽出
        mora_timings = self.extract_mora_timings(accent_phrases, original_text)
        
        # 字幕チャンク作成
        if original_text:
            # 元テキストがある場合は、それを基にチャンク作成
            subtitle_chunks = self.create_subtitle_chunks_from_text_and_timings(
                original_text, mora_timings
            )
        else:
            # 従来の方法（モーラベース）
            subtitle_chunks = self.create_subtitle_chunks(mora_timings)
        
        # ASS形式生成
        ass_content = self.generate_ass_content(subtitle_chunks)
        
        # ファイル出力（指定された場合）
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(ass_content)
        
        return ass_content


if __name__ == "__main__":
    import argparse
    import json
    import sys
    from pathlib import Path
    
    parser = argparse.ArgumentParser(
        description='ASS字幕生成器 - VoiceVox audio_queryからASS字幕ファイルを生成'
    )
    
    parser.add_argument('--audio-query', type=str, required=True, 
                        help='VoiceVox audio_queryのJSONファイルパス')
    parser.add_argument('--output', type=str, required=True, 
                        help='出力ASSファイルパス')
    
    args = parser.parse_args()
    
    try:
        # audio_query JSONファイルを読み込み
        if not Path(args.audio_query).exists():
            print(f"❌ エラー: audio_queryファイルが見つかりません: {args.audio_query}", file=sys.stderr)
            sys.exit(1)
        
        with open(args.audio_query, 'r', encoding='utf-8') as f:
            audio_query_data = json.load(f)
        
        accent_phrases = audio_query_data.get('accent_phrases', [])
        if not accent_phrases:
            print("❌ エラー: accent_phrasesが見つかりません", file=sys.stderr)
            sys.exit(1)
        
        print(f"📜 audio_query読み込み: {args.audio_query}", file=sys.stderr)
        print(f"   アクセント句数: {len(accent_phrases)}", file=sys.stderr)
        
        # ASS字幕生成
        generator = ASSSubtitleGenerator()
        ass_content = generator.generate_ass_from_accent_phrases(accent_phrases, args.output)
        
        print(f"✅ ASS字幕生成完了: {args.output}", file=sys.stderr)
        
        # 統計情報表示
        lines = ass_content.split('\n')
        dialogue_lines = [line for line in lines if line.startswith('Dialogue:')]
        print(f"   字幕セグメント数: {len(dialogue_lines)}", file=sys.stderr)
        
    except Exception as e:
        print(f"❌ エラー: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)