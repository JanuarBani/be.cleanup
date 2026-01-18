from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.exceptions import AuthenticationFailed

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):

    def validate(self, attrs):
        data = super().validate(attrs)

        # 🔴 BLOK USER NONAKTIF
        if not self.user.is_active:
            raise AuthenticationFailed(
                "Akun Anda telah dinonaktifkan oleh administrator."
            )

        data['user'] = {
            "id": self.user.id,
            "username": self.user.username,
            "role": self.user.role,
            "is_active": self.user.is_active
        }

        return data

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        token['role'] = user.role
        token['is_active'] = user.is_active
        return token


# from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
# from rest_framework.exceptions import AuthenticationFailed

# class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
#     @classmethod
#     def get_token(cls, user):
#         token = super().get_token(user)

#         # Tambahkan info user
#         token['username'] = user.username
#         token['role'] = user.role

#         return token

#     def validate(self, attrs):
#         data = super().validate(attrs)

#         data['user'] = {
#             "id": self.user.id,
#             "username": self.user.username,
#             "role": self.user.role
#         }

#         return data
