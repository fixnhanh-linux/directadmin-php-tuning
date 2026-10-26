# DirectAdmin PHP Tuning — Quick Reference

One-page cheat sheet. Full Vietnamese playbook: [../README.md](../README.md).

## First: patch, then tune

PHP2Shell (CVE-2026-109618 / CVE-2026-109619) is unauthenticated RCE, CVSS 9.2. Minimum fixed releases: **8.2.35, 8.3.36, 8.4.27, 8.5.12**. Patch and restart **all** workers (FPM, mod_php, queue CLI) before performance work. Details: <https://github.com/fixnhanh-linux/update-php-cve>.

## Key paths

| Item | Path |
|---|---|
| CustomBuild | `/usr/local/directadmin/custombuild` |
| Build options | `/usr/local/directadmin/custombuild/options.conf` |
| PHP binary | `/usr/local/php83/bin/php` |
| `php.ini` | `/usr/local/php83/lib/php.ini` |
| Extra ini dir | `/usr/local/php83/lib/php.conf.d/` |
| FPM global config | `/usr/local/php83/etc/php-fpm.conf` |
| Per-user pool | `/usr/local/directadmin/data/users/USER/php/php-fpm83.conf` |
| FPM socket | `/usr/local/php83/sockets/USER.sock` |
| FPM log | `/usr/local/php83/var/log/php-fpm.log` |
| Service | `php-fpm83` |
| Custom templates | `/usr/local/directadmin/data/templates/custom/` |
| OPcache custom | `/usr/local/directadmin/custombuild/custom/opcache/opcache.ini` |

## Daily commands

```bash
# What is configured?
grep -E '^(php[0-9]_|webserver=|opcache=)' \
  /usr/local/directadmin/custombuild/options.conf

da build opt_help | grep -E 'php|opcache|redis|webserver'
da build versions | head -30
da build used_configs | grep -i 'php\|opcache'

# Change PHP mode/version
da build set php1_mode php-fpm
da build set php1_release 8.3
da build php
da build rewrite_confs

# Read-only config values
da config-get php_fpm_max_children_default
da config-get php_version_selector
da config-get isolated_fpm
```

`da build php` compiles (5–20 min, can overwrite `php.ini`). `da build rewrite_confs` regenerates vhosts/pools only.

## PHP-FPM sizing

DirectAdmin: **one pool per user per PHP version**. All domains of a user share `pm.max_children`.

Defaults: `pm=ondemand`, `pm.max_children=10`, `pm.process_idle_timeout=20`, `pm.max_requests=500`.

```bash
# Average worker RSS
ps -eo rss,comm | awk '/php-fpm/ {s+=$1; n++} END {
  printf "%d workers, %.1f MB avg, %.1f MB total\n", n, s/n/1024, s/1024
}'

# Current limits
grep -H 'pm.max_children' /usr/local/directadmin/data/users/*/php/php-fpm83.conf
```

Formula:

```text
RAM_for_PHP    = total - OS - DB - Redis - reserve
max_workers    = RAM_for_PHP / avg_RSS
max_children   = floor(max_workers / concurrent_users)
```

16 GB, 45 MB/worker, 8 GB for PHP → ~182 workers. For 60 concurrent users → ~3 each. For 180 users → ~1 each. Do not leave 10 for everyone.

```bash
da config-set php_fpm_max_children_default 4
systemctl restart directadmin
da build rewrite_confs
systemctl restart php-fpm83
```

Per-domain override in Custom Httpd Config → `php-fpm83` → CUSTOM1:

```ini
|?MAX_CHILDREN=15|
```

Use `ondemand` on shared hosting. `dynamic` only for a few busy sites. `static` only when you control the load.

## OPcache

```bash
da build set opcache yes
da build opcache
systemctl restart php-fpm83
/usr/local/php83/bin/php -m | grep -i 'Zend OPcache'
```

`/usr/local/php83/lib/php.conf.d/99-opcache-tuning.ini`:

```ini
opcache.enable=1
opcache.enable_cli=0
opcache.memory_consumption=256
opcache.interned_strings_buffer=32
opcache.max_accelerated_files=32531
opcache.max_wasted_percentage=10
opcache.validate_timestamps=1
opcache.revalidate_freq=60
opcache.save_comments=1
opcache.jit=off
opcache.jit_buffer_size=0
```

