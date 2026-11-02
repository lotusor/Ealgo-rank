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
from apps.ranking.models import RankSnapshot, ScoreRecord

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


def _load_scored_counts(school_ids, year):
    """本赛季「计分场次」。

    取 `ScoreRecord`（与站内榜单 `RankSnapshot.contest_count` **同一来源**），
    不是 `Participation`：`rated=False` 的练习赛/节日赛也有参赛记录，但**不计分**，
    把它们算进「参赛次数」会让报表数字与榜单对不上。

    实测反例（2026-11-02）：选手「骑士猫猫」本赛季 7 条 participation 全是
    `rated=False`，所有计分场次来自 2025 年——按 participation 计会写 7，
    而榜单与他本人的计分场次都是 0。
    """
    rows = (
        ScoreRecord.objects
        .filter(
            platform_account__isnull=False,
            platform_account__school_id__in=school_ids,
            contest_time__year=year,
        )
        .values("platform_account__user_id")
        .annotate(n=Count("id"))
        .order_by()
    )
    return {r["platform_account__user_id"]: r["n"] for r in rows
            if r["platform_account__user_id"]}


def _load_participation_counts(school_ids, year):
    """本赛季「参赛条数」与「作弊场次」。

    参赛条数只用来判断「本赛季是否露过面」（决定该不该出行），不进报表数字；
    作弊是行为，与是否计分无关，单独统计。
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


def _rating_subquery(year):
    """`PlatformAccount` 上「最后一场有 rating 的比赛」的注解。

    year=None 表示不限赛季，用于「本赛季无计分赛」时的当前值回退。
    """
    qs = Participation.objects.filter(
        platform_account=OuterRef("pk"),
        new_rating__isnull=False,
    )
    if year is not None:
        qs = qs.filter(contest__start_time__year=year)
    return qs.order_by("-contest__start_time", "-id").values("new_rating")[:1]


def _load_platform_ratings(school_ids, year):
    """各平台 rating：返回 {user_id: {platform: (赛季末值, 全历史最新值)}}。

    两个值都取出来，是为了「本赛季没打该平台」时能回退到当前 rating
    而不是留空——报表要求如实反映选手现状，空值等于把人当不存在。

    用 `Subquery` 而不是 `DISTINCT ON`：后者 SQLite 不支持，CI 会红。
    """
    rows = (
        PlatformAccount.objects
        .filter(school_id__in=school_ids)
        .annotate(
            season_rating=Subquery(_rating_subquery(year)),
            latest_rating=Subquery(_rating_subquery(None)),
        )
        .values("user_id", "platform", "season_rating", "latest_rating")
    )
    out = {}
    for r in rows:
        if r["season_rating"] is None and r["latest_rating"] is None:
            continue
        out.setdefault(r["user_id"], {})[r["platform"]] = (
            r["season_rating"], r["latest_rating"])
    return out


def _load_total_ratings(user_ids, year):
    """站内有效分：返回 {user_id: (本赛季分, 全历史当前分)}。

    `RankSnapshot` 只给**有计分记录**的人建行，所以本赛季没计分赛的选手
    在 `period=<year>` 里根本不存在（骑士猫猫就是这种），必须能回退到
    `period="all"` 的当前分。
    """
    rows = (
        RankSnapshot.objects
        .filter(scope=RankSnapshot.Scope.STUDENT,
                period__in=[str(year), "all"],
                user_id__in=user_ids)
        .values("user_id", "period", "total_score")
    )
    out = {}
    for r in rows:
        slot = out.setdefault(r["user_id"], [None, None])
        if r["period"] == str(year):
            slot[0] = r["total_score"]
        else:
            slot[1] = r["total_score"]
    return {uid: tuple(v) for uid, v in out.items()}


def is_current_season(year):
    """是否当前赛季。回退只在当前赛季成立——把「今天的分」塞进往年报表是错的。"""
    return int(year) == timezone.localdate().year


def estimate_row_count(school_ids, year, include_zero_participation=False):
    """粗估行数，用于同步/异步分流。

    当前赛季按「已绑定账号人数」估（0 计分场的人也要出行）；历史赛季按
    该赛季实际参赛人数估，避免高估导致无谓地转异步。
    """
    if include_zero_participation:
        return User.objects.filter(school_id__in=school_ids,
                                   is_active=True).count()
    if is_current_season(year):
        return (
            PlatformAccount.objects
            .filter(school_id__in=school_ids, user__is_active=True)
            .values("user_id").distinct().count()
        )
    return (
        Participation.objects
        .filter(
            platform_account__isnull=False,
            platform_account__school_id__in=school_ids,
            contest__start_time__year=year,
        )
        .values("platform_account__user_id").distinct().count()
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
    """取全量数据并按学校分组。返回 (schools, rows_by_school, stats)。

    出行规则（2026-11-02 按用户口径修正）：只要这个人在本校**有绑定账号**，
    就保留一行，哪怕本赛季 0 计分场——他的平台 rating 与站内当前分仍然真实存在，
    写空等于把人从报表里抹掉。只有「完全没有任何数据」的人才按
    `include_zero_participation` 决定是否列出。
    """
    include_zero = bool(options.get("include_zero_participation"))
    rating_window = options.get("rating_window") or "season"
    current = is_current_season(year)

    schools = _load_schools(school_ids)
    users = _load_users(school_ids)
    scored = _load_scored_counts(school_ids, year)
    participation = _load_participation_counts(school_ids, year)
    ratings = _load_platform_ratings(school_ids, year)
    user_ids = [u["id"] for u in users]
    totals = _load_total_ratings(user_ids, year)

    skipped_zero = 0
    fallback_total = 0
    fallback_platform = 0
    rows_by_school = {sid: [] for sid in school_ids}

    for u in users:
        uid = u["id"]
        scored_cnt = scored.get(uid, 0)
        part_cnt, cheat_cnt = participation.get(uid, (0, 0))

        season_total, all_total = totals.get(uid, (None, None))
        if season_total is not None:
            total, total_fb = season_total, False
        elif current and all_total is not None:
            # 本赛季没有计分场 → 回退到站内当前分，仍参与校排
            total, total_fb = all_total, True
        else:
            total, total_fb = None, False

        plat = ratings.get(uid, {})
        picked = {}
        for platform, _label in PLATFORM_COLUMNS:
            season_v, latest_v = plat.get(platform, (None, None))
            if rating_window == "latest":
                picked[platform] = latest_v
            elif season_v is not None:
                picked[platform] = season_v
            elif current and latest_v is not None:
                picked[platform] = latest_v
                fallback_platform += 1
            else:
                picked[platform] = None

        # 「本赛季露过面」：参赛过、计过分、或被标记过作弊，任一即算。
        # 当前赛季额外接受「只有历史数据」的人（回退路径），历史赛季不接受——
        # 否则导 2025 会把只在 2026 打过的人拉进 2025 的表。
        met_this_season = bool(part_cnt or scored_cnt or cheat_cnt)
        usable_fallback = current and (total is not None
                                       or any(v is not None
                                              for v in picked.values()))
        if not (met_this_season or usable_fallback) and not include_zero:
            skipped_zero += 1
            continue
        if total_fb:
            fallback_total += 1

        rows_by_school.setdefault(u["school_id"], []).append({
            "_uid": uid,
            "name": _display_name(u),
            "student_no": (u["student_no"] or "").strip(),
            # 计分场次（不是参赛条数）：与榜单 contest_count 同源
            "contests": scored_cnt,
            "cheaters": cheat_cnt,
            "nowcoder": picked[Platform.NOWCODER],
            "codeforces": picked[Platform.CODEFORCES],
            "atcoder": picked[Platform.ATCODER],
            # 表里展示与排名都取整，避免「显示同分却不同名次」
            "total": None if total is None else int(round(float(total))),
            "total_fallback": total_fb,
            "rank": None,
        })

    for sid in list(rows_by_school):
        rows_by_school[sid] = _assign_ranks(rows_by_school[sid])

    stats = {
        "row_count": sum(len(v) for v in rows_by_school.values()),
        "skipped_zero": skipped_zero,
        "school_count": len([v for v in rows_by_school.values() if v]),
        "fallback_total": fallback_total,
        "fallback_platform": fallback_platform,
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
    "1. 参赛次数：该赛季内「计入积分」的场次数，与站内排行榜「学生榜」的参赛场次同源。"
    "不计分的比赛（练习赛、节日赛、rated=False 的场次）不计入——它们有参赛记录，"
    "但不产生积分，计进来会让报表数字与榜单对不上。",
    "2. 异常次数：该赛季内被平台标记作弊（exclude_reason=cheater）的场次。"
    "它统计的是「行为」，与是否计分无关，因此「与参赛次数不存在包含关系」，"
    "两者相减没有意义。",
    "3. 平台 rating：该平台在本赛季最后一场计分赛的赛后值。"
    "导出当前赛季时，若本赛季在该平台没有计分赛，则回退为该平台「最近一次」有 rating 的"
    "值（即选手当前 rating）；导出历史赛季不回退，留空。回退数量见上方统计。",
    "4. 总rating：站内本赛季有效分（最近若干场表现分衰减加权，并带 1200 新手先验），"
    "与站内排行榜「学生榜」同源，不等于三平台 rating 之和。"
    "导出当前赛季时，本赛季没有计分赛的选手回退为站内「当前分」（all 周期快照），"
    "仍参与校排；导出历史赛季不回退。",
    "5. 校排：校内按总rating 降序，同分并列同名次、后续跳号；"
    "仅在完全没有任何 rating 时才记「—」并排末位。",
    "6. 学号列已设为文本格式，避免长数字被科学计数法截断或丢失前导零。",
    "7. 学生归属以平台账号归属学校为准；学生转校后历史成绩随账号一并迁移，"
    "与站内榜单口径一致。",
]

# 解释「为什么有人本赛季 0 场却还有 rating」这类质询。用户 2026-11-02 要求
# 把这层解释直接写进表格，避免拿表的人反复来问。
_EXPLAIN_TITLE = "关于本表数字的几点说明（常见疑问）"
_EXPLAIN = [
    "问：为什么有人的「参赛次数」是 0，rating 却有值？",
    "答：参赛次数只数「计分」场次。该选手本赛季可能参加了若干不计分的练习赛，"
    "因此计分场次为 0；但其 rating 是选手账号上的「当前值」，来自更早的计分赛，"
    "按第 3、4 条回退规则如实输出，而不是抹成空值。",
    "问：为什么他的校排不为空，但本赛季一场计分赛都没打？",
    "答：校排按「本赛季有效分，缺则当前分」排序。这样选手不会因为一段时间没参赛"
    "就从榜单上消失。若要严格只看本赛季，请筛选「参赛次数 > 0」的行自行比对。",
    "问：异常次数为什么可能大于参赛次数？",
    "答：两者口径不同（见第 1、2 条）：参赛次数只数计分场次，异常次数数作弊行为，"
    "作弊场次本身通常不计分，因此前者可能小于后者，这不是数据错误。",
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
        ("无任何数据而跳过", f"{stats['skipped_zero']} 人"),
        # 让拿表的人一眼看到有多少数字是回退来的，避免把当前分误当成本赛季分
        ("总rating 用当前分回退", f"{stats.get('fallback_total', 0)} 行"),
        ("平台 rating 用最新值回退",
         f"{stats.get('fallback_platform', 0)} 个单元格"),
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

    # 用户 2026-11-02 明确要求：把「数字为什么长这样」直接写进表格，
    # 省得拿表的人反复来问，也避免被误当成数据错误。
    row += 1
    _put(ws, row, 1, _EXPLAIN_TITLE, font=_FONT_BOLD)
    row += 1
    for line in _EXPLAIN:
        _put(ws, row, 1, line, font=_FONT, align=_ALIGN_WRAP)
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
