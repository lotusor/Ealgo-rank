"""公开站点统计端点（首页数字看板）。"""
from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.schools.models import School


class PublicStatsViewTests(TestCase):
    def test_allow_any_and_counts(self):
        School.objects.create(name="统计大学", code="statu", short_name="统")
        get_user_model().objects.create_user(username="stat1", password="Test1234!")
        resp = self.client.get("/api/v1/stats/")
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(resp.data["schools"], 1)
        self.assertGreaterEqual(resp.data["users"], 1)
        self.assertEqual(
            set(resp.data.keys()),
            {"schools", "contests", "users", "participations"},
        )
