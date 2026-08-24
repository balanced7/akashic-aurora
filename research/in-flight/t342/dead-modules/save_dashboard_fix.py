from knowledge_base import KB

kb = KB()

kb.write("dashboard_fix", "attribute_error_fix", {
    "error": "AttributeError: 'list' object has no attribute 'get'",
    "location": "app.py line 437 - render_header()",
    "root_cause": "results.get() returned list instead of dict for some services",
    "fixes_applied": [
        "render_header: Added isinstance() checks before .get() calls",
        "render_dashboard: Added safe_get_status() helper",
        "render_chat: Added isinstance() check for models list",
        "render_models: Added isinstance() checks"
    ],
    "status": "fixed"
})

print("Dashboard fix saved to KB")