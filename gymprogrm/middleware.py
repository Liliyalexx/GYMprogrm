from django.utils import translation


class TrainerEnglishMiddleware:
    """Force English language for trainer accounts (non-student users)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not hasattr(request.user, 'student'):
            translation.activate('en')
            request.LANGUAGE_CODE = 'en'
        return self.get_response(request)
