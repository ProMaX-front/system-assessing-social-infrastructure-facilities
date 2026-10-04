import os

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Подготавливает единственную учётную запись системы."

    def handle(self, *args, **options):
        debug_mode = os.getenv("DJANGO_DEBUG", "1") == "1"

        if debug_mode:
            username = "pavel"
            password = "".join(str(number) for number in range(1, 9))
        else:
            username = os.getenv("DEFAULT_USERNAME", "pavel").strip()
            password = os.getenv("DEFAULT_PASSWORD", "")
            if not password:
                raise CommandError(
                    "Для рабочего окружения необходимо задать DEFAULT_PASSWORD."
                )

        user, _ = User.objects.get_or_create(username=username)
        user.email = ""
        user.is_active = True
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()

        User.objects.exclude(pk=user.pk).delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Единая учётная запись «{username}» подготовлена."
            )
        )
