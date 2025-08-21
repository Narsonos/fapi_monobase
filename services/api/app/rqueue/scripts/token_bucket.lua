local tokens_key = KEYS[1]
local refill_key = KEYS[2]
local request_key = KEYS[3]

local capacity = tonumber(ARGV[1])
local rate = tonumber(ARGV[2])
local min_delay = tonumber(ARGV[3])
local ttl = tonumber(ARGV[4])

local now_data = redis.call('TIME')
local now = tonumber(now_data[1]) + tonumber(now_data[2]) / 1000000

--minimal waiting time so servers would not loop in waiting
local min_wait = 0.1

local tokens = tonumber(redis.call('GET', tokens_key)) or capacity
local last_refill = tonumber(redis.call('GET', refill_key)) or now
local last_request = tonumber(redis.call('GET', request_key)) or 0

-- Refill tokens
local elapsed = now - last_refill
tokens = math.min(capacity, tokens + elapsed * rate)

-- Burst delay
local delay_since_last = now - last_request
if delay_since_last < min_delay then
    return {0, tostring(math.max(min_delay - delay_since_last, min_wait))}
end

if tokens < 1 then
    return {0, tostring(math.max((1 - tokens) / rate, min_wait))}
end

tokens = tokens - 1

-- Save updated state
redis.call('SET', tokens_key, tokens, 'EX', ttl)
redis.call('SET', refill_key, now, 'EX', ttl)
redis.call('SET', request_key, now, 'EX', ttl)

return {1, 0}