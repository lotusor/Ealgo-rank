"""权限判定：谁能对谁做什么。完整口径与例外见 HANDOVER §0.31。

角色序 `user 1 < school_admin 2 < super_admin 3`，针对他人的写操作一律要求
`rank(actor) > rank(target)`，校管在此之上再限本校：

    动作                        校管              超管
    读名单 / 参赛记录 / 留痕     本校全部（读不限）  全站
    平台账号 解绑/改绑/代绑      本校普通用户        普通用户 + 校管
    参赛记录 剔除/恢复           本校普通用户        普通用户 + 校管
    角色变更 set_role            ✗                 普通用户 ↔ 校管（不含同级超管）
    爬虫 / 系数 / 学校 / 公告    ✗（超管专属）       ✓

同级、上级与本人在任何一行都不放行。前端 `stores/auth.ts` 里那份 ROLE_RANK
只用于隐藏按钮，不是权限依据。
"""
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


# --------------------------------------------------------------------------
# 「只能向下管理」的唯一判定源
# --------------------------------------------------------------------------
# 角色序：管理动作要求 rank(actor) > rank(target)，同级与上级一律不可操作。
# 补这一层的原因：IsSchoolAdmin 只回答「是不是管理员」，而平台账号绑定、
# 成绩排除这类**针对他人**的写操作，光有同校范围不够 —— 校管之间是平级，
# 谁都能改谁的绑定等于谁都能把别人的成绩挪走；超管账号也不该被校管动。
# 权限矩阵与豁免面见 HANDOVER §0.31，改这里必须同步那份文档。
ROLE_RANK = {
    "user": 1,
    "school_admin": 2,
    "super_admin": 3,
}


def role_rank(user) -> int:
    """有效角色序；`is_superuser` 与 `role=super_admin` 同权（与 User.is_super_admin 一致）。"""
    if user is None or not getattr(user, "pk", None):
        return 0
    if getattr(user, "is_super_admin", False):
        return ROLE_RANK["super_admin"]
    return ROLE_RANK.get(getattr(user, "role", "") or "", 0)


def manageable_roles(actor):
    """actor 可管理的角色值列表（严格向下），供 queryset 过滤使用。"""
    rank = role_rank(actor)
    return [r for r, v in ROLE_RANK.items() if v < rank]


def manage_denial(actor, target):
    """能否对 target 动手：返回 None 表示可以，否则返回可直接展示给用户的理由。

    三道独立护栏，顺序即优先级：本人 → 角色序 → 学校范围。
    「本人」单列出来是因为管理端绕过了冷却与一周限制，放行自己等于给自己开
    后门；超管要改自己的绑定请走自助端点。
    """
    if target is None:
        return "目标用户不存在"
    if actor.pk == target.pk:
        return ("不能通过管理端操作自己的账号，请到「个人中心 → 资料编辑」"
                "自助办理（受一周改绑与解绑冷却限制）")
    if role_rank(actor) <= role_rank(target):
        return "只能管理权限低于自己的用户，同级与更高角色请由其上级处理"
    if not actor.is_super_admin:
        if target.school_id is None or target.school_id != actor.school_id:
            return "只能操作本校用户的记录"
    return None


def can_manage(actor, target) -> bool:
    return manage_denial(actor, target) is None
