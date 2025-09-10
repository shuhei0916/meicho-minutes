#!/usr/bin/env python3
"""
Meicho Minutes - 名著1分動画生成システム
Amazon書籍URLから自動でショート動画を生成するメインスクリプト
"""

import os
import sys
import json
import yaml
import logging
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

# プロジェクトパスを追加
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from src.amazon_scraper import AmazonScraper, BookInfo
from src.video_generator import VideoGenerator
from src.subtitle_image_generator import SubtitleStyle


# 設定とログの初期化
def setup_logging(config: Dict[str, Any]) -> logging.Logger:
    """ログ設定を初期化"""
    log_config = config.get('logging', {})
    
    # ログディレクトリを作成
    if log_config.get('file_enabled', True):
        log_file = Path(project_root) / log_config.get('file_path', 'logs/meicho_minutes.log')
        log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # ログ設定
    log_level = getattr(logging, log_config.get('level', 'INFO').upper())
    log_format = log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.FileHandler(log_file) if log_config.get('file_enabled', True) else logging.NullHandler(),
            logging.StreamHandler() if log_config.get('console_enabled', True) else logging.NullHandler()
        ]
    )
    
    return logging.getLogger('meicho_minutes')


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """設定ファイルを読み込み"""
    # プロジェクトルートからの絶対パスに変換
    config_file = Path(project_root) / config_path
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"⚠️ 設定ファイルが見つかりません: {config_file}")
        print("デフォルト設定を使用します")
        return {}
    except yaml.YAMLError as e:
        print(f"❌ 設定ファイルの読み込みエラー: {e}")
        sys.exit(1)


class MeichoMinutesError(Exception):
    """Meicho Minutes 関連のエラー"""
    pass


