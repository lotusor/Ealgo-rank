"""导出服务的核心实现：聚合取数、排名计算、写盘。

性能约束（本模块存在的全部理由）：

1. **四组数据只用四条 SQL 拿全，禁止 per-user / per-account 循环。**
   `accounts.serializers.get_platform_ratings` 是反面教材——它给每个平台账号
   发一次 `Participation...first()`，单校 200 人 × 3 平台 = 600 次查询，
   导出会从毫秒级退化到秒级，还要抢占只有 4 个的 gunicorn worker。

2. **平台 rating 用 `Subquery` 注解，不用 PostgreSQL 的 `DISTINCT ON`。**
   CI 的测试库是 SQLite（`ci.yml` 里写明「不需要 PG/Redis」），
   `distinct('field')` 在 SQLite 上直接抛 `NotSupportedError`，CI 必红。

3. **常规模式写 xlsx，不用 `write_only`。** 实测 `WriteOnlyWorksheet` 没有
   `merge_cells`（AttributeError），而模板第一行是合并标题。代价是内存随行数
   线性增长，因此用 `EXPORT_MAX_ROWS` 把上界钉死（默认 10000 行 ≈ 60–80MB）。

4. **所有字符串单元格强制 `data_type='s'`。** 姓名、学号、校名都是用户可控
   输入，`=HYPERLINK(...)` 这类值若被 openpyxl 识别成公式（`<f>` 节点），
   Excel 打开即执行。实测设 `data_type='s'` 后写出 `<c t="inlineStr"><is><t>`
   节点，Excel 按纯文本显示，不会执行。
"""
import hashlib
import os
import re
from datetime import date
from pathlib import Path

from django.conf import settings
from django.db.models import Count, OuterRef, Q, Subquery
from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter

from apps.accounts.models import PlatformAccount, User
from apps.common.models import ExcludeReason, Platform
from apps.contests.models import Participation
from apps.ranking.models import RankSnapshot

# 表头与列顺序严格对齐用户提供的模板：
# 姓名 | 学号 | 参赛次数 | 异常次数 | 牛客rating | CF rating | Atcoder rating | 总rating | 校排
BASE_HEADERS = ["姓名", "学号", "参赛次数", "异常次数"]
PLATFORM_COLUMNS = [
    (Platform.NOWCODER, "牛客rating"),
    (Platform.CODEFORCES, "CF rating"),
    (Platform.ATCODER, "Atcoder rating"),
]
TAIL_HEADERS = ["总rating", "校排"]
MERGED_HEADER = ["学校"] + BASE_HEADERS + [c[1] for c in PLATFORM_COLUMNS] \
    + TAIL_HEADERS + ["全站排名"]

XLSX_MIME = ("application/vnd.openxmlformats-officedocument"
             ".spreadsheetml.sheet")

# 宋体 11 与模板一致；样式对象复用，避免每格 new 一个 Font
_FONT = Font(name="宋体", size=11)
_FONT_BOLD = Font(name="宋体", size=11, bold=True)
_ALIGN_CENTER = Alignment(horizontal="center", vertical="center")
_ALIGN_WRAP = Alignment(vertical="center", wrap_text=True)

# Excel 里以这些前缀开头的字符串可能被当作公式/命令
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
_SHEET_BAD_CHARS = re.compile(r"[\[\]:*?/\\]")
_FILENAME_BAD_CHARS = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


class ExportError(Exception):
    """导出失败的基类；`code` 直接回给前端。"""

    code = "export_failed"
    detail = "导出失败"

    def __init__(self, detail=None, code=None):
        if detail:
            self.detail = detail
        if code:
            self.code = code
        super().__init__(self.detail)


class ExportEmptyScope(ExportError):
    code = "empty_scope"
    detail = "指定范围内没有可导出的学生数据"


class ExportTooLarge(ExportError):
    code = "export_too_large"
    detail = "数据量超出单次导出上限，请缩小到单校或指定年份"


class ExportDiskFull(ExportError):
    code = "export_disk_full"
    detail = "服务器可用磁盘空间不足，暂时无法生成导出文件"


# --------------------------------------------------------------------------
# 单元格写入：所有字符串都过这一层，公式注入在这里被拦住
# --------------------------------------------------------------------------
def safe_text(value):
    """把任意值转成可安全写入 xlsx 的文本。

    只做类型归一，不加单引号前缀——实测 `data_type='s'` 已能让 openpyxl
    写出 inlineStr 节点，Excel 按文本显示；再加 `'` 会把引号本身显示出来，
    反而污染数据。
    """
    if value is None:
        return None
    text = str(value)
    return text if text != "" else None


