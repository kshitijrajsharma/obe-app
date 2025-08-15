from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

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
        url = reverse("api:export_list")
        data = {
            "name": "Test Export for List",
            "description": "Test description",
            "area_of_interest": self.nepal_polygon,
            "source": "osm",
            "output_format": "geojson",
        }
        self.client.post(url, data, format="json")
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertEqual(response.data["results"]["type"], "FeatureCollection")    def test_get_export(self):
        url = reverse("api:export_list")
        data = {
            "name": "Test Export for Get",
            "description": "Test description",
            "area_of_interest": self.nepal_polygon,
            "source": "osm",
            "output_format": "geojson",
        }
        create_response = self.client.post(url, data, format="json")
        export_id = create_response.data["properties"]["id"]

        url = reverse("api:export_detail", kwargs={"pk": export_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["properties"]["name"], "Test Export for Get")

    def test_update_export(self):
        url = reverse("api:export_list")
        data = {
            "name": "Test Export for Update",
            "description": "Test description",
            "area_of_interest": self.nepal_polygon,
            "source": "osm",
            "output_format": "geojson",
        }
        create_response = self.client.post(url, data, format="json")
        export_id = create_response.data["properties"]["id"]

        url = reverse("api:export_detail", kwargs={"pk": export_id})
        update_data = {"name": "Updated Export", "description": "Updated description"}
        response = self.client.patch(url, update_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["properties"]["name"], "Updated Export")

    def test_delete_export(self):
        url = reverse("api:export_list")
        data = {
            "name": "Test Export for Delete",
            "description": "Test description",
            "area_of_interest": self.nepal_polygon,
            "source": "osm",
            "output_format": "geojson",
        }
        create_response = self.client.post(url, data, format="json")
        export_id = create_response.data["properties"]["id"]

        url = reverse("api:export_detail", kwargs={"pk": export_id})
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

        url = reverse("api:export_list")
        data = {
            "name": "Test Export for Runs",
            "description": "Test export for run testing",
            "area_of_interest": self.nepal_polygon,
            "source": "osm",
            "output_format": "geojson",
        }
        create_response = self.client.post(url, data, format="json")
        self.export_id = create_response.data["properties"]["id"]

    def test_list_runs(self):
        url = reverse("api:run_list", kwargs={"export_id": self.export_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_run(self):
        url = reverse("api:run_create", kwargs={"export_id": self.export_id})
        data = {"export": self.export_id}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_get_run(self):
        url = reverse("api:run_create", kwargs={"export_id": self.export_id})
        data = {"export": self.export_id}
        create_response = self.client.post(url, data, format="json")
        run_id = create_response.data["id"]

        url = reverse("api:run_detail", kwargs={"pk": run_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_start_run(self):
        url = reverse("api:run_create", kwargs={"export_id": self.export_id})
        data = {"export": self.export_id}
        create_response = self.client.post(url, data, format="json")
        run_id = create_response.data["id"]

        url = reverse("api:start_run", kwargs={"pk": run_id})
        response = self.client.post(url, format="json")
        self.assertIn(
            response.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]
        )

    def test_download_run(self):
        url = reverse("api:run_create", kwargs={"export_id": self.export_id})
        data = {"export": self.export_id}
        create_response = self.client.post(url, data, format="json")
        run_id = create_response.data["id"]

        url = reverse("api:download_run", kwargs={"pk": run_id})
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
        refresh = RefreshToken.for_user(user)

        nepal_polygon = {
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

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        url = reverse("api:export_list")
        data = {
            "name": "Public Export",
            "description": "Public export for testing",
            "area_of_interest": nepal_polygon,
            "source": "osm",
            "output_format": "geojson",
            "is_public": True,
        }
        self.client.post(url, data, format="json")

        self.client.credentials()
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
