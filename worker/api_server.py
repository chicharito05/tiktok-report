"""Worker APIサーバー

Mac mini上で動作し、VercelのAPI Routeから呼び出される。
レポート生成、CSV取込、スクショ解析、Notion同期の各機能をHTTP APIとして提供する。

Usage:
    uvicorn worker.api_server:app --host 0.0.0.0 --port 8787
"""

import asyncio
import logging
import os
import tempfile
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from worker.analyze import analyze_period, get_default_date_range
from worker.normalize import get_supabase_client, resolve_client_id

load_dotenv(override=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="TikTok Report Worker API", version="2.0.0")


class GenerateReportRequest(BaseModel):
    client_slug: str
    start_date: Optional[str] = None  # YYYY-MM-DD
    end_date: Optional[str] = None    # YYYY-MM-DD
    operation_month: Optional[str] = None  # 運用月フィルタ（例: "1ヶ月目"）
    # ユーザー入力の総評・改善案（空ならAI自動生成）
    user_commentary: Optional[dict] = None  # {best_post_analysis, improvement_suggestions, next_month_plan}


class GenerateReportResponse(BaseModel):
    report_id: Optional[str] = None
    html_path: str
    pdf_path: Optional[str] = None
    pptx_path: Optional[str] = None
    html_url: Optional[str] = None
    pptx_url: Optional[str] = None
    message: str
    summary: Optional[dict] = None


class RegenerateReportRequest(BaseModel):
    """プレビュー画面から総評・改善案を修正してHTML/PDF再生成"""
    report_id: str
    best_post_analysis: str = ""
    improvement_suggestions: str = ""
    next_month_plan: str = ""


class UploadCsvResponse(BaseModel):
    rows_imported: int
    message: str


class PostData(BaseModel):
    post_date: str
    caption: str
    views: int
    likes: int
    comments: int
    duration: str
    visibility: str


class UploadScreenshotResponse(BaseModel):
    posts: List[PostData]
    message: str


class NotionSyncRequest(BaseModel):
    client_id: str


class NotionSyncResponse(BaseModel):
    synced: int
    skipped: int
    total: int
    message: str


class FollowerSnapshotRequest(BaseModel):
    client_id: str
    date: str  # YYYY-MM-DD
    follower_count: int


class FollowerSnapshotBulkRequest(BaseModel):
    client_id: str
    snapshots: list  # [{date, follower_count}, ...]


