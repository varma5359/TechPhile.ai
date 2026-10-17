# views.py
from django.shortcuts import render, redirect
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from ipware import get_client_ip
from .forms import ContactForm
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .serializers import AboutSerializer, ServicesSerializer, ContactSerializer

# views.py
def home(request):
    return render(request, "home.html")


from django.middleware.csrf import get_token
from django.http import HttpResponse, JsonResponse

def debug_token(request):
    token = get_token(request)
    return HttpResponse(f"CSRF token: {token}")


def about (request):
    return render(request,"about.html")

def services(request):
    return render(request,"services.html")

@api_view(['GET'])
def api_about(request):
    data = {"message": "This is the About page content."}
    serializer = AboutSerializer(data)
    return Response(serializer.data)

@api_view(['GET'])
def api_services(request):
    data = {"message": "This is the Services page content."}
    serializer = ServicesSerializer(data)
    return Response(serializer.data)





from django.shortcuts import render, redirect
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from .models import Contact
from .forms import ContactForm
from .serializers import ContactSerializer

from django.shortcuts import render, redirect
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from .forms import ContactForm
from .models import Contact

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip, True

def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            # Save contact form with IP address
            contact = form.save(commit=False)
            client_ip, is_routable = get_client_ip(request)
            contact.ip_address = client_ip
            contact.save()
            
            # Send email notification to admin
            send_mail(
                subject=f"New Contact Form: {contact.get_subject_display()}",
                message=f"Name: {contact.name}\nEmail: {contact.email}\nPhone: {contact.phone}\nMessage: {contact.message}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.CONTACT_EMAIL],
                fail_silently=False,
            )
            
            # Add success message and redirect back to contact page
            messages.success(request, "Your message has been sent successfully!")
            return redirect('contact')
    else:
        form = ContactForm()  # This handles GET requests
    
    return render(request, 'contact.html', {
        'form': form,
        'active_page': 'contact'
    })
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

class ContactAPIView(APIView):
    permission_classes = [AllowAny]  # Allow access without authentication
    
    def post(self, request, *args, **kwargs):
        serializer = ContactSerializer(data=request.data)
        if serializer.is_valid():
            # Save with IP address
            contact = serializer.save()
            client_ip, is_routable = get_client_ip(request)
            contact.ip_address = client_ip
            contact.save()
            
            # Send email notification
            send_mail(
                subject=f"New API Contact Form: {contact.get_subject_display()}",
                message=f"Name: {contact.name}\nEmail: {contact.email}\nPhone: {contact.phone}\nMessage: {contact.message}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.CONTACT_EMAIL],
                fail_silently=False,
            )
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)