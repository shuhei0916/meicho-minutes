# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

Amazon書籍を自動で要約し、ショート動画として生成・投稿します。

## 開発環境

## ディレクトリ構造

meicho-minutes/
├── README.md # プロジェクト概要
├── CLAUDE.md # Claude向けガイドライン
├── requirements.txt # Python依存関係
├── config.yaml # 設定ファイル
├── main.py # エントリーポイント
│
├── src/ # 本番コード（ライブラリ/モジュール群）
│ ├── amazon_scraper.py
│ ├── gemini_script_generator.py
│ ├── subtitle_generator.py
│ ├── subtitle_image_generator.py
│ ├── video_generator.py
│ ├── voicevox_tts.py
│ └── ...
│
├── tests/ # pytestによる単体テスト
│ ├── test_amazon_api.py
│ ├── test_video_generator.py
│ └── ...
│
├── examples/ # 実験・サンプルコード（元: src直下に混在していたもの）
│ ├── ffmpeg_sample.py
│ ├── simple_video_test.py
│ └── ...
│
├── data/ # 入力データ（画像・HTMLサンプル）
│ ├── amazon_page_sample.html
│ ├── simple_background.jpg
│ └── ...
│
├── output/ # 生成された完成動画など
│ └── meicho_video.mp4
│
├── temp/ # 一時ファイル（キャッシュや途中生成物）
│ └── *.wav, *.png, *.mp4
│
├── logs/ # 実行ログ
│ └── meicho_minutes.log
│
├── todo.md # タスク管理（テストリスト含む）
└── venv/ # Python仮想環境（.gitignore推奨）


## 開発環境
- Python 3.10+
- pytest
- FFmpeg
- Pillow, MoviePy, OpenAI API, など（詳細は `requirements.txt` を参照）


## TDD

### 基本方針
- **IMPORTANT**: 本プロジェクトでは **必ずTDD（テスト駆動開発）** に従って開発を行うこと。  
- Claudeは **TDDの各ステップを順番に実行し、省略・飛ばしをしてはならない**。  

### TDDワークフロー（t-wada式）

1. **テストリストを作成する**  
   - 変更や新機能に対して期待される動作を、`todo.md` に網羅的にリストアップする。  
   - この段階では **実装の設計判断は行わず**、あくまでインターフェースと期待動作のみを定義する。  

2. 🔴 Red: **ひとつだけテストを書く**  
   - テストリストから「ひとつだけ」取り出し、実際に、具体的で、実行可能なテストコードに翻訳する。  
   - テストは **準備 → 実行 → 検証（アサーション）** の形を備えること。  
   - 一度に複数のテストを書いてはいけない。  
   - テストが失敗することを確認する。  

3. 🟢 Green: **テストを失敗させる → 成功させる**  
   - その後、プロダクトコードを修正し、そのテストと既存の全テストを成功させる。  
   - 成功後、`todo.md` の該当項目にチェックする。  
   - 過程で新しい必要性に気づいた場合は、テストリストに追記する。  

4. 🔵 Refactor: **リファクタリング**  
   - 必要に応じて実装の設計を改善する。  
   - リファクタリングは必須ではないが、次のサイクルに進む前に行う。  

5. **繰り返す**  
   - テストリストが空になるまで、ステップ2に戻って繰り返す。  

---

###  TDDにおける注意点

- Claudeは **必ず1サイクルごとにユーザーの確認を受けてからコミットし、次へ進むこと**。  
- **1テストケースにつき1アサーション** を原則とする。  
- **1サイクルにつき1コミット**。  
- コミットは **Conventional Commits** に従うこと。  

---


## コミュニケーション
- **IMPORTANT**: 本プロジェクトでは思考も含め、**必ず日本語** で回答してください。