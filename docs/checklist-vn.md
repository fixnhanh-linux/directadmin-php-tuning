# Checklist tối ưu PHP trên DirectAdmin

Dùng kèm [README](../README.md). In ra hoặc copy vào ticket, tick từng mục.

## 1. Trước khi bắt đầu

- [ ] Đã xác nhận phiên bản PHP và vá PHP2Shell: `8.2.35`, `8.3.36`, `8.4.27`, `8.5.12`.
- [ ] Đã chạy `scripts/da-php-audit.sh` và lưu kết quả.
- [ ] Đã đo baseline: TTFB p50/p95, RPS, CPU, RAM, worker, OPcache hit.
- [ ] Đã backup:
  - [ ] `options.conf`
  - [ ] `php.ini`
  - [ ] `php.conf.d/`
  - [ ] `templates/custom/`
  - [ ] pool của các user lớn
- [ ] Đã ghi lại `max_children` và `memory_limit` hiện tại.
- [ ] Đã có cửa sổ bảo trì và người trực thứ hai.
- [ ] Đã dán lệnh rollback vào terminal/notepad.
- [ ] Đã thông báo khách hàng nếu cần.

## 2. Trong khi làm

### 2.1. OPcache

- [ ] Kiểm tra `opcache_enabled` qua web, không chỉ CLI.
- [ ] Đặt `memory_consumption` theo `used_memory` thực tế.
- [ ] Đặt `max_accelerated_files` ≥ số file thực tế.
- [ ] Giữ `save_comments=1` nếu dùng annotation/Doctrine.
- [ ] Quyết định `validate_timestamps`:
  - [ ] `1` + `revalidate_freq=60` cho shared hosting.
  - [ ] `0` chỉ khi có quy trình reset cache.
- [ ] Tắt JIT nếu không có benchmark chứng minh.
- [ ] Restart FPM và đo lại.

### 2.2. PHP-FPM

- [ ] Đo RSS trung bình của worker.
- [ ] Tính `workers_toi_da = RAM_cho_PHP / RSS`.
- [ ] Đặt `php_fpm_max_children_default` vừa phải.
- [ ] Override `MAX_CHILDREN` cho user thật sự busy.
- [ ] Giữ `ondemand` trên shared hosting.
- [ ] Đặt `request_terminate_timeout` > `max_execution_time`.
- [ ] Bật slow log cho user lớn.
- [ ] Kiểm tra log sau 10 phút: không còn `max_children`, không segfault.
- [ ] Kiểm tra tổng trần worker × RSS không vượt RAM.

### 2.3. php.ini

- [ ] Sửa `99-*.ini`, không sửa `10-directadmin.ini`.
- [ ] `memory_limit` theo nhóm ứng dụng, không -1.
- [ ] `max_input_vars` vừa đủ (3000–5000).
- [ ] Chuỗi upload đồng bộ: nginx → Apache → PHP → app.
- [ ] `realpath_cache_size` 4096k–8192k.
- [ ] `display_errors=Off`, `log_errors=On`.
- [ ] `session.cookie_httponly=1`, `session.use_strict_mode=1`.
- [ ] Kiểm tra `phpinfo()` đúng file, đúng phiên bản.

### 2.4. Redis (nếu dùng)

- [ ] `redis-cli ping` qua socket thành công.
- [ ] `php -m | grep redis` có extension.
- [ ] User đã bật `redis=ON`.
- [ ] `WP_REDIS_PREFIX`/DB riêng cho từng site.
- [ ] `maxmemory` và policy phù hợp.
- [ ] Không mở Redis ra Internet.
- [ ] Có kế hoạch nếu Redis chết (fallback session/file cache).

### 2.5. Web server

- [ ] `client_max_body_size` ≥ `post_max_size`.
- [ ] `fastcgi_read_timeout`/`proxy_read_timeout` > timeout PHP.
- [ ] `nginx -t` / `apachectl configtest` sạch.
- [ ] Chỉ reload/restart sau khi test cú pháp.
- [ ] Kiểm tra 502/504 sau reload.

## 3. Sau khi làm

### 3.1. Sau 1 giờ

- [ ] Không có 502/504 mới.
- [ ] Log FPM không có `max_children`, segfault, OOM.
- [ ] RAM và load ổn định.
- [ ] OPcache hit rate > 95%.
- [ ] Redis (nếu có) không evict session.

### 3.2. Sau 24 giờ

- [ ] TTFB p95 tốt hơn baseline (hoặc không xấu đi).
- [ ] RPS không giảm.
- [ ] CPU không tăng.
- [ ] Không có phản hồi "web chậm" từ khách.
- [ ] Log không có lỗi mới lặp lại.

### 3.3. Sau 7 ngày

- [ ] Xu hướng RAM/CPU ổn định.
- [ ] `max_children` warning gần 0.
- [ ] OPcache `oom_restarts`/`hash_restarts` = 0.
- [ ] Redis memory ổn định.
- [ ] Dung lượng log/inode trong ngưỡng.
- [ ] Ghi lại kết quả vào change log.

## 4. Định kỳ hàng tháng

- [ ] Chạy `da-php-audit.sh`, so sánh với tháng trước.
- [ ] Kiểm tra PHP EOL và bản vá bảo mật.
- [ ] Kiểm tra OPcache hit rate, dung lượng, restart.
- [ ] Kiểm tra tổng worker FPM so với RAM.
- [ ] Kiểm tra Redis memory/eviction.
- [ ] Kiểm tra dung lượng disk/inode.
- [ ] Rà file PHP mới trong uploads, cron lạ, process lạ.
- [ ] Kiểm tra chứng chỉ TLS và thời hạn.
- [ ] Cập nhật tài liệu/change log.

## 5. Thẻ rollback nhanh

```bash
BK=/root/php-tuning-YYYY-MM-DD-HHMM

cp -a "$BK/php.conf.d/." /usr/local/php83/lib/php.conf.d/
cp -a "$BK/php.ini" /usr/local/php83/lib/php.ini
cp -a "$BK/options.conf" /usr/local/directadmin/custombuild/options.conf

da build rewrite_confs
systemctl restart php-fpm83

curl -sI https://example.com/ | head -1
tail -n 50 /usr/local/php83/var/log/php-fpm.log
```

## 6. Ghi chú

```text
Server:
Ngày:
Người làm:
Baseline TTFB p95:
Baseline RPS:
Baseline CPU/RAM:

Thay đổi 1:
  File:
  Cũ -> Mới:
  Kết quả:
  Rollback:

Thay đổi 2:
  File:
  Cũ -> Mới:
  Kết quả:
  Rollback:

Quyết định cuối:
Người xác nhận:
```
