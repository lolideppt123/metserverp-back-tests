from rest_framework.response import Response
from .serializers import *
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.views import APIView, exception_handler
from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated
from rest_framework.authentication import SessionAuthentication
from rest_framework import permissions, status
from .validations import *
from .models import *

class UserRegisterView(APIView):
    permission_classes = (permissions.AllowAny,)
    def post(self, request):
        clean_data = user_validation(request.data)
        serializer = UserSerializer(data=clean_data)
        if serializer.is_valid(raise_exception=True):
            user = serializer.create_normal_user(clean_data)
            if user:
                return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(status=status.HTTP_400_BAD_REQUEST)
    
class StaffRegisterView(APIView):
    permission_classes = (permissions.AllowAny,)
    def post(self, request):
        clean_data = user_validation(request.data)
        serializer = UserSerializer(data=clean_data)
        if serializer.is_valid(raise_exception=True):
            user = serializer.create_staff_user(clean_data)
            if user:
                return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(status=status.HTTP_400_BAD_REQUEST)
    
class AdminRegisterView(APIView):
    permission_classes = (permissions.AllowAny,)
    def post(self, request):
        clean_data = user_validation(request.data)
        serializer = UserSerializer(data=clean_data)
        if serializer.is_valid(raise_exception=True):
            user = serializer.create_admin_user(clean_data)
            if user:
                return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    permission_classes = (permissions.AllowAny,)
    authentication_classes = (SessionAuthentication,)
    def post(self, request):
        email = request.data['email']
        password = request.data['password']
        assert email_validation(email)
        assert password_validation(password)

        user = MyUser.objects.filter(email=email).first()
        if user is None:
            raise AuthenticationFailed('Invalid email or password')
        if not user.check_password(password):
            raise AuthenticationFailed('Invalid email or password')
        # This came from serializers.py
        token = MyTokenObtainPairSerializer.get_token(user) 

        response = Response()
        response.set_cookie(key='refresh-token', value=str(token), httponly=True)
        response.data = {'refresh': str(token), 'access': str(token.access_token)}
        return response

class UserView(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    # authentication_classes = (SessionAuthentication,) # cookie header authentication
    def get(self, request):
        print(request.user)
        serializer = UserSerializer(request.user)
        return Response({'user': "success"}, status=status.HTTP_200_OK)
    

class LogoutView(APIView):
    permission_classes = (permissions.AllowAny,)
    def post(self, request):
        response = Response()
        response.delete_cookie('access-token')
        response.data = {"message": "Successfully logout"}
        return response
        
        
    

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer


def custom_exception_handler(exc, context):
    if isinstance(exc, NotAuthenticated):
        return Response({"custom_key": "custom message"}, status=401)

    # else
    # default case
    return exception_handler(exc, context)