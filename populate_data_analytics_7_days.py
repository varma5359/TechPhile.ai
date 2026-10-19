
"""
Populate seven days of Data Analytics preparation notes.

Run from the Django project root:
    python populate_data_analytics_7_days.py

Preview without saving:
    python populate_data_analytics_7_days.py --dry-run

Intentionally replace lesson content for Days 1-7:
    python populate_data_analytics_7_days.py --overwrite

Only lesson-related fields are changed. Questions, attempts, scores,
users, and student progress are not modified.
"""

import os
import sys
import argparse

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "techphile_exams.settings")

import django

django.setup()

from django.db import transaction
from careers.models import CareerRole, LearningDay, LEVEL_BEGINNER


LESSONS = [
    {
        "day_number": 1,
        "title": "Introduction to Analytical Thinking",
        "difficulty_level": "Beginner",
        "estimated_minutes": 45,
        "objectives": """Convert vague business questions into measurable questions
Identify useful metrics and dimensions
Separate evidence from assumptions
Develop testable business hypotheses""",
        "topics": """Problem framing
Metrics and dimensions
Hypothesis-driven analysis
Analytical thinking""",
        "lesson_intro": """Data analytics begins with asking the right question, not immediately writing code or creating charts. This lesson teaches you to translate a business problem into measurable questions and investigate possible causes using evidence.""",
        "lesson_scenario": """A retail manager reports that weekly sales have fallen by 12%. The manager immediately asks the analytics team to recommend discounts. Your task is to determine what information is needed before recommending an action.""",
        "lesson_body": r"""
## 1. What Is Analytical Thinking?

Analytical thinking is the process of breaking a broad problem into smaller questions, examining evidence, and reaching a defensible conclusion.

A business statement such as **"sales are falling"** is a starting point, not a complete analysis.

Before acting, ask:

- Which sales measure decreased: revenue, orders, or units?
- Compared with which period?
- Is the reporting period complete?
- Which products, regions, and channels changed?
- What evidence supports each possible explanation?

## 2. Problem Framing

A useful problem statement defines the outcome, population, time period, and comparison.

**Weak question:** Why are sales bad?

**Improved question:** Why did online revenue decrease by 12% this week compared with the previous complete week?

The improved question identifies a metric, a channel, and a comparison period.

### A practical sequence

1. Clarify the business objective.
2. Define the metric.
3. Choose a comparison period.
4. Validate the available data.
5. Break the result into meaningful segments.
6. Investigate likely explanations.
7. Recommend an action supported by evidence.

## 3. Metrics and Dimensions

A **metric** is a measurable value. A **dimension** describes a category in which that value can be examined.

| Metric | Possible dimensions |
|---|---|
| Revenue | Date, product, region, channel |
| Number of orders | Customer segment, payment method |
| Conversion rate | Campaign, device, landing page |
| Average order value | Product category, customer type |

Dimensions help you locate where a change happened.

## 4. Hypothesis-Driven Analysis

A hypothesis is a possible explanation that can be checked against data.

Example hypothesis: "Online revenue decreased because the number of completed orders fell."

Test it by comparing completed orders and average order value across equivalent periods.

Revenue can decrease because fewer orders occur, customers spend less per order, or both. The hypothesis must be tested rather than assumed.

## 5. Worked Business Example

Suppose revenue changed as follows:

| Measure | Previous week | Current week |
|---|---:|---:|
| Orders | 1,000 | 800 |
| Average order value | ₹500 | ₹500 |
| Revenue | ₹5,00,000 | ₹4,00,000 |

Revenue fell by 20%, and order volume also fell by 20%. Average order value remained constant.

This suggests the decline is associated with fewer orders. It does not yet explain why orders fell. The next step is to investigate traffic, conversion, product availability, and channel performance.

## 6. Common Mistakes

- Recommending discounts before checking the cause.
- Comparing a complete week with an incomplete week.
- Treating correlation as proof of causation.
- Reporting a percentage without its baseline.
- Removing inconvenient observations without a valid reason.

!!! tip
    Ask "What evidence would change my mind?" before accepting a hypothesis.

!!! example
    If revenue falls but order count remains stable, investigate average order value and product mix before assuming customer demand has decreased.
""",
        "lesson_revision": """- Frame the business problem before selecting a solution.
- Metrics measure outcomes; dimensions help explain where changes occur.
- Compare equivalent periods and validate data completeness.
- Treat hypotheses as explanations to test, not facts.
- Recommend actions only after examining supporting evidence.""",
    },
    {
        "day_number": 2,
        "title": "Business Metrics and KPI Design",
        "difficulty_level": "Beginner",
        "estimated_minutes": 50,
        "objectives": """Distinguish metrics from KPIs
Understand revenue, orders, conversion, retention, and churn
Choose appropriate denominators for business rates
Connect analysis to business decisions""",
        "topics": """Business metrics
Key performance indicators
Rates and denominators
Metric definitions
Leading and lagging indicators""",
        "lesson_intro": """Businesses collect many measurements, but not every measurement is a key performance indicator. Learn how to define metrics consistently and choose indicators that support decisions.""",
        "lesson_scenario": """Marketing reports that users increased by 40%, while finance reports that revenue stayed flat. Your task is to determine whether the reports conflict or describe different aspects of the business.""",
        "lesson_body": r"""
## 1. Metrics Versus KPIs

A **metric** is any measurable value used to understand performance. A **key performance indicator (KPI)** is a metric selected to evaluate progress toward an important business objective.

Examples:

- Metrics: page views, clicks, orders, revenue.
- Possible KPIs: purchase conversion rate, monthly retention, contribution margin.

A metric becomes useful when its definition and business purpose are clear.

## 2. Common Business Metrics

| Metric | What it measures |
|---|---|
| Revenue | Money generated from sales |
| Order count | Number of orders placed or completed |
| Average order value | Revenue divided by the relevant order count |
| Conversion rate | Conversions divided by eligible opportunities |
| Retention rate | Proportion of a defined group that remains active |
| Churn rate | Proportion of a defined group that leaves or becomes inactive |

Always state what counts as an order, conversion, retained customer, or churned customer.

## 3. Why Denominators Matter

A rate is meaningful only when its numerator and denominator are defined.

For example:

- 50 purchases from 1,000 eligible visits = 5% conversion.
- 50 purchases from 500 eligible visits = 10% conversion.

The purchase count is the same, but the conversion rate differs because the number of opportunities differs.

Do not compare rates calculated from different populations or time windows without explaining the difference.

## 4. Resolve the Marketing and Finance Scenario

Marketing says users increased by 40%, but revenue is flat.

Investigate:

1. Does "user" mean registered users, active users, or unique visitors?
2. Are both reports using the same time window?
3. Did new users make purchases?
4. Did average order value change?
5. Did traffic increase in a lower-converting channel?
6. Are refunds or cancellations affecting reported revenue?

The reports may both be correct. User growth does not automatically produce revenue growth.

## 5. Leading and Lagging Indicators

A **leading indicator** may provide an early signal of future performance, such as qualified leads or product trial activation.

A **lagging indicator** describes an outcome that has already occurred, such as monthly revenue or completed sales.

Use leading indicators to monitor progress and lagging indicators to evaluate results. Neither category proves causation by itself.

## 6. KPI Definition Checklist

Before publishing a KPI, document:

- Business purpose.
- Exact formula.
- Numerator and denominator.
- Inclusion and exclusion rules.
- Time zone and reporting period.
- Data source and owner.
- Expected direction of improvement.

!!! warning
    Two dashboards can display different numbers simply because their metric definitions differ.

!!! example
    If a team wants to improve customer retention, define the eligible customer cohort and what counts as remaining active before comparing monthly results.
""",
        "lesson_revision": """- A KPI is a metric tied to an important business objective.
- Rates require clear numerators, denominators, populations, and time windows.
- User growth and revenue growth are different outcomes.
- Leading indicators signal possible future outcomes; lagging indicators record results.
- Document metric definitions before comparing dashboards.""",
    },
    {
        "day_number": 3,
        "title": "Data Quality and Reliable Reporting",
        "difficulty_level": "Beginner",
        "estimated_minutes": 50,
        "objectives": """Identify missing values and duplicate records
Validate data types and business rules
Detect inconsistent categories and reporting periods
Explain how data-quality issues affect conclusions""",
        "topics": """Missing values
Duplicate records
Data types
Range and consistency checks
Reporting validation""",
        "lesson_intro": """An analysis can be mathematically correct and still produce the wrong conclusion when the source data is incomplete or inconsistent. This lesson introduces practical checks to perform before interpreting results.""",
        "lesson_scenario": """A sales dashboard shows an unexpected drop. You discover that one day's transactions may not have loaded, some orders appear twice, and several dates use different formats.""",
        "lesson_body": r"""
## 1. What Is Data Quality?

Data quality describes whether data is suitable for its intended use.

Important dimensions include:

- **Completeness:** Are required records and values present?
- **Accuracy:** Do values represent what actually happened?
- **Consistency:** Do systems use compatible definitions and formats?
- **Validity:** Do values follow expected rules?
- **Uniqueness:** Are records duplicated unexpectedly?
- **Timeliness:** Is the data available for the period being reported?

Quality requirements depend on the business question.

## 2. Missing Values

A missing value can mean different things:

- Information was not collected.
- A source system failed.
- The field does not apply.
- A value was intentionally withheld.

Do not automatically replace every missing value with zero. Zero means an observed quantity of zero; missing means the value is unknown or unavailable.

Investigate the reason before choosing a treatment.

## 3. Duplicate Records

Duplicate transactions can inflate revenue and order counts.

For example, if order `A102` appears twice because a file was loaded twice, summing both rows may double-count the order.

However, repeated customer IDs are not necessarily duplicates: one customer can place multiple orders. Define the expected unit of analysis before removing records.

## 4. Data Types and Validity

Check whether:

- Dates are stored and interpreted as dates.
- Revenue is numeric rather than text.
- Category labels are standardized.
- Quantities follow reasonable business rules.
- Required identifiers are present.
- Event timestamps use the expected time zone.

Values such as `"1000"` and `1000` may look similar but behave differently in calculations.

## 5. Validate Reporting Periods

Before comparing this week with last week:

1. Confirm both periods are complete.
2. Check late-arriving transactions.
3. Check source-system outages.
4. Verify time zones and cutoff times.
5. Reconcile totals with a trusted source where possible.

An apparent decline can be a reporting artefact rather than a real business change.

## 6. Example Quality Checklist

| Check | Possible issue | Business impact |
|---|---|---|
| Missing dates | Incomplete daily load | False sales decline |
| Duplicate order IDs | Repeated transaction load | Inflated revenue |
| Negative quantities | Return or data error | Misleading unit totals |
| Inconsistent labels | `South`, `south`, `S` | Split regional totals |
| Mixed time zones | Events assigned to wrong day | Incorrect daily comparison |

## 7. Document Corrections

Record what was changed, why it was changed, how many records were affected, and whether results changed.

Never silently remove data just because it appears unusual. First establish whether the value is invalid, a legitimate exception, a refund, or a rare but real event.

!!! tip
    Validate the source and reporting process before explaining a sudden change in a business KPI.
""",
        "lesson_revision": """- Missing values are not automatically zero.
- Define the record grain before removing duplicates.
- Validate data types, dates, categories, and business rules.
- Confirm comparable and complete reporting periods.
- Document corrections and investigate unusual values before removing them.""",
    },
    {
        "day_number": 4,
        "title": "Exploratory Data Analysis and Distributions",
        "difficulty_level": "Beginner",
        "estimated_minutes": 55,
        "objectives": """Summarize data using appropriate descriptive statistics
Interpret distributions and outliers
Compare averages with medians
Choose visualizations that answer specific questions""",
        "topics": """Descriptive statistics
Mean and median
Distribution shape
Outliers
Histograms and box plots""",
        "lesson_intro": """Exploratory data analysis helps you understand the structure, distribution, and unusual patterns in a dataset before building explanations or models.""",
        "lesson_scenario": """An e-commerce manager says the average order value increased this month. You must determine whether most customers are spending more or whether a few unusually large purchases are driving the average.""",
        "lesson_body": r"""
## 1. What Is Exploratory Data Analysis?

Exploratory data analysis (EDA) uses summaries and visualizations to understand data before making conclusions.

Typical questions include:

- How many observations are present?
- Which variables are missing values?
- What are typical values?
- How spread out are the observations?
- Are there unusual values or clusters?
- Do groups differ meaningfully?

EDA helps identify patterns, data problems, and questions that require further investigation.

## 2. Mean and Median

The **mean** is the arithmetic average. The **median** is the middle value when observations are ordered.

Consider these order values:

`₹200, ₹250, ₹300, ₹350, ₹2,900`

The ₹2,900 order pulls the mean upward. The median remains ₹300.

This does not mean the mean is incorrect. It means the mean and median answer different questions.

- Use the mean to describe the arithmetic average.
- Use the median to describe the central ordered observation, especially when values are skewed.

## 3. Understand Distributions

A distribution shows how observations are spread across values.

- A roughly symmetric distribution has similar tails on both sides.
- A right-skewed distribution has a longer high-value tail.
- A left-skewed distribution has a longer low-value tail.
- Multiple peaks may indicate different underlying groups.

Income, order values, and claim amounts often have right-skewed distributions.

## 4. Choose a Useful Chart

| Chart | Useful for |
|---|---|
| Histogram | Shape and spread of one numeric variable |
| Box plot | Median, quartiles, and potential outliers |
| Bar chart | Comparing categories |
| Line chart | Changes over ordered time |
| Scatter plot | Relationship between two numeric variables |

A chart should answer a question, not merely decorate a report.

## 5. Outliers

An outlier is an observation that is unusually distant from other observations under a chosen rule or model.

It might represent:

- A data-entry mistake.
- A genuine high-value customer.
- Fraud or an unusual event.
- A different population.
- A rare but important business case.

Investigate before removing it. A valid high-value transaction may be the most important observation in the dataset.

## 6. Worked Business Investigation

Suppose the average order value rises from ₹600 to ₹750.

Before concluding that customer spending improved, examine:

1. The median order value.
2. The distribution of order values.
3. The number of orders.
4. Product and customer segments.
5. Unusually large transactions.
6. Whether the reporting populations changed.

If the mean rises but the median remains stable, the increase may be driven by a small number of large purchases.

!!! example
    A box plot can identify potential outliers, but it cannot decide whether those values are errors. Business context and source validation are still necessary.
""",
        "lesson_revision": """- EDA describes data before you draw conclusions.
- Mean and median respond differently to extreme values.
- Histograms show distribution shape; box plots summarize spread and potential outliers.
- Investigate outliers rather than automatically deleting them.
- Select charts based on the analytical question.""",
    },
    {
        "day_number": 5,
        "title": "Segmentation and Root-Cause Analysis",
        "difficulty_level": "Beginner",
        "estimated_minutes": 55,
        "objectives": """Break aggregate metrics into meaningful groups
Compare changes across segments
Separate symptoms from possible causes
Recommend follow-up analysis based on evidence""",
        "topics": """Segmentation
Group comparisons
Contribution analysis
Root-cause investigation
Confounding factors""",
        "lesson_intro": """Aggregate metrics describe what happened overall, but segmentation helps identify where a change occurred. This lesson builds a systematic approach to investigating business performance differences.""",
        "lesson_scenario": """A retailer's total sales fell by 10%. The leadership team wants to know which parts of the business contributed to the decline and which investigation should happen first.""",
        "lesson_body": r"""
## 1. Why Segment Data?

An aggregate result can hide important differences between groups.

Useful segmentation dimensions include:

- Product category.
- Region or store.
- Sales channel.
- Customer cohort.
- Marketing campaign.
- Device type.
- New versus returning customers.

Choose dimensions that relate to the business process and available evidence.

## 2. Compare Equivalent Groups

Suppose overall conversion decreases. Compare conversion by channel and device, using consistent definitions and time windows.

A segment with a large percentage decline may contribute little to the overall business if it represents a tiny share of activity. Consider both the change and the segment's size.

## 3. Contribution Versus Percentage Change

A segment's percentage change tells you how much it changed relative to its own baseline. Its absolute change tells you how much value was gained or lost.

| Region | Previous revenue | Current revenue | Absolute change |
|---|---:|---:|---:|
| North | ₹1,00,000 | ₹90,000 | -₹10,000 |
| South | ₹5,00,000 | ₹4,50,000 | -₹50,000 |
| West | ₹2,00,000 | ₹1,90,000 | -₹10,000 |

All three regions declined by 10%, but the South region accounts for the largest absolute revenue decrease because its baseline was larger.

This makes the South region a useful place to investigate first, without proving that it caused the overall decline.

## 4. Root-Cause Analysis Sequence

1. Validate the overall metric.
2. Check data completeness and comparable periods.
3. Segment the change by relevant dimensions.
4. Identify the largest meaningful contributions.
5. Form possible explanations.
6. Gather evidence that supports or contradicts each explanation.
7. Recommend a targeted next step.

## 5. Beware of Confounding

Two variables can change together without one causing the other.

For example, a marketing campaign and sales may both increase during a festival period. Seasonality could affect both. To assess the campaign's effect, investigate timing, audience differences, comparison groups, and other changes.

## 6. Turn Findings Into Actions

A useful finding identifies:

- What changed.
- Where it changed.
- The magnitude of the change.
- Evidence supporting the explanation.
- What remains uncertain.
- The next action or test.

!!! tip
    Prioritize segments using business impact, evidence quality, and the feasibility of taking action—not percentage change alone.

!!! warning
    The largest declining segment is a good investigation starting point, not automatic proof of root cause.
""",
        "lesson_revision": """- Segmentation reveals differences hidden by aggregate metrics.
- Compare equivalent populations and reporting periods.
- Examine both absolute change and percentage change.
- Correlation does not establish root cause.
- State the finding, supporting evidence, uncertainty, and next action.""",
    },
    {
        "day_number": 6,
        "title": "Hypothesis Testing and Evidence-Based Decisions",
        "difficulty_level": "Beginner",
        "estimated_minutes": 60,
        "objectives": """Form testable business hypotheses
Understand samples and population variation
Interpret confidence intervals and p-values conceptually
Distinguish statistical evidence from business importance""",
        "topics": """Business hypotheses
Sampling variation
Null and alternative hypotheses
P-values
Confidence intervals
Practical significance""",
        "lesson_intro": """A difference observed in data may reflect a real effect, ordinary variation, or limitations in how the data was collected. Learn how hypothesis testing supports careful business decisions.""",
        "lesson_scenario": """An online store changes its checkout design. Conversion appears to rise from 4.0% to 4.3%. The product manager wants to roll out the change immediately, but you need to evaluate the evidence and business impact.""",
        "lesson_body": r"""
## 1. Turn a Claim Into a Testable Hypothesis

A useful hypothesis describes an outcome that can be measured.

Example: "The redesigned checkout increases the purchase conversion rate compared with the existing checkout."

Define the population, outcome, comparison, time period, and success criteria before examining results.

## 2. Null and Alternative Hypotheses

The **null hypothesis** represents a reference assumption, often that there is no difference between the compared groups.

The **alternative hypothesis** represents the effect or difference being investigated.

For a checkout experiment:

- Null: The new and existing checkout have the same conversion rate.
- Alternative: Their conversion rates differ, or the new checkout performs better under a pre-specified directional test.

The test design should match the business question.

## 3. Sampling Variation

If two samples are drawn from the same population, their results will usually differ somewhat by chance.

A small observed difference is not automatically evidence of a reliable effect. Sample size, outcome variability, study design, and data quality all matter.

## 4. Understanding a P-Value

A p-value describes how unusual the observed data, or data more extreme, would be under the specified null hypothesis and statistical assumptions.

A small p-value can be evidence against the null hypothesis.

It is **not**:

- The probability that the null hypothesis is true.
- The probability that the result happened "only by chance."
- A measure of how large or useful the business effect is.

## 5. Confidence Intervals

A confidence interval communicates uncertainty around an estimated effect under the method's assumptions.

A narrow interval generally indicates a more precise estimate than a wide interval. Interpretation depends on the study design and the interval method.

For business decisions, examine both the estimated effect and its uncertainty.

## 6. Statistical Versus Practical Significance

Suppose an experiment detects a tiny improvement in conversion. The result may be statistically detectable but too small to justify engineering, operational, or maintenance costs.

Evaluate:

- Size of the estimated improvement.
- Uncertainty around that estimate.
- Number of customers affected.
- Revenue or profit impact.
- Implementation cost and risks.
- Whether the experiment was conducted fairly.

## 7. Good Experiment Practice

1. Define the primary metric before starting.
2. Choose eligible users and assign groups appropriately.
3. Avoid changing several factors without a suitable design.
4. Check sample quality and experiment duration.
5. Analyze the result using the planned method.
6. Report effect size and uncertainty.
7. Make a decision using both statistical evidence and business context.

!!! warning
    Repeatedly checking results and stopping as soon as a favorable number appears can distort the evidence unless the analysis accounts for sequential monitoring.

!!! example
    If the new checkout improves conversion slightly but creates more payment failures, conversion alone is not sufficient to decide whether to launch it.
""",
        "lesson_revision": """- Define a testable hypothesis before analyzing results.
- Sample results naturally vary.
- A p-value is interpreted under the null hypothesis and test assumptions.
- Confidence intervals communicate uncertainty about an estimate.
- Statistical evidence, business impact, costs, and risks all matter.""",
    },
    {
        "day_number": 7,
        "title": "Data Storytelling and Business Recommendations",
        "difficulty_level": "Beginner",
        "estimated_minutes": 50,
        "objectives": """Translate analysis into a clear business narrative
Choose charts that support the message
Communicate evidence and uncertainty honestly
Write actionable recommendations and next steps""",
        "topics": """Data storytelling
Chart selection
Executive summaries
Evidence and limitations
Business recommendations""",
        "lesson_intro": """The purpose of analytics is not just to produce charts or calculations. It is to help people make better decisions. This lesson explains how to communicate findings clearly and responsibly.""",
        "lesson_scenario": """You have investigated a sales decline and identified that a specific product category in one region accounts for much of the absolute revenue loss. Leadership needs a concise explanation and a practical plan.""",
        "lesson_body": r"""
## 1. What Is Data Storytelling?

Data storytelling combines evidence, context, and a clear message to help an audience understand a result and decide what to do.

A useful analytical story answers:

1. What happened?
2. Why does it matter?
3. What evidence supports the explanation?
4. What remains uncertain?
5. What should happen next?

## 2. Build a Clear Narrative

### Context

Explain the business objective, population, metric, and comparison period.

### Finding

State the most important observed change, including its magnitude and location.

### Evidence

Show the chart, comparison, or table that supports the finding.

### Interpretation

Explain what the evidence suggests and distinguish it from what has not been proven.

### Recommendation

Specify an action, owner, expected outcome, and follow-up measure.

## 3. Choose the Right Chart

| Question | Useful chart |
|---|---|
| How did performance change over time? | Line chart |
| Which categories differ? | Bar chart |
| How is a numeric variable distributed? | Histogram or box plot |
| How do two numeric variables relate? | Scatter plot |
| How do components contribute to a total? | Stacked bar chart when comparisons remain clear |

Avoid selecting a chart only because it looks attractive. The visual should make the intended comparison easy to understand.

## 4. Communicate Magnitude Correctly

Always provide context for a change.

"Sales fell by 10%" is incomplete without knowing:

- The baseline revenue.
- The period being compared.
- Whether the periods are comparable.
- Which segments contributed to the change.
- Whether the result is preliminary or final.

Absolute changes and percentage changes can tell different stories. Include both when they materially help the decision.

## 5. Write a Strong Recommendation

A weak recommendation says:

"Sales should improve."

A stronger recommendation says:

"Investigate product availability and conversion in the region contributing the largest absolute revenue decline. Validate inventory and checkout data first, then run a targeted intervention and monitor revenue, order count, and margin over the next complete reporting period."

The stronger recommendation defines the next investigation and the evidence to monitor.

## 6. Explain Limitations

Responsible reporting states limitations such as:

- Incomplete source data.
- Small sample size.
- Uncertain causal explanations.
- Changes in metric definitions.
- Missing comparison groups.
- Possible seasonal effects.

Limitations do not make an analysis useless. They help decision-makers understand how much confidence to place in the conclusion.

## 7. Final Reporting Checklist

Before sharing a report:

- Is the business question clear?
- Are metric definitions and time periods stated?
- Has data quality been checked?
- Does each chart support a specific point?
- Are findings separated from assumptions?
- Are limitations visible?
- Does the recommendation identify a practical next step?
- Is there a measure for evaluating the action?

!!! tip
    Lead with the decision-relevant finding, then show the evidence. Do not force a busy manager to discover the main message by reading every chart.

!!! example
    A good executive summary might state: "Revenue fell 10% over the comparable period. One region contributed the largest absolute decline. Inventory and channel conversion checks are the next steps; the current evidence does not yet establish a single root cause."
""",
        "lesson_revision": """- Start with the business question and most important finding.
- Support the narrative with relevant, readable evidence.
- Distinguish observed results from causal explanations.
- State uncertainty and limitations.
- Finish with an actionable recommendation and a follow-up metric.""",
    },
]