def _put(ws, row, col, value, *, font=None, align=None, number_format=None):
    cell = ws.cell(row=row, column=col)
    if isinstance(value, bool):
        cell.value = int(value)
    elif isinstance(value, (int, float)):
        cell.value = value
    else:
        text = safe_text(value)
        if text is None:
            cell.value = None
        else:
            cell.value = text
            # 关键：显式声明为字符串，避免 "=..." 被识别成公式
            cell.data_type = "s"
    if font is not None:
        cell.font = font
    if align is not None:
        cell.alignment = align
    if number_format is not None:
        cell.number_format = number_format
    return cell


def sanitize_sheet_name(raw, used):
    """清洗工作表名：非法字符、31 字符上限、重名去重。"""
    name = _SHEET_BAD_CHARS.sub("_", (raw or "").strip()) or "未命名"
    name = name[:31]
    base = name
    n = 2
    while name.lower() in used:
        suffix = f"({n})"
        name = base[: 31 - len(suffix)] + suffix
        n += 1
    used.add(name.lower())
    return name


def build_file_name(year, label, pk):
    """生成下载文件名。只由后端拼，绝不接受客户端传名。"""
    safe_label = _FILENAME_BAD_CHARS.sub("", label or "").strip() or "全站"
    stamp = timezone.localtime().strftime("%Y%m%d-%H%M")
    return f"{year}{safe_label}参赛情况_{stamp}_{pk}.xlsx"


def build_content_disposition(file_name):
    """同时给 ASCII 兜底与 RFC 5987 的 UTF-8 名，避免中文乱码。"""
    from urllib.parse import quote

    ascii_fallback = _FILENAME_BAD_CHARS.sub("_", file_name).encode(
        "ascii", "ignore").decode("ascii") or "export.xlsx"
    return (f'attachment; filename="{ascii_fallback}"; '
            f"filename*=UTF-8''{quote(file_name, safe='')}")


# --------------------------------------------------------------------------
# 取数：四条 SQL
# --------------------------------------------------------------------------
def _load_schools(school_ids):
    from apps.schools.models import School

    return {
        s.id: {"name": s.name, "short_name": s.short_name or s.name}
        for s in School.objects.filter(id__in=school_ids).only(
            "id", "name", "short_name")
    }


def _load_users(school_ids):
    """本校在职学生。`needs_username` 需 passport_user_id 参与判断。"""
    return list(
        User.objects
        .filter(school_id__in=school_ids, is_active=True)
        .values("id", "username", "real_name", "student_no", "school_id",
                "passport_user_id")
        .order_by("id")
    )


def _load_contest_counts(school_ids, year):
    """参赛次数 / 作弊次数，一次 GROUP BY 拿全。

    「异常次数」按用户口径只统计 `exclude_reason=cheater`。
    注意它与「参赛次数」是包含关系，相减**不等于**计分场次
    （还有赛后补交/人工剔除/打星等剔除原因），文件内的说明页已写明。
    """
    rows = (
        Participation.objects
        .filter(
            platform_account__isnull=False,
            platform_account__school_id__in=school_ids,
            contest__start_time__year=year,
        )
        .values("platform_account__user_id")
        .annotate(
            total=Count("id"),
            cheater=Count("id", filter=Q(exclude_reason=ExcludeReason.CHEATER)),
        )
        .order_by()
    )
    out = {}
    for r in rows:
        uid = r["platform_account__user_id"]
        if uid:
            out[uid] = (r["total"] or 0, r["cheater"] or 0)
    return out


def _load_platform_ratings(school_ids, year, rating_window):
    """各平台「赛季末最后一场」的赛后 rating，一次查询 N 行。

    用 `Subquery` 而不是 `DISTINCT ON`：后者 SQLite 不支持，CI 会红。
    """
    latest = Participation.objects.filter(
        platform_account=OuterRef("pk"),
        new_rating__isnull=False,
    )
    if rating_window == "season":
        latest = latest.filter(contest__start_time__year=year)
    latest = latest.order_by("-contest__start_time", "-id").values(
        "new_rating")[:1]

    rows = (
        PlatformAccount.objects
        .filter(school_id__in=school_ids)
        .annotate(latest_rating=Subquery(latest))
        .values("user_id", "platform", "latest_rating")
    )
    out = {}
    for r in rows:
        if r["latest_rating"] is None:
            continue
        out.setdefault(r["user_id"], {})[r["platform"]] = r["latest_rating"]
    return out


