-- TikTok Report Tool: 初期スキーマ
-- Phase 1: テーブル作成のみ（RLSは後のPhaseで設定）

-- クライアント管理
CREATE TABLE IF NOT EXISTS clients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    tiktok_username TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 日別Overview（TikTok Studioからエクスポート）
CREATE TABLE IF NOT EXISTS daily_overview (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    video_views INT DEFAULT 0,
    profile_views INT DEFAULT 0,
    likes INT DEFAULT 0,
    comments INT DEFAULT 0,
    shares INT DEFAULT 0,
    UNIQUE (client_id, date)
);

-- 投稿データ
CREATE TABLE IF NOT EXISTS posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    post_date TIMESTAMPTZ,
    caption TEXT,
    views INT DEFAULT 0,
    likes INT DEFAULT 0,
    comments INT DEFAULT 0,
    duration TEXT,
    visibility TEXT,
    UNIQUE (client_id, post_date, caption)
);

-- 生成済みレポート
CREATE TABLE IF NOT EXISTS reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    period TEXT NOT NULL,
    generated_by UUID,
    file_path TEXT,
    generated_at TIMESTAMPTZ DEFAULT now()
);

-- インデックス
CREATE INDEX IF NOT EXISTS idx_daily_overview_client_date ON daily_overview(client_id, date);
CREATE INDEX IF NOT EXISTS idx_posts_client_date ON posts(client_id, post_date);
CREATE INDEX IF NOT EXISTS idx_reports_client_period ON reports(client_id, period);
