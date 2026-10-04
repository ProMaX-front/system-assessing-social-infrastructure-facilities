from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView


class RussianTokenObtainPairSerializer(TokenObtainPairSerializer):
    default_error_messages = {
        "no_active_account": "Неверный логин или пароль.",
    }


class RussianTokenObtainPairView(TokenObtainPairView):
    serializer_class = RussianTokenObtainPairSerializer