class UpdatePostRequest(BaseModel):
    post_id: str
    caption: Optional[str] = None
    post_date: Optional[str] = None
    views: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None
    watch_through_rate: Optional[float] = None
    two_sec_view_rate: Optional[float] = None
    operation_month: Optional[str] = None


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/generate-report", response_model=GenerateReportResponse)
async def generate_report(req: GenerateReportRequest):
    """report_gen.pyを呼び出してレポートを生成する。"""
    from worker.report_gen import generate_report as run_generate

    if req.start_date and req.end_date:
        start_date, end_date = req.start_date, req.end_date
    else:
        start_date, end_date = get_default_date_range()

    logger.info("レポート生成開始: %s / %s〜%s", req.client_slug, start_date, end_date)

    try:
        html_path, pdf_path, pptx_path, summary = run_generate(
            req.client_slug, start_date, end_date, upload=True,
            user_commentary=req.user_commentary,
            operation_month=req.operation_month,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("レポート生成エラー")
        raise HTTPException(status_code=500, detail=f"レポート生成に失敗しました: {e}")

    # reportsテーブルから最新のレポートIDを取得
    report_id = None
    try:
        supabase = get_supabase_client()
        client_id = resolve_client_id(supabase, req.client_slug)
        result = (
            supabase.table("reports")
            .select("id")
            .eq("client_id", client_id)
            .eq("start_date", start_date)
            .eq("end_date", end_date)
            .order("generated_at", desc=True)
            .limit(1)
            .execute()
        )
        if result.data:
            report_id = result.data[0]["id"]
    except Exception:
        logger.warning("レポートID取得に失敗")

    # signed URL生成
    html_url = None
    pptx_url = None
    try:
        supabase2 = get_supabase_client()
        cid = resolve_client_id(supabase2, req.client_slug)
        html_storage_path = f"reports/{cid}/{start_date}_{end_date}_report.html"
        signed = supabase2.storage.from_("reports").create_signed_url(html_storage_path, 3600)
        if signed and signed.get("signedURL"):
            html_url = signed["signedURL"]
    except Exception:
        logger.warning("HTML signed URL生成に失敗")

    try:
        supabase3 = get_supabase_client()
        cid3 = resolve_client_id(supabase3, req.client_slug)
        pptx_storage_path = f"reports/{cid3}/{start_date}_{end_date}_report.pptx"
        signed_pptx = supabase3.storage.from_("reports").create_signed_url(pptx_storage_path, 3600)
        if signed_pptx and signed_pptx.get("signedURL"):
            pptx_url = signed_pptx["signedURL"]
    except Exception:
        logger.warning("PPTX signed URL生成に失敗")

    return GenerateReportResponse(
        report_id=report_id,
        html_path=str(html_path),
        pdf_path=str(pdf_path) if pdf_path else None,
        pptx_path=str(pptx_path) if pptx_path else None,
        html_url=html_url,
        pptx_url=pptx_url,
        message=f"レポート生成完了: {req.client_slug} / {start_date}〜{end_date}",
        summary=summary,
    )


@app.post("/regenerate-report")
async def regenerate_report(req: RegenerateReportRequest):
    """プレビュー画面から総評・改善案を修正してHTML/PDFを再生成する。"""
    from worker.report_gen import generate_report as run_generate

    supabase = get_supabase_client()

    # report_idからレポート情報を取得
    result = supabase.table("reports").select("*, clients(name, id)").eq("id", req.report_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="レポートが見つかりません")

    report = result.data
    client_name = report["clients"]["name"]
    client_id = report["client_id"]
    start_date = report["start_date"]
    end_date = report["end_date"]

    user_commentary = {
        "best_post_analysis": req.best_post_analysis,
        "improvement_suggestions": req.improvement_suggestions,
        "next_month_plan": req.next_month_plan,
    }

    logger.info("レポート再生成: %s / %s〜%s", client_name, start_date, end_date)

    try:
        # 古いStorageファイルを削除してから再アップロード
        try:
            safe_prefix = f"reports/{client_id}"
            supabase.storage.from_("reports").remove([
                f"{safe_prefix}/{start_date}_{end_date}_report.html",
                f"{safe_prefix}/{start_date}_{end_date}_report.pdf",
            ])
        except Exception:
            pass  # 削除失敗は無視

        html_path, pdf_path, pptx_path, _summary = run_generate(
            client_name, start_date, end_date, upload=True,
            user_commentary=user_commentary,
        )
    except Exception as e:
        logger.exception("レポート再生成エラー")
        raise HTTPException(status_code=500, detail=f"再生成に失敗しました: {e}")

    # signed URL生成
    html_url = None
    pdf_url = None
    try:
        html_storage_path = f"reports/{client_id}/{start_date}_{end_date}_report.html"
        signed = supabase.storage.from_("reports").create_signed_url(html_storage_path, 3600)
        if signed and signed.get("signedURL"):
            html_url = signed["signedURL"]
    except Exception:
        pass

    try:
        pdf_storage_path = f"reports/{client_id}/{start_date}_{end_date}_report.pdf"
        signed = supabase.storage.from_("reports").create_signed_url(pdf_storage_path, 3600)
        if signed and signed.get("signedURL"):
            pdf_url = signed["signedURL"]
    except Exception:
        pass

    pptx_url = None
    try:
        pptx_storage_path = f"reports/{client_id}/{start_date}_{end_date}_report.pptx"
        signed_pptx = supabase.storage.from_("reports").create_signed_url(pptx_storage_path, 3600)
        if signed_pptx and signed_pptx.get("signedURL"):
            pptx_url = signed_pptx["signedURL"]
    except Exception:
        pass

    return {
        "message": "レポートを再生成しました",
        "html_url": html_url,
        "pdf_url": pdf_url,
        "pptx_url": pptx_url,
    }


@app.post("/upload-csv", response_model=UploadCsvResponse)
async def upload_csv(
    client_slug: str = Form(...),
    year: int = Form(...),
    csv_type: Optional[str] = Form(None),
    file: UploadFile = File(...),
):
    """CSVファイルを受け取ってdaily_overview or postsに取り込む。"""
    from worker.csv_import import detect_csv_type, parse_csv, parse_posts_csv
    from worker.normalize import (
        get_supabase_client,
        resolve_client_id,
        upsert_daily_overview,
        upsert_posts,
    )

    with tempfile.NamedTemporaryFile(
        suffix=".csv", delete=False, mode="wb"
    ) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        detected_type = csv_type or detect_csv_type(tmp_path)
        supabase = get_supabase_client()
        client_id = resolve_client_id(supabase, client_slug)

        if detected_type == "posts":
            rows = parse_posts_csv(tmp_path, year)
            if not rows:
                return UploadCsvResponse(rows_imported=0, message="取り込みデータがありません")
            count = upsert_posts(supabase, client_id, rows)
            return UploadCsvResponse(
                rows_imported=count,
                message=f"{count}件の動画データを取り込みました",
            )
        else:
            rows = parse_csv(tmp_path, year)
            if not rows:
                return UploadCsvResponse(rows_imported=0, message="取り込みデータがありません")
            count = upsert_daily_overview(supabase, client_id, rows)
            return UploadCsvResponse(
                rows_imported=count,
                message=f"{count}件の概要データを取り込みました",
            )
    except Exception as e:
        logger.exception("CSV取込エラー")
        raise HTTPException(status_code=500, detail=f"CSV取込に失敗しました: {e}")
    finally:
        os.unlink(tmp_path)


@app.post("/upload-screenshot", response_model=UploadScreenshotResponse)
async def upload_screenshot(
    client_slug: str = Form(...),
    file: UploadFile = File(...),
):
    """スクリーンショットを受け取ってVision APIで解析する。"""
    from worker.vision_extract import extract_posts_from_image

    suffix = Path(file.filename or "image.png").suffix
    with tempfile.NamedTemporaryFile(
        suffix=suffix, delete=False, mode="wb"
    ) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        post_rows = extract_posts_from_image(tmp_path)
        posts = [
            PostData(
                post_date=p.post_date,
                caption=p.caption,
                views=p.views,
                likes=p.likes,
                comments=p.comments,
                duration=p.duration,
                visibility=p.visibility,
            )
            for p in post_rows
        ]
        return UploadScreenshotResponse(
            posts=posts,
            message=f"{len(posts)}件の投稿を検出しました",
        )
    except Exception as e:
        logger.exception("スクショ解析エラー")
        raise HTTPException(status_code=500, detail=f"スクショ解析に失敗しました: {e}")
    finally:
        os.unlink(tmp_path)


@app.post("/save-posts")
async def save_posts(
    client_slug: str = Form(...),
    posts_json: str = Form(...),
):
    """解析済み投稿データをDBに保存する。"""
    import json
    from worker.normalize import PostRow, upsert_posts

    try:
        posts_data = json.loads(posts_json)
        post_rows = [
            PostRow(
                post_date=p["post_date"],
                caption=p["caption"],
                views=p["views"],
                likes=p["likes"],
                comments=p["comments"],
                duration=p.get("duration", ""),
                visibility=p.get("visibility", ""),
            )
            for p in posts_data
        ]

        supabase = get_supabase_client()
        client_id = resolve_client_id(supabase, client_slug)
        count = upsert_posts(supabase, client_id, post_rows)

        return {"rows_saved": count, "message": f"{count}件の投稿を保存しました"}
    except Exception as e:
        logger.exception("投稿保存エラー")
        raise HTTPException(status_code=500, detail=f"投稿保存に失敗しました: {e}")


@app.post("/sync-notion", response_model=NotionSyncResponse)
async def sync_notion(req: NotionSyncRequest):
    """クライアントのNotion DBから投稿データを同期する。

    タイトル・投稿日のみ高速同期する。
    原稿本文は別エンドポイント /fetch-notion-content で取得する。
    """
    from worker.notion_sync import sync_notion_to_posts

    supabase = get_supabase_client()

    # クライアントのNotion DB IDを取得
    client_result = (
        supabase.table("clients")
        .select("notion_database_id")
        .eq("id", req.client_id)
        .single()
        .execute()
    )
    if not client_result.data:
        raise HTTPException(status_code=404, detail="クライアントが見つかりません")

    notion_db_id = client_result.data.get("notion_database_id")
    if not notion_db_id:
        raise HTTPException(
            status_code=400,
            detail="Notion DB IDが設定されていません。クライアント管理画面で設定してください。",
        )

    try:
        # タイトル・投稿日のみ高速同期（本文なし）
        result = await asyncio.to_thread(
            sync_notion_to_posts,
            supabase, req.client_id, notion_db_id, False,
        )

        return NotionSyncResponse(
            synced=result["synced"],
            skipped=result["skipped"],
            total=result["total"],
            message=f"Notion同期完了: {result['synced']}件同期, {result['skipped']}件スキップ",
        )
    except Exception as e:
        logger.exception("Notion同期エラー")
        raise HTTPException(status_code=500, detail=f"Notion同期に失敗しました: {e}")


@app.post("/fetch-notion-content")
async def fetch_notion_content(req: NotionSyncRequest):
    """未取得の原稿本文をNotionから取得してDBに保存する。

    レート制限対応（0.35秒/リクエスト）+ 差分取得（取得済みスキップ）。
    時間がかかるため、フロントエンドは長めのタイムアウトを設定すること。
    """
    from worker.notion_sync import sync_notion_to_posts

    supabase = get_supabase_client()

    client_result = (
        supabase.table("clients")
        .select("notion_database_id")
        .eq("id", req.client_id)
        .single()
        .execute()
    )
    if not client_result.data:
        raise HTTPException(status_code=404, detail="クライアントが見つかりません")

    notion_db_id = client_result.data.get("notion_database_id")
    if not notion_db_id:
        raise HTTPException(
            status_code=400,
            detail="Notion DB IDが設定されていません。",
        )

    try:
        result = await asyncio.to_thread(
            sync_notion_to_posts,
            supabase, req.client_id, notion_db_id, True,
        )

        content_fetched = result.get("content_fetched", 0)
        return {
            "synced": result["synced"],
            "content_fetched": content_fetched,
            "total": result["total"],
            "message": f"原稿本文 {content_fetched}件取得完了",
        }
    except Exception as e:
        logger.exception("原稿本文取得エラー")
        raise HTTPException(status_code=500, detail=f"原稿本文取得に失敗しました: {e}")


@app.get("/notion-articles")
async def get_notion_articles(
    client_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """クライアントの原稿一覧（本文付き）を取得する。"""
    from worker.notion_sync import fetch_notion_articles

    supabase = get_supabase_client()

    # クライアントのNotion DB IDを取得
    client_result = (
        supabase.table("clients")
        .select("notion_database_id")
        .eq("id", client_id)
        .single()
        .execute()
    )
    if not client_result.data:
        raise HTTPException(status_code=404, detail="クライアントが見つかりません")

    notion_db_id = client_result.data.get("notion_database_id", "")

    try:
        articles = fetch_notion_articles(
            supabase, client_id, notion_db_id,
            start_date=start_date, end_date=end_date,
        )
        return {"articles": articles}
    except Exception as e:
        logger.exception("原稿一覧取得エラー")
        raise HTTPException(status_code=500, detail=f"原稿一覧の取得に失敗しました: {e}")


@app.post("/update-post")
async def update_post(req: UpdatePostRequest):
    """個別投稿のデータを更新する。"""
    supabase = get_supabase_client()
    update_data = {}
    if req.caption is not None:
        update_data["caption"] = req.caption
    if req.post_date is not None:
        # date-onlyの場合はタイムゾーン付きに変換
        pd = req.post_date
        if len(pd) == 10:
            pd = pd + "T00:00:00+09:00"
        update_data["post_date"] = pd
    if req.views is not None:
        update_data["views"] = req.views
    if req.likes is not None:
        update_data["likes"] = req.likes
    if req.comments is not None:
        update_data["comments"] = req.comments
    if req.shares is not None:
        update_data["shares"] = req.shares
    if req.watch_through_rate is not None:
        update_data["watch_through_rate"] = req.watch_through_rate
    if req.two_sec_view_rate is not None:
        update_data["two_sec_view_rate"] = req.two_sec_view_rate
    if req.operation_month is not None:
        update_data["operation_month"] = req.operation_month

    if not update_data:
        return {"message": "更新するデータがありません"}

    try:
        supabase.table("posts").update(update_data).eq("id", req.post_id).execute()
        return {"message": "投稿データを更新しました"}
    except Exception as e:
        logger.exception("投稿更新エラー")
        raise HTTPException(status_code=500, detail=f"投稿更新に失敗しました: {e}")


class CreatePostRequest(BaseModel):
    client_id: str
    caption: str = ""
    post_date: str  # YYYY-MM-DD
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0


class DeletePostRequest(BaseModel):
    post_id: str


class DeleteFollowerSnapshotRequest(BaseModel):
    snapshot_id: str


@app.post("/create-post")
async def create_post(req: CreatePostRequest):
    """投稿を手動で新規作成する。"""
    supabase = get_supabase_client()
    try:
        pd = req.post_date
        if len(pd) == 10:
            pd = pd + "T00:00:00+09:00"
        result = supabase.table("posts").insert({
            "client_id": req.client_id,
            "caption": req.caption,
            "post_date": pd,
            "views": req.views,
            "likes": req.likes,
            "comments": req.comments,
            "shares": req.shares,
        }).execute()
        return {"message": "投稿を作成しました", "post": result.data[0] if result.data else None}
    except Exception as e:
        logger.exception("投稿作成エラー")
        raise HTTPException(status_code=500, detail=f"投稿作成に失敗しました: {e}")


@app.post("/delete-post")
async def delete_post(req: DeletePostRequest):
    """投稿を削除する。"""
    supabase = get_supabase_client()
    try:
        supabase.table("posts").delete().eq("id", req.post_id).execute()
        return {"message": "投稿を削除しました"}
    except Exception as e:
        logger.exception("投稿削除エラー")
        raise HTTPException(status_code=500, detail=f"投稿削除に失敗しました: {e}")


@app.post("/delete-follower-snapshot")
async def delete_follower_snapshot(req: DeleteFollowerSnapshotRequest):
    """フォロワースナップショットを削除する。"""
    supabase = get_supabase_client()
    try:
        supabase.table("follower_snapshots").delete().eq("id", req.snapshot_id).execute()
        return {"message": "フォロワーデータを削除しました"}
    except Exception as e:
        logger.exception("フォロワーデータ削除エラー")
        raise HTTPException(status_code=500, detail=f"削除に失敗しました: {e}")


@app.get("/follower-snapshots")
async def list_follower_snapshots(
    client_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """クライアントのフォロワー数スナップショット一覧を取得する。"""
    supabase = get_supabase_client()
    query = supabase.table("follower_snapshots").select("*").eq("client_id", client_id)
    if start_date:
        query = query.gte("date", start_date)
    if end_date:
        query = query.lte("date", end_date)
    result = query.order("date", desc=True).execute()
    return {"snapshots": result.data}


@app.post("/follower-snapshots")
async def upsert_follower_snapshot(req: FollowerSnapshotRequest):
    """フォロワー数スナップショットを登録・更新する。"""
    supabase = get_supabase_client()
    try:
        supabase.table("follower_snapshots").upsert(
            {
                "client_id": req.client_id,
                "date": req.date,
                "follower_count": req.follower_count,
            },
            on_conflict="client_id,date",
        ).execute()
        return {"message": "フォロワー数を保存しました"}
    except Exception as e:
        logger.exception("フォロワー数保存エラー")
        raise HTTPException(status_code=500, detail=f"保存に失敗しました: {e}")


@app.post("/follower-snapshots/bulk")
async def bulk_upsert_follower_snapshots(req: FollowerSnapshotBulkRequest):
    """フォロワー数スナップショットを一括登録・更新する。"""
    supabase = get_supabase_client()
    try:
        rows = [
            {
                "client_id": req.client_id,
                "date": s["date"],
                "follower_count": s["follower_count"],
            }
            for s in req.snapshots
        ]
        supabase.table("follower_snapshots").upsert(
            rows, on_conflict="client_id,date"
        ).execute()
        return {"message": f"{len(rows)}件のフォロワー数を保存しました", "count": len(rows)}
    except Exception as e:
        logger.exception("フォロワー数一括保存エラー")
        raise HTTPException(status_code=500, detail=f"一括保存に失敗しました: {e}")


@app.get("/posts")
async def list_posts(
    client_slug: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """クライアントの投稿データ一覧を取得する。"""
    supabase = get_supabase_client()
    client_id = resolve_client_id(supabase, client_slug)

    query = supabase.table("posts").select("*").eq("client_id", client_id)
    if start_date:
        query = query.gte("post_date", start_date + "T00:00:00+09:00")
    if end_date:
        query = query.lte("post_date", end_date + "T23:59:59+09:00")

    result = query.order("post_date", desc=True).execute()
    return {"posts": result.data}
