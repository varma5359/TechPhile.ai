from rest_framework import serializers
from .models import Contact

class AboutSerializer(serializers.Serializer):
    message = serializers.CharField()

class ServicesSerializer(serializers.Serializer):
    message = serializers.CharField()

class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ['name', 'email', 'phone', 'message', 'subject']
