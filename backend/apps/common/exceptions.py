import logging

from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


def api_exception_handler(exc, context):
    """
    统一错误响应体，前端只需判断 HTTP 状态码 + detail。
    未被 DRF 识别的异常返回 500 并记日志，不把堆栈泄露给客户端。
    """
    response = drf_exception_handler(exc, context)

    if response is None:
        if isinstance(exc, Http404):
            return Response({"detail": "资源不存在", "code": "not_found"}, status=404)
        if isinstance(exc, PermissionDenied):
            return Response({"detail": "没有权限", "code": "permission_denied"}, status=403)
        logger.exception("未处理异常: %s", exc)
        return Response({"detail": "服务器内部错误", "code": "server_error"}, status=500)

    data = response.data
    if isinstance(data, dict) and "detail" in data:
        payload = {"detail": str(data["detail"]), "code": _code_of(exc)}
    elif isinstance(data, dict):
        # 字段级校验错误，原样带回给前端做表单提示
        payload = {"detail": "参数校验失败", "code": "validation_error", "errors": data}
    else:
        payload = {"detail": data, "code": _code_of(exc)}

    response.data = payload
    return response


def _code_of(exc):
    if isinstance(exc, exceptions.APIException):
        return getattr(exc, "default_code", "error")
    return "error"
