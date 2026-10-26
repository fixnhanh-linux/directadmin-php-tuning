# directadmin-php-tuning

[![DirectAdmin](https://img.shields.io/badge/DirectAdmin-1.690%2B-2C3E50)](https://www.directadmin.com/)
[![PHP](https://img.shields.io/badge/PHP-8.2%20%7C%208.3%20%7C%208.4%20%7C%208.5-8892BF?logo=php&logoColor=white)](https://www.php.net/supported-versions.php)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Vietnamese](https://img.shields.io/badge/ng%C3%B4n%20ng%E1%BB%AF-Ti%E1%BA%BFng%20Vi%E1%BB%87t-blue)](README.md)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)](https://github.com/fixnhanh-linux/directadmin-php-tuning/pulls)

Playbook tối ưu **PHP trên DirectAdmin/CustomBuild** theo hướng đo lường, không theo phong trào. Viết cho sysadmin đang quản lý shared hosting, VPS hoặc cluster DirectAdmin có nhiều tài khoản và nhiều phiên bản PHP.

Trọng tâm:

- **PHP-FPM**: chọn chế độ chạy, tính số worker, đọc log, tránh OOM.
- **OPcache**: bật đúng, cấp bộ nhớ đúng, hiểu đánh đổi khi tắt kiểm tra file.
- **Redis**: object cache và session, kèm cảnh báo bảo mật khi dùng chung.
- **php.ini**: chỉnh theo ứng dụng, không copy một mức `memory_limit` cho mọi site.
- **Benchmark**: đo trước/sau bằng cùng một phương pháp, có số liệu và có rollback.

> [!CAUTION]
> **Bảo mật trước, tối ưu sau.** Nếu server còn chạy PHP thấp hơn `8.2.35`,
> `8.3.36`, `8.4.27` hoặc `8.5.12`, hãy vá **PHP2Shell** (CVE-2026-109618 /
> CVE-2026-109619, RCE không xác thực, CVSS 9.2) trước khi nghĩ đến chuyện tăng tốc.
> Hướng dẫn vá và xử lý khẩn cấp: [update-php-cve](https://github.com/fixnhanh-linux/update-php-cve).
> Tối ưu một server đang có lỗ hổng RCE chỉ làm server đó chạy nhanh hơn — cho cả kẻ tấn công.

> [!NOTE]
> Repo chỉ chứa **tài liệu và script chỉ-đọc**. Không có script tự sửa `php.ini`,
> tự restart service hay tự đổi `options.conf`. Mọi thay đổi cấu hình đều do bạn
> chủ động chạy, có backup và có đường rollback.

### Bạn sẽ nhận được gì

- Quy trình 60 phút để tối ưu một server DirectAdmin đang chạy thật, chia theo bước nhỏ.
- Công thức tính `pm.max_children` theo RAM thực tế, không đoán.
- Bộ cấu hình mẫu cho OPcache, php.ini, PHP-FPM và Redis.
- Script `da-php-audit.sh` đọc cấu hình, đếm worker, kiểm tra OPcache/Redis/PHP2Shell và in cảnh báo.
- Case study có số liệu trước/sau, kèm những thứ **không** hiệu quả.
- Checklist, bảng lỗi thường gặp, FAQ và thuật ngữ.

### Không dành cho

- Người muốn một câu thần chú `opcache.memory_consumption=1024` rồi coi là xong.
- Server dùng cPanel/Plesk (nguyên tắc tương tự nhưng đường dẫn và công cụ khác).
- Ứng dụng bị chậm vì query MySQL, API bên thứ ba hoặc code — tối ưu PHP không chữa được gốc rễ.

## Mục lục

- [1. TL;DR: mười việc nên làm theo thứ tự](#1-tldr-mười-việc-nên-làm-theo-thứ-tự)
- [2. Đo baseline trước khi tối ưu](#2-đo-baseline-trước-khi-tối-ưu)
- [3. DirectAdmin và CustomBuild: những đường dẫn cần biết](#3-directadmin-và-custombuild-những-đường-dẫn-cần-biết)
- [4. Chọn phiên bản PHP và handler](#4-chọn-phiên-bản-php-và-handler)
- [5. PHP-FPM: tính đúng số worker](#5-php-fpm-tính-đúng-số-worker)
- [6. OPcache: món hời lớn nhất, nhưng đừng tham](#6-opcache-món-hời-lớn-nhất-nhưng-đừng-tham)
- [7. Redis, session và object cache](#7-redis-session-và-object-cache)
- [8. php.ini: chỉnh đúng chỗ, đúng liều](#8-phpini-chỉnh-đúng-chỗ-đúng-liều)
- [9. Web server, timeout và các điểm nối với PHP](#9-web-server-timeout-và-các-điểm-nối-với-php)
- [10. Quy trình tối ưu 60 phút trên production](#10-quy-trình-tối-ưu-60-phút-trên-production)
- [11. Benchmark: đo cái gì và đo như thế nào](#11-benchmark-đo-cái-gì-và-đo-như-thế-nào)
- [12. Case study: 8 vCPU / 16 GB, 180 tài khoản WordPress](#12-case-study-8-vcpu--16-gb-180-tài-khoản-wordpress)
- [13. Troubleshooting: các lỗi thường gặp](#13-troubleshooting-các-lỗi-thường-gặp)
- [14. Checklist, rollback và giám sát định kỳ](#14-checklist-rollback-và-giám-sát-định-kỳ)
- [15. FAQ](#15-faq)
- [16. Thuật ngữ](#16-thuật-ngữ)
- [17. Cấu trúc repo, đóng góp và License](#17-cấu-trúc-repo-đóng-góp-và-license)

---

## 1. TL;DR: mười việc nên làm theo thứ tự

| # | Việc | Tác động | Rủi ro | Thời gian |
|---|---|---|---|---|
| 1 | Vá PHP2Shell và các bản vá bảo mật | Cao nhất — sống còn | Thấp nếu có backup | 5–15 phút |
| 2 | Đo baseline: CPU, RAM, TTFB, worker, OPcache | Không có baseline thì không biết mình giỏi lên hay tệ đi | Không | 15 phút |
| 3 | Bật **OPcache** nếu đang tắt | Rất cao, đặc biệt với WordPress/Laravel | Thấp | 5 phút |
| 4 | Tăng `realpath_cache_size` vừa phải | Trung bình, giảm `stat()` syscall | Thấp | 2 phút |
| 5 | Tính lại `pm.max_children` theo RAM | Cao — tránh OOM và 502 | Trung bình, cần theo dõi | 20 phút |
| 6 | Chỉnh `php.ini` theo từng nhóm ứng dụng | Trung bình, giảm lỗi upload/timeout | Trung bình | 20 phút |
| 7 | Redis cho object cache/session (nếu cần) | Cao với WooCommerce/Laravel | Trung bình | 30 phút |
| 8 | Đồng bộ timeout giữa web server và PHP | Giảm 502/504 oan | Thấp | 10 phút |
| 9 | Benchmark lại, cùng URL, cùng concurrency | Xác nhận có cải thiện thật | Không | 20 phút |
| 10 | Giám sát định kỳ: OPcache hit rate, `max_children`, EOL | Duy trì kết quả | Không | 10 phút/tháng |

### Bốn lệnh kiểm tra nhanh

```bash
# 1) DirectAdmin đang cấu hình PHP gì?
grep -E '^(php[0-9]_|webserver=|opcache=)' /usr/local/directadmin/custombuild/options.conf

# 2) Các phiên bản PHP đang có và chế độ chạy
da build versions 2>/dev/null | head -30

# 3) Dịch vụ FPM nào đang chạy?
systemctl list-units --type=service --state=running 'php-fpm*' --no-pager

# 4) Worker FPM đang tốn bao nhiêu RAM?
ps -eo rss,comm | awk '/php-fpm/ {s+=$1; n++} END {printf "%d worker, %.1f MB/worker, %.1f MB tong\n", n, (n?s/n/1024:0), s/1024}'
```

> [!TIP]
> Nếu chỉ có 15 phút, làm bước 1 và bước 3. Đây là hai việc cho tỷ lệ lợi ích/rủi ro cao nhất trên gần như mọi server DirectAdmin.

### Ba nguyên tắc

1. **Một thay đổi, một phép đo.** Đổi OPcache, FPM và php.ini cùng lúc rồi thấy nhanh hơn thì không biết cái nào có công, cái nào sẽ gây lỗi lúc 2 giờ sáng.
2. **Đo bằng số, không bằng cảm giác.** "Thấy web nhanh hơn" không phải dữ liệu. Dùng TTFB p95, RPS, CPU, RAM, tỷ lệ lỗi.
3. **Luôn có đường về.** Backup file cấu hình, ghi lại lệnh đã chạy, biết chính xác lệnh rollback trước khi bấm Enter.

---

## 2. Đo baseline trước khi tối ưu

Baseline là ảnh chụp server **trước khi sửa**. Không có nó, mọi con số "cải thiện 40%" chỉ là lời kể.

### 2.1. Thu thập thông tin hệ thống

```bash
install -d -m 700 /root/php-baseline
{
  date -Is
  uname -a
  nproc
  free -m
  uptime
  df -h
  df -i
  ss -s
} | tee /root/php-baseline/system.txt
```

### 2.2. Chụp cấu hình PHP và DirectAdmin

```bash
{
  echo "=== options.conf ==="
  grep -E '^(php[0-9]_|webserver=|opcache=|php_ini|php_htscanner|secure_php)' \
    /usr/local/directadmin/custombuild/options.conf

  echo "=== directadmin.conf (PHP) ==="
  da config-get php_fpm_max_children_default 2>/dev/null
  da config-get php_version_selector 2>/dev/null
  da config-get isolated_fpm 2>/dev/null

  echo "=== binary PHP ==="
  for b in /usr/local/php*/bin/php; do
    [ -x "$b" ] && "$b" -r 'echo PHP_BINARY, " => ", PHP_VERSION, PHP_EOL;'
  done

  echo "=== FPM service ==="
  systemctl list-units --all 'php-fpm*.service' --no-pager
} | tee /root/php-baseline/php-config.txt
```

### 2.3. Đếm worker và RAM thực tế

```bash
for svc in $(systemctl list-units --type=service --state=running 'php-fpm*.service' \
             --no-legend | awk '{print $1}'); do
  echo "=== $svc ==="
  systemctl show "$svc" -p MainPID -p MemoryCurrent -p Tasks
  main=$(systemctl show "$svc" -p MainPID --value)
  ps -o pid,ppid,rss,%cpu,etime,cmd --ppid "$main" 2>/dev/null | tail -n +2 | head -20
done
```

Ghi lại:

| Chỉ số | Lấy ở đâu | Ngưỡng cần chú ý |
|---|---|---|
| RAM/worker trung bình | `ps -o rss` của worker FPM | > 80 MB/worker là cao với WordPress thông thường |
| Tổng worker | `ps --ppid <MainPID>` | So với tổng `max_children` của các pool |
| CPU load | `uptime` | Load > số core kéo dài là dấu hiệu quá tải |
| Swap đang dùng | `free -m` | Swap tăng liên tục là thiếu RAM |
| Inode | `df -i` | Đầy inode cũng gây lỗi ghi file/session |
| TTFB p95 | `curl`/`wrk` (chương 11) | > 800 ms với trang động là chậm |
| OPcache hit rate | `opcache_get_status()` | < 95% là cần xem lại cấu hình |

### 2.4. Đo TTFB trước khi sửa

```bash
URL="https://example.com/"
for i in 1 2 3 4 5; do
  curl -o /dev/null -s -w '%{time_starttransfer}\n' "$URL"
done | tee /root/php-baseline/ttfb-before.txt
```

Chạy cùng URL, cùng thời điểm trong ngày, cùng trạng thái cache (nên warm up 3 request trước khi đo). Nếu đo trang admin đang đăng nhập, kết quả sẽ không đại diện cho người dùng thật.

### 2.5. Kiểm tra log trước khi sửa

```bash
# Log FPM mặc định của DirectAdmin
for f in /usr/local/php*/var/log/php-fpm.log; do
  [ -f "$f" ] || continue
  echo "=== $f ==="
  tail -n 2000 "$f" | grep -Ei 'max_children|segfault|oom|killed|error' | tail -20
done

# Journal của các service FPM
journalctl -u 'php-fpm*' --since '7 days ago' --no-pager 2>/dev/null \
  | grep -Ei 'max_children|segfault|oom|killed|emergency' | tail -30
```

Nếu log đã có `server reached max_children` từ trước, đó là dấu hiệu server **đang thiếu worker**, không phải chỉ chậm. Nếu có `segfault` hoặc OOM, ưu tiên điều tra nguyên nhân trước khi tăng giới hạn.

---

## 3. DirectAdmin và CustomBuild: những đường dẫn cần biết

DirectAdmin không cấu hình PHP bằng tay từng file như LEMP thuần. CustomBuild sinh cấu hình từ template, và **ghi đè** nhiều file mỗi lần build hoặc `rewrite_confs`. Biết file nào là nguồn, file nào là kết quả, là điều kiện tiên quyết để không mất công chỉnh.

### 3.1. Bảng đường dẫn

| Thành phần | Đường dẫn mặc định | Ghi chú |
|---|---|---|
| Thư mục CustomBuild | `/usr/local/directadmin/custombuild` | Nơi chạy `da build`, chứa `options.conf` |
| Cấu hình build | `/usr/local/directadmin/custombuild/options.conf` | Nguồn cho phiên bản, handler, webserver |
| PHP binary | `/usr/local/php83/bin/php` | Thay `83` bằng phiên bản thực tế |
| `php.ini` | `/usr/local/php83/lib/php.ini` | File chính, có thể bị CustomBuild ghi đè |
| Thư mục ini phụ | `/usr/local/php83/lib/php.conf.d/` | Nạp theo thứ tự alphabet |
| Ini do DA sinh | `10-directadmin.ini`, `50-webapps.ini` | **Không sửa trực tiếp** |
| FPM global config | `/usr/local/php83/etc/php-fpm.conf` | Cấu hình master |
| FPM pool theo user | `/usr/local/directadmin/data/users/USER/php/php-fpm83.conf` | Một pool/user/phiên bản |
| Socket FPM | `/usr/local/php83/sockets/USER.sock` | Web server nối vào đây |
| Log FPM | `/usr/local/php83/var/log/php-fpm.log` | Log master/pool |
| Service FPM | `php-fpm83` | `systemctl status php-fpm83` |
| Template gốc | `/usr/local/directadmin/data/templates/` | Không sửa |
| Template tùy biến | `/usr/local/directadmin/data/templates/custom/` | Sửa ở đây |
| Custom token toàn cục | `.../templates/custom/php-fpm.conf.custom1` | Áp dụng mọi user, mọi phiên bản |
| OPcache tùy biến | `/usr/local/directadmin/custombuild/custom/opcache/opcache.ini` | Nguồn cho mọi phiên bản |
| Web server | `/etc/httpd/`, `/etc/nginx/`, `/usr/local/lsws/` | Tùy `webserver=` |

> [!IMPORTANT]
> Đừng sửa file trong `/usr/local/directadmin/data/users/USER/php/` rồi mong nó tồn tại mãi.
> `da build rewrite_confs` sẽ sinh lại từ template. Muốn bền, hãy sửa **template custom**
> hoặc dùng token `CUSTOM1`/`CUSTOM2` trong giao diện Custom Httpd Config.

### 3.2. Các lệnh CustomBuild cần thuộc

```bash
# Xem toàn bộ tùy chọn và giá trị hiện tại
da build opt_help | grep -E 'php|opcache|redis|webserver' | head -40

# Danh sách phiên bản/software
da build versions | head -40

# File cấu hình nào đang được dùng cho PHP
da build used_configs | grep -i 'php\|opcache'

# Đọc/ghi một tùy chọn
da build set php1_mode php-fpm
da build set php1_release 8.3

# Build lại PHP (lâu, có thể 5–20 phút)
da build php

# Sinh lại toàn bộ cấu hình web/FPM, không build lại binary
da build rewrite_confs

# Xem giá trị trong directadmin.conf
da config-get php_fpm_max_children_default
```

`options.conf` thường có dạng:

```ini
php1_release=8.3
php1_mode=php-fpm
php2_release=8.2
php2_mode=php-fpm
php3_release=no
php4_release=no
webserver=nginx_apache
opcache=yes
php_ini=yes
php_htscanner=no
secure_php=yes
```

Không cần nhớ hết. Chỉ cần nhớ: **`options.conf` là nguồn**, `da build set` sửa nguồn, `da build php` biên dịch, `da build rewrite_confs` sinh cấu hình.

### 3.3. `da build php` khác `da build rewrite_confs` thế nào?

| Lệnh | Làm gì | Khi nào dùng | Rủi ro |
|---|---|---|---|
| `da build php` | Tải và biên dịch PHP, cài extension | Đổi phiên bản, thêm extension, đổi configure | Cao: lâu, tốn RAM/disk, có thể ghi đè `php.ini` |
| `da build rewrite_confs` | Sinh lại vhost, pool FPM, config web | Đổi `max_children`, template, timeout | Trung bình: reload dịch vụ, có thể ghi đè file sinh tự động |
| `da build opcache` | Build/cấu hình OPcache | Bật/tắt OPcache | Thấp–trung bình |
| `da build php_redis` | Build extension Redis cho PHP | Bật Redis | Thấp–trung bình |
| `da build redis` | Cài Redis server | Cần object cache/session | Trung bình: thêm service, RAM |

> [!WARNING]
> `da build php` có thể mất 5–20 phút tùy cấu hình và **không nên bị ngắt giữa chừng**.
> Chạy trong `tmux`/`screen`, kiểm tra dung lượng disk và RAM trước. Trên server đông
> người dùng, hãy làm trong cửa sổ bảo trì và có phương án rollback phiên bản.

### 3.4. Kiểm tra phiên bản thực tế, không tin mỗi giao diện

```bash
# CLI của từng phiên bản
for b in /usr/local/php*/bin/php; do
  [ -x "$b" ] && "$b" -v | head -1
done

# PHP mà web đang dùng (tạo file tạm, xóa sau khi kiểm tra)
# /home/USER/domains/example.com/public_html/php-info.php
# <?php phpinfo();
```

Đường dẫn `php.ini` trong `phpinfo()` mới là sự thật của **FPM**. CLI có thể dùng file khác, đặc biệt khi `php_ini` hoặc `PHP_INI_SCAN_DIR` bị đổi.

---

## 4. Chọn phiên bản PHP và handler

### 4.1. Phiên bản

Tính đến tháng 10/2026:

| Nhánh | Trạng thái | Hỗ trợ bảo mật đến | Khuyến nghị |
|---|---|---|---|
| 8.5 | Đang hoạt động | 31/12/2029 | Chỉ khi toàn bộ plugin/tooling đã tương thích |
| 8.4 | Đang hoạt động | 31/12/2028 | Ứng dụng mới, đã test kỹ |
| 8.3 | Ổn định | 31/12/2027 | **Mặc định cho production** |
| 8.2 | Sắp EOL | 31/12/2026 | Vá ngay, lên 8.3 trong 1–2 tháng |
| ≤ 8.1 | EOL | Đã hết | Nâng bắt buộc, không có bản vá upstream |

Luôn kiểm tra lại tại <https://www.php.net/supported-versions.php>. Bảng này chỉ là ảnh chụp.

### 4.2. Handler

| Handler | Cách chạy | Ưu điểm | Nhược điểm | Phù hợp |
|---|---|---|---|---|
| **PHP-FPM** | Daemon riêng, web server qua socket | Nhanh, OPcache tốt, chạy đúng user, cách ly pool | Tốn RAM theo worker, cấu hình phức tạp hơn | **Mặc định cho DirectAdmin** |
| `mod_php` | Module trong Apache | Tương thích `.htaccess`, đơn giản | PHP chạy chung user apache, RAM cao, khó cách ly | Server một ứng dụng, không shared hosting |
| FastCGI | Tiến trình FastCGI | Có OPcache, chạy đúng user | Cũ, ít linh hoạt, DA khuyến nghị FPM | Hệ thống cũ |
| LSPHP | LiteSpeed/OpenLiteSpeed | Nhanh, tích hợp LSCache | Phụ thuộc webserver, hành vi khác | LiteSpeed/OLS/CloudLinux |
| suPHP | CGI mỗi request | Cách ly user | Rất chậm, đã lỗi thời | Không dùng |

Với DirectAdmin, mặc định hiện tại là **PHP-FPM**. Nếu server đang dùng `mod_php` vì lý do lịch sử, chuyển sang FPM thường là thay đổi lớn nhất về hiệu năng và bảo mật — nhưng phải test kỹ `.htaccess`, `php_value`, và đường dẫn upload.

### 4.3. Chuyển handler/phiên bản

```bash
# Chuyển PHP 1 sang FPM
da build set php1_mode php-fpm
da build set php_htscanner yes     # nếu ứng dụng cần php_value trong .htaccess
da build php
da build rewrite_confs

# Đổi phiên bản mặc định
da build set php1_release 8.3
da build php
da build rewrite_confs

# Kiểm tra
/usr/local/php83/bin/php -v
systemctl status php-fpm83 --no-pager
```

Sau khi đổi, kiểm tra một domain thật:

```bash
curl -sI https://example.com/ | head -1
curl -s https://example.com/ | head -5
tail -n 50 /usr/local/php83/var/log/php-fpm.log
```

### 4.4. Nhiều phiên bản PHP: lợi và giá

DirectAdmin cho phép chạy nhiều phiên bản song song (`php1`–`php9`). Mỗi phiên bản hoạt động sẽ có:

- Một FPM master riêng.
- Một vùng OPcache riêng.
- Một bộ worker riêng.
- Một bộ extension/ini riêng.

Hệ quả: bật 4 phiên bản "cho chắc" làm tăng RAM nền và tăng bề mặt cập nhật bảo mật. Chỉ bật phiên bản thực sự cần.

```bash
# Kiểm tra selector phiên bản cho user
da config-get php_version_selector

# Liệt kê lựa chọn của một domain
grep -E '^php[0-9]_select=' /usr/local/directadmin/data/users/USER/domains/example.com.conf
```

> [!TIP]
> Chính sách thực dụng: **8.3 là mặc định**, **8.4 cho ứng dụng đã test**, **8.2 chỉ để chờ nâng cấp**, **8.1 trở xuống là nợ kỹ thuật phải trả**. Đừng giữ 5.6/7.x chỉ vì một plugin không ai còn bảo trì.

---
## 5. PHP-FPM: tính đúng số worker

Đây là phần dễ gây sự cố nhất. DirectAdmin mặc định khá "tiết kiệm" và điều đó tốt cho server đông người dùng, nhưng con số mặc định không phù hợp với mọi máy.

### 5.1. Một pool cho mỗi user, không phải mỗi domain

DirectAdmin sinh **một pool FPM cho mỗi user, cho mỗi phiên bản PHP**. Tất cả domain và subdomain của user đó dùng chung pool, chung socket, chung giới hạn worker.

Ví dụ pool mặc định:

```ini
; /usr/local/directadmin/data/users/USER/php/php-fpm83.conf
[USER]
user = USER
group = USER
listen = /usr/local/php83/sockets/USER.sock
listen.owner = USER
listen.group = apache
listen.mode = 660

pm = ondemand
pm.max_children = 10
pm.process_idle_timeout = 20
pm.max_requests = 500

php_admin_value[sendmail_path] = /usr/sbin/sendmail -t -i -f USER@example.com
php_value[session.save_path] = /home/USER/tmp
php_admin_value[open_basedir] = /home/USER:/tmp:/var/lib/php/sessions
```

Hệ quả quan trọng:

- 12 domain trong cùng một tài khoản chia nhau 10 worker. Một site bị crawl có thể làm nghẽn cả 12 site.
- Muốn cách ly theo domain, phải tách tài khoản hoặc dùng cơ chế isolated FPM (mục 5.6).
- `pm.max_children` là **giới hạn đồng thời**, không phải "số worker luôn chạy" khi dùng `ondemand`.

### 5.2. `ondemand`, `dynamic` hay `static`?

| Chế độ | Cách chạy | Ưu | Nhược | Dùng khi |
|---|---|---|---|---|
| `ondemand` | Chỉ tạo worker khi có request, chết sau `process_idle_timeout` | Tiết kiệm RAM nhất | Request đầu tiên sau thời gian rảnh bị chậm hơn | **Shared hosting, nhiều tài khoản ít traffic** |
| `dynamic` | Giữ một số worker tối thiểu, co giãn theo tải | Cân bằng độ trễ và RAM | Tốn RAM nền, cần tính `start_servers` | Server một vài site traffic đều |
| `static` | Luôn giữ đúng `max_children` worker | Không có độ trễ khởi tạo | Tốn RAM tối đa, dễ OOM nếu tính sai | Rất ít trường hợp, server chuyên dụng |

DirectAdmin dùng `ondemand` mặc định. **Giữ nguyên cho shared hosting** là quyết định đúng trong đa số trường hợp. Chỉ chuyển `dynamic` khi:

- Bạn quản lý một vài site lớn, traffic đều.
- Đã đo được độ trễ khởi tạo worker ảnh hưởng rõ đến p95.
- Đã tính được RAM cho `start_servers` + `max_spare_servers`.

### 5.3. Công thức tính `max_children`

Đừng dùng công thức `RAM / memory_limit`. `memory_limit` là giới hạn tối đa mỗi request, không phải RAM thực tế của worker.

Cần ba số:

1. **RAM khả dụng cho PHP**: tổng RAM trừ OS, database, Redis, page cache và phần dự phòng.
2. **RSS trung bình của một worker** khi đang xử lý request thật.
3. **Số user hoặc số request đồng thời tại đỉnh**.

Đo RSS:

```bash
# RSS trung bình của worker FPM đang chạy (KB -> MB)
ps -eo rss,comm | awk '/php-fpm/ {s+=$1; n++} END {
  if (n) printf "%d worker, trung binh %.1f MB, tong %.1f MB\n", n, s/n/1024, s/1024
}'

# Top worker ngốn RAM nhiều nhất
ps -eo pid,user,rss,%cpu,etime,cmd --sort=-rss | grep 'php-fpm' | head -10
```

Công thức thực dụng:

```text
RAM_cho_PHP     = RAM_tong - RAM_OS - RAM_DB - RAM_Redis - du_phong
workers_toi_da  = RAM_cho_PHP / RSS_trung_binh
max_children    = lam_tron_xuong(workers_toi_da / so_user_hoat_dong_dong_thoi)
```

Ví dụ với server 16 GB:

| Thành phần | RAM |
|---|---|
| Tổng | 16 GB |
| OS + panel + web server | 2 GB |
| MySQL/MariaDB | 4 GB |
| Redis + page cache + dự phòng | 2 GB |
| **Còn cho PHP** | **8 GB** |

Nếu RSS trung bình 45 MB:

```text
workers_toi_da = 8192 / 45 ≈ 182 worker
```

Nếu giả định 60 user hoạt động đồng thời vào giờ cao điểm:

```text
max_children mỗi user ≈ 182 / 60 ≈ 3
```

Nếu tất cả 180 user cùng hoạt động:

```text
max_children mỗi user ≈ 182 / 180 ≈ 1
```

Đây là lý do **không thể đặt 10 cho tất cả user** trên server 180 tài khoản rồi hy vọng an toàn. `ondemand` giúp giảm xác suất tất cả cùng spawn, nhưng không loại bỏ khả năng đó khi có crawler hoặc tấn công.

> [!IMPORTANT]
> DirectAdmin không có giới hạn tổng worker toàn server. Tổng `max_children` của các pool
> là **trần lý thuyết**, có thể vượt RAM nếu mọi user cùng bị tấn công. Hãy đặt
> `max_children` vừa phải, theo dõi RSS, và dùng cgroup `MemoryMax` làm chốt chặn cuối
> nếu server thật sự đông.

### 5.4. Bảng gợi ý nhanh

| RAM server | Số user | RSS/worker | Gợi ý `max_children` mặc định | Ghi chú |
|---|---|---|---|---|
| 8 GB | 50–80 | 40–50 MB | 2–3 | Ưu tiên ondemand, dè chừng MySQL |
| 16 GB | 100–200 | 40–55 MB | 3–5 | Override 10–15 cho user Woo/busy |
| 32 GB | 200–400 | 50–60 MB | 5–8 | Theo dõi tổng worker, cân nhắc isolated FPM |
| 64 GB | 400–800 | 50–70 MB | 8–12 | Cần monitoring và cgroup |

Đây là điểm khởi đầu, không phải chân lý. RSS thực tế của WordPress có thể từ 30 MB (site tối giản) đến 120 MB (WooCommerce nhiều plugin). Đo trước khi chốt.

### 5.5. Đặt giới hạn toàn cục và theo user

**Toàn cục** (áp dụng cho user chưa có override):

```bash
da config-set php_fpm_max_children_default 4
systemctl restart directadmin
da build rewrite_confs

# Restart đúng service của từng phiên bản đang dùng
systemctl restart php-fpm83
# systemctl restart php-fpm84
```

Kiểm tra:

```bash
da config-get php_fpm_max_children_default
grep -H 'pm.max_children' /usr/local/directadmin/data/users/*/php/php-fpm83.conf | head
```

**Theo domain/user** trong giao diện:

1. Admin Level → Custom Httpd Configurations.
2. Chọn domain → chọn `php-fpm83`.
3. Trong ô `CUSTOM1`, thêm:

```ini
|?MAX_CHILDREN=15|
```

4. Lưu, chạy `da build rewrite_confs`, restart `php-fpm83`.

**Theo template toàn cục** (bền qua rebuild):

```bash
# Template custom1 áp dụng cho mọi user, mọi phiên bản
install -d -m 755 /usr/local/directadmin/data/templates/custom
cat > /usr/local/directadmin/data/templates/custom/php-fpm.conf.custom1 <<'EOF'
|?MAX_CHILDREN=5|
EOF

da build rewrite_confs
systemctl restart php-fpm83
```

Cẩn thận: template toàn cục sẽ áp cho cả user cần nhiều worker. Sau khi đặt, kiểm tra file pool thực tế của vài user.

### 5.6. Isolated PHP-FPM: cách ly tốt hơn, RAM nhiều hơn

Từ DirectAdmin 1.690, mỗi user có thể có một FPM master riêng trong jail:

```bash
da config-set isolated_fpm 1
systemctl restart directadmin
da taskq --run 'action=rewrite&value=httpd'
```

Chỉ áp dụng cho user bật **Jailed**. Ưu điểm:

- Cách ly hoàn toàn giữa các user.
- Có thể áp `MemoryMax` riêng cho từng user.
- Phù hợp môi trường shared hosting cần bảo mật cao.

Giá phải trả:

- Mỗi master rảnh tốn khoảng **20 MB**.
- 200 user × 20 MB ≈ **4 GB** chỉ để giữ master.
- Mỗi user dùng nhiều phiên bản PHP sẽ có nhiều master hơn.
- OPcache và worker trở thành riêng lẻ, không chia sẻ.

Không bật isolated FPM chỉ vì "nghe hay". Bật khi cần cách ly hoặc khi đã có đủ RAM và monitoring.

### 5.7. Slow log và trạng thái pool

Thêm vào `CUSTOM1` của domain hoặc template custom:

```ini
request_slowlog_timeout = 5s
slowlog = /home/USER/.php/php-fpm-slow.log
request_terminate_timeout = 60s
```

- `request_slowlog_timeout`: ghi stack trace khi request chạy lâu hơn ngưỡng.
- `slowlog`: đặt trong home của user để user đọc được, tránh ghi vào thư mục hệ thống.
- `request_terminate_timeout`: kill request treo, tránh worker bị giữ vĩnh viễn. Phải **lớn hơn** `max_execution_time` của ứng dụng.

Đọc slow log:

```bash
tail -n 100 /home/USER/.php/php-fpm-slow.log
```

Muốn xem trạng thái pool, bật `pm.status_path` (chỉ trên môi trường kiểm soát):

```ini
pm.status_path = /fpm-status
```

Rồi gọi qua socket:

```bash
# Debian/Ubuntu: apt install libfcgi-bin
# RHEL/Rocky: dnf install fcgi
SCRIPT_NAME=/fpm-status SCRIPT_FILENAME=/fpm-status \
  cgi-fcgi -bind -connect /usr/local/php83/sockets/USER.sock
```

Không mở status ra Internet. Nó lộ số worker, queue, tên pool và thông tin nội bộ.

### 5.8. Dấu hiệu cần xử lý trong log

| Dòng log | Nghĩa | Việc cần làm |
|---|---|---|
| `server reached max_children setting` | Pool hết worker, request phải xếp hàng | Tăng `max_children` cho user đó **nếu còn RAM**, hoặc tối ưu app/query |
| `pool ... seems busy` | Tốc độ spawn không theo kịp | Tăng `pm.max_children`, xem lại traffic bất thường |
| `child ... exited on signal 11` | Segfault — lỗi extension/PHP | Kiểm tra extension, core dump, phiên bản PHP |
| `Killed` / `out of memory` | OOM killer | Giảm `max_children`, tăng RAM, tìm worker ngốn RAM |
| `Unable to open primary script` | Sai docroot hoặc `open_basedir` | Kiểm tra vhost và quyền file |
| `Permission denied` khi nối socket | Sai owner/group/mode hoặc SELinux | So sánh với pool khác đang chạy |

---

## 6. OPcache: món hời lớn nhất, nhưng đừng tham

OPcache lưu bytecode đã biên dịch trong shared memory. Không có nó, mỗi request phải đọc file, parse và compile lại. Với WordPress, bật OPcache thường là thay đổi đơn lẻ có lợi nhất về CPU.

### 6.1. Kiểm tra OPcache đã bật chưa

```bash
# CLI (lưu ý: CLI có cache riêng, có thể đang tắt)
/usr/local/php83/bin/php -v | grep -i 'Zend OPcache'
/usr/local/php83/bin/php -i | grep -E 'opcache.enable|opcache.memory_consumption|opcache.max_accelerated_files'

# Qua web: tạo file tạm, kiểm tra rồi xóa
cat > /home/USER/domains/example.com/public_html/opcache-check.php <<'EOF'
<?php
header('Content-Type: application/json');
$s = opcache_get_status(false);
echo json_encode([
    'enabled'      => $s['opcache_enabled'] ?? false,
    'used_mb'      => round(($s['memory_usage']['used_memory'] ?? 0) / 1048576, 1),
    'free_mb'      => round(($s['memory_usage']['free_memory'] ?? 0) / 1048576, 1),
    'cached_files' => $s['opcache_statistics']['num_cached_scripts'] ?? 0,
    'hits'         => $s['opcache_statistics']['hits'] ?? 0,
    'misses'       => $s['opcache_statistics']['misses'] ?? 0,
], JSON_PRETTY_PRINT);
EOF
curl -s https://example.com/opcache-check.php
rm -f /home/USER/domains/example.com/public_html/opcache-check.php
```

Nếu `opcache_enabled` là `false`, bật bằng CustomBuild:

```bash
da build set opcache yes
da build opcache

systemctl restart php-fpm83
```

Kiểm tra lại:

```bash
/usr/local/php83/bin/php -m | grep -i 'Zend OPcache'
```

### 6.2. Cấu hình mẫu

Tạo file riêng, đừng sửa `10-directadmin.ini`:

```bash
cat > /usr/local/php83/lib/php.conf.d/99-opcache-tuning.ini <<'EOF'
; OPcache tuning — xem README chương 6
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
EOF

systemctl restart php-fpm83
```

Giải thích:

| Directive | Ý nghĩa | Gợi ý |
|---|---|---|
| `opcache.memory_consumption` | Shared memory cho bytecode (MB) | 128–512 MB tùy số site/plugin |
| `opcache.interned_strings_buffer` | Bộ nhớ cho interned strings (MB) | 16–64 MB |
| `opcache.max_accelerated_files` | Số file tối đa | 16229–65407; PHP làm tròn lên mốc nguyên tố |
| `opcache.max_wasted_percentage` | % bộ nhớ lãng phí trước khi restart | 5–10% |
| `opcache.validate_timestamps` | Kiểm tra file thay đổi | `1` cho shared hosting |
| `opcache.revalidate_freq` | Giây giữa hai lần kiểm tra | 60 giây; giảm khi deploy liên tục |
| `opcache.save_comments` | Giữ comment trong bytecode | **`1`** nếu dùng annotation/Doctrine |
| `opcache.jit` | Bật JIT | `off` mặc định; chỉ bật sau khi benchmark |

### 6.3. Cấp bao nhiêu bộ nhớ?

| Quy mô | `memory_consumption` | `interned_strings_buffer` | `max_accelerated_files` |
|---|---|---|---|
| Vài site nhỏ, ít plugin | 128 MB | 16 MB | 16229 |
| 20–100 site WordPress | 256 MB | 32 MB | 32531 |
| Nhiều plugin/Woo/Laravel lớn | 512 MB | 64 MB | 65407 |
| Nhiều phiên bản PHP | Mỗi phiên bản một vùng riêng | | |

Theo dõi `used_memory` và `free_memory`. Nếu `free_memory` gần 0 và `oom_restarts` tăng, tăng dung lượng hoặc giảm số file cache. Nếu `used_memory` chỉ 40/256 MB, bạn đang lãng phí RAM — hạ xuống.

> [!WARNING]
> OPcache dùng shared memory **theo từng FPM master**, không phải theo từng pool.
> Bật 4 phiên bản PHP với 256 MB mỗi phiên bản là 1 GB RAM nền. Bật isolated FPM
> với 180 user và 256 MB mỗi master là công thức OOM: hãy giảm mạnh dung lượng
> OPcache cho isolated FPM, hoặc chỉ bật isolated cho nhóm user thật sự cần.

### 6.4. `validate_timestamps=0`: nhanh hơn, nhưng đừng quên deploy

`opcache.validate_timestamps=0` bỏ hẳn việc `stat()` file mỗi request. Đây là tối ưu tốt cho hệ thống deploy bất biến (immutable), nhưng trên shared hosting:

- User sửa file qua FTP/File Manager → **thay đổi không có hiệu lực** cho đến khi OPcache reset.
- Plugin cập nhật → có thể chạy code cũ.
- Debug trở nên khó hiểu.

Nếu dùng `0`, phải có bước reset trong quy trình deploy:

```bash
# Cách chắc chắn nhất: restart FPM (xóa shared memory)
systemctl restart php-fpm83

# Hoặc gọi opcache_reset() từ CLI có bật opcache.enable_cli
/usr/local/php83/bin/php -d opcache.enable_cli=1 -r 'var_dump(opcache_reset());'
```

Lưu ý: `opcache_reset()` từ CLI chỉ reset cache CLI, **không** reset cache của FPM. Muốn reset cache FPM phải gọi từ trong FPM (web) hoặc restart service.

Với shared hosting, khuyến nghị:

```ini
opcache.validate_timestamps=1
opcache.revalidate_freq=60
```

Chấp nhận chậm hơn một chút để user sửa file là thấy thay đổi trong tối đa 60 giây.

### 6.5. JIT: chỉ bật khi có số liệu

JIT (Just-In-Time) biên dịch opcode thành mã máy. Nó hữu ích cho tác vụ CPU-bound như tính toán khoa học, xử lý ảnh, game server. Với WordPress/WooCommerce — nơi thời gian chủ yếu nằm ở I/O, database và network — JIT thường **không cải thiện TTFB** và làm tăng RAM.

Nếu vẫn muốn thử:

```ini
opcache.jit=tracing
opcache.jit_buffer_size=64M
```

Đo trên staging với cùng workload. Nếu p95 không giảm ≥ 5% và RAM tăng, tắt lại:

```ini
opcache.jit=off
opcache.jit_buffer_size=0
```

### 6.6. Preload: không dành cho shared hosting

`opcache.preload` nạp trước file PHP khi master khởi động. Nó có thể giảm cold-start cho framework lớn, nhưng:

- Cần quyền root và `opcache.preload_user`.
- Preload script chạy với quyền hệ thống, không phải user.
- File thay đổi phải restart FPM.
- Trên shared hosting nhiều user, preload chung là rủi ro bảo mật và dễ sai đường dẫn.

Bỏ qua preload trừ khi bạn kiểm soát toàn bộ code và có quy trình deploy rõ ràng.

### 6.7. Đọc chỉ số OPcache

Các chỉ số quan trọng:

| Chỉ số | Ý nghĩa | Ngưỡng |
|---|---|---|
| `hits / (hits + misses)` | Tỷ lệ cache hit | > 99% là tốt; < 95% cần xem |
| `free_memory` | Bộ nhớ còn trống | > 10% dung lượng |
| `wasted_memory` | Bộ nhớ bị phân mảnh | < 10% |
| `oom_restarts` | Số lần restart vì hết bộ nhớ | 0; tăng là dấu hiệu thiếu |
| `hash_restarts` | Số lần restart vì hết bảng hash | 0; tăng là thiếu `max_accelerated_files` |
| `num_cached_scripts` | Số file đã cache | So với `max_accelerated_files` |

Nếu `hash_restarts` tăng, tăng `max_accelerated_files` lên mốc cao hơn (32531 → 65407). Nếu `oom_restarts` tăng, tăng `memory_consumption` hoặc giảm số site/plugin trên cùng master.

### 6.8. Ba lỗi thường gặp

1. **Bật OPcache nhưng kiểm tra bằng CLI.** `opcache.enable_cli=0` là mặc định; `php -v` vẫn hiện "Zend OPcache" nhưng cache CLI không đại diện cho web. Kiểm tra bằng `phpinfo()` hoặc script web.
2. **Sửa `10-directadmin.ini`.** File này do CustomBuild sinh lại. Dùng `99-custom.ini` hoặc `custom/opcache/opcache.ini`.
3. **Đặt `memory_consumption=1024` cho mọi phiên bản.** Tốn RAM, không nhanh hơn nếu cache không dùng hết. Đo `used_memory` rồi cấp vừa đủ.

---

## 7. Redis, session và object cache

Redis hữu ích khi ứng dụng dùng nhiều query lặp lại (WooCommerce, Laravel, Magento) hoặc cần session dùng chung giữa nhiều node. Redis **không** thay thế việc tối ưu query, và không làm chậm đi nếu cấu hình đúng — nhưng nếu cấu hình sai, nó là điểm lỗi mới.

### 7.1. Cài Redis server và extension

```bash
da build set redis yes
da build redis

da build set php_redis yes
da build php_redis

systemctl status redis --no-pager
redis-cli ping
```

Kiểm tra extension:

```bash
/usr/local/php83/bin/php -m | grep -i redis
```

### 7.2. Redis theo user trên DirectAdmin

DirectAdmin quản lý Redis theo user. Mỗi user được bật Redis sẽ có socket riêng, thường là:

```text
/home/USER/.redis/redis.sock
```

Bật trong gói/tài khoản:

- Admin Level → User Level → package/user → bật `redis=ON`.
- User Level → Advanced Features → Redis → lấy đường dẫn socket.

Kiểm tra:

```bash
ls -l /home/USER/.redis/redis.sock
redis-cli -s /home/USER/.redis/redis.sock ping
```

### 7.3. WordPress + Redis Object Cache

Cài plugin **Redis Object Cache**, sau đó thêm vào `wp-config.php` (trước dòng `require_once ABSPATH . 'wp-settings.php';`):

```php
define('WP_REDIS_SCHEME', 'unix');
define('WP_REDIS_PATH', '/home/USER/.redis/redis.sock');
define('WP_REDIS_PREFIX', 'wp_example_');
define('WP_CACHE', true);
```

Trong plugin, chọn **Enable Object Cache**. Kiểm tra trạng thái `Connected`.

Lưu ý:

- `WP_REDIS_PREFIX` phải khác nhau giữa các site dùng chung một Redis instance/DB.
- Nếu dùng TCP thay vì socket, đặt `WP_REDIS_HOST`, `WP_REDIS_PORT`, `WP_REDIS_PASSWORD`, `WP_REDIS_DATABASE`.
- Redis Object Cache không phải page cache. Nó không thay thế cache HTML/CDN.

### 7.4. Laravel

`.env` mẫu khi dùng Redis trên cùng máy:

```dotenv
CACHE_STORE=redis
SESSION_DRIVER=redis
QUEUE_CONNECTION=redis
REDIS_CLIENT=phpredis
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_PASSWORD=mat-khau-manh
REDIS_DB=0
REDIS_CACHE_DB=1
```

Nếu dùng socket riêng của DirectAdmin, cấu hình `config/database.php` theo kiểu:

```php
'redis' => [
    'client' => 'phpredis',
    'options' => [
        'scheme' => 'unix',
        'path'   => '/home/USER/.redis/redis.sock',
    ],
    'default' => ['database' => 0],
    'cache'   => ['database' => 1],
],
```

Kiểm tra:

```bash
/usr/local/php83/bin/php artisan cache:clear
/usr/local/php83/bin/php artisan config:clear
```

### 7.5. Session trong Redis: lợi và hại

Lợi:

- Session dùng chung giữa nhiều web node.
- Không phụ thuộc file trong `/home/USER/tmp`.
- Tốc độ đọc/ghi tốt hơn file trên đĩa chậm.

Hại:

- Redis chết → user bị đăng xuất hàng loạt.
- Cấu hình `maxmemory-policy` sai có thể evict session.
- Tăng độ phức tạp khi backup/khôi phục.

Cấu hình session Redis (đặt trong pool hoặc `php.ini`):

```ini
session.save_handler = redis
session.save_path = "tcp://127.0.0.1:6379?auth=MAT_KHAU&database=2"
redis.session.locking_enabled = 1
redis.session.lock_expire = 60
```

Với socket:

```ini
session.save_path = "unix:///home/USER/.redis/redis.sock?database=2"
```

`redis.session.locking_enabled=1` giúp tránh race condition khi nhiều request cùng ghi session, nhưng thêm độ trễ. Chỉ bật khi ứng dụng cần.

> [!WARNING]
> Không dùng `maxmemory-policy allkeys-lru` cho instance vừa chứa session vừa chứa cache.
> Redis có thể xóa session để lấy chỗ, gây đăng xuất ngẫu nhiên. Tách instance/DB, hoặc
> dùng policy không evict session (`noeviction` cho session, `allkeys-lru` cho cache riêng).

### 7.6. Bảo mật Redis

- **Không** mở Redis ra Internet. Bind `127.0.0.1` hoặc chỉ socket Unix.
- Đặt `requirepass` nếu dùng TCP, ngay cả trong mạng nội bộ.
- Phân quyền file socket: chỉ user sở hữu và nhóm web được đọc.
- Giới hạn `maxmemory` để Redis không ăn hết RAM.
- Không dùng chung một DB cho nhiều ứng dụng nếu không có prefix rõ ràng.

Kiểm tra nhanh:

```bash
ss -lntp | grep 6379
redis-cli -s /home/USER/.redis/redis.sock info memory | grep -E 'used_memory_human|maxmemory_human|maxmemory_policy'
redis-cli -s /home/USER/.redis/redis.sock --latency
```

### 7.7. APCu: cẩn thận trên shared hosting

APCu là cache userland trong shared memory, rất nhanh cho biến/array. Tuy nhiên:

- DirectAdmin không có sẵn tùy chọn build APCu trong danh sách extension chính thức; phải tự biên dịch.
- APCu dùng shared memory **chung cho tất cả worker của cùng một FPM master**. Trên shared hosting, nhiều user có thể nhìn thấy dữ liệu cache của nhau nếu trùng key.
- APCu không thay thế OPcache. OPcache cache bytecode; APCu cache dữ liệu ứng dụng.

Khuyến nghị:

- Shared hosting nhiều user: **ưu tiên Redis theo user**, hoặc chỉ bật APCu khi đã bật isolated FPM.
- Server chuyên dụng một ứng dụng: APCu là lựa chọn tốt, nhẹ hơn Redis.
- Luôn dùng prefix theo site: `apcu_store('site_a:'.$key, ...)`.

Cấu hình tham khảo (chỉ sau khi đã compile extension):

```ini
extension=apcu.so
apc.enabled=1
apc.shm_size=64M
apc.ttl=0
apc.gc_ttl=3600
apc.enable_cli=0
```

### 7.8. Redis không chữa được query chậm

Trước khi thêm Redis, kiểm tra xem thời gian request đang đi đâu:

```bash
# Nếu có MySQL/MariaDB
mysql -e 'SHOW FULL PROCESSLIST' | head -20
# Bật slow query log nếu chưa có, rồi đọc
mysqldumpslow -s t /var/log/mysql/slow.log | head -20
```

Nếu 70% thời gian nằm ở database, Redis object cache có thể giúp giảm query lặp lại, nhưng query chậm chưa được tối ưu vẫn là gốc rễ. Đừng dùng Redis để che một query `SELECT *` không index.

---
## 8. php.ini: chỉnh đúng chỗ, đúng liều

### 8.1. Năm tầng cấu hình

| Tầng | File/vị trí | Ai kiểm soát | Ghi đè được không |
|---|---|---|---|
| Global | `/usr/local/php83/lib/php.ini` | Root/CustomBuild | Bị `da build php` ghi đè nếu `php_ini=yes` |
| Drop-in toàn cục | `/usr/local/php83/lib/php.conf.d/*.ini` | Root | Nạp alphabet, sau `php.ini` |
| Per-user pool | `/usr/local/directadmin/data/users/USER/php/php-fpm83.conf` | Root/DA | Sinh lại bởi `rewrite_confs` |
| Per-domain/path | `php.conf.d/30-example.com.ini` với `[HOST=]`/`[PATH=]` | Root | Chỉ một số directive |
| Per-directory | `.user.ini` trong webroot | User | Chỉ directive `PHP_INI_PERDIR`/`PHP_INI_USER` |

Thứ tự thông thường (từ thấp đến cao): `php.ini` → drop-in → pool `php_value` → `.user.ini` (nếu được phép) → `ini_set()` trong code (chỉ directive `PHP_INI_ALL`).

`php_admin_value` **không thể** bị ghi đè bởi `.user.ini` hay `ini_set()`; nó đứng trên cùng trong phạm vi pool. Dùng nó cho giới hạn bảo vệ server. Dùng `php_value` cho thứ chỉ là tiện ích.

### 8.2. Nên sửa file nào?

| Mục đích | Sửa ở đâu |
|---|---|
| Áp dụng cho mọi user, mọi domain của một phiên bản PHP | `php.conf.d/99-php-tuning.ini` |
| Áp dụng cho một user | `php-fpmXX.conf` qua `CUSTOM1`/`CUSTOM2` hoặc template custom |
| Áp dụng cho một domain | `php.conf.d/30-example.com.ini` với `[HOST=example.com]` |
| Áp dụng cho một thư mục, user tự chỉnh | `.user.ini` (nếu `user_ini.filename` được bật) |
| Cấu hình OPcache | `99-opcache-tuning.ini` hoặc `custom/opcache/opcache.ini` |
| Cấu hình do DA sinh | **Không sửa** `10-directadmin.ini`, `50-webapps.ini` |

### 8.3. Bộ cấu hình tham khảo

```ini
; /usr/local/php83/lib/php.conf.d/99-php-tuning.ini
; Chỉ chỉnh sau khi đã đo baseline. Không copy cho mọi phiên bản.

; --- Bộ nhớ và thời gian ---
memory_limit = 256M
max_execution_time = 60
max_input_time = 60

; --- Form/upload ---
max_input_vars = 5000
post_max_size = 80M
upload_max_filesize = 64M
max_file_uploads = 20

; --- Đường dẫn ---
realpath_cache_size = 4096k
realpath_cache_ttl = 600

; --- Lỗi ---
expose_php = Off
display_errors = Off
display_startup_errors = Off
log_errors = On
error_reporting = E_ALL & ~E_DEPRECATED

; --- Output ---
output_buffering = 4096
zlib.output_compression = Off

; --- Session ---
session.use_strict_mode = 1
session.use_only_cookies = 1
session.cookie_httponly = 1
session.cookie_samesite = Lax

; --- Khác ---
allow_url_include = Off
date.timezone = Asia/Ho_Chi_Minh
```

Không đưa `error_log` vào file toàn cục nếu mỗi user cần log riêng. Đặt trong pool:

```ini
php_admin_value[error_log] = /home/USER/.php/php-error.log
php_admin_flag[log_errors] = on
```

### 8.4. Giải thích từng nhóm

#### `memory_limit`

- Đây là giới hạn **mỗi request**, không phải RAM của worker.
- WordPress thông thường: 256 MB. WooCommerce nhiều plugin: 512 MB. Laravel: 256–512 MB.
- Đặt 1024 MB cho tất cả là lãng phí và che giấu memory leak.
- Đo thực tế:

```php
<?php
echo memory_get_peak_usage(true) / 1048576, " MB\n";
```

Hoặc trong WordPress, bật `WP_DEBUG` ở staging và xem `memory_get_peak_usage()`.

> [!CAUTION]
> Không đặt `memory_limit = -1` trên production. Ngoại lệ duy nhất là biện pháp tạm
> thời ứng phó PHP2Shell, và **bắt buộc** phải có giới hạn cgroup bên ngoài. Xem
> [update-php-cve](https://github.com/fixnhanh-linux/update-php-cve) chương 2.

#### `max_execution_time`

- Tính theo **CPU time**, không phải thời gian thực. Một request chờ MySQL 5 phút có thể không bị giới hạn này kill.
- Đặt 60 giây cho web. Import/export lớn nên chạy qua CLI (CLI mặc định `0`).
- Dùng `request_terminate_timeout` của FPM để kill theo thời gian thực.

#### `max_input_vars`

- Giới hạn số biến POST/GET/COOKIE. Mặc định 1000.
- Form WooCommerce lớn, menu nhiều mục, page builder có thể cần 3000–5000.
- Đặt quá cao (100k) tạo bề mặt DoS. Tăng vừa đủ.

#### `post_max_size` và `upload_max_filesize`

Chuỗi giới hạn phải đồng bộ:

```text
nginx client_max_body_size
  >= Apache LimitRequestBody (nếu có)
  >= PHP post_max_size
  >= upload_max_filesize + overhead
  >= giới hạn của ứng dụng (WordPress, Laravel)
```

Nếu một mắt xích thấp hơn, upload sẽ thất bại với thông báo khó hiểu. Ví dụ: PHP cho 64 MB nhưng nginx chỉ cho 1 MB (`client_max_body_size 1m` mặc định) → request bị chặn trước khi đến PHP.

#### `realpath_cache_size` / `realpath_cache_ttl`

- Cache kết quả `realpath()`/`stat()`. WordPress với nhiều plugin gọi hàm này rất nhiều.
- 4096k là khởi đầu; 8192k–16384k cho site nhiều file.
- Cache này **theo từng process**, không chia sẻ. Tăng quá cao làm mỗi worker tốn thêm RAM.
- `ttl=600` giây là hợp lý; giảm nếu deploy file liên tục.

#### `expose_php`, `display_errors`, `log_errors`

- `expose_php=Off`: không gửi header `X-Powered-By`.
- `display_errors=Off`: không in lỗi ra trình duyệt (lộ đường dẫn, SQL, secret).
- `log_errors=On`: vẫn ghi log để debug.
- Nhớ đặt `error_log` riêng cho từng user và phân quyền đúng.

#### `session`

- `session.use_strict_mode=1`: chống session fixation.
- `session.cookie_httponly=1`: JavaScript không đọc được cookie session.
- `session.cookie_samesite=Lax`: giảm CSRF cross-site; test kỹ nếu app cần cookie cross-site.
- `session.gc_probability`: với file session, để mặc định hoặc dùng cron dọn dẹp. Với Redis, không cần garbage collector của PHP.
- `session.save_path` phải là thư mục user sở hữu, không dùng chung `/tmp` nếu có thể.

### 8.5. Per-domain và per-user

**Per-domain** (một file cho nhiều domain):

```ini
; /usr/local/php83/lib/php.conf.d/30-customers.ini
[HOST=example.com]
memory_limit = 512M
max_input_vars = 8000

[HOST=shop.example.com]
memory_limit = 768M
```

**Per-user** trong pool:

```ini
php_admin_value[memory_limit] = 512M
php_admin_value[max_input_vars] = 8000
php_admin_value[upload_max_filesize] = 128M
php_admin_value[post_max_size] = 160M
```

Sau khi sửa pool, phải `da build rewrite_confs` (nếu sửa template) hoặc restart FPM (nếu sửa file trực tiếp), rồi kiểm tra lại bằng `phpinfo()`.

### 8.6. `.user.ini`: cho user tự chỉnh, nhưng có giới hạn

Bật:

```ini
user_ini.filename = ".user.ini"
user_ini.cache_ttl = 300
```

User có thể tạo `.user.ini` trong webroot:

```ini
memory_limit = 512M
upload_max_filesize = 128M
post_max_size = 160M
```

Chỉ directive thuộc `PHP_INI_PERDIR`/`PHP_INI_USER` mới có hiệu lực. `opcache.*`, `extension`, `disable_functions` thường không đổi được theo cách này. `.user.ini` có cache TTL, nên sửa xong có thể phải đợi hoặc restart FPM.

### 8.7. Những thứ không nên đụng

| Directive | Lý do |
|---|---|
| `disable_functions` | DA có `secure_php`; thêm bừa có thể làm hỏng WP-CLI, plugin, cron |
| `open_basedir` toàn cục | DA đã đặt theo user; sửa toàn cục dễ gây lỗi chéo |
| `extension=` trùng | Load hai lần gây warning, thậm chí crash |
| `opcache.*` trong `.user.ini` | Không có hiệu lực hoặc không được phép |
| `memory_limit=-1` | Bỏ giới hạn bảo vệ, dễ OOM cả server |
| `max_execution_time=0` toàn cục | Request treo giữ worker vĩnh viễn |

> [!NOTE]
> Muốn biết một directive có hiệu lực ở đâu, xem cột "Changeable" trong
> [PHP manual](https://www.php.net/manual/en/ini.core.php). Đừng đoán.

---

## 9. Web server, timeout và các điểm nối với PHP

PHP không chạy một mình. Một request đi qua nhiều tầng, và tầng nào timeout trước sẽ quyết định lỗi người dùng thấy.

### 9.1. Chuỗi request

```text
Client → CDN/WAF → nginx → Apache (nếu nginx_apache) → PHP-FPM → MySQL/Redis
```

Với `nginx` thuần:

```text
Client → nginx → PHP-FPM → MySQL/Redis
```

Với LiteSpeed/OpenLiteSpeed:

```text
Client → LiteSpeed → LSPHP → MySQL/Redis
```

Mỗi mũi tên có timeout, buffer và giới hạn kích thước riêng. Lỗi 502/504 thường đến từ tầng **sau** chứ không phải tầng người dùng nhìn thấy.

### 9.2. `nginx_apache`

Đây là cấu hình phổ biến của DirectAdmin: nginx phục vụ file tĩnh và proxy request động sang Apache, Apache gọi PHP-FPM.

**nginx** (`/etc/nginx/nginx.conf` hoặc file trong `conf.d/`):

```nginx
client_max_body_size 64m;
client_body_buffer_size 128k;
client_header_buffer_size 4k;
large_client_header_buffers 4 16k;

proxy_connect_timeout 10s;
proxy_send_timeout    65s;
proxy_read_timeout    65s;
proxy_buffering       on;
```

**Apache** (`/etc/httpd/conf/extra/httpd-mpm.conf`, `httpd-default.conf`):

```apache
Timeout 65
ProxyTimeout 65
KeepAlive On
MaxKeepAliveRequests 100
KeepAliveTimeout 5
```

`MaxRequestWorkers` của Apache phải đủ cho số request đồng thời. Nếu Apache hết worker, request xếp hàng trước khi đến PHP, và tăng `max_children` của FPM không giúp gì.

### 9.3. `nginx` + PHP-FPM

```nginx
fastcgi_connect_timeout 10s;
fastcgi_send_timeout    65s;
fastcgi_read_timeout    65s;

fastcgi_buffer_size       32k;
fastcgi_buffers           16 16k;
fastcgi_busy_buffers_size 32k;

fastcgi_buffering on;
```

Nếu ứng dụng trả về header lớn (cookie, JWT), tăng `fastcgi_buffer_size`. Nếu response lớn hơn buffer, nginx ghi tạm ra đĩa — chậm và tốn I/O.

### 9.4. `mod_php`

Nếu buộc phải dùng `mod_php`:

- `MaxRequestWorkers` × RSS mỗi Apache process = RAM tối đa.
- PHP chạy dưới user `apache`, không phải user sở hữu file → vấn đề quyền ghi.
- OPcache vẫn dùng được, nhưng cache thuộc process Apache.
- Cách ly giữa các user kém hơn FPM.

Khuyến nghị: chuyển sang PHP-FPM nếu có thể, nhưng test kỹ `.htaccess` và `php_value`.

### 9.5. LiteSpeed / OpenLiteSpeed

- Dùng `lsphp`, không dùng `php-fpm`.
- Tham số quan trọng: số process `lsphp`, `PHP_LSAPI_CHILDREN`, `maxConns`, `instances`.
- LSCache là page cache mạnh, nhưng không thay thế OPcache.
- Đừng áp công thức `max_children` của FPM cho LSPHP; cơ chế khác.

### 9.6. Đồng bộ timeout

| Tầng | Directive | Giá trị gợi ý | Ghi chú |
|---|---|---|---|
| nginx | `fastcgi_read_timeout` / `proxy_read_timeout` | 65s | Lớn hơn timeout PHP |
| Apache | `Timeout`, `ProxyTimeout` | 65s | Áp dụng cả proxy và client |
| PHP-FPM | `request_terminate_timeout` | 60s | Kill request treo theo thời gian thực |
| PHP | `max_execution_time` | 60s | Tính CPU time, không phải wall clock |
| Ứng dụng | giới hạn riêng | ≤ 60s | Ví dụ timeout HTTP client nội bộ |

Quy tắc: **tầng ngoài cùng phải kiên nhẫn hơn tầng trong cùng**. Nếu nginx cắt ở 30s nhưng PHP cần 50s, người dùng nhận 504 dù PHP vẫn đang chạy và vẫn chiếm worker.

### 9.7. Sửa template DirectAdmin cho bền

Đừng sửa file vhost đã sinh. Quy trình:

```bash
# 1) Xem template đang dùng
ls /usr/local/directadmin/data/templates/ | grep -iE 'virtual|nginx|httpd' | head -30

# 2) Copy sang custom
install -d -m 755 /usr/local/directadmin/data/templates/custom
cp -p /usr/local/directadmin/data/templates/virtual_host2.conf \
      /usr/local/directadmin/data/templates/custom/virtual_host2.conf

# 3) Sửa file trong custom, giữ nguyên token |...|
# 4) Sinh lại cấu hình
da build rewrite_confs

# 5) Kiểm tra cú pháp trước khi reload
nginx -t
apachectl configtest
```

Tên template khác nhau giữa Apache, nginx, nginx_apache, LiteSpeed. Dùng `da build used_configs` và quan sát file thực tế thay vì đoán.

---

## 10. Quy trình tối ưu 60 phút trên production

Kịch bản dưới đây dành cho một server đang chạy, có cửa sổ bảo trì ngắn. Nếu server đông user, chia thành nhiều đêm.

### 10.1. Chuẩn bị (trước 24 giờ)

```bash
BK="/root/php-tuning-$(date +%F-%H%M)"
install -d -m 700 "$BK"

# Sao lưu cấu hình quan trọng
cp -a /usr/local/directadmin/custombuild/options.conf "$BK/"
cp -a /usr/local/php83/lib/php.ini "$BK/" 2>/dev/null || true
cp -a /usr/local/php83/lib/php.conf.d "$BK/" 2>/dev/null || true
cp -a /usr/local/directadmin/data/templates/custom "$BK/" 2>/dev/null || true
cp -a /usr/local/php83/etc/php-fpm.conf "$BK/" 2>/dev/null || true

# Danh sách pool của user
find /usr/local/directadmin/data/users -path '*/php/php-fpm*.conf' -print0 \
  | tar --null -T - -czf "$BK/user-pools.tar.gz" 2>/dev/null || true

ls -lh "$BK"
```

Ghi lại:

- Phiên bản PHP từng domain đang dùng.
- `max_children` hiện tại của các user lớn.
- Giờ cao điểm và lưu lượng ước tính.
- Người chịu trách nhiệm rollback.

### 10.2. Trình tự 60 phút

| Phút | Việc | Lệnh chính | Rollback |
|---|---|---|---|
| 0–5 | Kiểm tra bảo mật PHP | `php -v`, script audit | Vá trước, chưa tối ưu |
| 5–10 | Chụp baseline | `free`, `uptime`, `curl` | Không cần |
| 10–20 | Bật/tinh chỉnh OPcache | `99-opcache-tuning.ini`, restart FPM | Xóa file, restart |
| 20–30 | Đặt `max_children` | `da config-set`, `rewrite_confs` | Đặt lại số cũ |
| 30–40 | Chỉnh php.ini | `99-php-tuning.ini`, restart FPM | Xóa file, restart |
| 40–50 | Redis (nếu cần) | `da build redis`, cấu hình app | Tắt plugin/extension |
| 50–55 | Timeout web server | `nginx -t`, reload | Khôi phục file backup |
| 55–60 | Benchmark lại, ghi log | `wrk`, `curl` | Quyết định giữ/rollback |

### 10.3. Mẫu change log

```text
Thời gian: 2026-10-26 22:00 +07
Server: web-01 (16 GB, 8 vCPU, DA 1.713)
Người làm: ops
Thay đổi 1: bật OPcache 256/32/32531, validate_timestamps=1, revalidate_freq=60
  File: /usr/local/php83/lib/php.conf.d/99-opcache-tuning.ini
  Kết quả: TTFB p95 1.8s -> 1.1s, CPU 62% -> 48%
Thay đổi 2: php_fpm_max_children_default 10 -> 4
  Kết quả: RAM PHP 9.8 GB -> 8.9 GB, không có max_children warning trong 30 phút
Rollback: xóa 99-opcache-tuning.ini; da config-set php_fpm_max_children_default 10;
  da build rewrite_confs; systemctl restart php-fpm83
```

### 10.4. Nguyên tắc trong lúc làm

- **Không đổi hai thứ cùng lúc.** Nếu phải làm nhanh, ít nhất ghi lại thời điểm từng thay đổi.
- **Restart từng phiên bản, không restart tất cả.** `systemctl restart php-fpm83` trước, kiểm tra, rồi mới đến 8.4.
- **Theo dõi 10 phút sau mỗi thay đổi.** Xem 502/504, log FPM, RAM, load.
- **Có người thứ hai trực.** Nếu chỉ có một người, chuẩn bị lệnh rollback dán sẵn trong terminal.

### 10.5. Rollback

```bash
# Ví dụ khôi phục cấu hình đã backup
BK=/root/php-tuning-2026-10-26-2200

cp -a "$BK/php.conf.d/." /usr/local/php83/lib/php.conf.d/
cp -a "$BK/php.ini" /usr/local/php83/lib/php.ini
cp -a "$BK/options.conf" /usr/local/directadmin/custombuild/options.conf

da build rewrite_confs
systemctl restart php-fpm83

# Kiểm tra
curl -sI https://example.com/ | head -1
tail -n 50 /usr/local/php83/var/log/php-fpm.log
```

Nếu rollback bằng cách đổi phiên bản PHP, nhớ rằng code/extension có thể không tương thích ngược. Rollback version chỉ an toàn khi đã test.

---

## 11. Benchmark: đo cái gì và đo như thế nào

### 11.1. Chọn chỉ số

| Chỉ số | Cách đo | Ý nghĩa |
|---|---|---|
| TTFB p50/p95/p99 | `wrk --latency`, `curl -w` | Thời gian đến byte đầu tiên; phản ánh PHP/DB |
| RPS | `wrk`, `ab`, `hey` | Số request/giây |
| Tỷ lệ lỗi | access log, `wrk` non-2xx | 502/504/500 |
| CPU | `pidstat`, `top`, `vmstat` | Mức sử dụng CPU, iowait |
| RAM | `free -m`, RSS worker | Áp lực bộ nhớ |
| Worker queue | FPM status | Request đang chờ |
| OPcache hit | `opcache_get_status` | Hiệu quả cache |
| Query/request | query log, APM | Nút thắt database |

### 11.2. Cài công cụ

```bash
# Debian/Ubuntu
apt install -y wrk apache2-utils curl sysstat

# RHEL/Rocky/Alma
dnf install -y wrk httpd-tools curl sysstat
```

Nếu không cài được `wrk`, dùng `ab` có sẵn hoặc `hey`:

```bash
go install github.com/rakyll/hey@latest
```

### 11.3. Đo TTFB bằng `curl`

```bash
URL="https://example.com/"

for i in $(seq 1 20); do
  curl -o /dev/null -s -w \
    'dns=%{time_namelookup} connect=%{time_connect} tls=%{time_appconnect} ttfb=%{time_starttransfer} total=%{time_total}\n' \
    "$URL"
done | tee ttfb.txt

# p95 gần đúng (lấy cột ttfb)
sed -n 's/.*ttfb=\([0-9.]*\).*/\1/p' ttfb.txt \
  | sort -n | awk '{a[NR]=$1} END {print "p95:", a[int(NR*0.95)]}'
```

### 11.4. Đo tải bằng `wrk`

```bash
# 4 thread, 100 kết nối, 30 giây, in latency phân vị
wrk -t4 -c100 -d30s --latency https://example.com/
```

Đọc kết quả:

```text
Latency   1.20s   50%   320ms   90%   780ms   99%   1.50s
Req/Sec   85.3     50%    90     90%    110    99%    120
```

- **Latency**: phân vị thời gian phản hồi. p99 quan trọng hơn average.
- **Req/Sec**: throughput. Tăng RPS nhưng p99 tăng mạnh là đánh đổi không tốt.
- **Non-2xx**: nếu có, benchmark không hợp lệ.

### 11.5. Đo bằng `ab`

```bash
ab -n 2000 -c 50 -k https://example.com/
```

`ab` đơn giản nhưng kém chính xác hơn `wrk` với HTTP/2 và TLS. Dùng để so sánh tương đối, không dùng để tuyên bố con số tuyệt đối.

### 11.6. Đo trong lúc tải

```bash
# CPU/RAM từng process
pidstat -u -r -p ALL 1 30

# Tổng quan
vmstat 1 30
iostat -x 1 30

# Worker FPM
watch -n 2 'ps --ppid "$(systemctl show -p MainPID --value php-fpm83)" -o pid,rss,%cpu,etime,cmd'
```

### 11.7. Đọc OPcache và FPM status

OPcache: dùng script ở mục 6.1, gọi vài lần trong lúc benchmark.

FPM: bật `pm.status_path` tạm thời, gọi bằng `cgi-fcgi`. Xem `active processes`, `listen queue`, `max listen queue`, `slow requests`.

### 11.8. Bảng ghi kết quả

```text
| Kịch bản | RPS | TTFB p50 | TTFB p95 | TTFB p99 | CPU % | RAM PHP | Lỗi |
|---|---|---|---|---|---|---|---|
| Baseline | 210 | 480 ms | 1.8 s | 2.6 s | 62 | 9.8 GB | 0.4% |
| Sau OPcache | 330 | 300 ms | 1.1 s | 1.5 s | 48 | 10.2 GB | 0.2% |
| Sau FPM | 360 | 280 ms | 980 ms | 1.3 s | 45 | 9.4 GB | 0.1% |
| Sau Redis | 540 | 190 ms | 420 ms | 700 ms | 38 | 10.1 GB | 0.1% |
```

### 11.9. Cạm bẫy benchmark

1. **Đo trang admin đang đăng nhập.** Không đại diện cho khách.
2. **Cache chưa warm.** Request đầu tiên luôn chậm; warm up trước khi đo.
3. **Chỉ đo một URL.** Trang chủ có thể cache, trang sản phẩm mới là nút thắt.
4. **Chạy benchmark từ chính server.** `wrk` tranh CPU với PHP; dùng máy ngoài hoặc chấp nhận sai số.
5. **Tăng concurrency quá cao.** 10.000 kết nối từ một máy không mô phỏng người dùng thật, chỉ tạo SYN flood.
6. **Bỏ qua database.** PHP nhanh nhưng query 2 giây thì TTFB vẫn 2 giây.
7. **So sánh khác thời điểm.** Giờ cao điểm và 3 giờ sáng khác nhau rất nhiều.
8. **Không ghi lại cấu hình.** Ba tháng sau không biết con số đến từ đâu.

---
## 12. Case study: 8 vCPU / 16 GB, 180 tài khoản WordPress

> [!NOTE]
> Số liệu dưới đây lấy từ một lab dựng lại cấu hình shared hosting điển hình, không phải
> cam kết kết quả cho mọi server. Mục đích là minh họa **cách đo và ra quyết định**,
> không phải để copy nguyên si.

### 12.1. Bối cảnh

| Thành phần | Cấu hình |
|---|---|
| OS | AlmaLinux 9 |
| DirectAdmin | 1.713 |
| CPU/RAM | 8 vCPU / 16 GB |
| Disk | NVMe, 500 GB |
| Web server | `nginx_apache` |
| PHP | 8.3, PHP-FPM |
| Tài khoản | 180 user, 320 domain |
| Ứng dụng | 60% WordPress, 20% WooCommerce, 20% static/legacy |
| Database | MySQL 8 trên cùng máy |

### 12.2. Baseline

| Chỉ số | Giá trị |
|---|---|
| TTFB p95 | 1.8 s |
| RPS (wrk, 100 kết nối) | 210 |
| CPU | 62% |
| Load average | 8–10 |
| RAM cho PHP | 9.8 GB |
| OPcache | Bật nhưng chỉ 128 MB, `max_accelerated_files=10000` |
| `max_children` | 10 cho mọi user |
| `memory_limit` | 128 MB toàn cục |
| Redis | Chưa dùng |
| Log FPM | Có `server reached max_children` mỗi ngày |

Nhận xét ban đầu:

- OPcache bật nhưng cấu hình mặc định, chưa tối ưu cho 320 domain.
- `max_children=10` cho 180 user là trần lý thuyết 1.800 worker — không thể chứa trong 16 GB nếu tất cả cùng hoạt động.
- `memory_limit=128M` gây lỗi ở các site Woo lớn.
- Chưa có Redis, mọi query object cache đều đánh vào MySQL.

### 12.3. Thay đổi 1: OPcache

```ini
; /usr/local/php83/lib/php.conf.d/99-opcache-tuning.ini
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

```bash
systemctl restart php-fpm83
```

Kết quả sau 30 phút:

| Chỉ số | Trước | Sau |
|---|---|---|
| TTFB p95 | 1.8 s | 1.1 s |
| RPS | 210 | 330 |
| CPU | 62% | 48% |
| OPcache hit rate | 91% | 99.3% |
| `oom_restarts` | 0 | 0 |

### 12.4. Thay đổi 2: FPM sizing

```bash
da config-set php_fpm_max_children_default 4
systemctl restart directadmin
da build rewrite_confs
systemctl restart php-fpm83
```

Với 5 user Woo lớn, đặt override:

```ini
|?MAX_CHILDREN=12|
```

Thêm slow log cho các user lớn:

```ini
request_slowlog_timeout = 5s
slowlog = /home/USER/.php/php-fpm-slow.log
request_terminate_timeout = 60s
```

Kết quả:

| Chỉ số | Trước | Sau |
|---|---|---|
| RAM cho PHP | 9.8 GB | 9.4 GB |
| `max_children` warning/ngày | 12–20 | 0–2 |
| TTFB p95 | 1.1 s | 980 ms |
| 502/504 | 0.2% | 0.05% |

Điểm quan trọng: **giảm** `max_children` mặc định lại làm server ổn định hơn, vì tránh được tình trạng nhiều pool cùng spawn worker và tranh RAM.

### 12.5. Thay đổi 3: php.ini theo nhóm ứng dụng

```ini
; Toàn cục
memory_limit = 256M
max_input_vars = 5000
post_max_size = 80M
upload_max_filesize = 64M
realpath_cache_size = 8192k
realpath_cache_ttl = 600
display_errors = Off
log_errors = On
```

```ini
; Riêng user Woo lớn, trong pool
php_admin_value[memory_limit] = 512M
php_admin_value[max_input_vars] = 8000
php_admin_value[upload_max_filesize] = 128M
php_admin_value[post_max_size] = 160M
```

Kết quả:

- Lỗi "Allowed memory size exhausted" giảm từ 40–60/ngày xuống còn 2–5/ngày.
- Lỗi upload ảnh sản phẩm giảm rõ rệt.
- Không tăng RAM đáng kể vì `memory_limit` chỉ là trần, không phải mức dùng thực.

### 12.6. Thay đổi 4: Redis cho WooCommerce

```bash
da build set redis yes
da build redis
da build set php_redis yes
da build php_redis
```

Bật Redis cho 20 user Woo, cấu hình `wp-config.php`:

```php
define('WP_REDIS_SCHEME', 'unix');
define('WP_REDIS_PATH', '/home/USER/.redis/redis.sock');
define('WP_REDIS_PREFIX', 'wp_example_');
define('WP_CACHE', true);
```

Kết quả sau 24 giờ:

| Chỉ số | Trước | Sau |
|---|---|---|
| TTFB p95 | 980 ms | 420 ms |
| RPS | 360 | 540 |
| CPU | 45% | 38% |
| Query/request (Woo) | 38 | 11 |
| RAM Redis | 0 | 1.1 GB |

### 12.7. Tổng hợp

| Kịch bản | RPS | TTFB p95 | CPU | RAM PHP | Lỗi |
|---|---|---|---|---|---|
| Baseline | 210 | 1.8 s | 62% | 9.8 GB | 0.4% |
| + OPcache | 330 | 1.1 s | 48% | 10.2 GB | 0.2% |
| + FPM sizing | 360 | 980 ms | 45% | 9.4 GB | 0.05% |
| + php.ini | 370 | 950 ms | 44% | 9.5 GB | 0.05% |
| + Redis | 540 | 420 ms | 38% | 10.1 GB | 0.05% |

### 12.8. Những thứ đã thử và không hiệu quả

| Thử nghiệm | Kết quả | Kết luận |
|---|---|---|
| Bật JIT `tracing`, buffer 128 MB | TTFB không đổi, RAM +300 MB | Tắt; workload I/O-bound |
| OPcache 1 GB | Hit rate vẫn 99.3%, free memory 700 MB | Lãng phí; giữ 256 MB |
| `pm=static` cho mọi user | RAM tăng vọt, OOM 2 lần | Quay lại `ondemand` |
| `max_children=50` cho mọi user | Không tăng RPS, RAM +4 GB | Chỉ override user thật sự busy |
| `memory_limit=1024M` toàn cục | Không giảm lỗi, tăng RAM | Giữ 256M, override Woo 512M |
| Preload toàn bộ WordPress | Lỗi đường dẫn, khó rollback | Bỏ |

### 12.9. Sự cố trong quá trình làm

**Sự cố 1: OPcache lạnh sau `da build php`.**

`da build php` restart FPM, xóa OPcache. Trong 5–10 phút đầu, TTFB tăng gấp đôi vì cache chưa ấm. Cách xử lý:

```bash
# Warm up các URL chính sau khi build
for u in / /shop/ /blog/ /contact/; do
  curl -s -o /dev/null "https://example.com$u"
done
```

Hoặc chấp nhận vài phút chậm và thông báo trước.

**Sự cố 2: Import sản phẩm bị kill.**

Một user chạy import 20.000 sản phẩm qua web. `request_terminate_timeout=60s` kill worker giữa chừng. Cách xử lý: chuyển sang WP-CLI:

```bash
sudo -u USER -i /usr/local/php83/bin/php /home/USER/domains/example.com/public_html/wp-cli.phar \
  import products.csv
```

CLI không bị giới hạn `max_execution_time` của web (mặc định 0) và không chiếm worker FPM.

**Sự cố 3: Redis evict session.**

Một instance Redis dùng chung cho cache và session, đặt `allkeys-lru`, `maxmemory` thấp. User bị đăng xuất ngẫu nhiên. Cách xử lý: tách DB/instance, đặt session ở instance không evict, cache ở instance `allkeys-lru`.

### 12.10. Bài học

1. **OPcache là khoản đầu tư đầu tiên.** Trước khi nghĩ đến Redis, FPM hay JIT.
2. **Giảm `max_children` có thể làm server nhanh hơn.** Ít tranh chấp RAM hơn, ít OOM hơn.
3. **Override theo user, không đặt một con số cho tất cả.**
4. **Redis chỉ có lợi khi ứng dụng thật sự lặp query.** Đo query trước.
5. **Luôn có warm-up sau khi restart.** OPcache lạnh là cú sốc tạm thời nhưng thật.

---

## 13. Troubleshooting: các lỗi thường gặp

### 13.1. Bảng tra nhanh

| Triệu chứng | Nguyên nhân thường gặp | Kiểm tra | Xử lý |
|---|---|---|---|
| 502 Bad Gateway | FPM chết, sai socket, sai quyền | `systemctl status php-fpm83`, `ls -l socket` | Sửa quyền, restart, kiểm tra pool |
| 504 Gateway Timeout | Timeout web server < thời gian PHP | `nginx -t`, log | Tăng timeout ngoài, giảm việc trong PHP |
| `server reached max_children` | Hết worker | `grep pm.max_children`, RSS | Tăng vừa phải hoặc tối ưu app |
| OPcache full | Thiếu `memory_consumption`/`max_accelerated_files` | `opcache_get_status` | Tăng, restart FPM |
| Allowed memory exhausted | `memory_limit` thấp hoặc memory leak | `memory_get_peak_usage` | Tăng theo user, sửa leak |
| CPU cao | OPcache tắt, bot, query chậm, malware | `top`, `pidstat`, slow log | Bật OPcache, chặn bot, tối ưu query |
| Redis timeout | Sai socket/quyền/maxmemory | `redis-cli ping`, `--latency` | Sửa socket, tăng RAM, đổi policy |
| Config không có hiệu lực | Sai file, CLI vs FPM, OPcache | `phpinfo()`, `php -i` | Sửa đúng tầng, restart |
| Config bị ghi đè | Sửa file sinh tự động | So sánh sau `rewrite_confs` | Dùng template `custom/` |
| `No input file specified` | Sai docroot, `open_basedir`, chroot | vhost, `namei -l` | Sửa đường dẫn/quyền |

### 13.2. 502 Bad Gateway

```bash
# 1) Service còn sống?
systemctl status php-fpm83 --no-pager
systemctl is-active php-fpm83

# 2) Socket có tồn tại và đúng quyền?
ls -l /usr/local/php83/sockets/USER.sock
namei -l /usr/local/php83/sockets/USER.sock

# 3) Log FPM
tail -n 100 /usr/local/php83/var/log/php-fpm.log

# 4) Log web server
tail -n 100 /var/log/nginx/error_log
tail -n 100 /var/log/httpd/error_log

# 5) SELinux (nếu bật)
getenforce
ausearch -m avc -ts recent 2>/dev/null | tail -20
```

Thường gặp:

- Socket có owner `USER`, group `apache`, mode `660`; nếu group sai, web server không nối được.
- Pool không khởi động vì lỗi cú pháp trong `php-fpm83.conf`; `php-fpm83 -t` sẽ chỉ ra.
- `open_basedir` chặn file entry point.
- Isolated FPM + jail: đường dẫn tuyệt đối bị thay đổi trong chroot.
- `/tmp` riêng do `PrivateTmp=true`; ứng dụng ghi `/tmp` nhưng không thấy file từ ngoài.

Không sửa bằng cách `setenforce 0` rồi để đó. Nếu SELinux chặn, thêm context/boolean đúng.

### 13.3. 504 Gateway Timeout

Kiểm tra theo thứ tự:

```bash
# Timeout PHP-FPM
grep -R 'request_terminate_timeout' /usr/local/directadmin/data/users/*/php/ 2>/dev/null | head

# Timeout nginx
nginx -T 2>/dev/null | grep -E 'fastcgi_read_timeout|proxy_read_timeout'

# Timeout Apache
apachectl -t -D DUMP_RUN_CFG 2>/dev/null | head
grep -R 'ProxyTimeout\|^Timeout' /etc/httpd/ 2>/dev/null | head
```

Nếu PHP cần 90 giây nhưng nginx cắt ở 60 giây, tăng nginx lên 95 giây **hoặc** giảm công việc PHP xuống dưới 60 giây. Tăng timeout chỉ che vấn đề; request chậm vẫn chiếm worker.

### 13.4. `server reached max_children`

```bash
# 1) Xem giới hạn hiện tại
grep -H 'pm.max_children' /usr/local/directadmin/data/users/*/php/php-fpm83.conf | head -30

# 2) Tổng trần lý thuyết
awk -F= '/pm.max_children/ {s+=$2} END {print "tong max_children:", s}' \
  /usr/local/directadmin/data/users/*/php/php-fpm83.conf

# 3) RSS trung bình
ps -eo rss,comm | awk '/php-fpm/ {s+=$1; n++} END {printf "%.1f MB/worker\n", s/n/1024}'
```

Nếu tổng `max_children` × RSS >> RAM, đừng tăng nữa. Tối ưu query/code, giảm plugin, hoặc thêm RAM.

### 13.5. OPcache đầy

```bash
# Xem nhanh qua web (script ở mục 6.1)
# Hoặc CLI nếu bật opcache.enable_cli
/usr/local/php83/bin/php -d opcache.enable_cli=1 -r '
$s = opcache_get_status(false);
printf("used=%.1fMB free=%.1fMB files=%d oom=%d hash=%d\n",
  $s["memory_usage"]["used_memory"]/1048576,
  $s["memory_usage"]["free_memory"]/1048576,
  $s["opcache_statistics"]["num_cached_scripts"],
  $s["opcache_statistics"]["oom_restarts"],
  $s["opcache_statistics"]["hash_restarts"]);
'
```

Tăng `opcache.memory_consumption` theo bước 128 MB, và `max_accelerated_files` theo mốc 16229 → 32531 → 65407. Restart FPM sau khi đổi.

### 13.6. `Allowed memory size exhausted`

```bash
# Tìm request/plugin ngốn RAM
grep -R 'Allowed memory size' /home/USER/.php/php-error.log | tail -20
```

Trong WordPress, bật staging với `WP_DEBUG` và dùng plugin query monitor để xem peak memory. Đừng chỉ tăng `memory_limit` lên 1 GB; nếu memory leak, nó sẽ ăn hết.

### 13.7. CPU cao

```bash
top -H -b -n1 | head -30
pidstat -u -p ALL 1 10
ps -eo pid,user,%cpu,rss,etime,cmd --sort=-%cpu | head -20
```

Các nguyên nhân thường gặp:

- OPcache tắt hoặc `validate_timestamps=0` nhưng cache không được dùng.
- `wp-cron.php` chạy liên tục do traffic cao. Chuyển sang cron hệ thống:

```bash
# wp-config.php
define('DISABLE_WP_CRON', true);

# crontab của user
*/5 * * * * /usr/local/php83/bin/php /home/USER/domains/example.com/public_html/wp-cron.php >/dev/null 2>&1
```

- `admin-ajax.php` bị lạm dụng bởi plugin/heartbeat.
- `xmlrpc.php` bị brute force; chặn ở web server.
- Query chậm; xem slow query log.
- Crypto mining/webshell; kiểm tra process lạ, file PHP mới, kết nối ra ngoài.

### 13.8. Redis timeout hoặc không kết nối

```bash
# Socket có tồn tại?
ls -l /home/USER/.redis/redis.sock

# Ping qua socket
redis-cli -s /home/USER/.redis/redis.sock ping

# Độ trễ
redis-cli -s /home/USER/.redis/redis.sock --latency

# Bộ nhớ và policy
redis-cli -s /home/USER/.redis/redis.sock info memory | grep -E 'used_memory_human|maxmemory_human|maxmemory_policy'
```

Nếu `NOAUTH`, kiểm tra mật khẩu trong `wp-config.php`/`.env`. Nếu `MISCONF`, Redis không ghi được vì `stop-writes-on-bgsave-error`; kiểm tra disk và log Redis.

### 13.9. Sửa cấu hình nhưng không có hiệu lực

Thứ tự kiểm tra:

1. **Đúng file chưa?** `phpinfo()` → `Loaded Configuration File` và `Scan this dir`.
2. **Đúng phiên bản chưa?** Domain có thể chọn PHP 8.2 trong khi bạn sửa 8.3.
3. **Đúng tầng chưa?** `php_admin_value` trong pool thắng `.user.ini`.
4. **Đã restart FPM chưa?** `systemctl restart php-fpm83`.
5. **OPcache có cache file cũ?** `validate_timestamps=0` + không reset → code cũ.
6. **CLI khác FPM?** `php -i` có thể đọc file khác.

### 13.10. Cấu hình bị ghi đè sau khi build

- `10-directadmin.ini` và `50-webapps.ini` do CustomBuild sinh.
- `php.ini` có thể bị ghi đè nếu `php_ini=yes`.
- Pool user bị sinh lại bởi `da build rewrite_confs`.

Cách bền:

- Dùng `99-*.ini` trong `php.conf.d/`.
- Dùng `custom/opcache/opcache.ini`.
- Dùng `templates/custom/php-fpm.conf.custom1` hoặc `CUSTOM1`/`CUSTOM2`.
- Ghi lại mọi thay đổi vào change log.

### 13.11. `No input file specified` / `File not found`

```bash
# Kiểm tra đường dẫn thực tế
namei -l /home/USER/domains/example.com/public_html/index.php

# Kiểm tra docroot trong vhost
grep -R 'DocumentRoot\|root ' /usr/local/directadmin/data/users/USER/httpd.conf \
  /usr/local/directadmin/data/users/USER/nginx.conf 2>/dev/null | head

# Kiểm tra open_basedir trong pool
grep -i open_basedir /usr/local/directadmin/data/users/USER/php/php-fpm83.conf
```

Với isolated FPM/jail, đường dẫn nhìn từ trong chroot khác đường dẫn ngoài. Đừng sửa `open_basedir` bừa; hiểu jail trước.

### 13.12. `da build` thất bại

```bash
df -h
df -i
free -m
dmesg -T | tail -30
```

Các nguyên nhân: hết disk, hết RAM (OOM killer), thiếu compiler/header, network tải source lỗi. Đừng chạy lại liên tục; đọc output lỗi đầu tiên. Chạy trong `tmux` để không mất log khi SSH rớt.

---

## 14. Checklist, rollback và giám sát định kỳ

### 14.1. Trước khi tối ưu

- [ ] Đã vá PHP2Shell và các bản vá bảo mật khác.
- [ ] Có backup `options.conf`, `php.ini`, `php.conf.d`, template custom, pool user.
- [ ] Đã đo baseline và lưu file.
- [ ] Biết giờ cao điểm và có cửa sổ bảo trì.
- [ ] Có lệnh rollback dán sẵn.
- [ ] Có người thứ hai trực hoặc kênh liên lạc.
- [ ] Đã thông báo cho khách hàng nếu cần.

### 14.2. Trong khi tối ưu

- [ ] Mỗi lần chỉ đổi một nhóm cấu hình.
- [ ] Ghi lại thời điểm, file, giá trị cũ/mới.
- [ ] Restart từng phiên bản PHP, kiểm tra trước khi sang phiên bản khác.
- [ ] Theo dõi 502/504, log FPM, RAM, load trong 10 phút.
- [ ] Benchmark lại sau mỗi thay đổi lớn.
- [ ] Nếu p95 hoặc tỷ lệ lỗi xấu đi, rollback ngay — đừng cố "chờ nó ổn".

### 14.3. Sau 1 giờ / 24 giờ / 7 ngày

| Mốc | Kiểm tra |
|---|---|
| 1 giờ | 502/504, log FPM, RAM, load, `max_children` warning |
| 24 giờ | TTFB p95, RPS, CPU, RAM, tỷ lệ lỗi, phản hồi khách |
| 7 ngày | Xu hướng RAM/CPU, OPcache hit, Redis memory, dung lượng log |

### 14.4. Giám sát định kỳ

```bash
# Chạy audit chỉ-đọc mỗi sáng, lưu lại để so sánh
/root/directadmin-php-tuning/scripts/da-php-audit.sh \
  > "/root/php-audit-$(date +%F).txt" 2>&1
```

Thêm vào cron nếu muốn:

```cron
0 6 * * * /root/directadmin-php-tuning/scripts/da-php-audit.sh > /root/php-audit-$(date +\%F).txt 2>&1
```

Các chỉ số cần xem hàng tháng:

- OPcache hit rate và `oom_restarts`/`hash_restarts`.
- Tổng worker FPM so với RAM.
- `max_children` warning.
- Redis `used_memory` và eviction.
- PHP EOL và bản vá bảo mật.
- Dung lượng log, inode, disk.
- TTFB p95 từ monitoring bên ngoài.

### 14.5. Thẻ rollback nhanh

```bash
# 1) Khôi phục cấu hình
BK=/root/php-tuning-YYYY-MM-DD-HHMM
cp -a "$BK/php.conf.d/." /usr/local/php83/lib/php.conf.d/
cp -a "$BK/php.ini" /usr/local/php83/lib/php.ini
cp -a "$BK/options.conf" /usr/local/directadmin/custombuild/options.conf

# 2) Sinh lại cấu hình
da build rewrite_confs

# 3) Restart FPM
systemctl restart php-fpm83

# 4) Kiểm tra
curl -sI https://example.com/ | head -1
tail -n 50 /usr/local/php83/var/log/php-fpm.log
```

---
## 15. FAQ

**1. Tối ưu PHP có cần nâng RAM không?**

Không nhất thiết. OPcache, realpath cache và đúng cấu hình FPM thường cải thiện đáng kể mà không cần thêm RAM. Chỉ nâng RAM khi đã đo thấy thiếu thật (swap tăng, OOM, worker bị kill).

**2. OPcache 1 GB có nhanh hơn 256 MB?**

Chỉ khi cache thật sự cần nhiều hơn 256 MB. Nhìn `used_memory`: nếu chỉ dùng 120/1024 MB thì 1 GB là lãng phí. Tăng dung lượng không làm cache hit cao hơn nếu thiếu file hoặc code thay đổi liên tục.

**3. JIT có giúp WordPress không?**

Thường không. WordPress bị giới hạn bởi database, I/O và network, không phải phép tính CPU. JIT có thể tăng RAM mà không giảm TTFB. Benchmark trên staging trước khi bật.

**4. Nên dùng `ondemand`, `dynamic` hay `static`?**

Shared hosting nhiều tài khoản: `ondemand`. Server vài site traffic đều: `dynamic`. `static` chỉ khi bạn kiểm soát hoàn toàn tải và đã tính đủ RAM. Đừng đổi chỉ vì nghe nói `static` nhanh hơn.

**5. Đặt `max_children=100` cho mỗi user được không?**

Được về mặt cấu hình, nhưng thường là tự sát. 100 user × 100 worker × 50 MB = 500 GB. `max_children` là trần, không phải mục tiêu. Đặt theo RAM và override cho user thật sự cần.

**6. Redis có thay thế MySQL không?**

Không. Redis là cache/key-value, không phải database quan hệ. Nó giảm query lặp lại, không thay thế schema, index hay transaction.

**7. APCu hay Redis?**

Server chuyên dụng một ứng dụng: APCu nhẹ và nhanh. Shared hosting nhiều user: Redis an toàn hơn vì có thể tách theo user/socket/DB; APCu dùng chung shared memory giữa các worker của cùng master. Nếu dùng APCu trên shared hosting, phải có prefix và hiểu rủi ro.

**8. Đặt `memory_limit=512M` cho tất cả có sao không?**

Không chết người, nhưng lãng phí và che memory leak. `memory_limit` là trần mỗi request; đặt cao không làm PHP dùng nhiều hơn, nhưng nếu code leak thì worker có thể ăn tới 512 MB trước khi chết. Đặt theo nhóm ứng dụng.

**9. `opcache.validate_timestamps=0` có an toàn không?**

An toàn về hiệu năng, nhưng nguy hiểm về vận hành: sửa file không có hiệu lực đến khi reset cache. Chỉ dùng khi có quy trình deploy và reset rõ ràng. Shared hosting nên để `1` với `revalidate_freq=60`.

**10. Tại sao `da build rewrite_confs` làm mất chỉnh sửa của tôi?**

Vì nó sinh lại file từ template. Sửa file trong `templates/custom/` hoặc dùng `CUSTOM1`/`CUSTOM2`, đừng sửa file kết quả.

**11. PHP 8.2 còn dùng được không?**

Được đến 31/12/2026, nhưng không nên kế hoạch dài hạn. Sau mốc đó không còn bản vá bảo mật. Dùng thời gian còn lại để test và nâng 8.3.

**12. Có nên bỏ `nginx_apache`, dùng `nginx` thuần?**

`nginx` thuần nhẹ hơn và ít tầng hơn, nhưng mất `.htaccess` và một số tương thích. Nếu tất cả site đã kiểm soát rewrite, có thể chuyển. Nếu có nhiều ứng dụng cũ dùng `.htaccess`, `nginx_apache` an toàn hơn. Đây là thay đổi kiến trúc, không phải tinh chỉnh.

**13. Tối ưu có làm mất an toàn không?**

Có thể, nếu bạn tắt `open_basedir`, bật `display_errors`, đặt `memory_limit=-1`, mở Redis ra Internet hoặc dùng `max_children` quá cao. Mọi thay đổi bảo mật phải được xem xét cùng hiệu năng.

**14. Bao lâu đo lại một lần?**

Sau mỗi thay đổi lớn, sau mỗi lần nâng PHP/plugin, và định kỳ hàng tháng. Server thay đổi theo thời gian: thêm site, thêm plugin, traffic tăng. Một cấu hình tốt hôm nay có thể thành nút thắt sau ba tháng.

**15. `php-fpm83 -t` kiểm tra gì?**

Kiểm tra cú pháp file cấu hình FPM. Chạy trước khi restart:

```bash
/usr/local/php83/sbin/php-fpm -t
```

Nếu báo lỗi, sửa trước khi restart để tránh downtime.

**16. Có cần tối ưu MySQL không?**

Nếu TTFB cao mà CPU PHP thấp, nghi ngờ database trước. PHP tuning không chữa query chậm. Xem slow query log và `EXPLAIN` trước khi thêm Redis.

---

## 16. Thuật ngữ

| Thuật ngữ | Giải thích |
|---|---|
| **OPcache** | Bộ cache bytecode của PHP, lưu code đã biên dịch trong shared memory |
| **JIT** | Just-In-Time compiler, biên dịch opcode thành mã máy khi chạy |
| **PHP-FPM** | FastCGI Process Manager, daemon quản lý worker PHP |
| **Pool** | Nhóm worker FPM có cùng user, socket và giới hạn |
| **Worker** | Tiến trình con của FPM xử lý request |
| **`pm.max_children`** | Số worker tối đa đồng thời trong một pool |
| **`ondemand`** | Chế độ chỉ tạo worker khi có request |
| **`dynamic`** | Chế độ giữ một số worker tối thiểu và co giãn |
| **`static`** | Chế độ giữ cố định số worker |
| **Socket** | File Unix để web server giao tiếp với FPM |
| **RSS** | Resident Set Size, RAM thực tế tiến trình đang dùng |
| **TTFB** | Time To First Byte, thời gian đến byte đầu tiên |
| **p95/p99** | Phân vị 95/99, 95%/99% request nhanh hơn giá trị này |
| **RPS** | Requests per second, số request mỗi giây |
| **Object cache** | Cache dữ liệu đối tượng/query, thường dùng Redis/APCu |
| **Page cache** | Cache HTML đầu ra, thường ở CDN/nginx/LSCache |
| **Cold cache** | Cache chưa có dữ liệu, request đầu chậm |
| **Warm cache** | Cache đã có dữ liệu, request nhanh |
| **CustomBuild** | Công cụ build/quản lý service của DirectAdmin |
| **`rewrite_confs`** | Lệnh sinh lại cấu hình web/FPM từ template |
| **Isolated FPM** | Mỗi user một FPM master riêng, thường trong jail |
| **Jail** | Môi trường cách ly user của DirectAdmin |
| **`open_basedir`** | Giới hạn thư mục PHP được truy cập |
| **`php_admin_value`** | Giá trị cấu hình không thể ghi đè bởi user |
| **`realpath_cache`** | Cache kết quả `realpath()`/`stat()` theo process |
| **`max_input_vars`** | Số biến đầu vào tối đa của một request |
| **`request_terminate_timeout`** | Thời gian FPM kill request treo (wall clock) |
| **`max_execution_time`** | Giới hạn CPU time của PHP cho một request |

---

## 17. Cấu trúc repo, đóng góp và License

### 17.1. Cấu trúc

```text
directadmin-php-tuning/
├── README.md                      # Playbook chính (bạn đang đọc)
├── LICENSE                        # MIT
├── .gitignore
├── conf/
│   ├── 99-php-tuning.ini          # Cấu hình php.ini tham khảo
│   ├── 99-opcache-tuning.ini      # Cấu hình OPcache tham khảo
│   ├── php-fpm-pool-snippet.conf  # Snippet cho pool/CUSTOM1
│   └── redis-session.ini          # Session Redis + ghi chú bảo mật
├── docs/
│   ├── checklist-vn.md            # Checklist dạng tick-box
│   └── quick-reference-en.md      # Cheat sheet một trang tiếng Anh
└── scripts/
    └── da-php-audit.sh            # Audit chỉ-đọc, không sửa gì
```

### 17.2. Script audit

```bash
chmod +x scripts/da-php-audit.sh
sudo ./scripts/da-php-audit.sh
```

Script sẽ:

- Phát hiện DirectAdmin và đọc `options.conf`.
- Liệt kê phiên bản PHP, `php.ini`, `php.conf.d`.
- Kiểm tra OPcache, Redis, APCu, extension liên quan.
- Đếm FPM service, worker, socket, pool, `max_children`.
- Tính RSS trung bình và cảnh báo nếu tổng trần worker vượt RAM.
- Kiểm tra log `max_children`, segfault, OOM gần đây.
- Kiểm tra mức vá PHP2Shell theo từng nhánh.
- In gợi ý và exit code `1` nếu có cảnh báo nghiêm trọng.

Script **không** ghi file, không sửa cấu hình, không restart service, không gửi dữ liệu ra ngoài.

### 17.3. Đóng góp

- Mở issue mô tả môi trường (OS, DA version, PHP version, web server) và hành vi mong đợi.
- Pull request nên nhỏ, có lý do và có cách kiểm chứng.
- Không đưa thông tin nhận dạng khách hàng, mật khẩu, token, IP thật vào issue/PR.
- Nếu thêm con số hiệu năng, ghi rõ môi trường và phương pháp đo.

### 17.4. License

MIT — xem [LICENSE](LICENSE). Dùng, sửa, chia sẻ thoải mái, không bảo hành.

### 17.5. Tài liệu tham khảo

- [DirectAdmin — PHP-FPM](https://docs.directadmin.com/webservices/php/php-fpm.html)
- [DirectAdmin — PHP Options](https://docs.directadmin.com/webservices/php/php-options.html)
- [DirectAdmin — PHP Extensions](https://docs.directadmin.com/webservices/php/php-extensions.html)
- [DirectAdmin — Multiple PHP versions](https://docs.directadmin.com/webservices/php/multiple-php.html)
- [DirectAdmin — Redis](https://docs.directadmin.com/other-hosting-services/redis)
- [DirectAdmin — All directadmin.conf values](https://docs.directadmin.com/directadmin/general-usage/all-directadmin-conf-values.html)
- [DirectAdmin 1.690 — Isolated PHP-FPM](https://docs.directadmin.com/changelog/version-1.690.html)
- [PHP — Supported Versions](https://www.php.net/supported-versions.php)
- [PHP — OPcache configuration](https://www.php.net/manual/en/opcache.configuration.php)
- [PHP — FPM configuration](https://www.php.net/manual/en/install.fpm.configuration.php)
- [PHP — Core php.ini directives](https://www.php.net/manual/en/ini.core.php)
- [phpredis — Session handler](https://github.com/phpredis/phpredis#php-session-handler)
- [WordPress — Redis Object Cache](https://wordpress.org/plugins/redis-cache/)
- [nginx — FastCGI module](https://nginx.org/en/docs/http/ngx_http_fastcgi_module.html)
- [Apache — MPM tuning](https://httpd.apache.org/docs/2.4/mpm.html)
- [update-php-cve — vá PHP2Shell](https://github.com/fixnhanh-linux/update-php-cve)

---

> [!TIP]
> Nếu chỉ nhớ một câu: **đo trước, đổi một thứ, đo lại, và luôn biết cách quay về.**
> Mọi con số trong repo này là điểm khởi đầu, không phải chân lý cho server của bạn.
