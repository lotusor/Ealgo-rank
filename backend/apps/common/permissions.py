from rest_framework.permissions import SAFE_METHODS, BasePermission


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


class IsOwnSchoolAdmin(BasePermission):
    """
    对象级：只能管自己学校的数据。
    要求对象上有 school 字段，或对象本身就是 School。
    超管不受限制。
    """

    message = "只能管理本校数据"

    def has_object_permission(self, request, view, obj):
        u = request.user
        if not (u and u.is_authenticated):
            return False
        if u.is_super_admin:
            return True
        if not u.is_school_admin or u.school_id is None:
            return False
        target = getattr(obj, "school_id", None)
        if target is None and hasattr(obj, "pk"):
            # obj 本身是 School
            target = obj.pk if obj.__class__.__name__ == "School" else None
        return target == u.school_id


class ReadOnlyOrSchoolAdmin(BasePermission):
    """读开放，写需要学校管理员。"""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        u = request.user
        return bool(u and u.is_authenticated and (u.is_super_admin or u.is_school_admin))
