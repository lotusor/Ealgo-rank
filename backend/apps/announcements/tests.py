from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.announcements.models import Announcement, AnnouncementLevel


class AnnouncementAPITest(APITestCase):
    def setUp(self):
        self.super_admin = get_user_model().objects.create_superuser(
            username="root", email="root@ealgo.local", password="rootroot12")
        self.normal = get_user_model().objects.create_user(
            username="u1", password="u1u1u1u1")

    def test_public_only_active(self):
        Announcement.objects.create(
            title="a", content="c", level=AnnouncementLevel.INFO, is_active=True)
        Announcement.objects.create(
            title="b", content="c", level=AnnouncementLevel.WARNING, is_active=False)
        resp = self.client.get("/api/v1/announcements/public/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["title"], "a")

    def test_public_pinned_first(self):
        Announcement.objects.create(title="plain", content="c", pinned=False)
        Announcement.objects.create(title="pin", content="c", pinned=True)
        resp = self.client.get("/api/v1/announcements/public/")
        self.assertEqual(resp.json()[0]["title"], "pin")

    def test_superadmin_crud(self):
        self.client.force_authenticate(self.super_admin)
        resp = self.client.post(
            "/api/v1/announcements/", {"title": "t", "content": "c"}, format="json")
        self.assertEqual(resp.status_code, 201)
        aid = resp.json()["id"]

        resp = self.client.patch(
            f"/api/v1/announcements/{aid}/", {"pinned": True}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["pinned"])

        resp = self.client.delete(f"/api/v1/announcements/{aid}/")
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(Announcement.objects.filter(pk=aid).exists())

    def test_normal_user_cannot_create(self):
        self.client.force_authenticate(self.normal)
        resp = self.client.post(
            "/api/v1/announcements/", {"title": "t", "content": "c"}, format="json")
        self.assertEqual(resp.status_code, 403)

    def test_empty_title_rejected(self):
        self.client.force_authenticate(self.super_admin)
        resp = self.client.post(
            "/api/v1/announcements/", {"title": "  ", "content": "c"}, format="json")
        self.assertEqual(resp.status_code, 400)
