from django.contrib.auth import get_user_model
from django.contrib.gis.geos import GEOSGeometry
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.exports.models import Export

User = get_user_model()


class AuthAPITestCase(APITestCase):
    """Test cases for authentication endpoints"""

    def setUp(self):
        self.register_url = reverse("auth:register")
        self.login_url = reverse("auth:token_obtain_pair")
        self.profile_url = reverse("auth:profile")

        self.user_data = {
            "username": "testuser_nepal",
            "email": "test@nepal.com",
            "password": "NepalTest123!",
            "password_confirm": "NepalTest123!",
            "first_name": "Test",
            "last_name": "User",
        }

    def test_user_registration(self):
        """Test user registration with valid data"""
        response = self.client.post(self.register_url, self.user_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", response.data["user"])
        self.assertTrue(User.objects.filter(username="testuser_nepal").exists())

    def test_user_login(self):
        """Test user login with valid credentials"""
        # Create user first
        User.objects.create_user(
            username="testuser_nepal", email="test@nepal.com", password="NepalTest123!"
        )

        login_data = {"username": "testuser_nepal", "password": "NepalTest123!"}

        response = self.client.post(self.login_url, login_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)


class ExportAPITestCase(APITestCase):
    """Test cases for export endpoints with Nepal polygon"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="nepal_user", email="user@nepal.com", password="NepalTest123!"
        )

        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        self.exports_url = reverse("api:export_list")

        # Nepal polygon from user request - as GEOSGeometry for model creation
        nepal_coordinates = [
            [83.96184435207743, 28.212767538129086],
            [83.96184435207743, 28.20236573207498],
            [83.97605449676462, 28.20236573207498],
            [83.97605449676462, 28.212767538129086],
            [83.96184435207743, 28.212767538129086],
        ]
        coord_string = ", ".join(
            [f"{coord[0]} {coord[1]}" for coord in nepal_coordinates]
        )
        self.nepal_geom = GEOSGeometry(f"POLYGON(({coord_string}))")

    def test_create_export_nepal(self):
        """Test creating an export with Nepal polygon"""
        data = {
            "name": "Nepal Region Export",
            "description": "Export data for a region in Nepal",
            "area_of_interest": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [83.96184435207743, 28.212767538129086],
                        [83.96184435207743, 28.20236573207498],
                        [83.97605449676462, 28.20236573207498],
                        [83.97605449676462, 28.212767538129086],
                        [83.96184435207743, 28.212767538129086],
                    ]
                ],
            },
            "output_format": "geojson",
            "source": "osm",
        }

        response = self.client.post(self.exports_url, data, format="json")

        print(f"Response status: {response.status_code}")
        print(f"Response data: {response.data}")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["properties"]["name"], "Nepal Region Export")
        self.assertEqual(response.data["properties"]["source"], "osm")
        self.assertEqual(response.data["properties"]["output_format"], "geojson")
        self.assertIn("id", response.data["properties"])

        # Verify export was created in database
        self.assertTrue(Export.objects.filter(name="Nepal Region Export").exists())

    def test_create_export_microsoft_nepal(self):
        """Test creating an export with Microsoft source for Nepal"""
        data = {
            "name": "Nepal Microsoft Export",
            "description": "Export Microsoft building data for Nepal region",
            "area_of_interest": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [83.96184435207743, 28.212767538129086],
                        [83.96184435207743, 28.20236573207498],
                        [83.97605449676462, 28.20236573207498],
                        [83.97605449676462, 28.212767538129086],
                        [83.96184435207743, 28.212767538129086],
                    ]
                ],
            },
            "output_format": "geoparquet",
            "source": "microsoft",
        }

        response = self.client.post(self.exports_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["properties"]["source"], "microsoft")
        self.assertEqual(response.data["properties"]["name"], "Nepal Microsoft Export")

    def test_list_exports(self):
        """Test listing user's exports"""
        # Create test exports
        Export.objects.create(
            user=self.user,
            name="Nepal Export 1",
            description="First Nepal export",
            area_of_interest=self.nepal_geom,
            source="osm",
        )

        response = self.client.get(self.exports_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Response is paginated with GeoJSON FeatureCollection in 'results'
        self.assertIn("results", response.data)
        self.assertEqual(response.data["results"]["type"], "FeatureCollection")
        self.assertIn("features", response.data["results"])
        self.assertGreaterEqual(len(response.data["results"]["features"]), 1)
        # Check that each item is a Feature
        self.assertEqual(response.data["results"]["features"][0]["type"], "Feature")

    def test_unauthorized_access(self):
        """Test that unauthenticated users cannot access exports"""
        self.client.credentials()  # Remove authentication

        response = self.client.get(self.exports_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class UtilityAPITestCase(APITestCase):
    """Test cases for utility endpoints"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="nepal_validator",
            email="validator@nepal.com",
            password="NepalTest123!",
        )

        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        self.validate_url = reverse("api:validate_aoi")
        self.source_config_url = reverse(
            "api:source_schema", kwargs={"source": "microsoft"}
        )

        self.nepal_geometry = {
            "type": "Polygon",
            "coordinates": [
                [
                    [83.96184435207743, 28.212767538129086],
                    [83.96184435207743, 28.20236573207498],
                    [83.97605449676462, 28.20236573207498],
                    [83.97605449676462, 28.212767538129086],
                    [83.96184435207743, 28.212767538129086],
                ]
            ],
        }

    def test_validate_nepal_geometry(self):
        """Test geometry validation with Nepal polygon"""
        data = {"geometry": self.nepal_geometry}

        response = self.client.post(self.validate_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["valid"])
        self.assertIn("area_km2", response.data)
        self.assertIn("centroid", response.data)
        self.assertGreater(response.data["area_km2"], 0)

    def test_get_source_config_microsoft_nepal(self):
        """Test getting source configuration for Microsoft in Nepal"""
        response = self.client.get(self.source_config_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["source"], "microsoft")
        self.assertIn("schema", response.data)
        self.assertIsInstance(response.data["schema"], dict)


class IntegrationTestCase(APITestCase):
    """Complete workflow integration tests with Nepal data"""

    def setUp(self):
        self.register_url = reverse("auth:register")
        self.login_url = reverse("auth:token_obtain_pair")
        self.exports_url = reverse("api:export_list")

    def test_complete_nepal_workflow(self):
        """Test complete workflow: register -> login -> create export"""

        # 1. Register user
        register_data = {
            "username": "nepal_integration_user",
            "email": "integration@nepal.com",
            "password": "NepalIntegration123!",
            "password_confirm": "NepalIntegration123!",
            "first_name": "Nepal",
            "last_name": "User",
        }

        register_response = self.client.post(
            self.register_url, register_data, format="json"
        )
        self.assertEqual(register_response.status_code, status.HTTP_201_CREATED)

        # 2. Login
        login_data = {
            "username": "nepal_integration_user",
            "password": "NepalIntegration123!",
        }

        login_response = self.client.post(self.login_url, login_data, format="json")
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)

        # Set auth token
        token = login_response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        # 3. Create export with Nepal polygon
        export_data = {
            "name": "Complete Nepal Workflow Export",
            "description": "Integration test export for Nepal region",
            "area_of_interest": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [83.96184435207743, 28.212767538129086],
                        [83.96184435207743, 28.20236573207498],
                        [83.97605449676462, 28.20236573207498],
                        [83.97605449676462, 28.212767538129086],
                        [83.96184435207743, 28.212767538129086],
                    ]
                ],
            },
            "output_format": "geojson",
            "source": "microsoft",  # Using Microsoft for Nepal as specified
        }

        export_response = self.client.post(self.exports_url, export_data, format="json")
        self.assertEqual(export_response.status_code, status.HTTP_201_CREATED)

        export_id = export_response.data["properties"]["id"]

        # 4. Verify export was created correctly
        export_detail_url = reverse("api:export_detail", kwargs={"pk": export_id})
        export_detail_response = self.client.get(export_detail_url)

        self.assertEqual(export_detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            export_detail_response.data["properties"]["name"],
            "Complete Nepal Workflow Export",
        )
        self.assertEqual(
            export_detail_response.data["properties"]["source"], "microsoft"
        )
