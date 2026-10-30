"""导出任务的 Celery 入口，以及过期文件的清扫。

状态一律落 `ExportJob` 表，不用 `AsyncResult`（与 `crawler.CrawlJob` 同一范式）。

⚠️ **部署强耦合**：本任务路由到 `export` 队列。生产 worker 的启动命令必须包含
该队列（`-Q crawl,crawl_slow,export`），否则任务消息会无人消费、永远停在
pending。本仓历史上踩过一次「recompute 堆积在没人消费的 default 队列、榜单
两天没重算」，因此这里再加一道兜底：`reap_stale_export_jobs` 会把超过 30 分钟
仍未完成的 pending/running 任务判为 failed，用户不会无限等待。
"""
import logging
import time
from datetime import timedelta
from pathlib import Path

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from apps.exports.models import ExportEvent, ExportJob
from apps.exports.services import ExportError, audit, write_export_file

logger = logging.getLogger(__name__)

STALE_MINUTES = 30
ORPHAN_TMP_SECONDS = 24 * 3600


def _fail(job, code, message):
    job.status = ExportJob.Status.FAILED
    job.finished_at = timezone.now()
    job.error_message = f"[{code}] {message}"[:4000]
    job.save(update_fields=["status", "finished_at", "error_message",
                            "updated_at"])
    return {"ok": False, "code": code}


def _authorize(job):
    """执行前重新鉴权。

    排队期间 actor 可能被降级或转校；若只信任创建时的判断，被撤职的管理员
    仍能拿到本校全量学号。这里必须重取当前状态。
    """
    actor = job.actor
    if actor is None:
        return "actor_missing"
    if not (actor.is_super_admin or actor.is_school_admin):
        return "permission_revoked"
    if not actor.is_super_admin:
        if actor.school_id is None:
            return "no_school"
        if actor.school_id not in (job.scope_school_ids or []):
            return "school_changed"
    return None


def run_export(job_id, celery_task_id=""):
    """同步/异步共用入口。返回结果字典，不抛异常。"""
    job = (ExportJob.objects
           .select_related("actor")
           .filter(pk=job_id)
           .first())
    if job is None:
        return {"ok": False, "code": "not_found"}
    if job.status not in (ExportJob.Status.PENDING, ExportJob.Status.RUNNING):
        return {"ok": False, "code": f"status_{job.status}"}

    job.status = ExportJob.Status.RUNNING
    job.started_at = job.started_at or timezone.now()
    if celery_task_id:
        job.celery_task_id = celery_task_id[:64]
    job.save(update_fields=["status", "started_at", "celery_task_id",
                            "updated_at"])

    denial = _authorize(job)
    if denial:
        audit(job.actor, ExportEvent.DENIED, job=job, reason=denial,
              detail={"phase": "task_start"})
        return _fail(job, denial, "权限已变更，导出已终止")

    try:
        stats = write_export_file(job)
    except ExportError as exc:
        return _fail(job, exc.code, str(exc))
    except Exception as exc:  # noqa: BLE001 - 任务边界必须兜住一切
        logger.exception("导出生成失败 job=%s", job.pk)
        return _fail(job, "export_failed", str(exc)[:1000])

    job.status = ExportJob.Status.SUCCEEDED
    job.finished_at = timezone.now()
    job.expires_at = timezone.now() + timedelta(
        hours=settings.EXPORT_FILE_TTL_HOURS)
    job.error_message = ""
    job.save(update_fields=["status", "finished_at", "expires_at",
                            "error_message", "updated_at"])
    return {"ok": True, "row_count": stats["row_count"],
            "sheet_count": job.sheet_count}


@shared_task(bind=True, name="apps.exports.tasks.generate_export_task")
def generate_export_task(self, job_id):
    return run_export(job_id, celery_task_id=self.request.id or "")


