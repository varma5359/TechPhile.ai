
"""
Populate Data Analytics Days 6–10 in the TechPhile Django project.

Run a preview:
    .\.venv\Scripts\python.exe populate_data_analytics_days_6_to_10.py --dry-run

Save changes:
    .\.venv\Scripts\python.exe populate_data_analytics_days_6_to_10.py

Intentionally replace existing Day 6–10 lesson content:
    .\.venv\Scripts\python.exe populate_data_analytics_days_6_to_10.py --overwrite

Existing Days 1–5 are not touched.
Student attempts, answers, scores, progress, and milestone exams are not modified.
"""

import argparse
import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "techphile_exams.settings")

import django

django.setup()

from django.db import transaction
from careers.models import CareerRole, LearningDay, LEVEL_BEGINNER


LESSONS = [
    {
        "day_number": 6,
        "title": "Hypothesis Testing and Evidence-Based Decisions",
        "difficulty_level": "Intermediate",
        "estimated_minutes": 75,
        "objectives": """
Understand business hypotheses
Explain null and alternative hypotheses
Interpret p-values and statistical significance
Compare control and treatment groups
Make evidence-based business recommendations
""".strip(),
        "topics": """
Business questions and hypotheses
Null and alternative hypotheses
A/B testing
Control and treatment groups
P-values and significance levels
Statistical versus practical significance
""".strip(),
        "lesson_intro": """
# Day 6: Hypothesis Testing

Businesses frequently introduce changes and want to know whether those changes
actually improve results. Hypothesis testing provides a structured way to
evaluate evidence instead of relying on assumptions or a few observations.
""".strip(),
        "lesson_scenario": """
**Business scenario:** An e-commerce company introduces a new checkout page.
The manager sees higher sales on the first day and wants to release it to all
customers. As the analyst, you must check whether the available evidence
supports the decision.
""".strip(),
        "lesson_body": r"""
# 1. Start with a business question

Examples:

- Did a new checkout page improve conversion?
- Did a reminder reduce missed appointments?
- Did a training program improve productivity?
- Did a new delivery process reduce late deliveries?

A useful question identifies an outcome that can be measured.

# 2. Understand hypotheses

A hypothesis is a statement that can be examined using data.

For the checkout example:

- **Null hypothesis (H₀):** The new page does not improve conversion.
- **Alternative hypothesis (H₁):** The new page improves conversion.

The null hypothesis is the starting position. The analysis evaluates whether
the observed evidence is strong enough to challenge it.

# 3. Understand A/B testing

An A/B test compares two versions:

- **Control group:** customers use the existing page.
- **Treatment group:** customers use the new page.

For a fair comparison, check that the groups were assigned appropriately,
tracking works, and other factors are not systematically different.

# 4. Example: checkout conversion

| Metric | Existing page | New page |
|---|---:|---:|
| Visitors | 2,000 | 2,000 |
| Purchases | 200 | 230 |
| Conversion rate | 10% | 11.5% |

The new page's observed conversion rate is 1.5 percentage points higher.

This is a promising observation, but the table alone does not prove that the
new page caused the improvement. The analyst must consider uncertainty,
experiment design, data quality, and other influences.

# 5. What is a p-value?

A p-value describes how surprising the observed result, or a more extreme
result, would be if the null hypothesis and the test assumptions were true.

A p-value is **not** the probability that the null hypothesis is true.

A small p-value can provide evidence against the null hypothesis under the
test assumptions. It does not automatically mean that the business impact is
large or worth the cost.

# 6. Check before making a decision

Ask:

- Were the groups compared over the same period?
- Were tracking events recorded correctly?
- Was the sample large enough to be informative?
- Did a marketing campaign or outage affect the result?
- Was the metric chosen before examining the results?
- Is the observed improvement valuable to the business?

# 7. Analyst workflow

1. Define the business question.
2. Select the primary metric.
3. State the hypotheses.
4. Check data quality and experiment design.
5. Calculate the metric and an appropriate statistical test.
6. Explain uncertainty and limitations.
7. Recommend launching, continuing the test, or investigating further.

!!! example "Interview answer"
    To evaluate a new checkout page, I would compare a control group with a
    treatment group, validate tracking, calculate conversion rates, assess
    uncertainty with an appropriate test, and evaluate whether the impact is
    meaningful to the business.

## Practice task

A payment reminder was sent to one customer group but not another. List three
checks you would make before concluding that the reminder caused more
customers to pay on time.
""".strip(),
        "lesson_revision": """
A hypothesis is a testable statement about a business outcome.
The null hypothesis is the starting position.
A/B testing compares two versions using defined groups.
A p-value is not the probability that the null hypothesis is true.
Statistical significance and business value are different.
Check tracking, group comparability, and uncertainty before deciding.
""".strip(),
    },
    {
        "day_number": 7,
        "title": "Data Storytelling and Business Recommendations",
        "difficulty_level": "Intermediate",
        "estimated_minutes": 75,
        "objectives": """
Distinguish observations from insights
Choose charts for business questions
Explain findings to non-technical stakeholders
Write actionable recommendations
Communicate uncertainty and limitations
""".strip(),
        "topics": """
Business questions and audiences
Observations and insights
Chart selection
Executive summaries
Recommendations and action plans
Success metrics and limitations
""".strip(),
        "lesson_intro": """
# Day 7: Data Storytelling

An analysis is valuable when people understand the results and can act on
them. Data storytelling connects a business question to evidence, meaning,
and a practical recommendation.
""".strip(),
        "lesson_scenario": """
**Business scenario:** A retail manager receives a dashboard with 20 charts
but still cannot explain why profit declined. You must present the most
important findings and recommend what the business should investigate first.
""".strip(),
        "lesson_body": r"""
# 1. Observation versus insight

An observation describes what happened. An insight explains why it matters
in the business context.

**Observation:** Sales declined by 12% compared with the previous month.

**Possible insight:** The decline is concentrated in two regions and one
product category.

**Recommendation:** Investigate stock availability and promotion changes in
those regions before changing prices across the entire business.

The proposed explanation must be checked against the data; do not present an
unverified cause as a proven fact.

# 2. Understand your audience

Before preparing a report, ask:

- Who will make the decision?
- What decision do they need to make?
- Which metric matters to that decision?
- What comparison period is appropriate?
- What action is possible based on the evidence?

An executive may need three key findings. An operations analyst may need
detailed information about individual locations and dates.

# 3. Choose the right chart

| Business question | Useful chart |
|---|---|
| How did sales change over time? | Line chart |
| Which region had the highest sales? | Sorted bar chart |
| How are delivery times distributed? | Histogram or box plot |
| How are discount and profit related? | Scatter plot |
| Where do customers leave a process? | Funnel chart |

Use readable labels, appropriate scales, clear units, and relevant comparisons.

# 4. Structure a business story

A practical presentation follows five steps:

1. **Context:** What question are we answering?
2. **Finding:** What does the data show?
3. **Meaning:** Why does the finding matter?
4. **Action:** What should happen next?
5. **Measurement:** How will we evaluate the outcome?

Example:

**Context:** Delivery complaints increased in September.

**Finding:** Three delivery zones account for most of the increase.

**Meaning:** The issue may be concentrated rather than affecting every zone.

**Action:** Review staffing, route capacity, and dispatch delays in those zones.

**Measurement:** Track late-delivery rate and complaints weekly.

# 5. Make recommendations actionable

A useful recommendation includes:

- The proposed action
- The evidence supporting it
- The responsible team or owner
- The intended outcome
- The metric and review period

Avoid a vague statement such as "improve customer satisfaction."

Instead, recommend reviewing the three zones with the highest verified
late-delivery rates and monitoring weekly performance after a specific
operational change.

# 6. Communicate limitations

Tell stakeholders when data is incomplete, a sample is small, a comparison
is observational, or the evidence does not establish causation.

Being clear about uncertainty improves trust and helps stakeholders make
better decisions.

# 7. One-page report template

## Business question
What decision needs to be made?

## Key finding
State the result and comparison.

## Evidence
Show one or two useful charts or tables.

## Business impact
Explain the potential effect on cost, revenue, risk, or service.

## Recommendation
State the action and its owner.

## Success measure
Define the metric and review period.

## Practice task

Revenue increased by 8%, but profit decreased by 3%. Write an executive
summary with two possible explanations to investigate and one next step.
Do not claim a cause without evidence.
""".strip(),
        "lesson_revision": """
An observation describes what happened; an insight explains its significance.
Choose charts based on the question and audience.
Connect recommendations to evidence.
Identify an owner, action, metric, and review period.
Communicate uncertainty instead of inventing causes.
""".strip(),
    },
    {
        "day_number": 8,
        "title": "Customer Segmentation and Cohort Analysis",
        "difficulty_level": "Intermediate",
        "estimated_minutes": 80,
        "objectives": """
Explain why overall averages can hide differences
Create meaningful customer segments
Define cohorts consistently
Calculate and interpret retention rates
Recommend segment-specific investigations
""".strip(),
        "topics": """
Customer segmentation
Customer behavior and value
Cohort definitions
Retention and repeat purchases
Cohort tables and heatmaps
Segment size and comparison fairness
""".strip(),
        "lesson_intro": """
# Day 8: Customer Segmentation and Cohort Analysis

Customers do not all behave in the same way. Segmentation compares meaningful
groups, while cohort analysis follows groups that share a starting event or
time period.
""".strip(),
        "lesson_scenario": """
**Business scenario:** An online store's repeat-purchase rate is falling.
The marketing team wants to give every customer a discount. You will compare
customer groups and signup or purchase cohorts to determine where retention
is declining.
""".strip(),
        "lesson_body": r"""
# 1. Why segment customers?

An overall metric can hide important differences. Loyal customers may
continue purchasing while new customers rarely return.

Useful segments include:

- New versus returning customers
- Region or store
- Acquisition channel
- Product category
- Customer tenure
- Order-frequency group

Choose segments that support a business decision. Very small groups may
produce unstable percentages.

# 2. Example of customer segments

| Segment | Customers | Repeat-purchase rate |
|---|---:|---:|
| Established customers | 800 | 40% |
| New customers | 200 | 10% |

The two groups have different behavior. A single campaign for everyone may
not be the most effective approach.

Check that the groups have comparable observation windows and consistent
definitions before interpreting the difference.

# 3. What is a cohort?

A cohort is a group sharing a defined starting event or period.

For example:

- January cohort: customers whose first purchase happened in January.
- February cohort: customers whose first purchase happened in February.

Cohort analysis follows each group over subsequent periods.

Define what "active" means. It could mean making another purchase, using a
paid subscription, or completing another meaningful event.

# 4. Calculate retention

A basic retention rate is:

**Retention rate = returning members of the original cohort ÷ original cohort size × 100**

Suppose 500 customers made their first purchase in January. Of those,
150 purchased again in February.

Retention for that follow-up period is:

150 ÷ 500 × 100 = **30%**

Use the original cohort as the denominator, not all customers who purchased
in February.

# 5. Read a cohort table

| First-purchase cohort | Month 1 | Month 2 | Month 3 |
|---|---:|---:|---:|
| January | 35% | 25% | 20% |
| February | 38% | 29% | — |
| March | 30% | — | — |

This hypothetical table suggests that the February cohort retained a larger
share of customers than January in the first two follow-up months.

A dash may mean that the follow-up period has not happened yet. It does not
automatically mean zero retention.

# 6. Turn findings into action

If new customers rarely return, investigate:

- First-order experience
- Product quality and delivery
- Returns and refunds
- Acquisition-channel mix
- Onboarding and follow-up communication

If one channel has lower retention, also consider acquisition cost and
customer value. A low-retention segment is not automatically unprofitable.

# 7. Responsible analysis

- Keep segment definitions consistent.
- Compare equivalent time windows.
- Report group sizes alongside percentages.
- Protect personal information.
- Do not assume that a group label explains every individual's behavior.
- Recheck patterns because customer behavior changes.

## Practice task

Campaign A has 60% Month 1 retention and Campaign B has 42%. List three
checks you would perform before moving the entire marketing budget to A.
""".strip(),
        "lesson_revision": """
Segmentation compares meaningful customer groups.
A cohort shares a defined starting event or period.
Retention uses the original cohort as the denominator.
Compare equivalent time windows and report group sizes.
Group differences do not automatically explain their causes.
""".strip(),
    },
    {
        "day_number": 9,
        "title": "Funnel Analysis and Conversion Optimization",
        "difficulty_level": "Intermediate",
        "estimated_minutes": 80,
        "objectives": """
Define stages in a business funnel
Calculate conversion and drop-off rates
Validate event tracking and population definitions
Find important points of customer abandonment
Recommend and measure focused improvements
""".strip(),
        "topics": """
Funnel stages
Conversion rate and drop-off
Unique users, sessions, and events
Tracking validation
Device and channel segmentation
Experimentation and guardrail metrics
""".strip(),
        "lesson_intro": """
# Day 9: Funnel Analysis

A funnel shows how people move through a sequence of steps and where they
stop. It helps teams prioritize investigation instead of making broad
changes based only on the final conversion rate.
""".strip(),
        "lesson_scenario": """
**Business scenario:** An online retailer gets many product views but few
completed orders. The product team suspects checkout is the problem. You
will map the customer journey and calculate stage-to-stage conversion.
""".strip(),
        "lesson_body": r"""
# 1. Understand the funnel

An e-commerce funnel might contain:

1. Website visit
2. Product view
3. Add to cart
4. Checkout started
5. Purchase completed

The same approach can analyze recruitment, subscription signup, loan
applications, or hospital appointment booking.

Define each event clearly and consistently.

# 2. Calculate conversion and drop-off

**Conversion rate = people reaching the next stage ÷ people reaching the current stage × 100**

**Drop-off rate = 100% − conversion rate**

Example:

| Stage | People reaching stage | Conversion from previous stage |
|---|---:|---:|
| Website visit | 10,000 | — |
| Product view | 6,000 | 60% |
| Add to cart | 1,500 | 25% |
| Checkout started | 900 | 60% |
| Purchase | 630 | 70% |

From product view to add to cart:

1,500 ÷ 6,000 × 100 = **25% conversion**

The drop-off at this step is 75%.

The largest drop-off percentage is a signal to investigate, not automatic
proof that the stage is the most valuable place to make a change.

# 3. Validate the data

Ask:

- Are events tracked consistently on web and mobile?
- Are duplicate events inflating counts?
- Are the steps in the correct order?
- Are we counting people, sessions, or events?
- Is the time window long enough for completion?
- Are test transactions or bots included?
- Did tracking definitions change recently?

These checks help prevent incorrect conclusions.

# 4. Segment the funnel

Compare relevant groups, such as:

- Mobile versus desktop
- New versus returning visitors
- Marketing channel
- Region
- Product category
- Payment method

If mobile checkout completion is lower, investigate mobile usability,
page speed, form errors, and payment failures. The difference alone does not
prove that the device caused the problem.

# 5. Prioritize investigation

Consider:

- Number of people affected
- Size of the drop-off
- Potential business value
- Confidence in tracking quality
- Effort required to investigate or fix the issue

A small improvement at a high-volume stage may create more purchases than
a large improvement at a very low-volume stage.

# 6. Test a change

If customers abandon checkout when delivery fees appear, one possible
experiment is to display shipping costs earlier.

A responsible workflow is:

1. Confirm tracking quality.
2. Review customer feedback and errors.
3. Propose a specific change.
4. Define a primary metric and guardrail metrics.
5. Test fairly when possible.
6. Monitor conversion, refunds, complaints, and performance.

Do not increase conversion by hiding fees or making cancellation difficult.

## Practice task

Mobile checkout has 4,000 starts and 2,400 purchases. Desktop has 3,000
starts and 2,100 purchases.

Calculate both completion rates, find the percentage-point difference,
and list two checks before recommending a redesign.
""".strip(),
        "lesson_revision": """
A funnel tracks ordered stages in a process.
Define whether the unit is people, sessions, or events.
Calculate conversion using the previous stage as denominator.
Validate tracking before interpreting drop-off.
Test focused changes and monitor guardrail metrics.
""".strip(),
    },
    {
        "day_number": 10,
        "title": "Analytics Capstone and Business Decision Report",
        "difficulty_level": "Intermediate",
        "estimated_minutes": 100,
        "objectives": """
Translate a business problem into an analysis plan
Check data quality and define KPIs
Combine trend, segment, and funnel analysis
Separate evidence from assumptions
Present measurable business recommendations
""".strip(),
        "topics": """
Business problem framing
Data inventory and quality
KPI definitions
Trend and contribution analysis
Customer cohorts and funnels
Findings and limitations
Business decision report
""".strip(),
        "lesson_intro": """
# Day 10: Analytics Capstone

This capstone combines the skills developed in Days 1–9. The objective is
not to create the largest number of charts. It is to answer a business
question using reliable evidence and a clear recommendation.
""".strip(),
        "lesson_scenario": """
**Business scenario:** An online retailer reports higher revenue but lower
profit and repeat purchases. Delivery complaints have also increased.
Prepare an analysis plan that helps leadership decide what to investigate
first. Do not assume these changes share the same cause.
""".strip(),
        "lesson_body": r"""
# 1. Define the business question

A useful starting question is:

**Which factors should the retailer investigate first to understand the
decline in profit and repeat purchases?**

Break it into smaller questions:

- Did order volume, average order value, discounts, or costs change?
- Which categories or regions contributed most to the change?
- Are delivery complaints concentrated in specific areas?
- Are recent customer cohorts returning at lower rates?
- Did the data or tracking definitions change?

# 2. Inventory the data

| Dataset | Useful fields | Purpose |
|---|---|---|
| Orders | order ID, date, customer ID, status, revenue | Sales trends |
| Order items | product, quantity, price, discount | Product performance |
| Costs | product cost, shipping cost, fees | Profit analysis |
| Customers | customer ID, signup date, channel | Customer analysis |
| Deliveries | order ID, promised date, actual date | Late-delivery analysis |
| Complaints | complaint date, type, order ID | Service-quality analysis |

Check identifiers, date ranges, duplicates, missing values, canceled orders,
refunds, currency, and the definitions used in each dataset.

# 3. Define KPIs before calculating them

- **Revenue:** define gross sales or net revenue after discounts and returns.
- **Profit:** define which costs are included.
- **Average order value:** revenue divided by eligible orders.
- **Repeat-purchase rate:** define eligible customers, time window, and repeat behavior.
- **Late-delivery rate:** late eligible deliveries divided by eligible deliveries.
- **Complaint rate:** define the denominator, such as delivered orders.

A metric without a clear definition can lead to misleading comparisons.

# 4. Analyze in a useful order

## A. Trend analysis

Compare the current period with a relevant prior period. Check when the
change began and consider seasonality, promotions, and incomplete periods.

## B. Contribution analysis

Break revenue and profit down by category, region, and channel. Consider
both absolute changes and percentage changes.

A small segment can have a large percentage change but a small business
impact.

## C. Customer analysis

Compare new and returning customers. Use cohorts to check whether recent
customers return at similar rates to earlier cohorts. Ensure comparable
follow-up windows.

## D. Delivery and complaint analysis

Compare late-delivery and complaint rates by region or delivery partner
where the data supports it. Association does not automatically prove that
late delivery caused customers to leave.

## E. Hypothesis testing

When evaluating a specific change, define a hypothesis and use an
appropriate comparison or experiment. Not every descriptive question
requires a statistical test.

# 5. Turn findings into recommendations

If verified data shows that profit decline is concentrated in a category
with increased discounting, investigate discount rules and category costs
before changing prices everywhere.

If repeat purchases are declining for recent customers, investigate the
first-order experience, delivery performance, product expectations, and
acquisition-channel mix.

Prioritize actions based on evidence quality, potential business impact,
implementation effort, and customer risk.

# 6. Prepare the decision report

## Executive summary
State the business problem and the most important supported finding.

## Evidence
Include two or three metrics or charts with clear units and dates.

## Segment analysis
Explain where the change is concentrated and what remains uncertain.

## Recommendation
Name the next action and responsible team.

## Measurement plan
Define the primary success metric, guardrail metrics, baseline, and review date.

## Limitations
State data gaps, assumptions, and what the analysis cannot prove.

# 7. Capstone deliverables

Prepare:

1. A business problem statement.
2. A data-quality checklist.
3. A KPI dictionary.
4. Three relevant charts.
5. One segment or cohort comparison.
6. A finding that separates evidence from assumptions.
7. Two prioritized recommendations.
8. A plan to measure the outcome.

!!! tip "Portfolio advice"
    Show the business question, data-quality decisions, metric definitions,
    findings, limitations, and recommendations. Explaining why you made
    each decision is more valuable than a dashboard full of unrelated charts.

## Final practice task

Write a five-sentence executive summary for the retailer scenario. Include
a finding, a limitation, a recommended investigation, and a metric to
monitor. If no data is available, say that findings are pending rather
than inventing numerical results.
""".strip(),
        "lesson_revision": """
Start from a decision-focused business question.
Validate data and define metrics before calculating results.
Combine trends with relevant segment, cohort, or funnel analysis.
Distinguish findings from hypotheses and assumptions.
Finish with actionable recommendations and a measurement plan.
""".strip(),
    },
]


