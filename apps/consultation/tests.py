from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.users.models import CitizenUser
from apps.consultation.models import Vote, VoteStatSnapshot, VOTE_CHOICE
from apps.consultation.services import (
    compute_stats,
    get_or_refresh_snapshot,
    snapshot_to_stats,
)


class StatsTests(TestCase):
    def _user(self, i: int) -> CitizenUser:
        return CitizenUser.objects.create_user(phone_hash=f"hash-{i}")

    def _vote(self, i: int, choice: str) -> Vote:
        return Vote.objects.create(user=self._user(i), choice=choice, justification="x" * 40)

    def test_compute_stats_percentages(self):
        self._vote(1, VOTE_CHOICE.MAINTIEN)
        self._vote(2, VOTE_CHOICE.MAINTIEN)
        self._vote(3, VOTE_CHOICE.REVISION)
        self._vote(4, VOTE_CHOICE.CHANGEMENT)

        stats = compute_stats()
        self.assertEqual(stats["total"], 4)
        self.assertEqual(stats["maintien"], 2)
        self.assertEqual(stats["maintien_pct"], 50.0)
        self.assertEqual(stats["revision_pct"], 25.0)

    def test_one_vote_per_user(self):
        user = self._user(10)
        Vote.objects.create(user=user, choice=VOTE_CHOICE.MAINTIEN, justification="x" * 40)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Vote.objects.create(user=user, choice=VOTE_CHOICE.REVISION, justification="y" * 40)

    def test_snapshot_roundtrip(self):
        self._vote(20, VOTE_CHOICE.MAINTIEN)
        snapshot = get_or_refresh_snapshot()
        stats = snapshot_to_stats(snapshot)
        self.assertEqual(stats["total"], 1)
        self.assertEqual(stats["maintien_pct"], 100.0)

    def test_empty_stats(self):
        stats = compute_stats()
        self.assertEqual(stats["total"], 0)
        self.assertEqual(stats["maintien_pct"], 0)
