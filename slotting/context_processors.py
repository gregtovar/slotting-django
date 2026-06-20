"""
context_processors.py
------------------------
Injects the table/analysis/report lists into every template's context
automatically, so base.html's navigation doesn't need every view to
remember to pass them in explicitly.
"""

from app.config import ALL_TABLES, ALL_ANALYSES, ALL_REPORTS, APP_NAME, APP_SUBTITLE


def nav_context(request):
    return {
        "nav_tables": ALL_TABLES,
        "nav_analyses": ALL_ANALYSES,
        "nav_reports": ALL_REPORTS,
        "app_name": APP_NAME,
        "app_subtitle": APP_SUBTITLE,
    }
