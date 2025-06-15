import http from 'k6/http';
import { sleep, check } from 'k6';

export const options = {
  vus: 50,
  duration: '60s',
};

const BASE_URL = __ENV.LOAD_API_URL || 'http://localhost:8000';

export default function () {
  // upload small CSV and parse
  const fileData = open('./sample.csv');
  const res = http.post(`${BASE_URL}/upload`, fileData, {
    headers: { 'Content-Type': 'text/csv' },
  });
  check(res, { 'status 200': (r) => r.status === 200 });
  sleep(1);
}