import http, { get } from 'k6/http';
import { check, sleep, group  } from 'k6';
import {serverErrorRate, getRandomInt, generateRandomStringConcise, generateTraceparent} from './utils.js';

export default function () {
  let res;
  let username, password;
  let traceparent = generateTraceparent();
  //generate a valid login data
  //it is supposed that on a dev build we have users with such credentials
  if (Math.random() < 0.5) {
    username = `user${getRandomInt(1,15)}`
    password = '123123123'
  }
  else {
    username = generateRandomStringConcise(10)
    password = generateRandomStringConcise(10)
  }
  group('login', function () {
    res = http.post(
      'http://app:8000/api/auth/login', {
        'grant_type':'password',
        username,
        password
      },
      { 
        headers: {
          traceparent
        } 
      }
    );
    serverErrorRate.add(res.status >= 500);
    check(res, {
      'login_200': (r) => r.status === 200,
      'login_404': (r) => r.status === 404,
      'login_401': (r) => r.status === 401,
    });

    const token = res?.json()?.access_token;
    if (!token) return;

    if (token) {
       const params = {
          headers: {
            Authorization: `Bearer ${token}`,
            Accept: 'application/json',
            traceparent
          }
       }
       res = http.get('http://app:8000/api/me', params);
       serverErrorRate.add(res.status >= 500);
       check(res, {
         'login_200': (r) => r.status === 200,
         'login_404': (r) => r.status === 404,
         'login_401': (r) => r.status === 401,
       }); 
    }

  });

}