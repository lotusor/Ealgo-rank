"""导出学校赛情：接口层。

权限模型三层，缺一层就是漏洞（改之前请逐条确认）：

1. 视图层 `IsSchoolAdmin` —— 回答「是不是管理员」。
2. 查询集收口 `get_queryset()` —— 校管只能看到自己创建的任务，别人的 id
   一律 404（`ExportJob` 主键可枚举，返回 403 会变成存在性预言机）。
3. 下载/撤销的**当前权限复核** `_can_access()` —— 回答「现在还有没有资格」。
   创建时的判断不算数：排队期间被降级、转校后仍能拉走本校全量学号，
   是这类功能最常见的越权路径。
"""
import logging
from pathlib import Path

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import F
from django.http import FileResponse, HttpResponse
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.permissions import IsSchoolAdmin
from apps.exports.models import ExportEvent, ExportJob
from apps.exports.serializers import ExportCreateSerializer, ExportJobSerializer
from apps.exports.services import (
    XLSX_MIME,
    ExportEmptyScope,
    ExportError,
    audit,
    build_content_disposition,
    compute_fingerprint,
    estimate_row_count,
)
from apps.exports.tasks import enqueue_export, remove_export_file, run_export
from apps.exports.throttling import ExportCreateThrottle, ExportDownloadThrottle
from apps.schools.models import School
from config.pagination import StandardPagination

logger = logging.getLogger(__name__)

_ERROR_STATUS = {
    "empty_scope": status.HTTP_400_BAD_REQUEST,
    "export_too_large": status.HTTP_400_BAD_REQUEST,
    "invalid_school": status.HTTP_400_BAD_REQUEST,
    "export_disk_full": status.HTTP_503_SERVICE_UNAVAILABLE,
    "queue_unavailable": status.HTTP_503_SERVICE_UNAVAILABLE,
    "permission_revoked": status.HTTP_403_FORBIDDEN,
    "school_changed": status.HTTP_403_FORBIDDEN,
    "no_school": status.HTTP_403_FORBIDDEN,
    "actor_missing": status.HTTP_403_FORBIDDEN,
}


class _Denied(APIException):
    """越权拒绝。`default_code` 由调用点覆写，前端据此区分原因。"""

    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "没有权限执行该操作"
    default_code = "permission_denied"


def _deny(request, reason, detail):
    """写 `denied` 留痕后抛 403。

    越权尝试必须留痕——这是识别探测行为的唯一手段；但留痕本身是写操作，
    被脚本刷时会变成写入放大器，因此按 actor+原因 做 20 行/分钟的配额，
    超配额只记 warning 不再落库。
    """
    if _within_denied_log_quota(request, reason):
        audit(request.user, ExportEvent.DENIED, reason=reason,
              detail={"phase": "request"}, request=request)
    else:
        logger.warning("导出越权请求过多，已跳过留痕 actor=%s reason=%s",
                       getattr(request.user, "pk", None), reason)
    exc = _Denied(detail=detail)
    exc.default_code = reason
    raise exc


def _within_denied_log_quota(request, reason):
    """同一 actor+原因每分钟最多 20 行留痕。缓存不可用时放行（宁可多写）。"""
    from django.core.cache import cache

    user = getattr(request, "user", None)
    ident = getattr(user, "pk", None) or "anon"
    key = f"export:denied:{ident}:{reason}"
    try:
        if cache.add(key, 1, timeout=60):
            return True
        return cache.incr(key) <= 20
    except Exception:  # noqa: BLE001
        return True


def _error_payload(code, job):
    message = (job.error_message or "").strip()
    prefix = f"[{code}] "
    if message.startswith(prefix):
        message = message[len(prefix):]
    return {
        "detail": message or "导出失败，请稍后重试",
        "code": code or "export_failed",
        "job_id": job.pk,
    }


