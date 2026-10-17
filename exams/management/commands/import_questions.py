import openpyxl
from django.core.management.base import BaseCommand
from exams.models import Category, Exam, Question, Answer

class Command(BaseCommand):
    help = "Import java programming questions from Excel"

    def handle(self, *args, **kwargs):
        # Load the workbook
        wb = openpyxl.load_workbook("/root/techphile_exams/techphile_exams/sql_questions.xlsx")
        
        # Create or get category and exam once
        category, _ = Category.objects.get_or_create(
            name="Data Science ",
            slug="data-science",
            defaults={"description": "Sql Database questions for Data Science"}
        ) 
        
        exam, _ = Exam.objects.get_or_create(
            title="SQL Database", 
            slug="sql-database",
            category=category,
            defaults={
                "description": "Sql Database questions for Data Science",
                 "is_popular": True,
        "is_new": False,
            }
        )   

        # Process all sheets in order
        for sheet_name in sorted(wb.sheetnames):
            if not sheet_name.startswith(('sql_beg_', 'sql_med_')):
                continue
                
            sheet = wb[sheet_name]
            self.stdout.write(f"\nProcessing sheet: {sheet_name}")

            # Extract level and set number from sheet name
            parts = sheet_name.split('_')
            level_part = parts[1]  # 'beg' or 'med'
            set_part = parts[2]   # 'set1', 'set2', etc.
            
            # Map to proper level names
            level_map = {
                'beg': 'beginner',
                'med': 'intermediate'
            }
            level = level_map.get(level_part, 'beginner')
            set_number = int(set_part.replace('set', ''))

            for row_idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
                try:
                    # Skip empty rows or rows without order number
                    if not row or row[0] is None:
                        continue

                    # Extract data with proper column indexes
                    order = int(row[0])        # Column A (Order)
                    set_num = row[1]           # Column B (Set)
                    category_name = row[2]     # Column C
                    title = row[3]             # Column D
                    row_level = row[4]         # Column E (Level)
                    question_type = row[5]    # Column F
                    question_text = str(row[6]).strip()  # Column G
                    
                    options = [
                        str(row[7]).strip(),  # Option A
                        str(row[8]).strip(),  # Option B
                        str(row[9]).strip(),  # Option C
                        str(row[10]).strip()  # Option D
                    ]
                    answer = str(row[11]).strip().upper()  # Column L
                    explanation = str(row[12]).strip() if len(row) > 12 else ""  # Column M

                    # Verify level consistency
                    if row_level and row_level.lower() != level:
                        self.stdout.write(self.style.WARNING(
                            f"⚠️ Level mismatch in row {row_idx}: "
                            f"Sheet suggests {level}, row says {row_level}"
                        ))

                    # Validate required fields
                    if not question_text or not any(options) or not answer:
                        self.stdout.write(self.style.WARNING(
                            f"⚠️ Row {row_idx} skipped: Missing required fields"
                        ))
                        continue

                    # Check for duplicate question
                    if Question.objects.filter(
                        category=category,
                        level=level,
                        title=title,
                        set_number=set_number,
                        question_text=question_text,

                        order=order
                    ).exists():
                        self.stdout.write(self.style.WARNING(
                            f"⚠️ Skipping duplicate: {level.title()} Set {set_number} Q{order}"
                        ))
                        continue

                    # Create question
                    question = Question.objects.create(
                    category=category,
                    exam=exam,
                    question_text=question_text,
                    question_type='mcq',
                    marks=1,
                    explanation=explanation,
                    level=level,
                    set_number=set_number,
                    order=order,
                    title=title  # ✅ Ensure this is included
                )

                    # Create answers
                    answer_map = {'A': 0, 'B': 1, 'C': 2, 'D': 3}
                    correct_index = answer_map.get(answer, -1)
                    
                    for idx, (letter, option_text) in enumerate(zip(
                        ['A', 'B', 'C', 'D'],
                        options
                    )):
                        if option_text:  # Only create answer if option exists
                            Answer.objects.create(
                                question=question,
                                answer_text=option_text,
                                is_correct=(idx == correct_index)
                            )

                    self.stdout.write(self.style.SUCCESS(
                        f"✅ Imported: {level.title()} Set {set_number} Q{order}"
                    ))

                except Exception as e:
                    self.stdout.write(self.style.ERROR(
                        f"❌ Error in sheet {sheet_name} row {row_idx}: {str(e)}"
                    ))

        self.stdout.write(self.style.SUCCESS("\nImport completed!"))