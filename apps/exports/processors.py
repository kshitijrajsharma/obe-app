import tempfile
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional
from django.contrib.gis.geos import Polygon

try:
    import obe
    import geopandas as gpd
    from shapely.geometry import mapping
except ImportError:
    obe = None
    gpd = None

logger = logging.getLogger(__name__)


class BaseProcessor(ABC):
    
    @abstractmethod
    def process(self, area_of_interest: Polygon, source_config: Dict[str, Any], 
                output_format: str) -> Dict[str, Any]:
        pass
    
    def _convert_django_polygon_to_shapely(self, django_polygon: Polygon):
        from shapely.geometry import shape
        geom_dict = mapping(django_polygon)
        return shape(geom_dict)
    
    def _save_output(self, gdf, output_format: str, base_filename: str) -> Optional[str]:
        if gdf is None or gdf.empty:
            logger.warning("No data to save")
            return None
        
        try:
            temp_dir = Path(tempfile.mkdtemp())
            
            if output_format == 'geoparquet':
                file_path = temp_dir / f"{base_filename}.parquet"
                gdf.to_parquet(file_path)
                
            elif output_format == 'geojson':
                file_path = temp_dir / f"{base_filename}.geojson"
                gdf.to_file(file_path, driver='GeoJSON')
                
            elif output_format == 'shapefile':
                file_path = temp_dir / f"{base_filename}.shp"
                gdf.to_file(file_path, driver='ESRI Shapefile')
                
            elif output_format == 'geopackage':
                file_path = temp_dir / f"{base_filename}.gpkg"
                gdf.to_file(file_path, driver='GPKG')
                
            else:
                raise ValueError(f"Unsupported output format: {output_format}")
            
            logger.info(f"Saved {len(gdf)} buildings to {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Failed to save output: {str(e)}")
            return None


class GoogleProcessor(BaseProcessor):
    
    def process(self, area_of_interest: Polygon, source_config: Dict[str, Any], 
                output_format: str) -> Dict[str, Any]:
        
        if obe is None:
            raise ImportError("OBE library not available")
        
        try:
            aoi_shapely = self._convert_django_polygon_to_shapely(area_of_interest)
            confidence_threshold = source_config.get('confidence_threshold', 0.7)
            
            logger.info(f"Extracting Google buildings with confidence >= {confidence_threshold}")
            
            gdf = obe.download_google_buildings(
                aoi_shapely,
                confidence_threshold=confidence_threshold
            )
            
            if gdf is None or gdf.empty:
                return {
                    'status': 'completed',
                    'building_count': 0,
                    'message': 'No buildings found in the specified area'
                }
            
            file_path = self._save_output(gdf, output_format, 'google_buildings')
            
            total_area = gdf.geometry.area.sum() if hasattr(gdf.geometry, 'area') else 0
            avg_confidence = gdf['confidence'].mean() if 'confidence' in gdf.columns else 0
            
            return {
                'status': 'completed',
                'building_count': len(gdf),
                'total_area_m2': float(total_area),
                'average_confidence': float(avg_confidence),
                'file_path': file_path,
                'source': 'google',
                'config_used': source_config
            }
            
        except Exception as e:
            logger.error(f"Google processor failed: {str(e)}")
            raise


class MicrosoftProcessor(BaseProcessor):
    
    def process(self, area_of_interest: Polygon, source_config: Dict[str, Any], 
                output_format: str) -> Dict[str, Any]:
        
        if obe is None:
            raise ImportError("OBE library not available")
        
        try:
            aoi_shapely = self._convert_django_polygon_to_shapely(area_of_interest)
            region = source_config.get('region', 'global')
            
            logger.info(f"Extracting Microsoft buildings for region: {region}")
            
            gdf = obe.download_microsoft_buildings(aoi_shapely, region=region)
            
            if gdf is None or gdf.empty:
                return {
                    'status': 'completed',
                    'building_count': 0,
                    'message': 'No buildings found in the specified area'
                }
            
            file_path = self._save_output(gdf, output_format, 'microsoft_buildings')
            total_area = gdf.geometry.area.sum() if hasattr(gdf.geometry, 'area') else 0
            
            return {
                'status': 'completed',
                'building_count': len(gdf),
                'total_area_m2': float(total_area),
                'file_path': file_path,
                'source': 'microsoft',
                'region': region,
                'config_used': source_config
            }
            
        except Exception as e:
            logger.error(f"Microsoft processor failed: {str(e)}")
            raise


