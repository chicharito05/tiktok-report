-- Phase 3: 認証・RLS・Storageバケット設定

-- ユーザープロフィール
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    display_name TEXT,
    role TEXT NOT NULL DEFAULT 'member' CHECK (role IN ('admin', 'member')),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- auth.usersにユーザーが作成されたら自動でprofilesにも追加
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, email, display_name)
    VALUES (
        NEW.id,
        NEW.email,
        COALESCE(NEW.raw_user_meta_data->>'display_name', split_part(NEW.email, '@', 1))
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- reportsテーブルにgenerated_byのFK追加（既存カラムの型変更は不要、UUIDのまま）
-- generated_byはprofiles.idを参照
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'reports_generated_by_fkey'
    ) THEN
        ALTER TABLE reports
            ADD CONSTRAINT reports_generated_by_fkey
            FOREIGN KEY (generated_by) REFERENCES profiles(id);
    END IF;
END $$;

-- RLSポリシー設定
ALTER TABLE clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_overview ENABLE ROW LEVEL SECURITY;
ALTER TABLE posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

-- 認証済みユーザーは全データ参照可能（社内ツール）
CREATE POLICY "authenticated_select_clients" ON clients FOR SELECT TO authenticated USING (true);
CREATE POLICY "authenticated_select_daily_overview" ON daily_overview FOR SELECT TO authenticated USING (true);
CREATE POLICY "authenticated_select_posts" ON posts FOR SELECT TO authenticated USING (true);
CREATE POLICY "authenticated_select_reports" ON reports FOR SELECT TO authenticated USING (true);
CREATE POLICY "authenticated_select_profiles" ON profiles FOR SELECT TO authenticated USING (auth.uid() = id);

-- INSERT
CREATE POLICY "authenticated_insert_clients" ON clients FOR INSERT TO authenticated WITH CHECK (true);
CREATE POLICY "authenticated_insert_daily_overview" ON daily_overview FOR INSERT TO authenticated WITH CHECK (true);
CREATE POLICY "authenticated_insert_posts" ON posts FOR INSERT TO authenticated WITH CHECK (true);
CREATE POLICY "authenticated_insert_reports" ON reports FOR INSERT TO authenticated WITH CHECK (true);

-- UPDATE
CREATE POLICY "authenticated_update_daily_overview" ON daily_overview FOR UPDATE TO authenticated USING (true);
CREATE POLICY "authenticated_update_posts" ON posts FOR UPDATE TO authenticated USING (true);

-- クライアント管理はadminのみ
CREATE POLICY "admin_update_clients" ON clients FOR UPDATE TO authenticated
    USING (EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin'));
CREATE POLICY "admin_delete_clients" ON clients FOR DELETE TO authenticated
    USING (EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin'));

-- Supabase Storage バケット
INSERT INTO storage.buckets (id, name, public)
VALUES ('reports', 'reports', false)
ON CONFLICT (id) DO NOTHING;

-- Storage RLS
CREATE POLICY "authenticated_read_reports_storage" ON storage.objects FOR SELECT TO authenticated
    USING (bucket_id = 'reports');
CREATE POLICY "authenticated_upload_reports_storage" ON storage.objects FOR INSERT TO authenticated
    WITH CHECK (bucket_id = 'reports');
