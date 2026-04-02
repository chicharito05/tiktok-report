-- フォロワー数スナップショットテーブル
CREATE TABLE IF NOT EXISTS follower_snapshots (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
  date DATE NOT NULL,
  follower_count INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(client_id, date)
);

-- RLSポリシー
ALTER TABLE follower_snapshots ENABLE ROW LEVEL SECURITY;
CREATE POLICY "follower_snapshots_select" ON follower_snapshots FOR SELECT USING (true);
CREATE POLICY "follower_snapshots_insert" ON follower_snapshots FOR INSERT WITH CHECK (true);
CREATE POLICY "follower_snapshots_update" ON follower_snapshots FOR UPDATE USING (true);
CREATE POLICY "follower_snapshots_delete" ON follower_snapshots FOR DELETE USING (true);