def _load_total_ratings(user_ids, year):
    """站内赛季有效分：与排行榜 student 榜同源（RankSnapshot）。"""
    rows = (
        RankSnapshot.objects
        .filter(scope=RankSnapshot.Scope.STUDENT, period=str(year),
                user_id__in=user_ids)
        .values("user_id", "total_score")
    )
    return {r["user_id"]: r["total_score"] for r in rows}


def estimate_row_count(school_ids, year, include_zero_participation=False):
    """粗估行数，用于同步/异步分流。只发 1～2 条 COUNT，不碰明细。"""
    if include_zero_participation:
        return User.objects.filter(school_id__in=school_ids,
                                   is_active=True).count()
    return (
        Participation.objects
        .filter(
            platform_account__isnull=False,
            platform_account__school_id__in=school_ids,
            contest__start_time__year=year,
        )
        .values("platform_account__user_id")
        .distinct()
        .count()
    )


def _display_name(row):
    """姓名列：没有真实姓名时不把 UUID 占位名抖出来。"""
    real_name = (row.get("real_name") or "").strip()
    if real_name:
        return real_name
    username = (row.get("username") or "").strip()
    if not username:
        return ""
    # passport 首登用 UUID 顶 username，未认领时它不是人名，导出去只会污染表格
    if row.get("passport_user_id") and username == row["passport_user_id"]:
        return ""
    return username


def _assign_ranks(rows):
    """校内排名：总rating 降序，并列同名次、后续跳号；无值排末位记 None。

    先四舍五入再排名 —— 否则 1460.4 与 1460.6 会拿走 1、2 名，
    而表里两行都显示 1460，看着像排错了。
    """
    valued = [r for r in rows if r["total"] is not None]
    valued.sort(key=lambda r: (-r["total"], -r["contests"],
                               r["student_no"] or "", r["_uid"]))
    i = 0
    while i < len(valued):
        j = i
        while j + 1 < len(valued) and valued[j + 1]["total"] == valued[i]["total"]:
            j += 1
        rank = i + 1
        for k in range(i, j + 1):
            valued[k]["rank"] = rank
        i = j + 1

    rest = [r for r in rows if r["total"] is None]
    rest.sort(key=lambda r: (-r["contests"], r["student_no"] or "", r["_uid"]))
    for r in rest:
        r["rank"] = None
    return valued + rest


def collect(school_ids, year, options):
    """取全量数据并按学校分组。返回 (schools, rows_by_school, stats)。"""
    include_zero = bool(options.get("include_zero_participation"))
    rating_window = options.get("rating_window") or "season"

    schools = _load_schools(school_ids)
    users = _load_users(school_ids)
    counts = _load_contest_counts(school_ids, year)
    ratings = _load_platform_ratings(school_ids, year, rating_window)
    user_ids = [u["id"] for u in users]
    totals = _load_total_ratings(user_ids, year)

    skipped_zero = 0
    rows_by_school = {sid: [] for sid in school_ids}
    for u in users:
        uid = u["id"]
        total_cnt, cheat_cnt = counts.get(uid, (0, 0))
        if total_cnt == 0 and not include_zero:
            skipped_zero += 1
            continue
        plat = ratings.get(uid, {})
        score = totals.get(uid)
        rows_by_school.setdefault(u["school_id"], []).append({
            "_uid": uid,
            "name": _display_name(u),
            "student_no": (u["student_no"] or "").strip(),
            "contests": total_cnt,
            "cheaters": cheat_cnt,
            "nowcoder": plat.get(Platform.NOWCODER),
            "codeforces": plat.get(Platform.CODEFORCES),
            "atcoder": plat.get(Platform.ATCODER),
            # 表里展示与排名都取整，避免「显示同分却不同名次」
            "total": None if score is None else int(round(float(score))),
            "rank": None,
        })

    for sid in list(rows_by_school):
        rows_by_school[sid] = _assign_ranks(rows_by_school[sid])

    stats = {
        "row_count": sum(len(v) for v in rows_by_school.values()),
        "skipped_zero": skipped_zero,
        "school_count": len([v for v in rows_by_school.values() if v]),
    }
    return schools, rows_by_school, stats


