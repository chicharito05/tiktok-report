-- ===========================================
-- 008: reports テーブルを運用月ベースに移行
-- ===========================================
--
-- 2026-04-10: レポート生成を「日付範囲指定」から「運用月（◯ヶ月目）指定」に
-- 完全移行する。reports テーブルに operation_month 列を追加し、
-- start_date / end_date は参考情報として残しつつ NOT NULL 制約を外す。
--
-- 既存データはリセットスクリプト (scripts/reset_all_clients.sql) で
-- すべて削除される前提のため、データ移行ロジックは含めない。
-- ===========================================

ALTER TABLE reports ADD COLUMN IF NOT EXISTS operation_month TEXT;
COMMENT ON COLUMN reports.operation_month IS '運用月ラベル（例: "1ヶ月目"）。Notionの「運用月」プロパティと一致。';

-- start_date / end_date は migration 004 時点で NOT NULL 指定されていないため
-- 制約変更は不要（参考情報として残す）。

-- 同じクライアント × 同じ運用月のレポートは最新 1 件だけ持つ運用に備え、
-- 参照用の複合インデックスを作成（UNIQUE にはしない: 再生成履歴を残せるように）
CREATE INDEX IF NOT EXISTS idx_reports_client_operation_month
    ON reports(client_id, operation_month);
