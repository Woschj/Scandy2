import os
import jinja2
from datetime import datetime

def mock_render():
    template_dir = 'app/templates'
    loader = jinja2.FileSystemLoader(template_dir)
    env = jinja2.Environment(loader=loader)

    # Mock filters
    env.filters['trans'] = lambda x: x
    env.filters['datetime'] = lambda x: x.strftime('%d.%m.%Y %H:%M') if isinstance(x, datetime) else str(x)
    env.filters['format_datetime'] = lambda x: str(x)
    env.filters['author'] = lambda x: "Scandy Team"
    env.filters['version'] = lambda x: "1.0.0"

    # Mock globals
    env.globals['url_for'] = lambda endpoint, **kwargs: f"/{endpoint.replace('.', '/')}"
    env.globals['csrf_token'] = lambda: "mock_csrf_token"
    env.globals['get_flashed_messages'] = lambda **kwargs: []

    class MockUser:
        def __init__(self):
            self.is_authenticated = True
            self.role = 'admin'
            self.username = 'admin'
            self.is_mitarbeiter = True
            self.timesheet_enabled = True

    class MockRequest:
        def __init__(self):
            self.endpoint = 'admin.dashboard'
            self.referrer = None

    mock_ctx = {
        'request': MockRequest(),
        'current_user': MockUser(),
        'app_labels': {
            'tools': {'name': 'Werkzeuge', 'icon': 'fas fa-tools'},
            'consumables': {'name': 'Verbrauchsmaterial', 'icon': 'fas fa-box'},
            'tickets': {'name': 'Tickets', 'icon': 'fas fa-ticket-alt'}
        },
        'csp_nonce': 'mock_nonce',
        'departments_ctx': {'current': 'IT', 'allowed': ['IT', 'Lager']},
        'departments': {'current': 'IT', 'allowed': ['IT', 'Lager']},
        'version_info': {'local_version': '1.0.0'},
        'feature_settings': {'software_management': True},
        'features_enabled': {'ticket_system': True, 'weekly_reports': True},
        'tool_stats': {'total': 100, 'available': 80, 'lent': 15, 'defect': 5},
        'consumable_stats': {'total': 50, 'sufficient': 40, 'warning': 5, 'critical': 5},
        'worker_stats': {'total': 20, 'by_department': [{'name': 'IT', 'count': 5}]},
        'current_lendings': [],
        'warnings': {'defect_tools': [], 'duplicate_lendings': [], 'low_stock_consumables': [], 'overdue_lendings': []},
        'notices': []
    }

    # Render tools index
    try:
        mock_tools = [
            {'barcode': '12345', 'name': 'Hammer', 'category': 'Handwerkzeuge', 'location': 'Werkstatt', 'status': 'verfügbar'},
            {'barcode': '67890', 'name': 'Bohrmaschine', 'category': 'Elektrowerkzeuge', 'location': 'Lager', 'status': 'ausgeliehen'},
            {'barcode': '11223', 'name': 'Schraubenschlüssel', 'category': 'Handwerkzeuge', 'location': 'Werkstatt', 'status': 'defekt'}
        ]
        template = env.get_template('tools/index.html')
        rendered = template.render(**mock_ctx, tools=mock_tools, categories=['Handwerkzeuge', 'Elektrowerkzeuge'], locations=['Werkstatt', 'Lager'])
        os.makedirs('verification', exist_ok=True)
        with open('verification/tools_index.html', 'w') as f:
            f.write(rendered)
        print("Tools index rendered to verification/tools_index.html")
    except Exception as e:
        print(f"Error rendering tools index: {e}")

    # Render base to see quickscan modal (it's included in base.html)
    try:
        template = env.get_template('base.html')
        rendered = template.render(**mock_ctx)
        with open('verification/base.html', 'w') as f:
            f.write(rendered)
        print("Base rendered to verification/base.html")
    except Exception as e:
        print(f"Error rendering base: {e}")

if __name__ == "__main__":
    mock_render()
