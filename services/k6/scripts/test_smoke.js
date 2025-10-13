import http, { get } from 'k6/http';
import { check, sleep, group  } from 'k6';
import {serverErrorRate, getRandomInt, generateRandomStringConcise} from './utils.js';



export default function () {
  let res;
  if (Math.random() < 0.33) {
    group('get_by_id', function () {
      const userId = getRandomInt(1,5);
      res = http.get(`http://app:8000/api/users/${userId}`);
      check(res, {
        'get_by_id_200': (r) => r.status === 200,
        'get_by_id_404': (r) => r.status === 404,
      });
    });
  }
  else if (Math.random() < 0.66) {  
    group('list', function () {
      res = http.get('http://app:8000/api/users');
      check(res, {
        'list_200': (r) => r.status === 200,
      });
    });
  }
  else {
    group('login', function () {
      res = http.post(
        'http://app:8000/api/auth/login', {
          'grant_type':'password',
          'username':generateRandomStringConcise(10),
          'password':generateRandomStringConcise(10)
        }
      );
      check(res, {
        'login_200': (r) => r.status === 200,
        'login_404': (r) => r.status === 404,
        'login_401': (r) => r.status === 401,
      });
    });
  }
  serverErrorRate.add(res.status >= 500);
}