def _apply_global_rank(rows):
    """合并单表用：跨全部学校按总rating 排名，同样并列同名次。"""
    valued = [r for r in rows if r["total"] is not None]
    valued.sort(key=lambda r: (-r["total"], -r["contests"],
                               r["student_no"] or "", r["_uid"]))
    i = 0
    while i < len(valued):
        j = i
        while j + 1 < len(valued) and valued[j + 1]["total"] == valued[i]["total"]:
            j += 1
        for k in range(i, j + 1):
            valued[k]["global_rank"] = i + 1
        i = j + 1
    for r in rows:
        r.setdefault("global_rank", None)
    return rows


# --------------------------------------------------------------------------
# 写盘
# --------------------------------------------------------------------------
def _style_header(ws, width_row):
    """表头样式已由写入循环设好，这里只补列宽（避免重复赋值覆盖字体）。"""
    for idx, width in enumerate(width_row, start=1):
        ws.column_dimensions[get_column_letter(idx)].width = width


def _write_title(ws, title, ncols):
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=ncols)
    _put(ws, 1, 1, title, font=_FONT_BOLD, align=_ALIGN_CENTER)
    ws.row_dimensions[1].height = 22


def _write_per_school_sheet(ws, school, rows, year):
    ncols = len(BASE_HEADERS) + len(PLATFORM_COLUMNS) + len(TAIL_HEADERS)
    _write_title(ws, f"{year}{school['name']}参赛情况", ncols)

    for idx, text in enumerate(
            BASE_HEADERS + [c[1] for c in PLATFORM_COLUMNS] + TAIL_HEADERS,
            start=1):
        _put(ws, 2, idx, text, font=_FONT_BOLD, align=_ALIGN_CENTER)
    _style_header(ws, [14, 15, 10, 10, 12, 12, 14, 10, 8])

    for offset, r in enumerate(rows):
        row = 3 + offset
        _put(ws, row, 1, r["name"], font=_FONT)
        # 学号强制文本：2509030326 不加 '@' 会显示成 2.50903E+09 并丢末位
        _put(ws, row, 2, r["student_no"], font=_FONT, number_format="@")
        _put(ws, row, 3, r["contests"], font=_FONT)
        _put(ws, row, 4, r["cheaters"], font=_FONT)
        for idx, (platform, _label) in enumerate(PLATFORM_COLUMNS, start=5):
            _put(ws, row, idx, r.get(platform), font=_FONT)
        _put(ws, row, 8, r["total"], font=_FONT)
        _put(ws, row, 9, "—" if r["rank"] is None else r["rank"], font=_FONT)

    ws.freeze_panes = "A3"


def _write_merged_sheet(ws, rows, year):
    ncols = len(MERGED_HEADER)
    _write_title(ws, f"{year}全站参赛情况", ncols)
    for idx, text in enumerate(MERGED_HEADER, start=1):
        _put(ws, 2, idx, text, font=_FONT_BOLD, align=_ALIGN_CENTER)
    _style_header(ws, [20, 14, 15, 10, 10, 12, 12, 14, 10, 8, 10])

    order = sorted(rows, key=lambda r: (
        r["school_name"], r["rank"] is None, r["rank"] or 0,
        -r["contests"], r["_uid"]))
    for offset, r in enumerate(order):
        row = 3 + offset
        _put(ws, row, 1, r["school_name"], font=_FONT)
        _put(ws, row, 2, r["name"], font=_FONT)
        _put(ws, row, 3, r["student_no"], font=_FONT, number_format="@")
        _put(ws, row, 4, r["contests"], font=_FONT)
        _put(ws, row, 5, r["cheaters"], font=_FONT)
        for idx, (platform, _label) in enumerate(PLATFORM_COLUMNS, start=6):
            _put(ws, row, idx, r.get(platform), font=_FONT)
        _put(ws, row, 9, r["total"], font=_FONT)
        _put(ws, row, 10, "—" if r["rank"] is None else r["rank"], font=_FONT)
        _put(ws, row, 11, "—" if r["global_rank"] is None
             else r["global_rank"], font=_FONT)

    ws.freeze_panes = "A3"


