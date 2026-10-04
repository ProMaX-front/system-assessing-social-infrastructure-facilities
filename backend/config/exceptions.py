from rest_framework.views import exception_handler


TRANSLATIONS = {
    "Authentication credentials were not provided.": "Не указаны данные для авторизации.",
    "Given token not valid for any token type": "Сеанс авторизации недействителен. Выполните вход заново.",
    "Token is invalid or expired": "Срок действия сеанса истёк. Выполните вход заново.",
    "Token is blacklisted": "Сеанс авторизации завершён. Выполните вход заново.",
    "User not found": "Пользователь не найден.",
    "No active account found with the given credentials": "Неверный логин или пароль.",
    "Invalid token.": "Недействительный токен авторизации.",
    "Method \"GET\" not allowed.": "Метод GET не поддерживается для этого запроса.",
    "Method \"POST\" not allowed.": "Метод POST не поддерживается для этого запроса.",
    "Not found.": "Запрошенный ресурс не найден.",
    "Permission denied.": "Недостаточно прав для выполнения операции.",
}


def _translate(value):
    if isinstance(value, str):
        if value in TRANSLATIONS:
            return TRANSLATIONS[value]
        for english, russian in TRANSLATIONS.items():
            if english in value:
                return value.replace(english, russian)
        return value

    if isinstance(value, list):
        return [_translate(item) for item in value]

    if isinstance(value, dict):
        return {key: _translate(item) for key, item in value.items()}

    return value


def russian_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        response.data = _translate(response.data)
    return response
