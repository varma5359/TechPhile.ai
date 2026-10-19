# TechPhile.ai frontend inventory and design review

## Shared visual system

The active page shells load `static/css/design-system.css` and use the official `static/images/logo-nav.png` wordmark. The shared system follows the supplied dark dashboard reference: charcoal-navy page and card surfaces, bright blue actions and focus states, cyan accents, subtle violet highlights, accessible status colors, consistent typography, spacing, controls, tables, alerts, footer, responsive behavior, and reduced motion. Header logos use one compact size across the public, authentication, exam, coding, and course shells; they all reference `static/images/favicon.png`.

The shells retain the framework versions and editor assets their pages depend on. Their shared components use the same colors, typography, logo treatment, button and field shapes, footer, and interaction states. Saved user theme choices remain supported. Content layouts remain suited to the page: focused auth forms, learner dashboards, path navigation, readable lesson articles, exams, and coding editors.

## Route-to-template coverage

| Route or route family | Template(s) and shell | Review outcome |
| --- | --- | --- |
| `/`, `/about/`, `/services/`, `/contact/` | `templates/{home,about,services,contact}.html` → `templates/base.html` | Public pages use the common TechPhile header, footer, brand tokens, responsive sections, and forms. Contact retains its existing Django form and messages. |
| `/accounts/login/`, `/accounts/signup/` | `exams/templates/registration/{login,signup}.html` → `exams/templates/registration/registration_base.html` | Authentication forms retain CSRF, Django fields, messages, validation, redirect, and account links. The active resolver finds these app templates; similarly named files in `accounts/templates/` are not selected by these views. |
| `/accounts/logout/`, email verification | `accounts.views.logout_view` redirects; `verify_email` returns to login or signup | No standalone logout or verification page is rendered. Existing redirect and messages behavior is retained. |
| Password reset request, sent, confirmation, complete | Root `templates/registration/password_reset_{form,done,confirm,complete}.html`; root `templates/password_reset_{confirm,complete}.html` are also present | Focused forms/status screens use the registration shell. Reset email is not a browser page. |
| `/accounts/terms-of-service/`, `/accounts/privacy-policy/` | `exams/templates/registration/{terms_of_service,privacy_policy}.html` → registration shell | Legal reading pages use the same shell and readable content width. |
| `/careers/`, `/careers/dashboard/` | `careers/templates/careers/{role_list,dashboard}.html` → public shell | Career choices and progress use existing backend values and link to the appropriate path. |
| `/careers/<slug>/`, `/careers/<slug>/path/<level>/` | `role_detail.html` → public shell | Path and level information, progress, recommendations, and day/milestone links remain dynamic. |
| Career day, notes completion, result, milestone, and milestone result routes, including level variants | `day_detail.html`, `day_result.html`, `milestone_detail.html`, `milestone_result.html`, with `_lesson.html`, `_lesson_styles.html`, `_question_form.html`, `_day_nav.html`, `_shared.html`, `_review.html` → public shell | Lesson article, question, review, assessment, and previous/next patterns use shared styles and existing form workflows. |
| `/exams/mock-exams/`, exam detail, question, result, and no-question routes | `exams/templates/exams/{exam_list,exam_detail,exam_question,exam_result,no_questions}.html` → exam shell | Browse, assessment, empty, result, and feedback states use the common tokens and responsive surfaces. |
| `/exams/dashboard/`, `/exams/user-analytics/` | `student_dashboard.html`, `user_analytics.html` → exam shell | Learner metrics, recent attempts, and empty states use supplied data. |
| `/exams/settings/profile/` and update workflows | `profile_settings.html` → exam shell | Profile, career preferences, password, sessions, notifications, and display preferences retain their existing forms and permissions. |
| `/exams/study-guide/`, `/exams/sample-questions/<slug>/` | `study_guide.html`, `sample_questions.html` → exam shell | Guide and samples use shared typography, content widths, and assessment styling. |
| Mock-interview form, interviewer schedule/detail/edit/cancel/reschedule/join/feedback, interviewer dashboard | `interview_form.html`, `view_interview.html`, `edit_interview.html`, `cancel_interview.html`, `reschedule_interview.html`, `join_interview.html`, `interview_feedback.html`, `interviewer_dashboard.html` → exam shell | Reviewed as existing user-facing pages; visibility and feature flags remain unchanged. |
| Custom interviewer assignment | `exams/templates/admin/assign_interviewer.html` → Django admin shell; `static/css/admin-page.css` | Custom content is styled with the shared palette and form patterns while preserving admin functionality. Django admin/Jazzmin internals are not changed. |
| Coding practice home, problem list/detail, dashboard, leaderboard | `templates/coding_temp/coding/{home,problem_list,problem_detail,dashboard,leaderboard}.html` → `templates/coding_temp/base.html` | Common brand tokens and footer align the Tailwind shell. Code editor and editor scripts remain intact; the mobile menu exposes accessible state. |
| Course exploration, creativity/intelligence, topic/problem detail, leaderboard, datasets | `templates/coding_temp/core/{home,creativity_intelligence,topic_detail,problem_detail,leaderboard,datasets}.html` → `templates/coding_temp/core/base.html` | Bootstrap content uses the same brand tokens and footer; existing route and code submission behavior is retained. |

## Retained templates outside active page routes

`exams/templates/exams/study_demo.html`, old standalone account templates, and old coding login/register templates have no active route in the URL configurations reviewed. They were not promoted or wired into navigation. API-only routes, email bodies, PDF output, and Django's built-in admin screens are not browser UI pages in this redesign scope.

## Local work and safety

The workspace already contained user modifications in application code, templates, styles, and data files before this review. They were preserved. Database backups were not opened; no database connection, records, migrations, dependency installation, or Git stage/commit/push/reset/clean operation was performed.

## Validation limits

Source-level route/template and shared-shell review was completed. Parser-only checks passed for all five edited shared shell templates and all four relevant stylesheets (`design-system.css`, `learner-dashboards.css`, `profile-preferences.css`, and `admin-page.css`). `git diff --check` passed on the redesign styles and all edited shared shell templates except `templates/base.html`, which contains pre-existing trailing whitespace in a user-modified block; that block was preserved. A full Django template-loader pass was attempted with the repository's isolated SQLite validation settings; it stopped because `careers.templatetags.careers_extras` imports the unavailable `markdown` package. No package was installed. The favicon asset exists. Browser-based viewport and interaction checks at 375, 430, 768, 1024, and 1440 pixels were not available in this environment, so no claim of rendered browser verification is made. Database-backed pages were reviewed from route/view/template source; they were not opened against live data.