def get_data_analytics_role():
    """Return the existing Data Analytics career role."""
    role = CareerRole.objects.filter(slug="data-analytics").first()

    if role is None:
        role = CareerRole.objects.filter(name__iexact="Data Analytics").first()

    if role is None:
        raise RuntimeError(
            "Could not find the existing Data Analytics career role. "
            "Check its name or slug in Django Admin."
        )

    return role


def get_role_field_name():
    """Find the LearningDay foreign-key field pointing to CareerRole."""
    for field in LearningDay._meta.get_fields():
        if getattr(field, "is_relation", False) and getattr(
            field, "many_to_one", False
        ):
            if getattr(field, "related_model", None) == CareerRole:
                return field.name

    raise RuntimeError(
        "Could not identify the CareerRole relationship on LearningDay. "
        "Inspect careers/models.py before running this script."
    )


def populate_lessons(dry_run=False, overwrite=False):
    """Populate lesson fields on the existing Data Analytics days 1–7."""
    role = get_data_analytics_role()
    role_field = get_role_field_name()

    lesson_fields = (
        "title",
        "difficulty_level",
        "estimated_minutes",
        "objectives",
        "topics",
        "lesson_intro",
        "lesson_scenario",
        "lesson_body",
        "lesson_revision",
    )

    updated_days = 0
    skipped_days = 0

    with transaction.atomic():
        for lesson in LESSONS:
            day_number = lesson["day_number"]

            filters = {
                role_field: role,
                "level": LEVEL_BEGINNER,
                "day_number": day_number,
            }
            day = LearningDay.objects.filter(**filters).first()

            if day is None:
                print(
                    f"Day {day_number}: no existing LearningDay record found; "
                    "skipping. This script does not create day records."
                )
                skipped_days += 1
                continue

            changed_fields = []

            for field_name in lesson_fields:
                new_value = lesson.get(field_name)
                if new_value is None:
                    continue

                old_value = getattr(day, field_name, None)
                old_is_empty = old_value is None or (
                    isinstance(old_value, str) and not old_value.strip()
                )

                if overwrite or old_is_empty:
                    if old_value != new_value:
                        setattr(day, field_name, new_value)
                        changed_fields.append(field_name)

            # Publish only if all required lesson sections are present.
            required_fields = (
                "lesson_intro",
                "lesson_scenario",
                "lesson_body",
                "lesson_revision",
            )
            all_sections_ready = all(
                bool(str(getattr(day, field_name, "") or "").strip())
                for field_name in required_fields
            )

            if all_sections_ready and not day.is_published:
                day.is_published = True
                changed_fields.append("is_published")

            if not changed_fields:
                print(
                    f"Day {day_number}: no changes needed "
                    "(existing content preserved)."
                )
                continue

            print(
                f"Day {day_number}: "
                + ", ".join(changed_fields)
                + (" [dry run]" if dry_run else " [updated]")
            )

            if not dry_run:
                day.save(update_fields=list(dict.fromkeys(changed_fields)))

            updated_days += 1

        if dry_run:
            transaction.set_rollback(True)

    print("\nFinished.")
    print(f"Career role: {role}")
    print(f"Days with changes planned/applied: {updated_days}")
    print(f"Missing day records skipped: {skipped_days}")

    if dry_run:
        print("Dry run only: no database changes were saved.")


def main():
    """Parse command-line options and run the lesson population."""
    parser = argparse.ArgumentParser(
        description="Populate seven Data Analytics learning days."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned changes without saving them.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing lesson fields for Days 1–7.",
    )
    args = parser.parse_args()

    populate_lessons(
        dry_run=args.dry_run,
        overwrite=args.overwrite,
    )


if __name__ == "__main__":
    main()
