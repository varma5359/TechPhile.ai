import os
import django
import random

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "techphile_exams.settings")  # 🔁 Replace with your project name
django.setup()

from django.contrib.auth.models import User
from coding.models import UserProfile  # 🔁 Replace with your app name

first_names = [
    "Aarav Sharma", "Vihaan Mehta", "Vivaan Joshi", "Aditya Kapoor", "Arjun Reddy",
    "Sai Krishna", "Reyansh Patel", "Ayaan Verma", "Krishna Iyer", "Ishaan Bhatt",
    "Anaya Nair", "Diya Shah", "Myra Gupta", "Aadhya Desai", "Meera Chauhan",
    "Saanvi Rani", "Kiara Rao", "Pari Mukherjee", "Riya Agarwal", "Ira Das",
    "Yuvraj Bansal", "Tanvi Bhatia", "Ishita Sethi", "Pranav Pillai", "Devansh Saxena",
    "Laksh Goel", "Aanya Vyas", "Kavya Jha", "Aryan Dubey", "Nikhil Joshi",
    "Anushka Mahajan", "Harshitha Singh", "Ritvik Raj", "Siddharth Jain", "Tejas Shetty",
    "Divyansh Reddy", "Manav Ghosh", "Simran Kaul", "Raghav Sengupta", "Sneha Poddar",
    "Aman Tripathi", "Tanya Saluja", "Veer Nanda", "Isha Yadav", "Kriti Kohli",
    "Shaurya Choudhary", "Tanishq Narang", "Arnav Malik", "Mira Bhagat", "Arya Khatri",
    "Neha Barman", "Vivaan Rawat", "Zoya Luthra", "Saanvika Dey", "Kush Shah",
    "Vanya Bansal", "Harshit Arora", "Navya Puri", "Karan Thakur", "Yash Mittal",
    "Tanisha Kapoor", "Shrishti Chauhan", "Ishan Bharadwaj", "Aditi Dasgupta", "Ritvika Rao",
    "Avni Tiwari", "Prisha Kalra", "Atharv Joshi", "Reeva Malhotra", "Zayan Mehta",
    "Vihaana Soni", "Samar Jindal", "Darsh Pandey", "Naina Lal", "Advait Bajaj",
    "Aryaman Sinha", "Jia Dutta", "Neelam Nair", "Siddhi Basu", "Kabir Bhattacharya",
    "Aarohi Roy", "Trisha Suri", "Hrithik Kaul", "Sakshi Mishra", "Ayush Rathore",
    "Raghavi Reddy", "Daksh Kohli", "Nirav Baxi", "Palak Sehgal", "Deeksha Arora",
    "Rhea Kapoor", "Ayan Nayak", "Suhana Talwar", "Manan Gaur", "Avisha Modi",
    "Krish Bhalla", "Mahika Sood", "Rajvi Chopra", "Aaryan Seth", "Vansh Bedi",
    "Lavanya Kaur", "Tushar Khanna", "Diya Madaan", "Aaradhya Jain", "Vedant Khandelwal" ,
    "Sai Teja", "Venkatesh Reddy", "Harsha Vardhan", "Lakshmi Prasanna", "Bhargav Ch", 
    "Anusha Reddy", "Sravani G", "Tejaswi B", "Karthik Raju", "Sandeep Yadav",
    "Manoj Kumar", "Deepika Alla", "Naveen Kumar", "Swathi Rani", "Rohit Varma",
    "Vamshi Krishna", "Sunitha Devi", "Ravi Teja", "Chaitanya Reddy", "Sudheer Kumar",
    "Niharika Konidela", "Mounika J", "Sushmitha N", "Pavan Sai", "Rajesh Babu",
    "Divya Bharathi", "Meghana Priya", "Tarun Reddy", "Yamini S", "Vishnu Vardhan",
]


def create_dummy_users():
    for i, name in enumerate(first_names):
        username = name.lower()
        email = f"{username}@example.com"
        password = "test12345"
        
        user, created = User.objects.get_or_create(username=username, email=email)
        if created:
            user.set_password(password)
            user.save()
            print(f"✅ Created user: {username}")
        
        total = random.randint(10, 100)
        easy = random.randint(5, total // 2)
        medium = random.randint(0, (total - easy) // 2)
        hard = total - easy - medium
        rank = random.randint(1, 500)

        profile, created = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                "bio": f"I'm {name}, excited to solve problems!",
                "total_solved": total,
                "easy_solved": easy,
                "medium_solved": medium,
                "hard_solved": hard,
                "ranking": rank,
            }
        )
        if created:
            print(f"🧾 Profile created for: {username}")
        else:
            print(f"ℹ️ Profile already exists for: {username}")

if __name__ == "__main__":
    create_dummy_users()
