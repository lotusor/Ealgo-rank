"""平台注册表 —— 新增一个平台只改这一处。

为什么需要它：`Platform` 枚举只回答「有哪些平台」，回答不了「这个平台能干什么」。
在这之前能力散在并列的 if/elif 与字典字面量里（`_load_scraper`、`TASK_MAP`、
`auto_crawl_task.plans`、`PLATFORM_DEFAULT_BASE`、`platform_factor`、
`PLATFORM_CHOICES`、`ScoreRulesView`、日历的 rated 预判分支……），加一个平台要动
8 处后端 + 11 处前端，而**漏掉的那几处不报错、只静默给错数据**：未知平台的表现分
基线掉到兜底 1200、日历恒判「不计分」、前端标签渲染成另一个平台的颜色。

这里把能力声明成数据，配合 `validate_registry()` 在启动时核对（漏声明直接启动
失败），把「静默兜底」换成「立即失败」。校验挂在 `apps.contests.apps.ready()`：
contests 是持有 `platform` 字段的 app，且 `apps.common` 不在 INSTALLED_APPS 里。
"""
from dataclasses import dataclass

from django.core.exceptions import ImproperlyConfigured

from apps.common.models import Platform

#: `crawl_param`：后台触发与自动爬取用的窗口参数形状。
#:   count       —— 「最近 N 场」（CF / AtCoder）
#:   months_back  —— 「最近 N 个月」（牛客，按月历翻页）
CRAWL_PARAMS = ("", "count", "months_back")

#: `rated_preview`：日历里未开赛场次的计分判定来源。
#:   official_page —— 读官方赛事页公布的计分区间（AtCoder）
#:   contest_api   —— 读官方详情接口（牛客 contest-info）
#:   name_hint     —— 只有命名可用，作预判，赛后由真实判定覆盖（CF）
#:   provider      —— provider 自己就给了真实判定，日历层不再加工（洛谷）
#:   ""            —— 无判定源：等于让该平台在日历里永远是「不计分」，禁止
RATED_PREVIEWS = ("", "official_page", "contest_api", "name_hint", "provider")


@dataclass(frozen=True)
class PlatformSpec:
    """一个平台的全部能力声明。字段为空 = 该平台不具备这项能力。"""

    value: str                  # 与 Platform 枚举一致，也是 DB 存储值与 API 传参值
    label: str
    # ---- 爬取 / 计分 ----
    scraper_module: str = ""    # crawlers/ 下的模块名
    scraper_class: str = ""     # 模块里的客户端类名
    crawl_task: str = ""        # apps.crawler.tasks 里的任务属性名
    crawl_param: str = ""       # 见 CRAWL_PARAMS
    crawl_defaults: tuple = ()  # 触发时固定附带的参数，如 (("mode", "rating"),)
    config_field: str = ""      # CrawlConfig 上对应的窗口字段名
    perf_base: int = None       # 表现分公式的平台默认难度基线 D
    factor_field: str = ""      # ScoreConfig 上对应的平台系数列名
    scoring: bool = False       # 是否允许进积分链路（见 contests 的 countable 护栏）
    bindable: bool = False      # 是否开放「绑定平台账号」
    # ---- 日历 ----
    calendar_source: str = ""   # 排期 provider 名：clist / luogu / …
    rated_preview: str = ""     # 见 RATED_PREVIEWS


PLATFORM_SPECS = (
    PlatformSpec(
        value=Platform.CODEFORCES, label="Codeforces",
        scraper_module="cf_scraper", scraper_class="CodeforcesScraper",
        crawl_task="crawl_codeforces", crawl_param="count",
        crawl_defaults=(("mode", "rating"),),
        config_field="cf_count", perf_base=1400, factor_field="cf_factor",
        scoring=True, bindable=True,
        calendar_source="clist", rated_preview="name_hint",
    ),
    PlatformSpec(
        value=Platform.ATCODER, label="AtCoder",
        scraper_module="atcoder_scraper", scraper_class="AtCoderScraper",
        crawl_task="crawl_atcoder", crawl_param="count",
        config_field="atcoder_count", perf_base=900,
        factor_field="atcoder_factor",
        scoring=True, bindable=True,
        calendar_source="clist", rated_preview="official_page",
    ),
    PlatformSpec(
        value=Platform.NOWCODER, label="牛客",
        scraper_module="nowcoder_scraper", scraper_class="NowCoderScraper",
        crawl_task="crawl_nowcoder", crawl_param="months_back",
        config_field="nowcoder_months_back", perf_base=1000,
        factor_field="nowcoder_factor",
        scoring=True, bindable=True,
        calendar_source="clist", rated_preview="contest_api",
    ),
    PlatformSpec(
        # 洛谷：官方榜单页 404、用户页需登录（2026-09-26 实测），拿不到逐人名次，
        # 所以本期只做「官方排期 + 真实计分判定」的日历展示：不爬榜、不计分、
        # 不开放绑定。判定用官方 `rated` 整数的等级分位，是真实判定而非预判，
        # 故 rated_preview=provider（日历富化环节不再加工）。
        value=Platform.LUOGU, label="洛谷",
        scraper_module="luogu_scraper", scraper_class="LuoguScraper",
        calendar_source="luogu", rated_preview="provider",
    ),
)

_BY_VALUE = {s.value: s for s in PLATFORM_SPECS}


