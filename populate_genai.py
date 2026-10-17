from techphile_exams.explore_courses.populate_base import *

def populate():
    admin_user = get_admin_user()
    genai_topic = Topic.objects.get(name="Generative AI")
    
    # Generative AI Problems
    problems = [
        {
            "title": "Generate Text with GPT-2",
            "description": "Use the transformers library to generate text with GPT-2.",
            "starter_code": '''from transformers import pipeline

# Your code here''',
            "expected_output": "Generated text that continues the prompt",
            "solution": '''from transformers import pipeline

generator = pipeline('text-generation', model='gpt2')
output = generator("In a shocking turn of events,", max_length=50)
print(output[0]['generated_text'])''',
            "difficulty": "intermediate",
            "points": 200,
            "dataset": None
        },
        {
            "title": "Image Generation with Stable Diffusion",
            "description": "Generate an image from text prompt using Stable Diffusion.",
            "starter_code": '''from diffusers import StableDiffusionPipeline
import torch

# Your code here''',
            "expected_output": "Generated image saved to file",
            "solution": '''from diffusers import StableDiffusionPipeline
import torch

model_id = "runwayml/stable-diffusion-v1-5"
pipe = StableDiffusionPipeline.from_pretrained(model_id, torch_dtype=torch.float16)
pipe = pipe.to("cuda")

prompt = "a photo of an astronaut riding a horse on mars"
image = pipe(prompt).images[0]  
image.save("astronaut_rides_horse.png")''',
            "difficulty": "advanced",
            "points": 300,
            "dataset": None
        },
        {
            "title": "Fine-tune a Language Model",
            "description": "Fine-tune a small language model on custom data.",
            "starter_code": '''from transformers import AutoTokenizer, AutoModelForCausalLM
from datasets import load_dataset

# Your code here''',
            "expected_output": "Model fine-tuned successfully",
            "solution": '''from transformers import AutoTokenizer, AutoModelForCausalLM, Trainer, TrainingArguments
from datasets import load_dataset

# Load model and tokenizer
model_name = "distilgpt2"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)

# Load and prepare dataset
dataset = load_dataset("text", data_files={"train": "train.txt", "validation": "valid.txt"})

def tokenize_function(examples):
    return tokenizer(examples["text"])

tokenized_datasets = dataset.map(tokenize_function, batched=True, remove_columns=["text"])

# Training arguments
training_args = TrainingArguments(
    output_dir="./results",
    evaluation_strategy="epoch",
    learning_rate=2e-5,
    num_train_epochs=3,
    per_device_train_batch_size=16,
)

# Train
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_datasets["train"],
    eval_dataset=tokenized_datasets["validation"],
)

trainer.train()''',
            "difficulty": "advanced",
            "points": 400,
            "dataset": None
        }
    ]
    
    for p in problems:
        Problem.objects.get_or_create(
            title=p["title"],
            topic=genai_topic,
            dataset=p.get("dataset"),
            difficulty=p["difficulty"],
            description=p["description"],
            starter_code=p["starter_code"],
            expected_output=p["expected_output"],
            solution=p["solution"],
            points=p["points"],
            created_by=admin_user
        )
    
    print("Generative AI problems populated.")

if __name__ == '__main__':
    populate()