class OSMProcessor(BaseProcessor):
    
    def process(self, area_of_interest: Polygon, source_config: Dict[str, Any], 
                output_format: str) -> Dict[str, Any]:
        
        if obe is None:
            raise ImportError("OBE library not available")
        
        try:
            aoi_shapely = self._convert_django_polygon_to_shapely(area_of_interest)
            building_types = source_config.get(
                'building_types', 
                ['yes', 'house', 'apartments', 'commercial', 'industrial']
            )
            
            logger.info(f"Extracting OSM buildings with types: {building_types}")
            
            gdf = obe.download_osm_buildings(aoi_shapely, building_types=building_types)
            
            if gdf is None or gdf.empty:
                return {
                    'status': 'completed',
                    'building_count': 0,
                    'message': 'No buildings found in the specified area'
                }
            
            file_path = self._save_output(gdf, output_format, 'osm_buildings')
            
            total_area = gdf.geometry.area.sum() if hasattr(gdf.geometry, 'area') else 0
            building_type_counts = gdf['building'].value_counts().to_dict() if 'building' in gdf.columns else {}
            
            return {
                'status': 'completed',
                'building_count': len(gdf),
                'total_area_m2': float(total_area),
                'building_type_counts': building_type_counts,
                'file_path': file_path,
                'source': 'osm',
                'config_used': source_config
            }
            
        except Exception as e:
            logger.error(f"OSM processor failed: {str(e)}")
            raise


class OvertureProcessor(BaseProcessor):
    
    def process(self, area_of_interest: Polygon, source_config: Dict[str, Any], 
                output_format: str) -> Dict[str, Any]:
        
        if obe is None:
            raise ImportError("OBE library not available")
        
        try:
            aoi_shapely = self._convert_django_polygon_to_shapely(area_of_interest)
            include_height = source_config.get('include_height', True)
            min_area = source_config.get('min_area', 10)
            
            logger.info(f"Extracting Overture buildings (min_area: {min_area}, include_height: {include_height})")
            
            gdf = obe.download_overture_buildings(
                aoi_shapely,
                include_height=include_height,
                min_area=min_area
            )
            
            if gdf is None or gdf.empty:
                return {
                    'status': 'completed',
                    'building_count': 0,
                    'message': 'No buildings found in the specified area'
                }
            
            file_path = self._save_output(gdf, output_format, 'overture_buildings')
            
            total_area = gdf.geometry.area.sum() if hasattr(gdf.geometry, 'area') else 0
            avg_height = gdf['height'].mean() if 'height' in gdf.columns else None
            
            results = {
                'status': 'completed',
                'building_count': len(gdf),
                'total_area_m2': float(total_area),
                'file_path': file_path,
                'source': 'overture',
                'config_used': source_config
            }
            
            if avg_height is not None:
                results['average_height_m'] = float(avg_height)
            
            return results
            
        except Exception as e:
            logger.error(f"Overture processor failed: {str(e)}")
            raise


PROCESSORS = {
    'google': GoogleProcessor,
    'microsoft': MicrosoftProcessor,
    'osm': OSMProcessor,
    'overture': OvertureProcessor,
}


def get_processor(source: str):
    if source not in PROCESSORS:
        raise ValueError(f"Unsupported source: {source}")
    
    processor_class = PROCESSORS[source]
    return processor_class()
