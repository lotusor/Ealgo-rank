from rest_framework.permissions import BasePermission


class IsSuperAdmin(BasePermission):
    """超级管理员。服务器信息、危险操作只放给这类账号。"""

    message = "需要超级管理员权限"

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.is_super_admin)


class IsSchoolAdmin(BasePermission):
    """学校管理员（超管天然满足）。"""

    message = "需要学校管理员权限"

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and (u.is_super_admin or u.is_school_admin))