# 口径说明：这七条是「同一份报表两次导出数值不同」这类质询的唯一挡箭牌，
# 改动统计口径时必须同步改这里。
_NOTES = [
    "1. 参赛次数：该赛季内、以平台账号归属校为准的全部参赛记录数（含被剔除场次）。",
    "2. 异常次数：仅统计平台标记作弊（exclude_reason=cheater）的场次；不含赛后补交、"
    "人工剔除、打星等其它剔除原因。因此「参赛次数 − 异常次数」不等于计分场次。",
    "3. 平台 rating：该平台在本赛季内最后一场比赛的赛后 rating；本赛季未参加该平台"
    "比赛则留空（不是 0）。",
    "4. 总rating：站内赛季有效分（最近若干场表现分衰减加权，并带 1200 新手先验），"
    "与站内排行榜「学生榜」同源，不等于三平台 rating 之和。",
    "5. 校排：校内按总rating 降序，同分并列同名次、后续跳号；无总rating 者排末位并记「—」。",
    "6. 学号列已设为文本格式，避免长数字被科学计数法截断或丢失前导零。",
    "7. 学生归属以平台账号归属学校为准；学生转校后历史成绩随账号一并迁移，"
    "与站内榜单口径一致。",
]


def _write_notes_sheet(ws, job, schools, stats):
    _put(ws, 1, 1, "本表口径说明", font=_FONT_BOLD)
    ws.column_dimensions["A"].width = 100

    scope_text = "、".join(
        schools[sid]["name"] for sid in job.scope_school_ids if sid in schools
    ) or "（范围为空）"
    if job.scope_kind == "all":
        scope_text = f"全站（{len(schools)} 所学校）"

    meta = [
        ("导出时间", timezone.localtime().strftime("%Y-%m-%d %H:%M:%S")),
        ("赛季", f"{job.year} 年"),
        ("范围", scope_text),
        ("形态", job.get_layout_display()),
        ("数据行数", f"{stats['row_count']} 行"),
        ("跳过零参赛学生", f"{stats['skipped_zero']} 人"),
        ("榜单快照版本", str(_ranking_version())),
        ("操作人", getattr(job.actor, "username", "") or "-"),
    ]
    row = 3
    for label, value in meta:
        _put(ws, row, 1, f"{label}：{value}", font=_FONT)
        row += 1

    row += 1
    _put(ws, row, 1, "口径与注意事项", font=_FONT_BOLD)
    row += 1
    for note in _NOTES:
        _put(ws, row, 1, note, font=_FONT, align=_ALIGN_WRAP)
        row += 1


def _ranking_version():
    from apps.ranking.cache import get_ranking_version

    return get_ranking_version()


def build_workbook(job, schools, rows_by_school, stats):
    """组装工作簿。返回 (workbook, sheet_count)。"""
    wb = Workbook()
    wb.remove(wb.active)
    used = set()

    if job.layout == "merged":
        flat = []
        for sid, rows in rows_by_school.items():
            school_name = (schools.get(sid) or {}).get("name", "")
            for r in rows:
                r["school_name"] = school_name
                flat.append(r)
        flat = _apply_global_rank(flat)
        ws = wb.create_sheet(sanitize_sheet_name(
            f"{job.year}全站汇总", used))
        _write_merged_sheet(ws, flat, job.year)
        data_sheets = 1
    else:
        data_sheets = 0
        for sid in job.scope_school_ids:
            rows = rows_by_school.get(sid) or []
            if not rows:
                continue
            school = schools.get(sid) or {"name": str(sid), "short_name": str(sid)}
            ws = wb.create_sheet(sanitize_sheet_name(
                school["short_name"] or school["name"], used))
            _write_per_school_sheet(ws, school, rows, job.year)
            data_sheets += 1

    notes = wb.create_sheet(sanitize_sheet_name("说明", used))
    _write_notes_sheet(notes, job, schools, stats)
    return wb, data_sheets


def ensure_disk_space():
    """生成前检查可用磁盘。Windows 开发机没有 statvfs，直接放行。"""
    root = Path(settings.EXPORT_ROOT)
    root.mkdir(parents=True, exist_ok=True)
    if not hasattr(os, "statvfs"):
        return
    st = os.statvfs(root)
    free = st.f_bavail * st.f_frsize
    if free < settings.EXPORT_MIN_FREE_BYTES:
        raise ExportDiskFull()


