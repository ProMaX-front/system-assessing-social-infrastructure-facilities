import os

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Создаёт единственную учётную запись для локального стенда из переменных окружения."

    def handle(self, *args, **options):
        username = os.getenv("DEFAULT_USERNAME", "Павел").strip()
        password = os.getenv("DEFAULT_PASSWORD", "")

        if not password:
            raise CommandError(
                "Не задан DEFAULT_PASSWORD в .env. "
                "Пароль намеренно не хранится в публичном репозитории."
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
            self.style.SUCCESS(f"Единая учётная запись «{username}» подготовлена.")
        )
