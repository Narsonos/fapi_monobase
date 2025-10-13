import { Rate } from 'k6/metrics';
import crypto from "k6/crypto"
export const serverErrorRate = new Rate('server_error_rate');

export function getRandomInt(min, max) {
  min = Math.ceil(min);
  max = Math.floor(max);
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

export function generateRandomStringConcise(length) {
  const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  return Array.from({ length }, () => characters.charAt(Math.floor(Math.random() * characters.length))).join('');
}

export function generateTraceparent() {
  const traceId = crypto.randomBytes(16).toString("hex");
  const spanId = crypto.randomBytes(8).toString("hex");
  const traceparent = `00-${traceId}-${spanId}-01`;
  return traceparent;
}