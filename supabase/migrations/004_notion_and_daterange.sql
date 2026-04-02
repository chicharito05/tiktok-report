-- ===========================================
-- 004: Notion連携 + 日付範囲レポート対応
-- ===========================================

-- 1. clientsテーブルにNotion DB IDカラムを追加
ALTER TABLE clients ADD COLUMN IF NOT EXISTS notion_database_id TEXT DEFAULT NULL;

-- 2. reportsテーブルを月単位(period) → 日付範囲(start_date/end_date)に変更
ALTER TABLE reports ADD COLUMN IF NOT EXISTS start_date DATE;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS end_date DATE;

-- 既存データのマイグレーション（periodが存在する場合）
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'reports' AND column_name = 'period'
  ) THEN
    UPDATE reports SET
      start_date = (period || '-01')::date,
      end_date = (date_trunc('month', (period || '-01')::date) + interval '1 month' - interval '1 day')::date
    WHERE period IS NOT NULL AND start_date IS NULL;

    ALTER TABLE reports DROP COLUMN period;
  END IF;
END $$;
