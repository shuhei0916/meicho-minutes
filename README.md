# 📚 meicho-minutes

「１分で名著」 — Amazon書籍を自動で要約し、ショート動画として生成・投稿するプロジェクト。
AIによる台本作成、音声合成、動画編集を組み合わせ、アフィリエイト収益を狙います。

## 🚀 プロジェクト概要

Amazon APIから書籍情報・レビューを取得

LLM（GPT）で1分解説用の台本を生成

AI音声でナレーションを作成

書影＋背景画像＋字幕を合成してショート動画を自動生成

YouTube APIを通じてアップロード（説明欄にアフィリエイトリンク付き）

## 📂 ワークフロー
flowchart TD
    A[Amazon API] --> B[書籍データ取得]
    B --> C[GPTで台本生成]
    C --> D[AI音声合成]
    C --> E[字幕テキスト生成]
    D --> F[動画生成]
    E --> F
    B --> F
    F --> G[YouTube API アップロード]

## 🛠 技術スタック

言語: Python 3.11+

データ取得: Amazon Product Advertising API（またはスクレイピング）

AI処理(要約・台本生成) : Gemini API

動画編集: FFmpeg, MoviePy

音声合成: VOICEVOX

画像: Amazon公式書影画像

自動化: cron / GitHub Actions

公開: YouTube Data API v3