from rest_framework.serializers import ModelSerializer
from .models import *
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken # import for manually creating token


class UserSerializer(ModelSerializer):
    class Meta:
        model = MyUser
        fields = '__all__'
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create_normal_user(self, validated_data):
        password = validated_data.pop('password', None)
        user_obj = self.Meta.model.objects.create_user(**validated_data)
        user_obj.set_password(password)
        user_obj.save()
        return user_obj
    
    def create_staff_user(self, validated_data):
        password = validated_data.pop('password', None)
        user_obj = self.Meta.model.objects.create_staffuser(**validated_data)
        user_obj.set_password(password)
        user_obj.save()
        return user_obj
    
    def create_admin_user(self, validated_data):
        password = validated_data.pop('password', None)
        user_obj = self.Meta.model.objects.create_adminuser(**validated_data)
        user_obj.set_password(password)
        user_obj.save()
        return user_obj

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims
        token['email'] = user.email
        token['first_name'] = user.first_name
        token['last_name'] = user.last_name
        # ...

        return token
    
# function to create token manually
# I'm not using this because need to customize token claims
def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)

    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }