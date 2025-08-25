from django.http import JsonResponse
from django.db import connection, DatabaseError
from django.core.cache import cache, CacheKeyWarning


def health_check(_request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        cache.set("health_check", "ok", 1)
        cache_status = cache.get("health_check")
        
        return JsonResponse({
            "status": "healthy",
            "database": "ok",
            "cache": "ok" if cache_status == "ok" else "error"
        })
    except (DatabaseError, CacheKeyWarning):
        return JsonResponse({
            "status": "unhealthy"
        }, status=503)
