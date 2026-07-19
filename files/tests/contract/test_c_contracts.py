from pathlib import Path
import json, unittest, yaml
ROOT = Path(__file__).resolve().parents[2]

class CContractTests(unittest.TestCase):
    def test_openapi_contains_reliability_contract(self):
        api = yaml.safe_load((ROOT/'contracts/openapi.yaml').read_text(encoding='utf-8'))
        self.assertIn('/ai/invoke', api['paths'])
        self.assertIn('/ai/call-logs/{callId}/attempts', api['paths'])
        responses = api['paths']['/ai/invoke']['post']['responses']
        for code in ('200','409','425','429','502','504'): self.assertIn(code, responses)
        schema = api['components']['schemas']['AiInvokeRequest']['properties']['timeoutMs']
        self.assertEqual(200, schema['minimum'])

    def test_database_migration_contains_all_reliability_state(self):
        sql = (ROOT/'local/backend/src/main/resources/db/migration/V2__ai_gateway_reliability.sql').read_text(encoding='utf-8').lower()
        for fragment in ('lease_until','recovery_count','ai_call_attempt_log','ai_rate_limit_bucket','total_backoff_ms','parent_call_id'):
            self.assertIn(fragment, sql)

    def test_generated_assets_are_c_only_and_schemas_exist(self):
        domain = json.loads((ROOT/'kingdee/domain-models/generated/common-foundation-models.import.json').read_text(encoding='utf-8'))
        self.assertEqual('C', domain['owner'])
        self.assertGreaterEqual(len(domain['models']), 9)
        tools = sorted((ROOT/'kingdee/agent-tools/generated').glob('*.registration.json'))
        self.assertEqual(3, len(tools))
        for path in tools:
            tool = json.loads(path.read_text(encoding='utf-8'))
            self.assertIn(tool['path'], ('/api/v1/tasks','/api/v1/files/{id}','/api/v1/ai/invoke'))
            self.assertEqual('object', tool['inputSchema']['type'])

if __name__ == '__main__': unittest.main()
