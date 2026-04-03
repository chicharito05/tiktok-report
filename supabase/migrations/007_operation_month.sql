-- 運用月カラムを追加
ALTER TABLE posts ADD COLUMN IF NOT EXISTS operation_month TEXT;
COMMENT ON COLUMN posts.operation_month IS '運用月（例: 1ヶ月目, 2ヶ月目）Notionから同期';
CREATE INDEX IF NOT EXISTS idx_posts_operation_month ON posts(client_id, operation_month);
