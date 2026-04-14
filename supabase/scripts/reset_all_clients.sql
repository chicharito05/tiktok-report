-- ============================================================
-- 全クライアントデータの完全削除スクリプト（1 回だけ実行）
-- ============================================================
--
-- 2026-04-10: 運用月ベースのレポート生成体制へ移行するにあたり、
-- 既存 5 社（inthegolf / kyuden / kai_city / dr_recella / sanix）を
-- 一旦すべて削除し、Notion 連携済みクライアントを新規登録しなおす。
--
-- clients 表を TRUNCATE することで ON DELETE CASCADE により
--   - daily_overview
--   - posts
--   - follower_snapshots
--   - reports
-- の関連行もすべて削除される。
--
-- ⚠️  本スクリプトは不可逆。実行前に Supabase のバックアップを取得すること。
-- ⚠️  Supabase Storage 上の reports/<client_id>/*.{html,pdf,pptx} は
--     この SQL では消えない。ダッシュボードから手動削除するか、
--     service_role で storage.objects を削除すること。
-- ============================================================

BEGIN;

-- 件数確認（実行前のスナップショット）
SELECT 'clients' AS table_name, count(*) FROM clients
UNION ALL
SELECT 'daily_overview', count(*) FROM daily_overview
UNION ALL
SELECT 'posts', count(*) FROM posts
UNION ALL
SELECT 'follower_snapshots', count(*) FROM follower_snapshots
UNION ALL
SELECT 'reports', count(*) FROM reports;

-- CASCADE で子テーブルごと削除
TRUNCATE TABLE clients RESTART IDENTITY CASCADE;

-- 削除後の件数確認（すべて 0 になっていることを確認）
SELECT 'clients' AS table_name, count(*) FROM clients
UNION ALL
SELECT 'daily_overview', count(*) FROM daily_overview
UNION ALL
SELECT 'posts', count(*) FROM posts
UNION ALL
SELECT 'follower_snapshots', count(*) FROM follower_snapshots
UNION ALL
SELECT 'reports', count(*) FROM reports;

-- 問題なければ COMMIT、やめる場合は ROLLBACK;
COMMIT;
