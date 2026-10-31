"""Remove old generated files that are no longer referenced by the database."""

from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.datasets.models import Dataset
from apps.models.models import MLModel


class Command(BaseCommand):
    help = "Remove old unreferenced generated dataset/model files."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List orphan files without deleting them.",
        )
        parser.add_argument(
            "--older-than-minutes",
            type=int,
            default=60,
            help="Only remove files older than this many minutes.",
        )

    def handle(self, *args, **options):
        root = Path(settings.STORAGE_ROOT).resolve()
        if not root.exists():
            self.stdout.write(self.style.SUCCESS("Storage root does not exist; nothing to clean."))
            return

        referenced = set(
            Dataset.objects.values_list("storage_path", flat=True)
        ) | set(
            MLModel.objects.exclude(artifact_reference="").values_list(
                "artifact_reference", flat=True
            )
        )
        cutoff = timezone.now() - timedelta(minutes=max(0, options["older_than_minutes"]))
        cutoff_timestamp = cutoff.timestamp()
        extensions = {".csv", ".joblib", ".tmp", ".previous"}
        removed = 0

        for directory_name in ("datasets", "trained_models"):
            directory = root / directory_name
            if not directory.is_dir():
                continue
            for path in directory.rglob("*"):
                if not path.is_file() or path.suffix not in extensions:
                    continue
                relative = path.relative_to(root).as_posix()
                if relative in referenced:
                    continue
                try:
                    if path.stat().st_mtime > cutoff_timestamp:
                        continue
                    if options["dry_run"]:
                        self.stdout.write(f"Would remove: {relative}")
                    else:
                        path.unlink()
                        self.stdout.write(f"Removed: {relative}")
                    removed += 1
                except OSError as exc:
                    self.stderr.write(f"Could not inspect/remove {relative}: {exc}")

        self.stdout.write(self.style.SUCCESS(f"Processed {removed} orphan file(s)."))
