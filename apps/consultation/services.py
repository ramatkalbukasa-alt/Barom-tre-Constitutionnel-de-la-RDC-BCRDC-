from django.db.models import Count
from .models import Vote, VoteStatSnapshot, VOTE_CHOICE


def compute_stats() -> dict:
    total = Vote.objects.count()
    if total == 0:
        return {
            "total": 0,
            "maintien": 0, "revision": 0, "changement": 0,
            "maintien_pct": 0, "revision_pct": 0, "changement_pct": 0,
            "by_province": {}, "by_location": {}, "by_age": {}, "by_gender": {}, "by_argument": {},
        }

    counts = {
        row["choice"]: row["count"]
        for row in Vote.objects.values("choice").annotate(count=Count("choice"))
    }
    m = counts.get(VOTE_CHOICE.MAINTIEN, 0)
    r = counts.get(VOTE_CHOICE.REVISION, 0)
    c = counts.get(VOTE_CHOICE.CHANGEMENT, 0)

    by_province = {}
    for row in Vote.objects.values("user__province", "choice").annotate(count=Count("choice")):
        prov = row["user__province"] or "inconnu"
        if prov not in by_province:
            by_province[prov] = {"maintien": 0, "revision": 0, "changement": 0}
        by_province[prov][row["choice"]] = row["count"]

    by_location = {
        row["user__location_type"]: row["count"]
        for row in Vote.objects.values("user__location_type").annotate(count=Count("id"))
    }

    by_age = {
        row["user__age_group"]: row["count"]
        for row in Vote.objects.values("user__age_group").annotate(count=Count("id"))
    }

    by_gender = {
        row["user__gender"]: row["count"]
        for row in Vote.objects.values("user__gender").annotate(count=Count("id"))
    }

    by_argument = {
        row["argument_category"]: row["count"]
        for row in Vote.objects.values("argument_category").annotate(count=Count("id"))
    }

    return {
        "total": total,
        "maintien": m,
        "revision": r,
        "changement": c,
        "maintien_pct": round(m / total * 100, 1),
        "revision_pct": round(r / total * 100, 1),
        "changement_pct": round(c / total * 100, 1),
        "by_province": by_province,
        "by_location": by_location,
        "by_age": by_age,
        "by_gender": by_gender,
        "by_argument": by_argument,
    }


def get_or_refresh_snapshot() -> VoteStatSnapshot:
    snapshot, _ = VoteStatSnapshot.objects.get_or_create(pk=1)
    stats = compute_stats()
    snapshot.total_votes = stats["total"]
    snapshot.maintien_count = stats["maintien"]
    snapshot.revision_count = stats["revision"]
    snapshot.changement_count = stats["changement"]
    snapshot.stats_by_province = stats["by_province"]
    snapshot.stats_by_location = stats["by_location"]
    snapshot.stats_by_age = stats["by_age"]
    snapshot.stats_by_gender = stats["by_gender"]
    snapshot.stats_by_argument = stats["by_argument"]
    snapshot.save()
    return snapshot
