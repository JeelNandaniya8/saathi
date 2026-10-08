"""Keep local Flask development, but never use its development server on Render."""
import os


def serve(app, environment=None):
    environment = os.environ if environment is None else environment
    port = int(environment.get('PORT', '5000'))
    if not 1 <= port <= 65535:
        raise ValueError('PORT must be between 1 and 65535.')
    if environment.get('RENDER', '').lower() != 'true':
        app.run(host='0.0.0.0', port=port,
                debug=environment.get('FLASK_DEBUG', 'false').lower() == 'true')
        return
    # A legacy Render service can still be configured with `python app.py`.
    # Load the existing WSGI object; do not import it again or repeat migrations.
    from gunicorn.app.base import BaseApplication
    app.debug = False

    class RenderApplication(BaseApplication):
        def load_config(self):
            settings = {'bind': f'0.0.0.0:{port}', 'workers': 1, 'worker_class': 'gthread',
                        'threads': 8, 'timeout': 120, 'graceful_timeout': 30,
                        'accesslog': None, 'errorlog': '-', 'preload_app': False}
            for key, value in settings.items():
                self.cfg.set(key, value)

        def load(self):
            return app

    RenderApplication().run()
