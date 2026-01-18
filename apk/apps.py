from django.apps import AppConfig


class ApkConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apk'

    def ready(self):
        import apk.signals
        import apk.signals_user
