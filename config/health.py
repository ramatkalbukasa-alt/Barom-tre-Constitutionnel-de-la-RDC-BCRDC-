from django.db import connection
from django.http import JsonResponse


def healthz(request):
    """Lightweight liveness/readiness probe for load balancers and orchestrators."""
    db_ok = True
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        db_ok = False

    payload = {"status": "ok" if db_ok else "degraded", "database": db_ok}
    return JsonResponse(payload, status=200 if db_ok else 503)
