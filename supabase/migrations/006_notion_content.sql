-- 投稿テーブルにNotion原稿本文カラムを追加
ALTER TABLE posts ADD COLUMN IF NOT EXISTS notion_content TEXT;

COMMENT ON COLUMN posts.notion_content IS 'Notionページから取得した原稿本文';
