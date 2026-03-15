1. **Goal:** Add missing tests for `AdminEmailTemplatesService.get_template_mappings` fallback branch in `app/services/admin_email_templates_service.py`
2. **Setup:** I've created a new test file `tests/unit/services/test_admin_email_templates_service.py` to contain tests for `AdminEmailTemplatesService`.
3. **Write test:** Mock `mongodb.find_one` to raise an `Exception` inside the test function `test_get_template_mappings_exception_fallback`, which verifies that `AdminEmailTemplatesService.get_template_mappings()` returns the default hardcoded mappings `{'auftrag_confirmation': 'auftrag_confirmation', 'password_reset': 'password_reset', 'user_welcome': 'user_welcome'}`
4. **Run tests:** I've verified the new test passes and correctly covers lines 46-51 where the fallback exception logic resides.
5. **Add pre-commit:** Run pre-commit instructions before finalizing.
6. **Submit:** Submit the PR.
