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


class FirstMessageTests(TestCase):
    """统一异常处理：字段级校验错误的第一条原因提升为 detail（2026-09-13）。"""

    def test_first_message_forms(self):
        from apps.common.exceptions import _first_message

        cases = [
            # (输入, 期望)
            ({"school": ["你本月已提交过申请，请下月再试"]},
             "你本月已提交过申请，请下月再试"),
            # serializer 级 validate() 的 non_field_errors 优先
            ({"school": ["字段级"], "non_field_errors": ["非字段级"]},
             "非字段级"),
            # 嵌套 serializer（dict 套 dict）
            ({"profile": {"name": ["名字太长"]}}, "名字太长"),
            # list 内嵌 dict
            ([{"a": ["深层"]}], "深层"),
            # 字符串
            ("直接字符串", "直接字符串"),
            # 空结构
            ({}, ""),
        ]
        for data, expect in cases:
            with self.subTest(data=data):
                self.assertEqual(_first_message(data), expect)

    def test_handler_promotes_first_reason(self):
        """端到端：触发字段级校验错误，detail 应为具体原因而非通用文案。"""
        from rest_framework import serializers, viewsets
        from rest_framework.permissions import AllowAny
        from rest_framework.test import APIRequestFactory

        from apps.common.exceptions import api_exception_handler

        class _Ser(serializers.Serializer):
            school = serializers.CharField()

            def validate_school(self, v):
                raise serializers.ValidationError("你本月已提交过申请，请下月再试")

        class _View(viewsets.ViewSet):
            permission_classes = [AllowAny]

            def create(self, request):
                ser = _Ser(data=request.data)
                ser.is_valid(raise_exception=True)
                return serializers.Response({})

        factory = APIRequestFactory()
        req = factory.post("/", {"school": "x"}, format="json")
        view = _View.as_view({"post": "create"})
        # DRF dispatch 会捕获 ValidationError 并走配置的统一 handler，
        # 直接返回 400 响应（不抛异常）
        resp = view(req)
        resp.render()  # 显式渲染（test client 之外不自动渲染）
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data["detail"], "你本月已提交过申请，请下月再试")
        self.assertEqual(resp.data["code"], "validation_error")
        # errors 明细保留
        self.assertIn("school", resp.data["errors"])
