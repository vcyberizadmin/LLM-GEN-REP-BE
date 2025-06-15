import path from 'path';
import { Pact, Matchers } from '@pact-foundation/pact';
import fetch from 'node-fetch';

const { like, eachLike, regex } = Matchers;

describe('Anthropic API Consumer Pact', () => {
  const provider = new Pact({
    consumer: 'LLM-GEN-REPORT Backend',
    provider: 'AnthropicAPI',
    port: 1234,
    log: path.resolve(process.cwd(), 'logs', 'pact.log'),
    dir: path.resolve(process.cwd(), 'pacts'),
    logLevel: 'INFO',
  });

  beforeAll(() => provider.setup());
  afterAll(() => provider.finalize());
  afterEach(() => provider.verify());

  describe('when sending an analyze request', () => {
    beforeAll(() =>
      provider.addInteraction({
        state: 'Anthropic API is available',
        uponReceiving: 'a request to create a message',
        withRequest: {
          method: 'POST',
          path: '/v1/messages',
          headers: {
            'Content-Type': 'application/json',
            Authorization: regex({ generate: 'Bearer test-api-key', matcher: '^Bearer [A-Za-z0-9-]+$' }),
          },
          body: {
            model: like('claude-3-7-sonnet-20250219'),
            max_tokens: like(1024),
            messages: eachLike({
              role: like('user'),
              content: like('test query'),
            }),
          },
        },
        willRespondWith: {
          status: 200,
          headers: {
            'Content-Type': 'application/json; charset=utf-8',
          },
          body: {
            completion: like('This is a response'),
          },
        },
      })
    );

    it('sends the correct payload to Anthropic API', async () => {
      const response = await fetch('http://localhost:1234/v1/messages', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer test-api-key',
        },
        body: JSON.stringify({
          model: 'claude-3-7-sonnet-20250219',
          max_tokens: 1024,
          messages: [{ role: 'user', content: 'test query' }],
        }),
      });
      expect(response.status).toBe(200);
      const body = await response.json();
      expect(body.completion).toEqual(expect.any(String));
    });
  });
});