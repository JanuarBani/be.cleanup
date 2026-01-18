from rest_framework_simplejwt.views import TokenObtainPairView
from .auth_serializers import CustomTokenObtainPairSerializer

class CustomLoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


# from rest_framework_simplejwt.views import TokenObtainPairView
# from .auth_serializers import CustomTokenObtainPairSerializer

# class CustomLoginView(TokenObtainPairView):
#     serializer_class = CustomTokenObtainPairSerializer