- OPcache RAM is per FPM master, not per pool. Multiple PHP versions = multiple caches.
- Isolated FPM = one master per user; lower OPcache memory drastically.
- `validate_timestamps=0` needs an explicit cache reset on deploy.
- JIT usually does not help WordPress; benchmark before enabling.
- Check `hits/(hits+misses)`, `free_memory`, `oom_restarts`, `hash_restarts`.

## php.ini starting point

```ini
memory_limit = 256M
max_execution_time = 60
max_input_time = 60
max_input_vars = 5000
post_max_size = 80M
upload_max_filesize = 64M
max_file_uploads = 20
realpath_cache_size = 4096k
realpath_cache_ttl = 600
expose_php = Off
display_errors = Off
log_errors = On
output_buffering = 4096
zlib.output_compression = Off
session.use_strict_mode = 1
session.cookie_httponly = 1
allow_url_include = Off
date.timezone = Asia/Ho_Chi_Minh
```

Upload chain must match: `nginx client_max_body_size` ≥ Apache `LimitRequestBody` ≥ `post_max_size` ≥ `upload_max_filesize`.

Never set `memory_limit=-1` on production (exception: temporary PHP2Shell mitigation with a cgroup limit).

## Redis

```bash
da build set redis yes
da build redis
da build set php_redis yes
da build php_redis

redis-cli -s /home/USER/.redis/redis.sock ping
/usr/local/php83/bin/php -m | grep -i redis
```

WordPress `wp-config.php`:

```php
define('WP_REDIS_SCHEME', 'unix');
define('WP_REDIS_PATH', '/home/USER/.redis/redis.sock');
define('WP_REDIS_PREFIX', 'wp_example_');
define('WP_CACHE', true);
```

- Do not expose Redis to the Internet.
- Do not use `allkeys-lru` on an instance holding sessions.
- APCu shares memory across workers of the same master; on shared hosting prefer Redis or isolated FPM.

## Timeouts

| Layer | Directive | Suggested |
|---|---|---|
| nginx | `fastcgi_read_timeout` / `proxy_read_timeout` | 65s |
| Apache | `Timeout` / `ProxyTimeout` | 65s |
| PHP-FPM | `request_terminate_timeout` | 60s |
| PHP | `max_execution_time` | 60s |

Outer layer must be more patient than inner layer. `max_execution_time` is CPU time, not wall clock.

## Benchmark

```bash
wrk -t4 -c100 -d30s --latency https://example.com/
ab -n 2000 -c50 -k https://example.com/

curl -o /dev/null -s -w \
  'dns=%{time_namelookup} connect=%{time_connect} tls=%{time_appconnect} ttfb=%{time_starttransfer} total=%{time_total}\n' \
  https://example.com/
```

Measure p50/p95/p99, RPS, error rate, CPU, RAM. Warm cache first. Compare same URL/time/concurrency.

## Troubleshooting

| Symptom | Check | Fix |
|---|---|---|
| 502 | `systemctl status php-fpm83`, socket perms, FPM log | Fix pool/socket, restart |
| 504 | nginx/Apache timeout vs PHP | Raise outer timeout or reduce work |
| `max_children` | limits + RSS | Raise carefully or optimize |
| OPcache full | `opcache_get_status` | Raise memory/files, restart |
| Memory exhausted | `memory_get_peak_usage` | Raise per user, fix leak |
| Config ignored | `phpinfo()` loaded file, PHP version | Edit correct layer, restart |
| Config overwritten | `rewrite_confs` / `build php` | Use `templates/custom/` and `99-*.ini` |
| Redis timeout | socket, auth, maxmemory | Fix path/perms/policy |
| `No input file` | docroot, `open_basedir`, jail | Fix path/permissions |

## Rollback

```bash
BK=/root/php-tuning-YYYY-MM-DD-HHMM

cp -a "$BK/php.conf.d/." /usr/local/php83/lib/php.conf.d/
cp -a "$BK/php.ini" /usr/local/php83/lib/php.ini
cp -a "$BK/options.conf" /usr/local/directadmin/custombuild/options.conf

da build rewrite_confs
systemctl restart php-fpm83
curl -sI https://example.com/ | head -1
```

## Rule of thumb

Measure first, change one thing, measure again, and always know the way back.