def spec(platform):
    """按站内平台值取声明。未知值直接抛，不返回 None 让调用方静默兜底。"""
    try:
        return _BY_VALUE[platform]
    except KeyError:
        raise ImproperlyConfigured(
            f"平台 {platform!r} 没有注册：请在 apps/common/platforms.py 的 "
            f"PLATFORM_SPECS 里补一条声明") from None


def is_known(platform):
    return platform in _BY_VALUE


def crawlable_specs():
    """有榜单爬虫、可被自动爬取调度的平台（按声明顺序）。"""
    return tuple(s for s in PLATFORM_SPECS if s.crawl_task)


def scoring_platforms():
    return tuple(s.value for s in PLATFORM_SPECS if s.scoring)


def bindable_platforms():
    return tuple(s.value for s in PLATFORM_SPECS if s.bindable)


def non_scoring_platforms():
    """只做展示、不进积分链路的平台 —— `countable()` 的第二道闸用。"""
    return tuple(s.value for s in PLATFORM_SPECS if not s.scoring)


def calendar_specs(source=None):
    """进日历的平台；`source` 给定时只要该排期 provider 覆盖的平台。"""
    return tuple(s for s in PLATFORM_SPECS
                 if s.calendar_source and (source is None
                                           or s.calendar_source == source))


def crawl_choices():
    """可手动/自动爬取的平台选项（给 DRF ChoiceField 用）。

    只列 `crawl_task` 非空的平台：把只做展示的平台放进触发接口，会先落一条
    没人消费的 CrawlJob 再抛 KeyError（历史上就是这么炸的）。
    """
    return tuple((s.value, s.label) for s in crawlable_specs())


def perf_bases():
    """平台默认难度基线。没有基线的平台不该进表现分公式，由引擎侧显式报错。"""
    return {s.value: s.perf_base for s in PLATFORM_SPECS if s.perf_base is not None}


def factor_fields():
    return {s.value: s.factor_field for s in PLATFORM_SPECS if s.factor_field}


def validate_registry():
    """启动期自检：枚举 ↔ 注册表 ↔ 被点名的模型字段三者必须对齐。

    只查结构、不打库也不打网络，所以放在 AppConfig.ready() 里；生产无 CI，这是
    「加了平台忘了配」最便宜的拦截点。
    """
    from apps.crawler.models import CrawlConfig
    from apps.schools.models import ScoreConfig

    def name(value):
        """枚举成员按字面值打印：`repr()` 会给出 `Platform.LUOGU`，读的人还得再猜。"""
        return f"'{value}'"

    errors = []
    enum_values = {c[0] for c in Platform.choices}
    registered = set(_BY_VALUE)
    if enum_values != registered:
        errors.append(
            f"Platform 枚举与注册表不一致："
            f"只在枚举={sorted(str(v) for v in enum_values - registered)} "
            f"只在注册表={sorted(str(v) for v in registered - enum_values)}")

    crawl_cols = {f.name for f in CrawlConfig._meta.get_fields()}
    factor_cols = {f.name for f in ScoreConfig._meta.get_fields()}

    for s in PLATFORM_SPECS:
        where = f"平台 {name(s.value)}"
        try:
            if s.label != Platform(s.value).label:
                errors.append(f"{where}: 注册表 label={s.label} "
                              f"与枚举 label={Platform(s.value).label} 不一致")
        except ValueError:
            errors.append(f"{where}: 不在 Platform 枚举里")
        if bool(s.scraper_module) != bool(s.scraper_class):
            errors.append(f"{where}: scraper_module / scraper_class 必须成对")
        if s.crawl_task and not s.scraper_module:
            errors.append(f"{where}: 声明了 crawl_task 却没有榜单客户端")
        if s.crawl_task and s.crawl_param not in CRAWL_PARAMS[1:]:
            errors.append(f"{where}: 有 crawl_task 却没有合法的窗口参数形状")
        if s.crawl_param and s.crawl_param not in CRAWL_PARAMS:
            errors.append(f"{where}: crawl_param={s.crawl_param} 非法")
        if s.rated_preview and s.rated_preview not in RATED_PREVIEWS:
            errors.append(f"{where}: rated_preview={s.rated_preview} 非法")
        if s.config_field and s.config_field not in crawl_cols:
            errors.append(f"{where}: CrawlConfig 上没有字段 {s.config_field}")
        if s.crawl_task and s.config_field and not s.crawl_param:
            errors.append(f"{where}: 有 CrawlConfig 窗口字段却没声明参数形状")
        if s.scoring:
            if s.perf_base is None:
                errors.append(f"{where}: 计分平台必须有 perf_base，"
                              f"否则表现分会静默落到兜底基线")
            if not s.factor_field or s.factor_field not in factor_cols:
                errors.append(f"{where}: 计分平台的平台系数列 "
                              f"{name(s.factor_field)} 在 ScoreConfig 上不存在")
            if not s.bindable:
                errors.append(f"{where}: 计分平台必须可绑定，否则成绩无归属")
        if s.calendar_source and not s.rated_preview:
            errors.append(f"{where}: 进日历却没有计分判定源 —— 它在日历里会永远"
                          f"显示成「不计分」，Rated 筛选对它失效")
    if errors:
        raise ImproperlyConfigured(
            "平台注册表校验失败：\n  - " + "\n  - ".join(errors))
    return True
