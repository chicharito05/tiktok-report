# TikTok Report Tool

TikTokアカウントのパフォーマンスデータを自動収集・分析し、クライアント向け月次レポートを自動生成する社内ツールです。

合同会社LEAD ONE 自社利用専用。

## 技術スタック

- **DB / Auth / Storage**: Supabase (PostgreSQL + Auth + Storage)
- **データ収集**: Python + Playwright / Claude Vision API
- **AI分析**: Claude API (claude-sonnet-4-20250514)
- **レポート生成**: Jinja2 + WeasyPrint (HTML → PDF)
- **Web UI** (Phase 3): Next.js (App Router) + TypeScript + Tailwind CSS

## セットアップ

### 1. Python環境

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 環境変数

```bash
cp .env.example .env
# .env を編集して各種キーを設定
```

### 3. Supabase

1. Supabaseプロジェクトを作成
2. `supabase/migrations/001_initial_schema.sql` をSQL Editorで実行
3. `.env` に `SUPABASE_URL` と `SUPABASE_KEY` を設定

### 4. クライアント登録

`config/clients.yaml` にクライアント情報を追加し、SupabaseのclientsテーブルにもINSERT。

## 使い方

### CSV取り込み（TikTok Studio Overview）

```bash
python worker/csv_import.py --client inthegolf --file data/Overview.csv --year 2026
```

### Playwrightスクレイパー

```bash
python worker/scraper.py --client inthegolf --chrome-profile /path/to/profile
```

### Vision解析（スクリーンショットから抽出）

```bash
python worker/vision_extract.py --client inthegolf --image screenshot.png
```

### 月次分析

```bash
python worker/analyze.py --client inthegolf --period 2026-03
```

## ディレクトリ構成

```
tiktok-report/
├── config/          # クライアント設定
├── worker/          # データ収集・分析スクリプト
├── templates/       # レポートテンプレート (Phase 2)
├── data/            # 入力データ (CSV, スクリーンショット)
├── output/          # 生成済みレポート
├── supabase/        # DBマイグレーション
└── web/             # Web UI (Phase 3)
```
