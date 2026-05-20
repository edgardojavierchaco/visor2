from rest_framework.views import APIView
from rest_framework.response import Response

from .serializers import IndicatorQuerySerializer
from apps.indicators.services.indicator_service import IndicatorService


class IndicatorView(APIView):

    def get(self, request):

        serializer = IndicatorQuerySerializer(
            data=request.GET
        )

        serializer.is_valid(
            raise_exception=True
        )

        service = IndicatorService()

        data = service.get_indicators(
            serializer.validated_data
        )

        return Response({
            "count": len(data),
            "results": data
        })