class ExportJobViewSet(mixins.CreateModelMixin,
                       mixins.ListModelMixin,
                       mixins.RetrieveModelMixin,
                       mixins.DestroyModelMixin,
                       viewsets.GenericViewSet):
    """导出任务的创建、查询、下载、撤销。不允许 PUT/PATCH 改历史记录。"""

    serializer_class = ExportJobSerializer
    permission_classes = [IsSchoolAdmin]
    pagination_class = StandardPagination
    ordering = ["-created_at"]

    # ---------------------------------------------------------------- 基础
    def get_queryset(self):
        qs = ExportJob.objects.select_related("actor")
        user = self.request.user
        if not getattr(user, "is_super_admin", False):
            # 校管只看自己的；别人的 id 一律 404，不做「存在但无权」的区分
            qs = qs.filter(actor=user)
        status_ = self.request.query_params.get("status")
        year = self.request.query_params.get("year")
        if status_:
            qs = qs.filter(status=status_)
        if year and year.isdigit():
            qs = qs.filter(year=int(year))
        return qs

    def get_throttles(self):
        # 全局的 anon/user 节流对本组接口不适用：创建与下载各有更严的配额
        if self.action == "create":
            return [ExportCreateThrottle()]
        if self.action == "download":
            return [ExportDownloadThrottle()]
        return []

    def get_permissions(self):
        """下载/撤销只要求登录，角色判定交给 `_can_access`。

        若这里仍挂 `IsSchoolAdmin`，被降级的管理员会先撞上权限类的通用 403
        （`permission_denied`），拿不到「你的角色变了」这个可诊断的原因。
        """
        if self.action in ("download", "destroy"):
            return [IsAuthenticated()]
        return super().get_permissions()

    def _can_access(self, actor, job):
        """当前权限复核：创建时是管理员，不代表现在还是。"""
        if not (actor.is_super_admin or actor.is_school_admin):
            return "permission_revoked"
        if actor.is_super_admin:
            return None
        if actor.school_id is None:
            return "no_school"
        if actor.school_id not in (job.scope_school_ids or []):
            return "school_changed"
        return None

    # ---------------------------------------------------------------- 创建
    def _resolve_scope(self, request, actor, data):
        """把请求范围归一化成具体 school_id 列表。

        **不做静默改写**：校管传别校 id 必须 403 并留痕，而不是悄悄换成本校。
        静默改写会把越权探测伪装成正常请求，事后无从发现。
        """
        kind = data["scope_kind"]
        ids = data["school_ids"]

        if not actor.is_super_admin:
            if actor.school_id is None:
                _deny(request, "no_school",
                      "你的账号未归属学校，无法导出赛情")
            if kind != ExportJob.ScopeKind.SCHOOL:
                _deny(request, "scope_forbidden", "学校管理员只能导出本校数据")
            if ids != [actor.school_id]:
                _deny(request, "school_mismatch",
                      "只能导出本校数据，请勿指定其他学校")
            return [actor.school_id], ExportJob.ScopeKind.SCHOOL

        if kind == ExportJob.ScopeKind.ALL:
            school_ids = list(
                School.objects.filter(is_active=True)
                .order_by("id").values_list("id", flat=True))
        else:
            school_ids = ids

        if not school_ids:
            raise ExportEmptyScope("范围内没有可导出的学校")

        found = set(School.objects.filter(id__in=school_ids)
                    .values_list("id", flat=True))
        missing = [i for i in school_ids if i not in found]
        if missing:
            raise ValidationError({
                "school_ids": [f"学校不存在：{missing[:5]}"],
            })
        return school_ids, kind

    def create(self, request, *args, **kwargs):
        ser = ExportCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        actor = request.user

        try:
            school_ids, kind = self._resolve_scope(request, actor, data)
        except ExportError as exc:
            return Response({"detail": str(exc), "code": exc.code},
                            status=_ERROR_STATUS.get(exc.code,
                                                     status.HTTP_400_BAD_REQUEST))
        options = {
            "include_zero_participation": data["include_zero_participation"],
            "include_global_rank": data["include_global_rank"],
            "rating_window": data["rating_window"],
        }
        fingerprint = compute_fingerprint(
            actor.pk, kind, school_ids, data["year"], data["layout"], options)

        # 幂等复用：10 分钟内同参数且文件还在，直接把上一份还给他。
        # 指纹含 actor_id —— 否则超管与校管会互相命中对方任务，
        # 命中者因归属校验失败而「点了没反应」。
        reused = (ExportJob.objects
                  .filter(actor=actor, fingerprint=fingerprint,
                          status=ExportJob.Status.SUCCEEDED,
                          expires_at__gt=timezone.now())
                  .first())
        if reused and reused.file_path and (
                Path(settings.EXPORT_ROOT) / reused.file_path).exists():
            audit(actor, ExportEvent.CREATE, job=reused, reason="reuse",
                  detail={"year": data["year"], "layout": data["layout"]},
                  request=request)
            return Response(self.get_serializer(reused).data,
                            status=status.HTTP_200_OK)

        active = (ExportJob.objects
                  .filter(actor=actor,
                          status__in=[ExportJob.Status.PENDING,
                                      ExportJob.Status.RUNNING])
                  .first())
        if active:
            return Response({
                "detail": "已有导出任务正在生成，请等它完成后再发起",
                "code": "export_in_progress",
                "job_id": active.pk,
            }, status=status.HTTP_409_CONFLICT)

        try:
            with transaction.atomic():
                job = ExportJob.objects.create(
                    actor=actor,
                    actor_role=actor.role,
                    scope_kind=kind,
                    scope_school_ids=school_ids,
                    year=data["year"],
                    layout=data["layout"],
                    options=options,
                    fingerprint=fingerprint,
                    ip=_safe_ip(request),
                    device_fp=_safe_fp(request),
                    user_agent=request.META.get("HTTP_USER_AGENT", "")[:255],
                )
        except IntegrityError:
            # 并发双击：DB 的部分唯一索引兜住了
            return Response({
                "detail": "已有导出任务正在生成，请等它完成后再发起",
                "code": "export_in_progress",
            }, status=status.HTTP_409_CONFLICT)

        estimate = estimate_row_count(
            school_ids, data["year"], data["include_zero_participation"])
        sheet_bound = (len(school_ids)
                       if data["layout"] == ExportJob.Layout.PER_SCHOOL else 1)

        if (estimate <= settings.EXPORT_SYNC_MAX_ROWS
                and sheet_bound <= settings.EXPORT_SYNC_MAX_SHEETS):
            result = run_export(job.pk)
            job.refresh_from_db()
            if not result.get("ok"):
                code = result.get("code") or "export_failed"
                return Response(_error_payload(code, job),
                                status=_ERROR_STATUS.get(
                                    code, status.HTTP_500_INTERNAL_SERVER_ERROR))
            audit(actor, ExportEvent.CREATE, job=job,
                  detail={"year": data["year"], "layout": data["layout"],
                          "mode": "sync", "rows": job.row_count},
                  request=request)
            return Response(self.get_serializer(job).data,
                            status=status.HTTP_201_CREATED)

        if not enqueue_export(job):
            job.refresh_from_db()
            return Response(_error_payload("queue_unavailable", job),
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)

        job.refresh_from_db()
        audit(actor, ExportEvent.CREATE, job=job,
              detail={"year": data["year"], "layout": data["layout"],
                      "mode": "async", "estimate": estimate},
              request=request)
        return Response(self.get_serializer(job).data,
                        status=status.HTTP_202_ACCEPTED)

    # ---------------------------------------------------------------- 下载
    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request, pk=None):
        job = self.get_object()  # 别人的任务在这里就是 404
        actor = request.user

        reason = self._can_access(actor, job)
        if reason:
            _deny(request, reason, "权限已变更，无法下载该导出文件")

        if job.status == ExportJob.Status.SUCCEEDED and job.is_expired:
            ExportJob.objects.filter(pk=job.pk).update(
                status=ExportJob.Status.EXPIRED, file_path="")
            audit(actor, ExportEvent.DENIED, job=job, reason="expired",
                  request=request)
            return Response({"detail": "导出文件已过期，请重新生成",
                             "code": "export_expired"},
                            status=status.HTTP_410_GONE)

        if job.status != ExportJob.Status.SUCCEEDED:
            return Response(_error_payload(f"status_{job.status}", job),
                            status=status.HTTP_409_CONFLICT)
        if not job.file_path:
            return Response({"detail": "导出文件已清理，请重新生成",
                             "code": "export_expired"},
                            status=status.HTTP_410_GONE)

        path = Path(settings.EXPORT_ROOT) / job.file_path
        # 路径穿越兜底：file_path 由后端生成，仍显式校验前缀
        try:
            root = Path(settings.EXPORT_ROOT).resolve()
            if not str(path.resolve()).startswith(str(root)):
                raise ValueError("path escape")
        except (OSError, ValueError):
            logger.error("导出文件路径异常 job=%s path=%s", job.pk, job.file_path)
            return Response({"detail": "导出文件不可用，请重新生成",
                             "code": "export_expired"},
                            status=status.HTTP_410_GONE)
        if not path.exists():
            ExportJob.objects.filter(pk=job.pk).update(
                status=ExportJob.Status.EXPIRED, file_path="")
            return Response({"detail": "导出文件已清理，请重新生成",
                             "code": "export_expired"},
                            status=status.HTTP_410_GONE)

        self._record_download(request, job)

        disposition = build_content_disposition(job.file_name or
                                                f"{job.pk}.xlsx")
        if not settings.EXPORT_ACCEL_ENABLED:
            # 本地开发无 nginx：直接回流文件（生产绝不该走这条）
            response = FileResponse(open(path, "rb"),
                                    content_type=XLSX_MIME)
            response["Content-Disposition"] = disposition
            return response

        response = HttpResponse(status=status.HTTP_200_OK)
        response["Content-Type"] = XLSX_MIME
        response["Content-Disposition"] = disposition
        response["Cache-Control"] = "no-store"
        # nginx 的 internal location 直出，Python 进程不碰文件字节
        response["X-Accel-Redirect"] = (
            f"{settings.EXPORT_INTERNAL_PREFIX}{job.file_path}")
        return response

    def _record_download(self, request, job):
        """计数 + 异常识别。任何失败都不得阻断下载。"""
        try:
            ExportJob.objects.filter(pk=job.pk).update(
                download_count=F("download_count") + 1,
                last_download_at=timezone.now())
            job.refresh_from_db(fields=["download_count", "suspicious"])
            audit(request.user, ExportEvent.DOWNLOAD, job=job,
                  detail={"n": job.download_count,
                          "listed_rows": job.row_count},
                  request=request)
            limit = settings.EXPORT_SUSPICIOUS_DOWNLOAD_LIMIT
            if job.download_count > limit and not job.suspicious:
                ExportJob.objects.filter(pk=job.pk).update(suspicious=True)
                self._alert_super_admins(job, request.user)
        except Exception:  # noqa: BLE001
            logger.warning("导出下载计数失败 job=%s", job.pk, exc_info=True)

    def _alert_super_admins(self, job, actor):
        """同一文件被反复下载 → 通知全部超管。失败不影响主流程。"""
        try:
            from apps.accounts.models import NotificationType, notify

            message = (f"导出任务 #{job.pk}（{job.year} 年）已被下载 "
                       f"{job.download_count} 次，超过阈值 "
                       f"{settings.EXPORT_SUSPICIOUS_DOWNLOAD_LIMIT}，"
                       f"请核查是否存在链接外泄。")
            for admin in _super_admins():
                notify(admin, "导出文件下载异常", message,
                       type=NotificationType.SYSTEM,
                       link="/admin/exports")
            audit(actor, ExportEvent.DENIED, job=job, reason="suspicious_download",
                  detail={"n": job.download_count})
        except Exception:  # noqa: BLE001
            logger.warning("导出异常下载告警失败 job=%s", job.pk, exc_info=True)

    # ---------------------------------------------------------------- 撤销
    def destroy(self, request, *args, **kwargs):
        job = self.get_object()
        reason = self._can_access(request.user, job)
        if reason:
            _deny(request, reason, "权限已变更，无法撤销该导出")

        from apps.exports.tasks import remove_export_file as _rm

        _rm(Path(settings.EXPORT_ROOT) / job.file_path
            if job.file_path else None)
        ExportJob.objects.filter(pk=job.pk).update(
            status=ExportJob.Status.REVOKED, file_path="")
        audit(request.user, ExportEvent.REVOKE, job=job,
              detail={"status_before": job.status}, request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)


def _super_admins():
    from apps.accounts.models import User

    return list(User.objects.filter(role="super_admin", is_active=True))


def _safe_ip(request):
    from apps.accounts.security import get_client_ip

    try:
        return get_client_ip(request)[:45] or None
    except Exception:  # noqa: BLE001
        return None


def _safe_fp(request):
    from apps.accounts.security import get_device_fingerprint

    try:
        return get_device_fingerprint(request)[:64]
    except Exception:  # noqa: BLE001
        return ""
