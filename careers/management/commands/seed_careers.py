from django.core.management.base import BaseCommand
from django.db import transaction

from careers.models import (
    CareerRole, LearningDay, MilestoneExam, QuestionOption, ScenarioQuestion, Skill,
)
from careers import lessons
from careers.seed_data import ROLES

# The objectives the first seed wrote for this day; replaced only if still unedited.
ORIGINAL_DAY1_OBJECTIVES = ROLES[0]['days'][0]['objectives']


class Command(BaseCommand):
    help = (
        'Load the starter career roles, five learning days per role, scenario questions and '
        'Milestone Exam 1. Existing records are left unchanged, so admin edits are never overwritten.'
    )

    @transaction.atomic
    def handle(self, *args, **options):
        counts = {'roles': 0, 'days': 0, 'questions': 0, 'milestones': 0}
        for order, data in enumerate(ROLES, start=1):
            role, created = CareerRole.objects.get_or_create(
                title=data['title'],
                defaults={
                    'summary': data['summary'], 'objectives': data['objectives'],
                    'responsibilities': data['responsibilities'], 'expected_skills': data['expected_skills'],
                    'syllabus': data['syllabus'], 'duration_days': data['duration_days'],
                    'is_published': True, 'display_order': order,
                })
            counts['roles'] += created

            for number, day_data in enumerate(data['days'], start=1):
                day, created = LearningDay.objects.get_or_create(
                    role=role, day_number=number,
                    defaults={
                        'title': day_data['title'], 'objectives': day_data['objectives'],
                        'topics': day_data['topics'], 'is_published': True,
                    })
                counts['days'] += created
                for q_order, item in enumerate(day_data['questions'], start=1):
                    skill, _ = Skill.objects.get_or_create(name=item['skill'])
                    question, created = ScenarioQuestion.objects.get_or_create(
                        day=day, text=item['text'], scenario=item['scenario'],
                        defaults={
                            'skill': skill, 'topic': item['topic'], 'difficulty': item['difficulty'],
                            'explanation': item['explanation'], 'order': q_order,
                        })
                    if created:
                        counts['questions'] += 1
                        QuestionOption.objects.bulk_create([
                            QuestionOption(question=question, text=text, is_correct=(i == item['correct']), order=i)
                            for i, text in enumerate(item['options'])
                        ])

            _, created = MilestoneExam.objects.get_or_create(
                role=role, number=1,
                defaults={'start_day': 1, 'end_day': 5, 'question_count': 10, 'is_published': True})
            counts['milestones'] += created

        self.stdout.write(self.style.SUCCESS(
            'Seed complete. Created: {roles} roles, {days} days, {questions} questions, '
            '{milestones} milestone exams.'.format(**counts)))
        self.apply_lessons()

    def apply_lessons(self):
        """Fill the redesigned day's lesson and feedback, leaving existing text untouched."""
        day = LearningDay.objects.filter(
            role__title=lessons.ROLE_TITLE, day_number=lessons.DAY_NUMBER).first()
        if day is None:
            return
        if not day.objectives.strip() or day.objectives == ORIGINAL_DAY1_OBJECTIVES:
            day.objectives = lessons.OBJECTIVES
            day.save(update_fields=['objectives'])
        changed = []
        for field, value in lessons.DAY_FIELDS.items():
            if not getattr(day, field):
                setattr(day, field, value)
                changed.append(field)
        if changed:
            day.save(update_fields=changed)
            self.stdout.write('Lesson content added to %s.' % day)
        for question in day.questions.prefetch_related('options'):
            feedback = lessons.QUESTION_FEEDBACK.get(question.text)
            if not feedback:
                continue
            if not question.takeaway:
                question.takeaway = feedback['takeaway']
                question.save(update_fields=['takeaway'])
            for option, text in zip(question.options.all(), feedback['options']):
                if not option.explanation:
                    option.explanation = text
                    option.save(update_fields=['explanation'])
