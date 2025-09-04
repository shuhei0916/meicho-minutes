import html
from typing import List, Dict
from src.gemini_script_generator import VideoScript


class SubtitleGenerator:
    """字幕テキスト生成機能を提供するクラス"""
    
    def __init__(self):
        """SubtitleGeneratorを初期化"""
        pass
    
    def generate_subtitle_text(self, script: VideoScript) -> str:
        """
        VideoScriptから字幕用テキストを生成
        
        Args:
            script: 動画台本
            
        Returns:
            字幕用テキスト
        """
        return script.to_text()
    
    def generate_subtitle_with_timing(self, script: VideoScript, audio_duration: float) -> List[Dict]:
        """
        VideoScriptからタイミング情報付き字幕を生成
        
        Args:
            script: 動画台本
            audio_duration: 音声の長さ（秒）
            
        Returns:
            タイミング情報付き字幕セグメントのリスト
        """
        # 台本の各部分を取得
        parts = []
        if script.title:
            parts.append(script.title)
        if script.overview:
            parts.append(script.overview)
        for comment in script.comments:
            parts.append(comment)
        if script.conclusion:
            parts.append(script.conclusion)
        
        # 各部分に均等に時間を配分
        segment_duration = audio_duration / len(parts) if parts else audio_duration
        
        subtitle_segments = []
        for i, part in enumerate(parts):
            start_time = i * segment_duration
            end_time = (i + 1) * segment_duration
            
            subtitle_segments.append({
                "text": part,
                "start_time": start_time,
                "end_time": end_time
            })
        
        return subtitle_segments
    
    def format_text_with_line_breaks(self, text: str, max_chars_per_line: int = 20) -> str:
        """
        文字数制限に応じてテキストを改行する
        
        Args:
            text: 改行処理するテキスト
            max_chars_per_line: 1行あたりの最大文字数
            
        Returns:
            改行処理されたテキスト
        """
        if len(text) <= max_chars_per_line:
            return text
        
        lines = []
        current_line = ""
        
        for char in text:
            if len(current_line) + 1 <= max_chars_per_line:
                current_line += char
            else:
                lines.append(current_line)
                current_line = char
        
        # 最後の行を追加
        if current_line:
            lines.append(current_line)
        
        return '\n'.join(lines)
    
    def escape_special_characters(self, text: str) -> str:
        """
        特殊文字をエスケープする
        
        Args:
            text: エスケープするテキスト
            
        Returns:
            エスケープされたテキスト
        """
        return html.escape(text)


if __name__ == "__main__":
    import sys
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description='字幕・テキスト処理機能のテスト')
    parser.add_argument('--script', type=str, help='VideoScriptのJSONファイルパス')
    parser.add_argument('--text', type=str, help='直接テキストを指定')
    parser.add_argument('--duration', type=float, default=60.0, help='音声の長さ（秒）')
    parser.add_argument('--max-chars', type=int, default=20, help='1行あたりの最大文字数')
    parser.add_argument('--demo', action='store_true', help='デモ用サンプルを実行')
    
    args = parser.parse_args()
    
    generator = SubtitleGenerator()
    
    if args.demo:
        # デモ用サンプル実行
        from src.gemini_script_generator import VideoScript
        
        sample_script = VideoScript(
            title="デモタイトル：効率的な学習法",
            overview="この本では、短時間で効果的に学習する方法について詳しく解説しています。",
            comments=["重要なのは集中力を維持することです。", "反復学習が記憶定着に効果的です。"],
            conclusion="継続こそが成功への鍵となります。"
        )
        
        print("=== デモ実行結果 ===")
        print("\n1. 字幕テキスト生成:")
        subtitle_text = generator.generate_subtitle_text(sample_script)
        print(f"'{subtitle_text}'")
        
        print("\n2. タイミング付き字幕:")
        timed_subtitles = generator.generate_subtitle_with_timing(sample_script, args.duration)
        for i, segment in enumerate(timed_subtitles):
            print(f"  {i+1}. {segment['start_time']:.1f}s-{segment['end_time']:.1f}s: '{segment['text']}'")
        
        print("\n3. 改行処理:")
        long_text = "これは非常に長い文章で、字幕として表示する際には適切な位置で改行する必要があります。"
        formatted = generator.format_text_with_line_breaks(long_text, args.max_chars)
        print(f"元テキスト: '{long_text}'")
        print(f"改行後:\n'{formatted}'")
        
        print("\n4. 特殊文字エスケープ:")
        special_text = 'これは"特殊"文字<>を&含むテキストです'
        escaped = generator.escape_special_characters(special_text)
        print(f"元テキスト: '{special_text}'")
        print(f"エスケープ後: '{escaped}'")
    
    elif args.script:
        # JSONファイルからVideoScriptを読み込み
        try:
            with open(args.script, 'r', encoding='utf-8') as f:
                script_data = json.load(f)
            
            from src.gemini_script_generator import VideoScript
            script = VideoScript(
                title=script_data['title'],
                overview=script_data['overview'],
                comments=script_data['comments'],
                conclusion=script_data['conclusion']
            )
            
            print(f"スクリプトファイルから字幕生成: {args.script}")
            
            # 字幕テキスト生成
            subtitle_text = generator.generate_subtitle_text(script)
            print(f"\n字幕テキスト:\n{subtitle_text}")
            
            # タイミング付き字幕
            timed_subtitles = generator.generate_subtitle_with_timing(script, args.duration)
            print(f"\nタイミング付き字幕 (音声長: {args.duration}秒):")
            for i, segment in enumerate(timed_subtitles):
                formatted_text = generator.format_text_with_line_breaks(segment['text'], args.max_chars)
                escaped_text = generator.escape_special_characters(formatted_text)
                print(f"  {i+1}. {segment['start_time']:.1f}s-{segment['end_time']:.1f}s:")
                print(f"     {escaped_text}")
        
        except Exception as e:
            print(f"エラー: スクリプトファイルの処理中にエラーが発生しました: {e}")
            sys.exit(1)
    
    elif args.text:
        # 直接テキストから処理
        print(f"テキスト処理: '{args.text}'")
        
        # 改行処理
        formatted = generator.format_text_with_line_breaks(args.text, args.max_chars)
        print(f"\n改行処理後 (最大{args.max_chars}文字/行):\n{formatted}")
        
        # 特殊文字エスケープ
        escaped = generator.escape_special_characters(formatted)
        print(f"\n特殊文字エスケープ後:\n{escaped}")
    
    else:
        print("使用方法:")
        print("  --demo                    : デモ実行")
        print("  --script script.json      : VideoScriptファイルから字幕生成")
        print("  --text '文字列'           : 直接テキスト処理")
        print("  --duration 60             : 音声の長さ指定")
        print("  --max-chars 20            : 1行最大文字数指定")
        print("\n例:")
        print("  python src/subtitle_generator.py --demo")
        print("  python src/subtitle_generator.py --text 'テストメッセージ' --max-chars 10")
        sys.exit(1)