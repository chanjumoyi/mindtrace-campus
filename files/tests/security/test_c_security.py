from pathlib import Path
import unittest, yaml
ROOT = Path(__file__).resolve().parents[2]

class CSecurityTests(unittest.TestCase):
    def test_service_token_has_no_committed_secret(self):
        app = (ROOT/'local/backend/src/main/resources/application.yml').read_text(encoding='utf-8')
        self.assertIn('service-token: ${APP_SERVICE_TOKEN:}', app)
        self.assertNotIn('replace-with-at-least-32-random-characters', app)

    def test_service_account_permissions_are_least_privilege(self):
        app = yaml.safe_load((ROOT/'local/backend/src/main/resources/application.yml').read_text(encoding='utf-8'))
        permissions = str(app['xinji']['auth']['service-permissions'])
        self.assertIn('ai:invoke', permissions)
        self.assertNotIn('audit:read', permissions)
        self.assertNotIn('file:write', permissions)

    def test_java_core_whitelists_paths_and_redacts_secrets(self):
        core = (ROOT/'kingdee/java-plugin/src/main/java/com/xinji/kingdee/FoundationPluginCore.java').read_text(encoding='utf-8')
        self.assertIn('ALLOWED_PATH_PREFIXES', core)
        self.assertIn('authorization', core.lower())
        self.assertNotIn('UnsupportedOperationException', core)
        self.assertIn('value.startsWith(prefix + \"/\")', core)

    def test_cors_exposes_rate_limit_headers(self):
        source = (ROOT/'local/backend/src/main/java/com/xinji/foundation/config/SecurityConfig.java').read_text(encoding='utf-8')
        self.assertIn('Retry-After', source)
        self.assertIn('X-RateLimit-Limit', source)

if __name__ == '__main__': unittest.main()
