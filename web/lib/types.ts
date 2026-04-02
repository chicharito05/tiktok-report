export interface Client {
  id: string;
  name: string;
  tiktok_username: string | null;
  notion_database_id: string | null;
  created_at: string;
}

export interface DailyOverview {
  id: string;
  client_id: string;
  date: string;
  video_views: number;
  profile_views: number;
  likes: number;
  comments: number;
  shares: number;
}

export interface Post {
  id: string;
  client_id: string;
  post_date: string;
  caption: string;
  views: number;
  likes: number;
  comments: number;
  duration: string;
  visibility: string;
  notion_content: string | null;
}

export interface Report {
  id: string;
  client_id: string;
  start_date: string;
  end_date: string;
  generated_by: string | null;
  file_path: string | null;
  generated_at: string;
  // joined fields
  clients?: { name: string };
  profiles?: { display_name: string | null; email: string };
}

export interface Profile {
  id: string;
  email: string;
  display_name: string | null;
  role: "admin" | "member";
  created_at: string;
}

export interface GenerateReportResponse {
  report_id: string | null;
  html_path: string;
  pdf_path: string | null;
  message: string;
}

export interface UploadCsvResponse {
  rows_imported: number;
  message: string;
}

export interface ScreenshotPost {
  post_date: string;
  caption: string;
  views: number;
  likes: number;
  comments: number;
  duration: string;
  visibility: string;
}

export interface UploadScreenshotResponse {
  posts: ScreenshotPost[];
  message: string;
}
