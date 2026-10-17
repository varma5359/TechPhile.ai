from techphile_exams.explore_courses.populate_base import *
import pandas as pd
import numpy as np
from PIL import Image, ImageDraw

def create_image_dataset(name, width, height, color, admin_user):
    import os
    os.makedirs("datasets", exist_ok=True)
    filename = f"{name.replace(' ', '_').lower()}.jpg"
    filepath = f"datasets/{filename}"

    if color == "linear_gradient":
        # Create horizontal grayscale gradient
        img = Image.new("RGB", (width, height))
        draw = ImageDraw.Draw(img)
        for x in range(width):
            gray = int(255 * x / width)
            draw.line((x, 0, x, height), fill=(gray, gray, gray))
    else:
        img = Image.new("RGB", (width, height), color=color)

    img.save(filepath)

    # Save to DB
    return Dataset.objects.create(
        name=name,
        filename=filename,
        uploaded_by=admin_user
    )

def populate():
    admin_user = get_admin_user()
    cv_topic = Topic.objects.get_or_create(name="CV")[0]

    # Create basic datasets
    red_image = create_image_dataset("Red Square", 400, 400, "red", admin_user)
    blue_image = create_image_dataset("Blue Circle", 500, 500, "blue", admin_user)
    gradient_image = create_image_dataset("Gradient", 600, 400, "linear_gradient", admin_user)

    problems = [
        {
            "title": "Load and Show Image",
            "description": "Load an image using OpenCV and display it in a window.",
            "starter_code": "import cv2\n# Your code here",
            "solution": f"img = cv2.imread('datasets/{red_image.filename}')\ncv2.imshow('Image', img)\ncv2.waitKey(0)\ncv2.destroyAllWindows()",
            "expected_output": "Image window displayed",
            "difficulty": "beginner",
            "points": 50
        },
        {
            "title": "Convert Image to Grayscale",
            "description": "Load an image and convert it to grayscale.",
            "starter_code": "import cv2\n# Your code here",
            "solution": f"img = cv2.imread('datasets/{red_image.filename}')\ngray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)\ncv2.imshow('Grayscale', gray)\ncv2.waitKey(0)",
            "expected_output": "Grayscale image displayed",
            "difficulty": "beginner",
            "points": 50
        },
        {
            "title": "Save Image to File",
            "description": "Load an image and save it as 'output.jpg'.",
            "starter_code": "import cv2\n# Your code here",
            "solution": f"img = cv2.imread('datasets/{red_image.filename}')\ncv2.imwrite('output.jpg', img)\nprint('output.jpg')",
            "expected_output": "output.jpg",
            "difficulty": "beginner",
            "points": 50,
        },
        {
            "title": "Get Image Dimensions",
            "description": "Print the width, height and number of color channels of an image.",
            "starter_code": "import cv2\n# Your code here",
            "solution": f"img = cv2.imread('datasets/{red_image.filename}')\nprint(f'Dimensions: {{img.shape}}')",
            "expected_output": "Dimensions: (height, width, channels)",
            "difficulty": "beginner",
            "points": 50
        },
        {
            "title": "Draw a Rectangle on Image",
            "description": "Draw a green rectangle on the image from (50,50) to (200,200) with thickness 2.",
            "starter_code": "import cv2\n# Your code here",
            "solution": f"img = cv2.imread('datasets/{red_image.filename}')\ncv2.rectangle(img, (50,50), (200,200), (0,255,0), 2)\ncv2.imshow('Rectangle', img)\ncv2.waitKey(0)",
            "expected_output": "Image with green rectangle displayed",
            "difficulty": "beginner",
            "points": 75
        },
        {
            "title": "Draw a Circle on Image",
            "description": "Draw a blue circle centered at (300,300) with radius 100 and thickness 3.",
            "starter_code": "import cv2\n# Your code here",
            "solution": f"img = cv2.imread('datasets/{blue_image.filename}')\ncv2.circle(img, (300,300), 100, (255,0,0), 3)\ncv2.imshow('Circle', img)\ncv2.waitKey(0)",
            "expected_output": "Image with blue circle displayed",
            "difficulty": "beginner",
            "points": 75
        },
        {
            "title": "Add Text to Image",
            "description": "Add white text 'Hello CV' at position (50,100) with font scale 2 and thickness 2.",
            "starter_code": "import cv2\n# Your code here",
            "solution": f"img = cv2.imread('datasets/{blue_image.filename}')\ncv2.putText(img, 'Hello CV', (50,100), cv2.FONT_HERSHEY_SIMPLEX, 2, (255,255,255), 2)\ncv2.imshow('Text', img)\ncv2.waitKey(0)",
            "expected_output": "Image with text displayed",
            "difficulty": "beginner",
            "points": 75
        },
        {
            "title": "Crop Image",
            "description": "Crop the image to show only the region from (100,100) to (300,300).",
            "starter_code": "import cv2\n# Your code here",
            "solution": f"img = cv2.imread('datasets/{red_image.filename}')\ncropped = img[100:300, 100:300]\ncv2.imshow('Cropped', cropped)\ncv2.waitKey(0)",
            "expected_output": "Cropped image displayed",
            "difficulty": "beginner",
            "points": 75
        },
        {
            "title": "Resize Image",
            "description": "Resize the image to 200x200 pixels.",
            "starter_code": "import cv2\n# Your code here",
            "solution": f"img = cv2.imread('datasets/{red_image.filename}')\nresized = cv2.resize(img, (200,200))\ncv2.imshow('Resized', resized)\ncv2.waitKey(0)",
            "expected_output": "Resized image displayed",
            "difficulty": "beginner",
            "points": 75
        },
        {
            "title": "Flip Image Horizontally",
            "description": "Flip the image horizontally (left-right).",
            "starter_code": "import cv2\n# Your code here",
            "solution": f"img = cv2.imread('datasets/{red_image.filename}')\nflipped = cv2.flip(img, 1)\ncv2.imshow('Flipped', flipped)\ncv2.waitKey(0)",
            "expected_output": "Horizontally flipped image displayed",
            "difficulty": "beginner",
            "points": 75
        },
        {
            "title": "Convert BGR to RGB",
            "description": "Convert the image from BGR to RGB color space and display it.",
            "starter_code": "import cv2\n# Your code here",
            "solution": f"img = cv2.imread('datasets/{red_image.filename}')\nrgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)\ncv2.imshow('RGB', rgb)\ncv2.waitKey(0)",
            "expected_output": "RGB image displayed",
            "difficulty": "beginner",
            "points": 75
        },
        {
            "title": "Image Rotation",
            "description": "Rotate the image by 45 degrees clockwise.",
            "starter_code": "import cv2\nimport numpy as np\n# Your code here",
            "solution": f"img = cv2.imread('datasets/{red_image.filename}')\nh,w = img.shape[:2]\nM = cv2.getRotationMatrix2D((w/2,h/2), -45, 1)\nrotated = cv2.warpAffine(img, M, (w,h))\ncv2.imshow('Rotated', rotated)\ncv2.waitKey(0)",
            "expected_output": "Rotated image displayed",
            "difficulty": "intermediate",
            "points": 100
        },
        {
            "title": "Edge Detection",
            "description": "Apply Canny edge detection to the image.",
            "starter_code": "import cv2\n# Your code here",
            "solution": f"img = cv2.imread('datasets/{gradient_image.filename}', 0)\nedges = cv2.Canny(img, 100, 200)\ncv2.imshow('Edges', edges)\ncv2.waitKey(0)",
            "expected_output": "Image edges displayed",
            "difficulty": "intermediate",
            "points": 100
        },
        {
            "title": "Image Blurring",
            "description": "Apply Gaussian blur with 5x5 kernel to the image.",
            "starter_code": "import cv2\n# Your code here",
            "solution": f"img = cv2.imread('datasets/{red_image.filename}')\nblurred = cv2.GaussianBlur(img, (5,5), 0)\ncv2.imshow('Blurred', blurred)\ncv2.waitKey(0)",
            "expected_output": "Blurred image displayed",
            "difficulty": "beginner",
            "points": 75
        },
        {
            "title": "Thresholding",
            "description": "Convert image to grayscale and apply binary threshold at 127.",
            "starter_code": "import cv2\n# Your code here",
            "solution": f"img = cv2.imread('datasets/{gradient_image.filename}', 0)\nret, thresh = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY)\ncv2.imshow('Threshold', thresh)\ncv2.waitKey(0)",
            "expected_output": "Thresholded image displayed",
            "difficulty": "beginner",
            "points": 75
        },
        {
            "title": "Contour Detection",
            "description": "Find and draw contours on a thresholded image.",
            "starter_code": "import cv2\n# Your code here",
            "solution": f"img = cv2.imread('datasets/{blue_image.filename}', 0)\nret, thresh = cv2.threshold(img, 127, 255, 0)\ncontours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)\nimg = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)\ncv2.drawContours(img, contours, -1, (0,255,0), 3)\ncv2.imshow('Contours', img)\ncv2.waitKey(0)",
            "expected_output": "Image with contours displayed",
            "difficulty": "intermediate",
            "points": 100
        },
        {
            "title": "Color Channel Splitting",
            "description": "Split the image into its B, G, R components and display each channel.",
            "starter_code": "import cv2\nimport numpy as np\n# Your code here",
            "solution": f"img = cv2.imread('datasets/{red_image.filename}')\nb,g,r = cv2.split(img)\ncv2.imshow('Blue', b)\ncv2.imshow('Green', g)\ncv2.imshow('Red', r)\ncv2.waitKey(0)",
            "expected_output": "Three windows showing individual color channels",
            "difficulty": "beginner",
            "points": 75
        },
        {
            "title": "Image Histogram",
            "description": "Calculate and display histogram of a grayscale image.",
            "starter_code": "import cv2\nimport matplotlib.pyplot as plt\n# Your code here",
            "solution": f"img = cv2.imread('datasets/{gradient_image.filename}', 0)\nplt.hist(img.ravel(), 256, [0,256])\nplt.show()",
            "expected_output": "Histogram plot displayed",
            "difficulty": "intermediate",
            "points": 100,
        },
        {
            "title": "Image Translation",
            "description": "Shift the image 100 pixels right and 50 pixels down.",
            "starter_code": "import cv2\nimport numpy as np\n# Your code here",
            "solution": f"img = cv2.imread('datasets/{red_image.filename}')\nM = np.float32([[1,0,100],[0,1,50]])\nshifted = cv2.warpAffine(img, M, (img.shape[1], img.shape[0]))\ncv2.imshow('Shifted', shifted)\ncv2.waitKey(0)",
            "expected_output": "Shifted image displayed",
            "difficulty": "intermediate",
            "points": 100
        },
        {
            "title": "Image Blending",
            "description": "Blend two images with equal weights.",
            "starter_code": "import cv2\n# Your code here",
            "solution": f"img1 = cv2.imread('datasets/{red_image.filename}')\nimg2 = cv2.imread('datasets/{blue_image.filename}')\nblended = cv2.addWeighted(img1, 0.5, img2, 0.5, 0)\ncv2.imshow('Blended', blended)\ncv2.waitKey(0)",
            "expected_output": "Blended image displayed",
            "difficulty": "intermediate",
            "points": 100
        }
    ]

    for p in problems:
        Problem.objects.get_or_create(
            title=p["title"],
            topic=cv_topic,
            dataset=red_image,  # Default dataset
            difficulty=p["difficulty"],
            description=p["description"],
            starter_code=p["starter_code"],
            expected_output=p["expected_output"],
            solution=p["solution"],
            points=p["points"],
            created_by=admin_user,
        )

    print("✅ 20 Basic Computer Vision problems populated.")

# Run populate
populate()
