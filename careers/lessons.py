"""Starter lesson for Data Analytics, Day 1, written as the Markdown an admin would edit.

``seed_careers`` copies these values into the database only where the matching
field is still empty, so edits made in Django admin are never overwritten. After
seeding, the database (edited in Django admin) is the only source the student
page reads; nothing here is used at request time.
"""

ROLE_TITLE = 'Data Analytics'
DAY_NUMBER = 1

OBJECTIVES = (
    'Explain why a headline metric is a symptom and not a diagnosis\n'
    'Follow a six-step process from business problem to decision\n'
    'Tell a real change from a data or reporting problem\n'
    'Use segmentation to find where a change comes from'
)

DAY_FIELDS = {
    'difficulty_level': 'Beginner',
    'estimated_minutes': 25,
    'lesson_intro': (
        'Analytical thinking is the habit of turning a vague business worry into a question the data can answer. '
        'It is the skill every later topic in this path builds on, and the one interviewers test first.'
    ),
    'lesson_scenario': (
        '### The 12% sales drop\n\n'
        'On Monday, a retail manager tells you that **weekly sales fell by 12%**. She wants to launch '
        'store-wide discounts today to win customers back.\n\n'
        '*Before reading on: is there enough evidence to justify discounts? What would you want to know first?*'
    ),
    'lesson_body': '''## What is analytical thinking?

**Analytical thinking** means breaking a problem into smaller, measurable parts and using evidence to decide what to do. You do not start with a solution. You start with a question.

A number such as "sales are down 12%" is a **symptom**. Your job is to find out whether it is real, where it comes from, and why it happened.

!!! note "Two words you will use daily"
    **Metric** = the number you measure (weekly sales). **Dimension** = a way to slice it (region, product, channel).

## A six-step approach

1. **Frame the question.** Say exactly what changed, by how much, and compared with what.
2. **Validate the data.** Check it is complete, uses one definition, and covers the same dates.
3. **Compare like with like.** Use equivalent periods, for example this Monday-Sunday versus the last one.
4. **Segment the change.** Split by region, product and channel to see where the drop sits.
5. **Form hypotheses.** List plausible causes, then look for evidence for and against each.
6. **Decide and communicate.** Recommend an action the evidence supports, and state what you are unsure about.

!!! tip
    Interviewers reward a clear order of thinking more than a quick answer. Say your steps out loud.

!!! warning "Watch out"
    Do not jump from a headline number straight to a solution. Discounts cost margin and are hard to reverse.

## Real change or reporting artefact?

Many "drops" are not business problems at all. Rule these out in step 2 before investigating causes.

| Looks like a real drop | Might actually be |
|---|---|
| Sales fell 12% | The latest week is incomplete because the data had not finished loading |
| Fewer orders this month | The month has fewer trading days or a holiday |
| One region collapsed | Tracking broke in that region, so orders are missing from the report |
| Average order value rose | A definition changed, for example refunds are now excluded |

## See it as a picture

### From business problem to decision

```flow
Business problem | "Sales are down 12%"
Validate the data | Complete? Same definitions?
Compare equivalent periods | Week vs week, same days
Investigate segments | Region, product, channel
Identify possible causes | Stock-out, tracking, campaign, season
Evidence-based decision | Act on what the data supports
```

**How to read it.** Each box answers one question and hands a cleaner problem to the next. The decision comes last, because every earlier box can change what the right decision is.

### Should we react to the drop?

```tree
? Is the drop visible in complete, comparable data?
  No -> Fix or complete the data first. Do not act yet.
  Yes ? Is the drop concentrated in one segment?
    Yes -> Investigate that segment: stock, tracking, local events, competitors.
    No -> Look at broad causes: pricing, seasonality, marketing spend, market demand.
```

**How to read it.** Two questions are enough to avoid most bad reactions. None of the outcomes is "launch discounts". A discount only becomes a candidate once you know the cause.

### Reactive versus evidence-based

| | Reactive approach | Evidence-based approach |
|---|---|---|
| Starts from | A solution ("discount") | A question ("what changed?") |
| Data check | Skipped | Completeness and definitions verified |
| Comparison | Last week vs this week, whatever it covers | Equivalent periods only |
| Risk | Costly fix for a problem that may not exist | Action matched to the real cause |

**How to read it.** Both approaches react to the same 12%. Only one of them knows what it is reacting to.

## Worked example: where did the 12% go?

!!! example "Business situation"
    A retailer sold 100,000 last week and 88,000 this week, a drop of 12,000 (12%). Sales are reported for three regions. The figures below are illustrative.

**Problem:** is the drop real, and where is it coming from?

**Step-by-step approach**

1. Check the data covers the full Monday-Sunday for every region. *Why: an incomplete week would fake a drop.*
2. Compare with the equivalent previous week and note any holidays or campaigns. *Why: different calendars make a comparison unfair.*
3. Split the change by region. *Why: a single total hides where the movement is.*
4. Check the largest mover for causes: stock-outs, tracking faults, local events. *Why: the segment tells you where to look, not yet why.*

| Region | Last week | This week | Change | Share of the drop |
|---|---|---|---|---|
| North | 40,000 | 39,200 | -2% | 7% |
| South | 35,000 | 34,300 | -2% | 6% |
| **West** | **25,000** | **14,500** | **-42%** | **88%** |

**Reasoning.** North and South are almost flat, and West alone explains about 88% of the drop. Store-wide discounts would give away margin in two healthy regions to fix a problem in one.

**Conclusion.** The evidence points at the West region, not at pricing across the business. Check West for a tracking failure, a stock-out or a local event first. Consider discounts only if that shows a demand problem.

!!! warning "Common mistake"
    Reading the 12% total and approving company-wide discounts straight away. It treats a symptom as the cause and skips the data check, so the drop may not even be real.
''',
    'lesson_revision': '''**Most important idea:** validate the data, compare like with like and locate the change before you explain it or act on it.

- A headline number is a symptom, not a diagnosis.
- Check completeness and definitions before analysing causes.
- Compare equivalent periods only.
- Segment the change to find where it lives.
- Recommend an action only when the evidence supports it, and say what you are unsure about.

!!! tip "Memory rule"
    **Real? Where? Why?** Only then: what should we do?
''',
}

# Extra feedback for the two existing questions, matched by question text.
QUESTION_FEEDBACK = {
    'What should you do first?': {
        'takeaway': 'Confirm the drop is real and find where it sits before proposing any fix.',
        'options': [
            'A discount is a solution, and you do not yet know the problem. It costs margin and may not address the cause.',
            'Correct. It confirms the number is trustworthy and narrows the search to where the drop actually is.',
            'Waiting is not analysis. You can validate the data and segment the change today.',
            'Removing days to make the data look tidy hides evidence. Outliers should be understood, not deleted.',
        ],
    },
    'What is the most useful first step to reconcile the two?': {
        'takeaway': 'When two metrics disagree, compare definitions and time windows before deciding who is right.',
        'options': [
            'Both numbers may be correct for what they measure. Picking one without checking is a guess.',
            'Averaging two numbers that measure different things produces a figure that means nothing.',
            'Correct. Different definitions of "user" and different periods are the usual cause, and low-value new users '
            'would explain growth without revenue.',
            'Asking for a restatement assumes marketing is wrong. First find out where the definitions differ.',
        ],
    },
}
