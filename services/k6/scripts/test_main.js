
import smokeTest from './test_smoke.js';
import authTest from './test_auth.js';

export const options = {
  thresholds: {
    'http_req_duration': ['p(95)<500'], 
    'server_error_rate': ['rate<0.01'], 
  },
  scenarios: {
    test: {
      executor: 'ramping-vus', 
      exec: 'authTest',                                              
      startTime: '0s',               
      stages: [
        { duration: '30s',  target: 30 }, 
        { duration: '20m',   target: 30 },  
        { duration: '10s',  target: 0 },  
      ],
    },
  },
};


export { authTest };