class MainPipeline:
    """メインパイプライン: 全フェーズを統合管理"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # 各コンポーネントを初期化
        self._init_components()
        
        # 出力ディレクトリを作成
        output_dir_path = config.get('files', {}).get('output_dir', 'output')
        self.output_dir = Path(project_root) / output_dir_path
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 一時ディレクトリ設定
        self.temp_dir = config.get('files', {}).get('temp_dir', '/tmp')
    
    def _init_components(self):
        """各コンポーネントを初期化"""
        try:
            # Amazon Scraper初期化
            amazon_config = self.config.get('amazon', {})
            self.scraper = AmazonScraper(
                request_delay=amazon_config.get('request_delay', 1.0),
                max_retries=amazon_config.get('max_retries', 3)
            )
            
            # Video Generator初期化（デフォルト設定使用）
            self.video_generator = VideoGenerator()
            
            # Subtitle Styleはvideo_generatorのデフォルト設定を使用
            self.subtitle_style = self.video_generator.default_subtitle_style
            
            self.logger.info("全コンポーネントの初期化完了")
            
        except Exception as e:
            self.logger.error(f"コンポーネント初期化エラー: {e}")
            raise MeichoMinutesError(f"コンポーネント初期化に失敗しました: {e}")
    
    def run_full_pipeline(self, url: str = None, html_file: str = None, output_filename: str = None) -> Dict[str, Any]:
        """完全パイプライン: URL/HTMLファイル → 動画の一気通貫処理"""
        source = html_file or url
        self.logger.info(f"完全パイプライン開始: {source}")
        start_time = datetime.now()
        
        try:
            # ファイル名を生成
            if output_filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_filename = f"meicho_video_{timestamp}.mp4"
            
            output_path = self.output_dir / output_filename
            
            # Phase 1: Amazon Scraping
            self.logger.info("Phase 1: Amazon書籍情報取得開始")
            book_info = self.run_phase1_scraping(url, html_file)
            self.logger.info(f"取得完了: {book_info.title}")
            
            try:
                # Phase 2: Script Generation
                self.logger.info("Phase 2: Gemini台本生成開始")
                script = self.run_phase2_script(book_info)
                self.logger.info(f"台本生成完了: {script.title}")
                
                # Phase 3: Audio Generation
                self.logger.info("Phase 3: VoiceVox音声生成開始")
                temp_audio = os.path.join(self.temp_dir, f"audio_{os.getpid()}.wav")
                audio_path = self.run_phase3_audio(script, temp_audio)
                
                # Phase 4: Video Generation (字幕付き)
                self.logger.info("Phase 4: 字幕付き動画生成開始")
                video_path = self.run_phase4_video(book_info, script, audio_path, str(output_path))
                
            except MeichoMinutesError as e:
                self.logger.warning(f"完全パイプラインでエラー、フォールバックに切り替え: {e}")
                # フォールバックとして字幕なし動画を生成
                self.logger.info("Phase 4: 字幕なし動画生成開始（フォールバック）")
                video_path = self.run_phase4_video_fallback(book_info, str(output_path))
            
            # 実行時間計算
            execution_time = (datetime.now() - start_time).total_seconds()
            
            result = {
                'success': True,
                'book_info': asdict(book_info),
                'video_path': video_path,
                'output_filename': output_filename,
                'execution_time_seconds': execution_time,
                'timestamp': datetime.now().isoformat()
            }
            
            self.logger.info(f"完全パイプライン完了: {execution_time:.2f}秒")
            return result
            
        except Exception as e:
            self.logger.error(f"完全パイプラインエラー: {e}")
            return {
                'success': False,
                'error': str(e),
                'execution_time_seconds': (datetime.now() - start_time).total_seconds(),
                'timestamp': datetime.now().isoformat()
            }
    
    def run_phase1_scraping(self, url: str = None, html_file: str = None) -> BookInfo:
        """Phase 1: Amazon書籍情報を取得"""
        try:
            if html_file:
                # プロジェクトルートからの絶対パスに変換
                html_file_path = Path(project_root) / html_file
                self.logger.info(f"ローカルHTMLファイルからスクレイピング: {html_file_path}")
                book_info = self.scraper.scrape_book_info_from_html_file(str(html_file_path))
            elif url:
                self.logger.info(f"Amazon URLからスクレイピング: {url}")
                book_info = self.scraper.scrape_book_info_from_url(url)
            else:
                raise MeichoMinutesError("URLまたはHTMLファイルが必要です")
            
            if not book_info.title:
                raise MeichoMinutesError("書籍タイトルが取得できませんでした")
            
            self.logger.info(f"スクレイピング成功: タイトル={book_info.title}, 著者={book_info.author}")
            return book_info
            
        except Exception as e:
            self.logger.error(f"Phase 1 スクレイピングエラー: {e}")
            raise MeichoMinutesError(f"書籍情報の取得に失敗しました: {e}")
    
    def run_phase2_script(self, book_info: BookInfo):
        """Phase 2: Gemini で動画台本を生成"""
        try:
            from src.gemini_script_generator import GeminiScriptGenerator
            
            self.logger.info("Gemini APIで台本生成開始")
            script_generator = GeminiScriptGenerator()
            script = script_generator.generate_script_from_book_info(book_info)
            
            self.logger.info(f"台本生成成功: タイトル={script.title}")
            return script
            
        except Exception as e:
            self.logger.error(f"Phase 2 台本生成エラー: {e}")
            raise MeichoMinutesError(f"台本生成に失敗しました: {e}")
    
    def run_phase3_audio(self, script, output_path: str) -> str:
        """Phase 3: VoiceVox で音声を生成"""
        try:
            from src.voicevox_tts import VoiceVoxTTS
            
            self.logger.info("VoiceVoxで音声生成開始")
            tts = VoiceVoxTTS()
            tts.generate_audio_from_script(script, output_path)
            
            self.logger.info(f"音声生成成功: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Phase 3 音声生成エラー: {e}")
            raise MeichoMinutesError(f"音声生成に失敗しました: {e}")
    
    def run_phase4_video(self, book_info: BookInfo, script, audio_path: str, output_path: str) -> str:
        """Phase 4: 動画を生成（字幕付き）"""
        try:
            self.logger.info("字幕付き動画生成開始")
            
            # 1. 字幕セグメントを生成
            from moviepy.editor import AudioFileClip
            audio_clip = AudioFileClip(audio_path)
            audio_duration = audio_clip.duration
            audio_clip.close()
            
            subtitle_segments = self.subtitle_generator.generate_subtitle_with_timing(script, audio_duration)
            
            # 2. 動画を生成（背景色はデフォルト設定で自動設定）
            result = self.video_generator.create_video(
                audio_path=audio_path,
                subtitle_segments=subtitle_segments,
                output_path=output_path,
                subtitle_style=self.subtitle_style
            )
            
            self.logger.info(f"字幕付き動画生成完了: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"Phase 4 動画生成エラー: {e}")
            raise MeichoMinutesError(f"動画生成に失敗しました: {e}")
    
    


def main_phase1_scraping(url: str = None, html_file: str = None, config: Dict[str, Any] = None) -> BookInfo:
    """Phase 1 単体実行: Amazon書籍情報取得"""
    pipeline = MainPipeline(config)
    return pipeline.run_phase1_scraping(url, html_file)


def main_phase2_script(book_info: BookInfo, config: Dict[str, Any]):
    """Phase 2 単体実行: 台本生成"""
    pipeline = MainPipeline(config)
    return pipeline.run_phase2_script(book_info)


def main_phase3_audio(script, output_path: str, config: Dict[str, Any]) -> str:
    """Phase 3 単体実行: 音声生成"""
    pipeline = MainPipeline(config)
    return pipeline.run_phase3_audio(script, output_path)


def main_phase4_video(book_info: BookInfo, script, audio_path: str, output_path: str, config: Dict[str, Any]) -> str:
    """Phase 4 単体実行: 動画生成"""
    pipeline = MainPipeline(config)
    return pipeline.run_phase4_video(book_info, script, audio_path, output_path)


def main_full_pipeline(url: str = None, html_file: str = None, output_filename: str = None, config: Dict[str, Any] = None) -> Dict[str, Any]:
    """完全パイプライン実行"""
    pipeline = MainPipeline(config)
    return pipeline.run_full_pipeline(url, html_file, output_filename)


def show_config(config: Dict[str, Any]):
    """設定情報を表示"""
    print("=== Meicho Minutes 設定情報 ===\\n")
    
    def print_section(name: str, data: Dict[str, Any], indent: int = 0):
        print("  " * indent + f"[{name}]")
        for key, value in data.items():
            if isinstance(value, dict):
                print_section(key, value, indent + 1)
            else:
                print("  " * (indent + 1) + f"{key}: {value}")
        print()
    
    for section_name, section_data in config.items():
        if isinstance(section_data, dict):
            print_section(section_name, section_data)
        else:
            print(f"{section_name}: {section_data}")


def main():
    """シンプルなメイン関数"""
    
    # 設定（必要に応じて変更）
    amazon_url = "https://www.amazon.co.jp/dp/4167193205/?coliid=INDCGOENPV1NP&colid=YAEUCTRPQIXU&psc=0&ref_=list_c_wl_lv_ov_lig_dp_it_im"  # 実際のURL
    html_file = "data/amazon_page_sample.html"  # サンプルHTMLファイル
    output_filename = "meicho_video_new.mp4"
    
    # 設定読み込み
    config = load_config('config.yaml')
    setup_logging(config)
    
    # パイプライン実行
    pipeline = MainPipeline(config)
    
    print("🚀 動画生成開始")
    
    # URLの代わりにHTMLファイルを使用（安定性のため）
    result = pipeline.run_full_pipeline(None, html_file, output_filename)
    
    # 結果表示
    if result['success']:
        print(f"🎉 動画生成成功!")
        print(f"📹 ファイル: {result['video_path']}")
        print(f"📚 書籍: {result['book_info']['title']}")
        print(f"⏱️ 時間: {result['execution_time_seconds']:.2f}秒")
    else:
        print(f"❌ エラー: {result['error']}")


if __name__ == "__main__":
    main()