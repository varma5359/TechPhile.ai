import os
import re

# Path to your explore_courses directory
directory = './techphile_exams/explore_courses'

# Regex pattern to find the problematic import
pattern = re.compile(r'from\s+techphile_exams\.explore_courses\s+import\s+(populate_base)')

# Loop through all .py files in the directory
for filename in os.listdir(directory):
    if filename.endswith('.py') and not filename.startswith('__'):
        filepath = os.path.join(directory, filename)
        with open(filepath, 'r') as f:
            content = f.read()

        # Substitute the problematic import line
        new_content, count = pattern.subn(r'import \1', content)

        if count > 0:
            with open(filepath, 'w') as f:
                f.write(new_content)
            print(f'✅ Fixed import in {filename}')
        else:
            print(f'➖ No change needed in {filename}')
