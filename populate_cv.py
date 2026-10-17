from techphile_exams.explore_courses.populate_base import *  # Ensure this includes Django setup and get_admin_user()
import numpy as np
from PIL import Image
from django.core.files import File
import io
import os

def create_image_dataset(name, width, height, color, admin_user):
    """Create and register a dummy image dataset."""
    dataset_dir = os.path.join('datasets')
    os.makedirs(dataset_dir, exist_ok=True)
    
    # Create dummy RGB image
    img = Image.new('RGB', (width, height), color=color)
    
    filename = f"{name.lower().replace(' ', '_')}.jpg"
    filepath = os.path.join(dataset_dir, filename)
    
    # Save image to file
    img.save(filepath, format='JPEG')
    
    # Save image file to Dataset model
    with open(filepath, 'rb') as f:
        dataset, _ = Dataset.objects.get_or_create(
            name=name,
            defaults={
                "filename": filename,
                "description": f"{color} {width}x{height} dummy image for CV tasks",
                "file": File(f, name=filename),
                "uploaded_by": admin_user,
                "is_public": True,
                "mime_type": "image/jpeg",
                "file_size": os.path.getsize(filepath)
            }
        )
    return dataset

def populate():
    admin_user = get_admin_user()
    cv_topic = Topic.objects.get_or_create(name="Computer Vision")[0]
    
    # Create datasets
    red_image = create_image_dataset("Red Line", 800, 600, "red", admin_user)
    blue_image = create_image_dataset("Blue Square", 500, 500, "blue", admin_user)
    green_image = create_image_dataset("Green Rectangle", 600, 400, "green", admin_user)
    yellow_image = create_image_dataset("Yellow Triangle", 500, 500, "yellow", admin_user)
    bw_image = create_image_dataset("Black and White", 400, 400, "black", admin_user)  # Actually creates black image    face_image = create_image_dataset("Face Image", 800, 600, "blue", admin_user)

    # Define problems
    problems = [
        {
            "title": "Create Blank Image",
            "description": "Create a 300x300 blank white image and display it.",
            "starter_code": "import cv2\nimport numpy as np\n# Your code here",
            "solution": "blank = np.ones((300,300,3), dtype=np.uint8) * 255\ncv2.imshow('Blank', blank)\ncv2.waitKey(0)",
            "expected_output": "White image displayed",
            "difficulty": "beginner",
            "points": 50
        },
        {
            "title": "Draw a Line",
            "description": "Draw a red line from (50,50) to (250,250) with thickness 3.",
            "starter_code": "import cv2\n# Your code here",
            "solution": f"img = cv2.imread('datasets/{green_image.filename}')\ncv2.line(img, (50,50), (250,250), (0,0,255), 3)\ncv2.imshow('Line', img)\ncv2.waitKey(0)",
            "expected_output": "Image with red line displayed",
            "difficulty": "beginner",
            "points": 50
        },
        {
            "title": "Draw a Polygon",
            "description": "Draw a yellow triangle (3-sided polygon) with points (100,100), (300,100), (200,300).",
            "starter_code": "import cv2\nimport numpy as np\n# Your code here",
            "solution": f"img = cv2.imread('datasets/{bw_image.filename}')\npts = np.array([[100,100], [300,100], [200,300]])\ncv2.polylines(img, [pts], True, (0,255,255), 3)\ncv2.imshow('Triangle', img)\ncv2.waitKey(0)",
            "expected_output": "Image with triangle displayed",
            "difficulty": "beginner",
            "points": 75
        },
        {
            "title": "Change Pixel Color",
            "description": "Change the color of pixel at (100,100) to blue and display the image.",
            "starter_code": "import cv2\n# Your code here",
            "solution": f"img = cv2.imread('datasets/{green_image.filename}')\nimg[100,100] = [255,0,0]\ncv2.imshow('Pixel Changed', img)\ncv2.waitKey(0)",
            "expected_output": "Image with changed pixel displayed",
            "difficulty": "beginner",
            "points": 50
        },
        {
            "title": "Image Negative",
            "description": "Create and display the negative of an image.",
            "starter_code": "import cv2\n# Your code here",
            "solution": f"img = cv2.imread('datasets/{green_image.filename}')\nnegative = 255 - img\ncv2.imshow('Negative', negative)\ncv2.waitKey(0)",
            "expected_output": "Negative image displayed",
            "difficulty": "beginner",
            "points": 75
        },
        {
            "title": "Brightness Adjustment",
            "description": "Increase image brightness by 50 units.",
            "starter_code": "import cv2\nimport numpy as np\n# Your code here",
            "solution": f"img = cv2.imread('datasets/{bw_image.filename}')\nbright = cv2.add(img, 50)\ncv2.imshow('Brightened', bright)\ncv2.waitKey(0)",
            "expected_output": "Brightened image displayed",
            "difficulty": "beginner",
            "points": 75
        },
        {
            "title": "Contrast Adjustment",
            "description": "Increase image contrast by 1.5 times.",
            "starter_code": "import cv2\nimport numpy as np\n# Your code here",
            "solution": f"img = cv2.imread('datasets/{bw_image.filename}')\ncontrast = cv2.multiply(img, 1.5)\ncv2.imshow('Contrast', contrast)\ncv2.waitKey(0)",
            "expected_output": "Higher contrast image displayed",
            "difficulty": "beginner",
            "points": 75
        },
        {
            "title": "Image Averaging Filter",
            "description": "Apply 3x3 averaging filter to blur the image.",
            "starter_code": "import cv2\n# Your code here",
            "solution": f"img = cv2.imread('datasets/{green_image.filename}')\nblur = cv2.blur(img, (3,3))\ncv2.imshow('Averaged', blur)\ncv2.waitKey(0)",
            "expected_output": "Blurred image displayed",
            "difficulty": "beginner",
            "points": 75
        },
        {
            "title": "Median Filter",
            "description": "Apply 3x3 median filter to the image.",
            "starter_code": "import cv2\n# Your code here",
            "solution": f"img = cv2.imread('datasets/{green_image.filename}')\nmedian = cv2.medianBlur(img, 3)\ncv2.imshow('Median', median)\ncv2.waitKey(0)",
            "expected_output": "Median filtered image displayed",
            "difficulty": "beginner",
            "points": 75
        },
        {
            "title": "Image Padding",
            "description": "Add 20 pixel black border around the image.",
            "starter_code": "import cv2\n# Your code here",
            "solution": f"img = cv2.imread('datasets/{yellow_image.filename}')\npadded = cv2.copyMakeBorder(img, 20,20,20,20, cv2.BORDER_CONSTANT, value=[0,0,0])\ncv2.imshow('Padded', padded)\ncv2.waitKey(0)",
            "expected_output": "Padded image displayed",
            "difficulty": "beginner",
            "points": 75
        },
        {
            "title": "Bitwise Operations",
            "description": "Create a white circle on black background and perform AND operation with another image.",
            "starter_code": "import cv2\nimport numpy as np\n# Your code here",
            "solution": f"img = cv2.imread('datasets/{yellow_image.filename}')\nmask = np.zeros(img.shape[:2], dtype=np.uint8)\ncv2.circle(mask, (250,250), 100, 255, -1)\nresult = cv2.bitwise_and(img, img, mask=mask)\ncv2.imshow('Masked', result)\ncv2.waitKey(0)",
            "expected_output": "Image with circular region displayed",
            "difficulty": "intermediate",
            "points": 100
        },
        {
            "title": "Image Concatenation",
            "description": "Concatenate two images horizontally and display the result.",
            "starter_code": "import cv2\n# Your code here",
            "solution": f"img1 = cv2.imread('datasets/{red_image.filename}')\nimg2 = cv2.imread('datasets/{blue_image.filename}')\ncombined = cv2.hconcat([img1, img2])\ncv2.imshow('Combined', combined)\ncv2.waitKey(0)",
            "expected_output": "Combined images displayed side by side",
            "difficulty": "beginner",
            "points": 75
        },
        {
            "title": "Color Detection",
            "description": "Detect all green pixels in an image and display them in white.",
            "starter_code": "import cv2\nimport numpy as np\n# Your code here",
            "solution": f"img = cv2.imread('datasets/{green_image.filename}')\nhsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)\nlower_green = np.array([40,50,50])\nupper_green = np.array([80,255,255])\nmask = cv2.inRange(hsv, lower_green, upper_green)\nimg[mask > 0] = [255,255,255]\ncv2.imshow('Green Detection', img)\ncv2.waitKey(0)",
            "expected_output": "Image with green regions highlighted",
            "difficulty": "intermediate",
            "points": 100
        },
        {
            "title": "Image Pyramid",
            "description": "Create and display a Gaussian pyramid with 4 levels.",
            "starter_code": "import cv2\n# Your code here",
            "solution": f"img = cv2.imread('datasets/{yellow_image.filename}')\nlayer = img.copy()\nfor i in range(4):\n    layer = cv2.pyrDown(layer)\n    cv2.imshow(f'Layer {i}', layer)\ncv2.waitKey(0)",
            "expected_output": "Multi-resolution pyramid displayed",
            "difficulty": "intermediate",
            "points": 100
        },
        {
            "title": "Simple Background Subtraction",
            "description": "Subtract two images to find differences.",
            "starter_code": "import cv2\nimport numpy as np\n# Your code here",
            "solution": f"img1 = cv2.imread('datasets/{red_image.filename}')\nimg2 = cv2.imread('datasets/{blue_image.filename}')\ndiff = cv2.absdiff(img1, img2)\ncv2.imshow('Difference', diff)\ncv2.waitKey(0)",
            "expected_output": "Difference image displayed",
            "difficulty": "intermediate",
            "points": 100
        },
        {
            "title": "Erosion Operation",
            "description": "Apply erosion with 3x3 kernel to a binary image.",
            "starter_code": "import cv2\nimport numpy as np\n# Your code here",
            "solution": f"img = cv2.imread('datasets/{bw_image.filename}', 0)\nkernel = np.ones((3,3), np.uint8)\neroded = cv2.erode(img, kernel)\ncv2.imshow('Eroded', eroded)\ncv2.waitKey(0)",
            "expected_output": "Eroded image displayed",
            "difficulty": "intermediate",
            "points": 100
        },
        {
            "title": "Dilation Operation",
            "description": "Apply dilation with 3x3 kernel to a binary image.",
            "starter_code": "import cv2\nimport numpy as np\n# Your code here",
            "solution": f"img = cv2.imread('datasets/{bw_image.filename}', 0)\nkernel = np.ones((3,3), np.uint8)\ndilated = cv2.dilate(img, kernel)\ncv2.imshow('Dilated', dilated)\ncv2.waitKey(0)",
            "expected_output": "Dilated image displayed",
            "difficulty": "intermediate",
            "points": 100
        },
        {
            "title": "Image Moments",
            "description": "Calculate and print the moments of a binary image.",
            "starter_code": "import cv2\n# Your code here",
            "solution": f"img = cv2.imread('datasets/{bw_image.filename}', 0)\nmoments = cv2.moments(img)\nprint(moments)",
            "expected_output": "Dictionary of moment values printed",
            "difficulty": "intermediate",
            "points": 100
        },
        {
            "title": "Image Masking",
            "description": "Apply a circular mask to an image.",
            "starter_code": "import cv2\nimport numpy as np\n# Your code here",
            "solution": f"img = cv2.imread('datasets/{yellow_image.filename}')\nmask = np.zeros(img.shape[:2], dtype=np.uint8)\ncv2.circle(mask, (250,250), 200, 255, -1)\nmasked = cv2.bitwise_and(img, img, mask=mask)\ncv2.imshow('Masked', masked)\ncv2.waitKey(0)",
            "expected_output": "Circular region of image displayed",
            "difficulty": "intermediate",
            "points": 100
        },
        {
            "title": "Image Warping",
            "description": "Apply perspective transformation to an image.",
            "starter_code": "import cv2\nimport numpy as np\n# Your code here",
            "solution": f"img = cv2.imread('datasets/{yellow_image.filename}')\npts1 = np.float32([[50,50],[450,50],[50,450],[450,450]])\npts2 = np.float32([[0,0],[400,50],[50,400],[450,450]])\nM = cv2.getPerspectiveTransform(pts1, pts2)\nwarped = cv2.warpPerspective(img, M, (500,500))\ncv2.imshow('Warped', warped)\ncv2.waitKey(0)",
            "expected_output": "Perspective transformed image displayed",
            "difficulty": "intermediate",
            "points": 150
        }
    ]

    # Create Problem entries
    for p in problems:
        Problem.objects.get_or_create(
            title=p["title"],
            topic=cv_topic,
            dataset=p.get("dataset"),
            difficulty=p["difficulty"],
            description=p["description"],
            starter_code=p["starter_code"],
            expected_output=p["expected_output"],
            solution=p["solution"],
            points=p["points"],
            created_by=admin_user
        )
    
    print("✅ Computer Vision problems and image datasets populated.")

if __name__ == '__main__':
    populate()
