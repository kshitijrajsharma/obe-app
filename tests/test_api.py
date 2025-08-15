from django.contrib.auth import get_user_model
from django.contrib.gis.geos import GEOSGeometry
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.exports.models import Export, ExportRun

User = get_user_model()


class AuthAPITest(APITestCase):
    def setUp(self):
        self.user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "TestPass123!",
            "password_confirm": "TestPass123!",
            "first_name": "Test",
            "last_name": "User",
        }

    def test_register(self):
        url = reverse("auth:register")
        response = self.client.post(url, self.user_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", response.data["user"])

    def test_login(self):
        User.objects.create_user(
            username="testuser", email="test@example.com", password="TestPass123!"
        )
        url = reverse("auth:token_obtain_pair")
        data = {"username": "testuser", "password": "TestPass123!"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_token_refresh(self):
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="TestPass123!"
        )
        refresh = RefreshToken.for_user(user)
        url = reverse("auth:token_refresh")
        data = {"refresh": str(refresh)}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_token_verify(self):
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="TestPass123!"
        )
        refresh = RefreshToken.for_user(user)
        url = reverse("auth:token_verify")
        data = {"token": str(refresh.access_token)}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_profile(self):
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="TestPass123!"
        )
        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        url = reverse("auth:profile")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "testuser")

    def test_change_password(self):
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="TestPass123!"
        )
        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        url = reverse("auth:change_password")
        data = {
            "old_password": "TestPass123!",
            "new_password": "NewPass123!",
            "new_password_confirm": "NewPass123!",
        }
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_user_list(self):
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
            is_staff=True,
        )
        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        url = reverse("auth:user_list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_user_detail(self):
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
            is_staff=True,
        )
        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        url = reverse("auth:user_detail", kwargs={"pk": user.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ExportAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="TestPass123!"
        )
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        self.nepal_polygon = {
            "type": "Polygon",
            "coordinates": [
                [
                    [83.962, 28.213],
                    [83.962, 28.202],
                    [83.976, 28.202],
                    [83.976, 28.213],
                    [83.962, 28.213],
                ]
            ],
        }
        self.nepal_geom = GEOSGeometry(
            "POLYGON((83.962 28.213, 83.962 28.202, 83.976 28.202, 83.976 28.213, 83.962 28.213))"
        )

    def test_create_export(self):
        url = reverse("api:export_list")
        data = {
            "name": "Test Export",
            "description": "Test description",
            "area_of_interest": self.nepal_polygon,
            "source": "osm",
            "output_format": "geojson",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["properties"]["name"], "Test Export")

    def test_list_exports(self):
        Export.objects.create(
            user=self.user,
            name="Test Export",
            area_of_interest=self.nepal_geom,
            source="osm",
        )
        url = reverse("api:export_list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertEqual(response.data["results"]["type"], "FeatureCollection")

    def test_get_export(self):
        export = Export.objects.create(
            user=self.user,
            name="Test Export",
            area_of_interest=self.nepal_geom,
            source="osm",
        )
        url = reverse("api:export_detail", kwargs={"pk": export.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["properties"]["name"], "Test Export")

    def test_update_export(self):
        export = Export.objects.create(
            user=self.user,
            name="Test Export",
            area_of_interest=self.nepal_geom,
            source="osm",
        )
        url = reverse("api:export_detail", kwargs={"pk": export.pk})
        data = {"name": "Updated Export", "description": "Updated description"}
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["properties"]["name"], "Updated Export")

    def test_delete_export(self):
        export = Export.objects.create(
            user=self.user,
            name="Test Export",
            area_of_interest=self.nepal_geom,
            source="osm",
        )
        url = reverse("api:export_detail", kwargs={"pk": export.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_unauthorized_access(self):
        self.client.credentials()
        url = reverse("api:export_list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ExportRunAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="TestPass123!"
        )
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        self.nepal_geom = GEOSGeometry(
            "POLYGON((83.962 28.213, 83.962 28.202, 83.976 28.202, 83.976 28.213, 83.962 28.213))"
        )
        self.export = Export.objects.create(
            user=self.user,
            name="Test Export",
            area_of_interest=self.nepal_geom,
            source="osm",
        )

    def test_list_runs(self):
        url = reverse("api:run_list", kwargs={"export_id": self.export.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_run(self):
        url = reverse("api:run_create", kwargs={"export_id": self.export.pk})
        data = {"export": self.export.pk}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_get_run(self):
        run = ExportRun.objects.create(export=self.export)
        url = reverse("api:run_detail", kwargs={"pk": run.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_start_run(self):
        run = ExportRun.objects.create(export=self.export)
        url = reverse("api:start_run", kwargs={"pk": run.pk})
        response = self.client.post(url, format="json")
        self.assertIn(
            response.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]
        )

    def test_download_run(self):
        run = ExportRun.objects.create(export=self.export, status="SUCCESS")
        url = reverse("api:download_run", kwargs={"pk": run.pk})
        response = self.client.get(url)
        self.assertIn(
            response.status_code,
            [
                status.HTTP_200_OK,
                status.HTTP_404_NOT_FOUND,
                status.HTTP_400_BAD_REQUEST,
            ],
        )


class PublicAPITest(APITestCase):
    def test_public_exports(self):
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="TestPass123!"
        )
        nepal_geom = GEOSGeometry(
            "POLYGON((83.962 28.213, 83.962 28.202, 83.976 28.202, 83.976 28.213, 83.962 28.213))"
        )
        Export.objects.create(
            user=user,
            name="Public Export",
            area_of_interest=nepal_geom,
            source="osm",
            is_public=True,
        )

        url = reverse("api:public_exports")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class UtilityAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="TestPass123!"
        )
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

    def test_validate_aoi(self):
        url = reverse("api:validate_aoi")
        data = {
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [83.962, 28.213],
                        [83.962, 28.202],
                        [83.976, 28.202],
                        [83.976, 28.213],
                        [83.962, 28.213],
                    ]
                ],
            }
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_source_config_schema(self):
        url = reverse("api:source_schema", kwargs={"source": "osm"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