def parse_args():
    """Parse safe execution options."""
    parser = argparse.ArgumentParser(
        description="Create and populate Data Analytics Days 6–10."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes and roll back all database writes.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing content for Days 6–10.",
    )
    return parser.parse_args()


def find_data_analytics_role():
    """Find the Data Analytics role using the model's actual fields."""
    role = CareerRole.objects.filter(slug="data-analytics").first()
    if role is None:
        role = CareerRole.objects.filter(title__iexact="Data Analytics").first()
    if role is None:
        raise LookupError(
            'CareerRole "Data Analytics" was not found. '
            "Check its title and slug in Django Admin."
        )
    return role


def populate_lessons():
    """Create missing Day 6–10 records and safely populate lesson content."""
    args = parse_args()
    role = find_data_analytics_role()

    # One transaction makes --dry-run safe: every insert/update is rolled back.
    with transaction.atomic():
        changed_days = 0
        created_days = 0

        print(f"Role: {role.title}")
        print(f"Mode: {'DRY RUN' if args.dry_run else 'SAVE CHANGES'}")
        print(f"Overwrite existing content: {'YES' if args.overwrite else 'NO'}")
        print()

        for lesson in LESSONS:
            day_number = lesson["day_number"]
            day, created = LearningDay.objects.get_or_create(
                role=role,
                level=LEVEL_BEGINNER,
                day_number=day_number,
                defaults={
                    "title": lesson["title"],
                    "objectives": lesson["objectives"],
                    "topics": lesson["topics"],
                    "lesson_intro": lesson["lesson_intro"],
                    "difficulty_level": lesson["difficulty_level"],
                    "estimated_minutes": lesson["estimated_minutes"],
                    "lesson_scenario": lesson["lesson_scenario"],
                    "lesson_body": lesson["lesson_body"],
                    "lesson_revision": lesson["lesson_revision"],
                    "is_published": True,
                },
            )

            if created:
                created_days += 1
                changed_days += 1
                print(
                    f"Day {day_number}: "
                    f"{'would create' if args.dry_run else 'created'} "
                    f"— {lesson['title']}"
                )
                continue

            changes = {}
            for field in (
                "title",
                "objectives",
                "topics",
                "lesson_intro",
                "difficulty_level",
                "estimated_minutes",
                "lesson_scenario",
                "lesson_body",
                "lesson_revision",
                "is_published",
            ):
                desired = (
                    True if field == "is_published"
                    else lesson[field]
                )
                current = getattr(day, field)

                # Normal mode fills blank fields and preserves existing content.
                blank = current is None or (
                    isinstance(current, str) and not current.strip()
                )
                if args.overwrite or blank:
                    if current != desired:
                        changes[field] = desired

            if changes:
                changed_days += 1
                print(
                    f"Day {day_number}: {', '.join(changes.keys())} "
                    f"[{'dry run' if args.dry_run else 'updated'}]"
                )
                if not args.dry_run:
                    for field, value in changes.items():
                        setattr(day, field, value)
                    day.save(update_fields=list(changes.keys()))
            else:
                print(
                    f"Day {day_number}: no changes needed "
                    "(existing content preserved)."
                )

        if args.dry_run:
            transaction.set_rollback(True)

    print("\nFinished.")
    print(f"Days with changes planned/applied: {changed_days}")
    print(f"New day records planned/created: {created_days}")
    if args.dry_run:
        print("Dry run only: all database writes were rolled back.")


if __name__ == "__main__":
    try:
        populate_lessons()
    except Exception as exc:
        print(f"\nERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