def enqueue_export(job):
    """把任务丢进 export 队列。broker 不可用时立刻失败，绝不让用户干等。"""
    try:
        async_result = generate_export_task.apply_async(
            args=[job.pk], queue="export")
    except Exception:  # noqa: BLE001 - 队列不可用是环境问题，不是 bug
        logger.exception("导出任务入队失败 job=%s", job.pk)
        job.status = ExportJob.Status.FAILED
        job.finished_at = timezone.now()
        job.error_message = "[queue_unavailable] 任务队列不可用，请稍后重试"
        job.save(update_fields=["status", "finished_at", "error_message",
                                "updated_at"])
        return False
    job.celery_task_id = (async_result.id or "")[:64]
    job.save(update_fields=["celery_task_id", "updated_at"])
    return True


def reap_stale_export_jobs(minutes=STALE_MINUTES):
    """卡死兜底：超过 N 分钟没跑完的 pending/running 一律判失败。

    同时覆盖 pending —— worker 没起 / 队列无人消费时任务永远停在排队中，
    只兜 running 会让用户无限等待。
    """
    cutoff = timezone.now() - timedelta(minutes=minutes)
    stale = ExportJob.objects.filter(
        status__in=[ExportJob.Status.PENDING, ExportJob.Status.RUNNING],
        created_at__lt=cutoff,
    )
    count = 0
    for job in stale:
        job.status = ExportJob.Status.FAILED
        job.finished_at = timezone.now()
        job.error_message = (f"[task_timeout] 超过 {minutes} 分钟未完成，"
                             "已自动终止，请重试")
        job.save(update_fields=["status", "finished_at", "error_message",
                                "updated_at"])
        count += 1
    if count:
        logger.warning("清理卡死导出任务 %s 个", count)
    return count


def purge_expired_exports():
    """删过期文件、清孤儿临时文件、执行磁盘配额。"""
    root = Path(settings.EXPORT_ROOT)
    if not root.exists():
        return {"expired": 0, "orphan": 0, "quota": 0}

    now = timezone.now()
    expired = 0
    for job in ExportJob.objects.filter(
            status=ExportJob.Status.SUCCEEDED,
            expires_at__lt=now).only("id", "file_path"):
        _remove_file(root / job.file_path if job.file_path else None)
        ExportJob.objects.filter(pk=job.pk).update(
            status=ExportJob.Status.EXPIRED, file_path="")
        expired += 1

    orphan = 0
    for path in root.glob("*.tmp"):
        try:
            if time.time() - path.stat().st_mtime > ORPHAN_TMP_SECONDS:
                path.unlink()
                orphan += 1
        except OSError:
            pass

    quota = _enforce_quota(root)
    return {"expired": expired, "orphan": orphan, "quota": quota}


def _remove_file(path):
    if not path:
        return
    try:
        if path.exists():
            path.unlink()
    except OSError:
        logger.warning("导出文件删除失败 %s", path, exc_info=True)


def remove_export_file(path):
    """公开别名：视图层撤销任务时复用同一套删除逻辑，避免两份实现。"""
    return _remove_file(path)


def _enforce_quota(root):
    """磁盘配额：超出后按创建时间从旧到新删，直到回到配额内。"""
    try:
        files = [(p, p.stat()) for p in root.glob("*.xlsx")]
    except OSError:
        return 0
    total = sum(st.st_size for _p, st in files)
    quota = settings.EXPORT_DISK_QUOTA_BYTES
    if total <= quota:
        return 0
    files.sort(key=lambda item: item[1].st_mtime)
    removed = 0
    for path, st in files:
        if total <= quota:
            break
        try:
            path.unlink()
            total -= st.st_size
            removed += 1
            ExportJob.objects.filter(file_path=path.name).update(
                status=ExportJob.Status.EXPIRED, file_path="")
        except OSError:
            continue
    if removed:
        logger.warning("导出目录超配额，清理最旧文件 %s 个", removed)
    return removed


@shared_task(name="apps.exports.tasks.export_maintenance_task")
def export_maintenance_task():
    """每小时一次：清理卡死任务 + 过期文件 + 磁盘配额。"""
    return {
        "stale": reap_stale_export_jobs(),
        **purge_expired_exports(),
    }