def write_export_file(job):
    """生成文件并回填 job 的路径/大小/校验和。失败时清理半截文件。"""
    ensure_disk_space()

    schools, rows_by_school, stats = collect(
        job.scope_school_ids, job.year, job.options or {})

    if stats["row_count"] == 0:
        raise ExportEmptyScope()
    if stats["row_count"] > settings.EXPORT_MAX_ROWS:
        raise ExportTooLarge(
            f"本次导出预计 {stats['row_count']} 行，超过单次上限 "
            f"{settings.EXPORT_MAX_ROWS} 行，请缩小到单校或指定年份")
    if stats["school_count"] > settings.EXPORT_MAX_SHEETS:
        raise ExportTooLarge(
            f"涉及 {stats['school_count']} 所学校，超过单次上限 "
            f"{settings.EXPORT_MAX_SHEETS} 所，请改用合并单表形态")

    wb, sheets = build_workbook(job, schools, rows_by_school, stats)
    if sheets > settings.EXPORT_MAX_SHEETS:
        raise ExportTooLarge()

    root = Path(settings.EXPORT_ROOT)
    final_name = f"{job.pk}.xlsx"
    tmp_path = root / f"{final_name}.tmp"
    final_path = root / final_name
    try:
        wb.save(tmp_path)
        # backend 容器以 root 写、nginx worker 以 nginx 读；不显式放开会 403
        os.chmod(tmp_path, 0o644)
        os.replace(tmp_path, final_path)
    finally:
        if tmp_path.exists():
            try:
                os.remove(tmp_path)
            except OSError:
                pass

    digest = hashlib.sha256()
    with open(final_path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 256), b""):
            digest.update(chunk)

    job.file_path = final_name
    job.file_name = build_file_name(
        job.year, "全站" if job.layout == "merged" else _scope_label(job, schools),
        job.pk)
    job.file_size = final_path.stat().st_size
    job.checksum = digest.hexdigest()
    job.row_count = stats["row_count"]
    job.sheet_count = sheets
    job.save(update_fields=[
        "file_path", "file_name", "file_size", "checksum", "row_count",
        "sheet_count", "updated_at",
    ])
    return stats


def _scope_label(job, schools):
    names = [schools[sid]["short_name"] for sid in job.scope_school_ids
             if sid in schools]
    if len(names) == 1:
        return names[0]
    return f"{len(names)}校" if names else "全站"


# --------------------------------------------------------------------------
# 留痕：写入失败绝不阻断主流程，但必须留日志（不能静默）
# --------------------------------------------------------------------------
def audit(actor, event, *, job=None, reason="", detail=None, request=None):
    import logging

    from apps.exports.models import ExportAuditLog

    logger = logging.getLogger(__name__)
    try:
        ExportAuditLog.objects.create(
            job_id_snapshot=getattr(job, "pk", None),
            actor=actor if getattr(actor, "pk", None) else None,
            actor_username=getattr(actor, "username", "") or "",
            event=event,
            reason=reason,
            detail=detail or {},
            ip=_client_ip(request) if request is not None else None,
            device_fp=_device_fp(request) if request is not None else "",
            user_agent=(request.META.get("HTTP_USER_AGENT", "")[:255]
                        if request is not None else ""),
        )
    except Exception:
        logger.exception("导出留痕写入失败 event=%s job=%s", event,
                         getattr(job, "pk", None))


def _client_ip(request):
    """复用 accounts.security 的取 IP 逻辑，避免出现第二套 XFF 解析。"""
    from apps.accounts.security import get_client_ip

    try:
        return get_client_ip(request)[:45] or None
    except Exception:
        return None


def _device_fp(request):
    from apps.accounts.security import get_device_fingerprint

    try:
        return get_device_fingerprint(request)[:64]
    except Exception:
        return ""


def compute_fingerprint(actor_id, scope_kind, school_ids, year, layout, options):
    """幂等指纹。

    必须含 `actor_id`：超管导出「某校」与该校校管导出同参数时，指纹若相同，
    校管会命中超管的任务，最终因归属校验失败而「点了没反应」。
    """
    normalized = "|".join([
        f"u{actor_id}",
        scope_kind,
        ",".join(str(x) for x in sorted(school_ids)),
        str(year),
        layout,
        "1" if options.get("include_zero_participation") else "0",
        options.get("rating_window") or "season",
        str(_ranking_version()),
    ])
    return hashlib.md5(normalized.encode("utf-8")).hexdigest()


def today_year():
    return timezone.localdate().year


def default_year():
    """默认赛季：优先取当前配置，退回自然年（不要因为缺 Season 行就 500）。"""
    try:
        from apps.ranking.models import SeasonConfig

        cfg = SeasonConfig.get_config()
        if cfg.current_season:
            return int(cfg.current_season)
    except Exception:
        pass
    return date.today().year
