import json
import logging
import time
from typing import Any, Dict, Optional

import requests
from django.conf import settings
from django.contrib.gis.geos import Polygon

logger = logging.getLogger(__name__)


class PopulationEstimator:
    @staticmethod
    def estimate_population(polygon: Polygon) -> Optional[Dict[str, Any]]:
        worldpop_token = getattr(settings, "WORLDPOP_API_KEY", None)

        logger.info(
            "Attempting WorldPop API (key: %s)", "yes" if worldpop_token else "no"
        )
        result = PopulationEstimator._get_worldpop_data(polygon, worldpop_token)
        if result:
            logger.info(
                "WorldPop success: %s people", result.get("population_estimate")
            )
            return result

        logger.info("WorldPop failed or no data returned")
        return None

    @staticmethod
    def _get_worldpop_data(
        polygon: Polygon, api_key: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        try:
            if polygon.srid != 4326:
                polygon.transform(4326)

            geojson = {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {},
                        "geometry": json.loads(polygon.geojson),
                    }
                ],
            }

            params = {
                "dataset": "wpgppop",
                "year": "2020",
                "geojson": json.dumps(geojson),
                "runasync": "false",
            }

            if api_key:
                params["key"] = api_key

            response = requests.get(
                "https://api.worldpop.org/v1/services/stats", params=params, timeout=35
            )

            logger.info("WorldPop API response: %s", response.status_code)

            if response.status_code != 200:
                logger.warning("WorldPop API error: %s", response.text)
                return None

            data = response.json()
            logger.info("WorldPop response data: %s", data.get("status"))

            if data.get("status") == "created":
                task_id = data.get("taskid")
                if task_id:
                    logger.info("WorldPop async task created: %s", task_id)
                    return PopulationEstimator._poll_worldpop_task(task_id)
            elif data.get("status") == "finished":
                pop_data = data.get("data", {})
                total_pop = pop_data.get("total_population", 0)

                logger.info("WorldPop direct result: %s people", total_pop)

                if total_pop:
                    area_km2 = PopulationEstimator._calculate_area_km2(polygon)
                    return {
                        "population_estimate": int(total_pop),
                        "area_km2": round(area_km2, 2),
                        "density_per_km2": round(total_pop / area_km2, 1)
                        if area_km2 > 0
                        else 0,
                        "source": "worldpop",
                        "method": "worldpop_api_2020",
                        "year": 2020,
                    }

            return None

        except (requests.RequestException, json.JSONDecodeError, KeyError) as e:
            logger.warning("WorldPop API failed: %s", str(e))
            return None

    @staticmethod
    def _poll_worldpop_task(
        task_id: str, max_attempts: int = 5
    ) -> Optional[Dict[str, Any]]:
        for attempt in range(max_attempts):
            try:
                time.sleep(2**attempt)
                response = requests.get(
                    f"https://api.worldpop.org/v1/tasks/{task_id}", timeout=10
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "finished":
                        pop_data = data.get("data", {})
                        total_pop = pop_data.get("total_population", 0)

                        logger.info(
                            "WorldPop task %s finished with %s people",
                            task_id,
                            total_pop,
                        )

                        if total_pop:
                            return {
                                "population_estimate": int(total_pop),
                                "source": "worldpop",
                                "method": "worldpop_api_async_2020",
                                "year": 2020,
                                "task_id": task_id,
                            }
                        break
                    elif data.get("error"):
                        logger.warning(
                            "WorldPop task %s failed: %s", task_id, data.get("error")
                        )
                        break

            except (requests.RequestException, json.JSONDecodeError) as e:
                logger.warning("WorldPop task polling failed: %s", str(e))

        return None

    @staticmethod
    def _calculate_area_km2(polygon: Polygon) -> float:
        try:
            polygon_proj = polygon.transform(3857, clone=True)
            area_m2 = polygon_proj.area
            return area_m2 / 1_000_000
        except (AttributeError, ValueError):
            return 0.0
