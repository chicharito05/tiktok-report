import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** 日付範囲を日本語表記に変換する */
export function formatDateRange(startDate: string, endDate: string): string {
  const start = new Date(startDate + "T00:00:00");
  const end = new Date(endDate + "T00:00:00");

  const sy = start.getFullYear();
  const sm = start.getMonth() + 1;
  const sd = start.getDate();
  const ey = end.getFullYear();
  const em = end.getMonth() + 1;
  const ed = end.getDate();

  // 同一月の月初〜月末なら「YYYY年M月」
  const lastDay = new Date(sy, sm, 0).getDate();
  if (sy === ey && sm === em && sd === 1 && ed === lastDay) {
    return `${sy}年${sm}月`;
  }
  if (sy === ey && sm === em) {
    return `${sy}年${sm}月${sd}日〜${ed}日`;
  }
  if (sy === ey) {
    return `${sy}年${sm}月${sd}日〜${em}月${ed}日`;
  }
  return `${sy}年${sm}月${sd}日〜${ey}年${em}月${ed}日`;
}

/** ISO日時 → YYYY/MM/DD */
export function formatDate(dateStr: string): string {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  return `${d.getFullYear()}/${String(d.getMonth() + 1).padStart(2, "0")}/${String(d.getDate()).padStart(2, "0")}`;
}

/** 数値をカンマ区切りに */
export function formatNumber(n: number): string {
  return n.toLocaleString("ja-JP");
}

/** デフォルトの対象期間（前月1日〜末日）を返す */
export function getDefaultDateRange(): { startDate: string; endDate: string } {
  const now = new Date();
  const prevMonth = new Date(now.getFullYear(), now.getMonth() - 1, 1);
  const lastDay = new Date(prevMonth.getFullYear(), prevMonth.getMonth() + 1, 0).getDate();

  const y = prevMonth.getFullYear();
  const m = String(prevMonth.getMonth() + 1).padStart(2, "0");

  return {
    startDate: `${y}-${m}-01`,
    endDate: `${y}-${m}-${String(lastDay).padStart(2, "0")}`,
  };
}

/** Worker API のベースURL */
export function getWorkerApiUrl(): string {
  return process.env.WORKER_API_URL || "http://localhost:8787";
}
