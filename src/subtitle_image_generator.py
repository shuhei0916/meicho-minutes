"""
PIL/Pillowベースの字幕画像生成システム
ImageMagick依存のTextClipの代替として実装
"""

from PIL import Image, ImageDraw, ImageFont
import os
import tempfile
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class SubtitleStyle:
    """字幕スタイルの設定"""
    font_size: int = 40
    font_color: Tuple[int, int, int] = (255, 255, 255)  # 白
    background_color: Optional[Tuple[int, int, int, int]] = (0, 0, 0, 128)  # 半透明黒
    outline_color: Optional[Tuple[int, int, int]] = (0, 0, 0)  # 黒のアウトライン
    outline_width: int = 2
    margin: int = 20  # テキストの周りの余白
    line_spacing: int = 5  # 行間
    max_width_ratio: float = 0.8  # 画面幅に対する最大文字幅の比率


class SubtitleImageGenerator:
    """PIL/Pillowを使用した字幕画像生成クラス"""
    
    def __init__(self, video_width: int = 1080, video_height: int = 1920):
        """
        字幕画像生成器を初期化
        
        Args:
            video_width: 動画の幅
            video_height: 動画の高さ
        """
        self.video_width = video_width
        self.video_height = video_height
        
        # デフォルトフォントを設定
        self._default_font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Ubuntu/Debian
            "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",  # Arch Linux
            "/System/Library/Fonts/Arial.ttf",  # macOS
            "C:/Windows/Fonts/arial.ttf",  # Windows
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",  # CentOS/RHEL
        ]
    
    def _get_font(self, size: int) -> ImageFont.FreeTypeFont:
        """
        利用可能なフォントを取得
        
        Args:
            size: フォントサイズ
            
        Returns:
            フォントオブジェクト
        """
        # 利用可能なフォントパスを探す
        for font_path in self._default_font_paths:
            if os.path.exists(font_path):
                try:
                    return ImageFont.truetype(font_path, size)
                except OSError:
                    continue
        
        # デフォルトフォントを使用
        try:
            return ImageFont.truetype("arial.ttf", size)
        except OSError:
            # デフォルトの内蔵フォントを使用
            return ImageFont.load_default()
    
    def _wrap_text(self, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
        """
        テキストを指定幅で改行
        
        Args:
            text: 元のテキスト
            font: フォントオブジェクト
            max_width: 最大幅
            
        Returns:
            改行されたテキストのリスト
        """
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            # 現在の行に単語を追加した場合のテキスト
            test_line = " ".join(current_line + [word])
            
            # テキストの幅を取得
            bbox = font.getbbox(test_line)
            text_width = bbox[2] - bbox[0]
            
            if text_width <= max_width:
                current_line.append(word)
            else:
                # 行を確定し、新しい行を開始
                if current_line:
                    lines.append(" ".join(current_line))
                    current_line = [word]
                else:
                    # 単語が長すぎる場合はそのまま追加
                    lines.append(word)
        
        # 最後の行を追加
        if current_line:
            lines.append(" ".join(current_line))
        
        return lines
    
    def create_subtitle_image(
        self, 
        text: str, 
        style: SubtitleStyle,
        output_path: str,
        position: str = "bottom"
    ) -> str:
        """
        字幕画像を生成
        
        Args:
            text: 字幕テキスト
            style: 字幕スタイル設定
            output_path: 出力画像パス
            position: 字幕位置 ("bottom", "center", "top")
            
        Returns:
            生成された画像ファイルのパス
        """
        # フォントを取得
        font = self._get_font(style.font_size)
        
        # 最大テキスト幅を計算
        max_text_width = int(self.video_width * style.max_width_ratio)
        
        # テキストを改行処理
        lines = self._wrap_text(text, font, max_text_width)
        
        # 各行の幅と全体の高さを計算
        line_heights = []
        max_line_width = 0
        
        for line in lines:
            bbox = font.getbbox(line)
            line_width = bbox[2] - bbox[0]
            line_height = bbox[3] - bbox[1]
            
            max_line_width = max(max_line_width, line_width)
            line_heights.append(line_height)
        
        # 全体の高さを計算（行間を含む）
        total_text_height = sum(line_heights) + (len(lines) - 1) * style.line_spacing
        
        # 画像サイズを決定
        image_width = max_line_width + style.margin * 2
        image_height = total_text_height + style.margin * 2
        
        # 透明な画像を作成
        image = Image.new("RGBA", (image_width, image_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # 背景を描画（指定されている場合）
        if style.background_color:
            draw.rectangle(
                [0, 0, image_width, image_height],
                fill=style.background_color
            )
        
        # テキストを描画
        y_offset = style.margin
        
        for i, line in enumerate(lines):
            # 行の幅を取得してセンタリング
            bbox = font.getbbox(line)
            line_width = bbox[2] - bbox[0]
            x_offset = (image_width - line_width) // 2
            
            # アウトラインを描画（指定されている場合）
            if style.outline_color and style.outline_width > 0:
                for dx in range(-style.outline_width, style.outline_width + 1):
                    for dy in range(-style.outline_width, style.outline_width + 1):
                        if dx != 0 or dy != 0:
                            draw.text(
                                (x_offset + dx, y_offset + dy),
                                line,
                                font=font,
                                fill=style.outline_color
                            )
            
            # メインテキストを描画
            draw.text(
                (x_offset, y_offset),
                line,
                font=font,
                fill=style.font_color
            )
            
            # 次の行のY座標を計算
            y_offset += line_heights[i] + style.line_spacing
        
        # 画像を保存
        image.save(output_path, "PNG")
        
        return output_path
    
    def create_subtitle_images_from_segments(
        self, 
        subtitle_segments: List[Dict],
        style: SubtitleStyle,
        temp_dir: str = "/tmp"
    ) -> List[Dict]:
        """
        字幕セグメントから字幕画像リストを生成
        
        Args:
            subtitle_segments: 字幕セグメント情報のリスト
            style: 字幕スタイル設定
            temp_dir: 一時ディレクトリ
            
        Returns:
            字幕画像情報のリスト (path, start_time, end_time)
        """
        subtitle_images = []
        
        for i, segment in enumerate(subtitle_segments):
            # 一時画像ファイルパスを生成
            image_path = os.path.join(temp_dir, f"subtitle_{i:03d}_{os.getpid()}.png")
            
            # 字幕画像を生成
            self.create_subtitle_image(
                segment["text"],
                style,
                image_path
            )
            
            # 画像情報を追加
            subtitle_images.append({
                "image_path": image_path,
                "start_time": segment["start_time"],
                "end_time": segment["end_time"]
            })
        
        return subtitle_images


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='PIL/Pillow字幕画像生成テスト')
    parser.add_argument('--text', type=str, default="これはテスト字幕です。\n長いテキストの改行処理もテストします。", help='字幕テキスト')
    parser.add_argument('--output', type=str, default="test_subtitle.png", help='出力画像ファイル')
    parser.add_argument('--font-size', type=int, default=40, help='フォントサイズ')
    parser.add_argument('--demo', action='store_true', help='デモ画像を複数生成')
    
    args = parser.parse_args()
    
    generator = SubtitleImageGenerator()
    
    if args.demo:
        print("=== PIL字幕画像生成デモ ===")
        
        # 複数のスタイルでデモ画像を生成
        demo_texts = [
            "シンプルな字幕テスト",
            "これは長い字幕テキストです。\n自動改行処理のテストを行います。",
            "背景付き字幕のテスト\nアウトライン効果付き"
        ]
        
        styles = [
            SubtitleStyle(font_size=40, background_color=None),  # 背景なし
            SubtitleStyle(font_size=45, background_color=(0, 0, 0, 128)),  # 半透明背景
            SubtitleStyle(font_size=50, background_color=(255, 0, 0, 100), outline_width=3)  # 赤背景+太いアウトライン
        ]
        
        for i, (text, style) in enumerate(zip(demo_texts, styles)):
            output_path = f"demo_subtitle_{i+1}.png"
            result = generator.create_subtitle_image(text, style, output_path)
            print(f"✅ デモ画像 {i+1} 生成完了: {result}")
        
        print("🎨 全デモ画像の生成が完了しました！")
    
    else:
        # 単一画像生成
        style = SubtitleStyle(font_size=args.font_size)
        
        try:
            result = generator.create_subtitle_image(args.text, style, args.output)
            print(f"✅ 字幕画像生成完了: {result}")
            
            # 画像情報を表示
            if os.path.exists(result):
                size = os.path.getsize(result)
                print(f"   ファイルサイズ: {size} bytes")
                
                # PIL で画像サイズを確認
                with Image.open(result) as img:
                    print(f"   画像サイズ: {img.size[0]}x{img.size[1]} pixels")
                    print(f"   カラーモード: {img.mode}")
        
        except Exception as e:
            print(f"エラー: {e}")
            import traceback
            traceback.print_exc()