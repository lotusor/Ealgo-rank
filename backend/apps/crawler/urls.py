"""爬虫路由：CrawlJob 列表/详情 + 手动触发。"""
from rest_framework.routers import DefaultRouter

from apps.crawler import views

app_name = "crawler"

router = DefaultRouter()
router.register("crawl-jobs", views.CrawlJobViewSet, basename="crawl-job")
router.register("crawl-configs", views.CrawlConfigViewSet,
                basename="crawl-config")

urlpatterns = router.urls
