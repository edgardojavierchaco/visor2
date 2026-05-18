from apps.indicators.models import Indicator

class IndicatorRegistry:

    @staticmethod
    def get(code: str) -> Indicator:
        return Indicator.objects.get(code=code)

    @staticmethod
    def list_active():
        return Indicator.objects.filter(active=True)