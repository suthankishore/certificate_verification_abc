from app import create_app

app = create_app()
with app.test_request_context('/'):
    tpl = app.jinja_env.get_template('admin_dashboard.html')
    rendered = tpl.render(
        total_certificates=5,
        graph_labels=['Jan 2026', 'Feb 2026'],
        graph_values=[2, 3],
        max_value=3,
    )
    print('RENDER OK')
