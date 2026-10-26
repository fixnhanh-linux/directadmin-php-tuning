#!/usr/bin/env bash
# ============================================================================
# da-php-audit.sh — audit PHP/DirectAdmin ở chế độ CHỈ-ĐỌC
#
# Mục đích:
#   - Phát hiện DirectAdmin, đọc options.conf và cấu hình PHP.
#   - Liệt kê phiên bản PHP, php.ini, extension, OPcache, Redis.
#   - Đếm FPM service, worker, socket, pool và max_children.
#   - Cảnh báo nếu tổng trần worker vượt RAM hoặc PHP chưa vá PHP2Shell.
#
# An toàn:
#   - Không ghi file, không sửa cấu hình, không restart service.
#   - Không gửi dữ liệu ra ngoài.
#
# Cách dùng:
#   sudo ./scripts/da-php-audit.sh
#
# Exit code:
#   0 — không có cảnh báo nghiêm trọng
#   1 — có cảnh báo hoặc lỗi cần xem
# ============================================================================

set -u
LC_ALL=C
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

WARN=0
CRIT=0
DA_FOUND=0
DA_CMD=""
PHP_BINS=()

hr() { printf '%s\n' "------------------------------------------------------------"; }
section() { hr; printf '== %s ==\n' "$1"; }
info() { printf '[i] %s\n' "$*"; }
ok() { printf '[ok] %s\n' "$*"; }
warn() { printf '[!] %s\n' "$*"; WARN=$((WARN + 1)); }
crit() { printf '[x] %s\n' "$*"; CRIT=$((CRIT + 1)); }
note() { printf '    %s\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }

run_da() {
  [ -n "$DA_CMD" ] || return 0
  "$DA_CMD" "$@" 2>/dev/null
}

# ---------------------------------------------------------------------------
# Phát hiện môi trường
# ---------------------------------------------------------------------------
detect_directadmin() {
  if [ -d /usr/local/directadmin ] || [ -f /usr/local/directadmin/custombuild/options.conf ]; then
    DA_FOUND=1
  fi
  if have da; then
    DA_CMD="$(command -v da)"
  fi
}

collect_php_bins() {
  local b x
  for b in /usr/local/php*/bin/php /usr/bin/php /usr/bin/php[0-9]*; do
    [ -e "$b" ] || continue
    [ -x "$b" ] || continue
    if [ ${#PHP_BINS[@]} -gt 0 ]; then
      for x in "${PHP_BINS[@]}"; do
        [ "$x" = "$b" ] && continue 2
      done
    fi
    PHP_BINS+=("$b")
  done
  if have php; then
    b="$(command -v php)"
    if [ ${#PHP_BINS[@]} -gt 0 ]; then
      for x in "${PHP_BINS[@]}"; do
        [ "$x" = "$b" ] && return 0
      done
    fi
    PHP_BINS+=("$b")
  fi
}

# ---------------------------------------------------------------------------
# Kiểm tra bản vá PHP2Shell theo nhánh
# ---------------------------------------------------------------------------
check_php2shell() {
  local bin="$1" ver branch patch min
  ver="$("$bin" -r 'echo PHP_VERSION;' 2>/dev/null || true)"
  if [ -z "$ver" ]; then
    warn "khong doc duoc PHP_VERSION tu $bin"
    return 0
  fi

  branch="${ver%.*}"
  patch="${ver##*.}"
  patch="${patch%%[!0-9]*}"

  case "$branch" in
    8.5) min=12 ;;
    8.4) min=27 ;;
    8.3) min=36 ;;
    8.2) min=35 ;;
    8.1 | 8.0 | 7.* | 5.*)
      crit "PHP $ver ($bin): nhanh da EOL, KHONG co ban va PHP2Shell upstream"
      note "Kiem backport cua vendor/LTS hoac nang len 8.3+ truoc khi toi uu."
      return 0
      ;;
    8.6)
      info "PHP $ver: nhanh 8.6 (RC) da co fix PHP2Shell; khong dung cho production"
      return 0
      ;;
    *)
      info "PHP $ver: chua co du lieu ban va cho nhanh nay, kiem tra php.net"
      return 0
      ;;
  esac

  if [ -z "$patch" ]; then
    warn "PHP $ver: khong doc duoc patch level, tu kiem tra lai"
  elif [ "$patch" -lt "$min" ]; then
    crit "PHP $ver < $branch.$min: CHUA VA PHP2Shell (RCE khong xac thuc, CVSS 9.2)"
    note "Cap nhat ngay, sau do restart TOAN BO worker (FPM, mod_php, queue CLI)."
  else
    ok "PHP $ver: da co ban va PHP2Shell (toi thieu $branch.$min)"
  fi
}

# ---------------------------------------------------------------------------
# Audit một binary PHP
# ---------------------------------------------------------------------------
audit_php_bin() {
  local bin="$1"

  section "PHP binary: $bin"
  "$bin" -v 2>/dev/null | head -1 || warn "khong chay duoc $bin -v"
  check_php2shell "$bin"

  info "php.ini va scan dir:"
  "$bin" --ini 2>/dev/null | grep -E 'Loaded Configuration File|Scan this dir|Additional .ini' | while IFS= read -r l; do
    note "$l"
  done

  info "cau hinh quan trong:"
  "$bin" -r '
    $keys = [
      "memory_limit", "max_execution_time", "max_input_vars",
      "post_max_size", "upload_max_filesize", "realpath_cache_size",
      "opcache.enable", "opcache.memory_consumption",
      "opcache.max_accelerated_files", "opcache.validate_timestamps",
      "opcache.jit", "opcache.jit_buffer_size"
    ];
    foreach ($keys as $k) {
      printf("%s=%s\n", $k, ini_get($k));
    }
  ' 2>/dev/null | while IFS= read -r l; do
    note "$l"
  done

  if "$bin" -m 2>/dev/null | grep -q '^Zend OPcache$'; then
    ok "OPcache extension da load"
  else
    warn "OPcache extension CHUA load cho $bin"
  fi

  if "$bin" -m 2>/dev/null | grep -q '^redis$'; then
    info "redis extension da load"
  else
    info "redis extension chua load (binh thuong neu khong dung Redis)"
  fi

  if "$bin" -m 2>/dev/null | grep -q '^apcu$'; then
    info "apcu extension da load"
    note "APCu dung shared memory chung cho cac worker cung FPM master."
    note "Tren shared hosting, can prefix theo site hoac bat isolated FPM."
  fi
}

# ---------------------------------------------------------------------------
# Audit dịch vụ FPM
# ---------------------------------------------------------------------------
audit_fpm_services() {
  local units u state main mem_raw tasks mem_mb wpids rss_kb workers
  section "Dich vu PHP-FPM"

  if ! have systemctl; then
    warn "khong co systemctl - bo qua kiem tra service FPM"
    return 0
  fi

  units="$(systemctl list-units --type=service --all 'php-fpm*.service' --no-legend 2>/dev/null | awk '{print $1}')"
  if [ -z "$units" ]; then
    warn "khong thay service php-fpm*.service"
    return 0
  fi

  for u in $units; do
    state="$(systemctl is-active "$u" 2>/dev/null || true)"
    info "$u: ${state:-unknown}"
    [ "$state" = "active" ] || continue

    main="$(systemctl show "$u" -p MainPID --value 2>/dev/null || true)"
    tasks="$(systemctl show "$u" -p Tasks --value 2>/dev/null || true)"
    mem_raw="$(systemctl show "$u" -p MemoryCurrent --value 2>/dev/null || true)"

    case "$mem_raw" in
      '' | *[!0-9]*) mem_mb="n/a" ;;
      *) mem_mb="$((mem_raw / 1024 / 1024)) MB" ;;
    esac

    info "MainPID=${main:-?} Tasks=${tasks:-?} MemoryCurrent=${mem_mb}"

    if [ -n "${main:-}" ] && [ "$main" -gt 0 ] 2>/dev/null; then
      mapfile -t wpids < <(pgrep -P "$main" 2>/dev/null)
      workers="${#wpids[@]}"
      if [ "$workers" -gt 0 ]; then
        rss_kb="$(ps -o rss= -p "${wpids[@]}" 2>/dev/null | awk '{s+=$1; n++} END {if (n) printf "%.1f", s/n/1024; else print "0"}')"
        info "worker: $workers, RSS trung binh: ${rss_kb} MB"
      else
        info "worker: 0 (master dang cho request hoac vua restart)"
      fi
    fi
  done
}

# ---------------------------------------------------------------------------
# Audit socket
# ---------------------------------------------------------------------------
audit_sockets() {
  local count
  section "Socket PHP-FPM"
  count="$(find /usr/local/php*/sockets -maxdepth 1 -type s -name '*.sock' 2>/dev/null | wc -l | tr -d ' ')"
  info "so socket tim thay: ${count:-0}"

  if [ "${count:-0}" -gt 0 ]; then
    find /usr/local/php*/sockets -maxdepth 1 -type s -name '*.sock' -printf '%m %u %g %p\n' 2>/dev/null \
      | head -8 | while IFS= read -r l; do
        note "$l"
      done
  fi
}

# ---------------------------------------------------------------------------
# Audit pool FPM và trần worker
# ---------------------------------------------------------------------------
audit_pools() {
  local pool_files=() f mc total_max missing sample avg_rss_kb ram_mb worst_mb
  section "Pool PHP-FPM (per-user)"

  while IFS= read -r -d '' f; do
    pool_files+=("$f")
  done < <(find /usr/local/directadmin/data/users -path '*/php/php-fpm*.conf' -type f -print0 2>/dev/null)

  if [ ${#pool_files[@]} -eq 0 ]; then
    warn "khong thay file pool trong /usr/local/directadmin/data/users/*/php/"
    return 0
  fi

  info "so file pool: ${#pool_files[@]}"

  total_max=0
  missing=0
  sample=0

  for f in "${pool_files[@]}"; do
    mc="$(awk -F= '/^[[:space:]]*pm\.max_children[[:space:]]*=/{gsub(/[^0-9]/, "", $2); print $2; exit}' "$f")"
    if [ -n "$mc" ]; then
      total_max=$((total_max + mc))
    else
      missing=$((missing + 1))
    fi

    if [ "$sample" -lt 3 ]; then
      info "mau: $f"
      awk -F= '
        /^[[:space:]]*(pm|pm\.max_children|pm\.max_requests|pm\.process_idle_timeout|request_terminate_timeout|request_slowlog_timeout)[[:space:]]*=/ {
          gsub(/^[[:space:]]+|[[:space:]]+$/, "", $1);
          gsub(/^[[:space:]]+|[[:space:]]+$/, "", $2);
          printf("    %s = %s\n", $1, $2)
        }
      ' "$f"
      sample=$((sample + 1))
    fi
  done

  info "tong pm.max_children (tran ly thuyet): $total_max"
  [ "$missing" -gt 0 ] && info "so pool khong doc duoc max_children: $missing"

  avg_rss_kb="$(ps -eo rss,comm 2>/dev/null | awk '/php-fpm/ {s+=$1; n++} END {if (n) print int(s/n); else print 0}')"
  ram_mb="$(awk '/MemTotal/ {print int($2/1024)}' /proc/meminfo 2>/dev/null || echo 0)"

  if [ "${avg_rss_kb:-0}" -gt 0 ] && [ "$total_max" -gt 0 ] && [ "${ram_mb:-0}" -gt 0 ]; then
    worst_mb=$((total_max * avg_rss_kb / 1024))
    info "RSS trung binh: $((avg_rss_kb / 1024)) MB, RAM tong: ${ram_mb} MB"
    info "neu moi pool dat max_children cung luc: ${worst_mb} MB"

    if [ "$worst_mb" -gt "$ram_mb" ]; then
      crit "tran ly thuyet ${worst_mb} MB > RAM ${ram_mb} MB - nguy co OOM khi tai cao"
      note "Giam php_fpm_max_children_default hoac override tung user; theo doi RSS."
    elif [ "$worst_mb" -gt "$((ram_mb * 80 / 100))" ]; then
      warn "tran ly thuyet ${worst_mb} MB > 80% RAM ${ram_mb} MB - can theo doi"
    else
      ok "tran ly thuyet nam trong 80% RAM"
    fi
  else
    info "chua du du lieu worker de tinh tran RAM (co the FPM dang ranh)"
  fi

  if [ -n "$DA_CMD" ]; then
    local def
    def="$(run_da config-get php_fpm_max_children_default || true)"
    [ -n "$def" ] && info "php_fpm_max_children_default=$def"
    def="$(run_da config-get isolated_fpm || true)"
    [ -n "$def" ] && info "isolated_fpm=$def"
  fi
}

# ---------------------------------------------------------------------------
# Audit log FPM
# ---------------------------------------------------------------------------
audit_logs() {
  local f hits
  section "Log PHP-FPM"

  for f in /usr/local/php*/var/log/php-fpm.log; do
    [ -f "$f" ] || continue
    info "$f"
    hits="$(tail -n 3000 "$f" 2>/dev/null | grep -Eic 'max_children|segfault|oom|out of memory|killed|emergency' || true)"
    if [ "${hits:-0}" -gt 0 ]; then
      warn "$hits dong bat thuong trong 3000 dong cuoi"
      tail -n 3000 "$f" 2>/dev/null \
        | grep -Ei 'max_children|segfault|oom|out of memory|killed|emergency' \
        | tail -5 | while IFS= read -r l; do
          note "$l"
        done
    else
      ok "khong thay max_children/segfault/OOM trong 3000 dong cuoi"
    fi
  done

  if have journalctl; then
    hits="$(journalctl -u 'php-fpm*' --since '7 days ago' --no-pager 2>/dev/null \
      | grep -Eic 'max_children|segfault|oom|out of memory|killed' || true)"
    if [ "${hits:-0}" -gt 0 ]; then
      warn "journal 7 ngay: $hits dong bat thuong"
    fi
  fi
}

# ---------------------------------------------------------------------------
# Audit hệ thống
# ---------------------------------------------------------------------------
audit_system() {
  local cores load1 load_int mem_total mem_avail swap_total disk_pct inode_pct
  section "He thong"

  cores="$(nproc 2>/dev/null || echo 1)"
  read -r load1 _ < /proc/loadavg 2>/dev/null || load1="0.00"
  load_int="${load1%.*}"

  mem_total="$(awk '/MemTotal/ {print int($2/1024)}' /proc/meminfo 2>/dev/null || echo 0)"
  mem_avail="$(awk '/MemAvailable/ {print int($2/1024)}' /proc/meminfo 2>/dev/null || echo 0)"
  swap_total="$(awk '/SwapTotal/ {print int($2/1024)}' /proc/meminfo 2>/dev/null || echo 0)"

  info "CPU core: $cores | load1: $load1 | RAM: ${mem_total} MB | RAM trong: ${mem_avail} MB | swap: ${swap_total} MB"

  if [ "${load_int:-0}" -gt "$((cores * 2))" ]; then
    warn "load trung binh cao hon 2x so core"
  fi

  if [ "${swap_total:-0}" -gt 0 ] && [ "${mem_avail:-0}" -lt 512 ]; then
    warn "RAM trong thap (<512 MB) va co swap - nguy co OOM"
  fi

  if have df; then
    disk_pct="$(df -P / 2>/dev/null | awk 'NR==2 {gsub(/%/, "", $5); print $5}')"
    inode_pct="$(df -Pi / 2>/dev/null | awk 'NR==2 {gsub(/%/, "", $5); print $5}')"
    info "disk /: ${disk_pct:-?}% | inode /: ${inode_pct:-?}%"
    [ -n "${disk_pct:-}" ] && [ "$disk_pct" -gt 85 ] 2>/dev/null && warn "disk / tren 85%"
    [ -n "${inode_pct:-}" ] && [ "$inode_pct" -gt 85 ] 2>/dev/null && warn "inode / tren 85%"
  fi
}

# ---------------------------------------------------------------------------
# Audit DirectAdmin options
# ---------------------------------------------------------------------------
audit_directadmin() {
  local opt def
  section "DirectAdmin / CustomBuild"
  info "DirectAdmin: da phat hien"
  [ -n "$DA_CMD" ] && info "lenh da: $DA_CMD" || info "khong thay lenh 'da' trong PATH"

  if [ -n "$DA_CMD" ]; then
    def="$(run_da config-get php_version_selector || true)"
    [ -n "$def" ] && info "php_version_selector=$def"
    def="$(run_da config-get php_fpm_max_children_default || true)"
    [ -n "$def" ] && info "php_fpm_max_children_default=$def"
  fi

  opt=/usr/local/directadmin/custombuild/options.conf
  if [ -r "$opt" ]; then
    info "options.conf:"
    grep -E '^(php[0-9]_|webserver=|opcache=|php_ini|php_htscanner|secure_php)' "$opt" 2>/dev/null \
      | while IFS= read -r l; do
        note "$l"
      done
  else
    warn "khong doc duoc $opt (can quyen root?)"
  fi

  if [ -n "$DA_CMD" ]; then
    info "phien ban software (da build versions):"
    run_da build versions 2>/dev/null | head -15 | while IFS= read -r l; do
      note "$l"
    done
  fi
}

# ---------------------------------------------------------------------------
# Tổng kết
# ---------------------------------------------------------------------------
summary() {
  section "Tong ket"
  info "canh bao: $WARN | nghiem trong: $CRIT"

  if [ "$CRIT" -gt 0 ]; then
    crit "co loi nghiem trong - doc cac dong [x] o tren"
  elif [ "$WARN" -gt 0 ]; then
    warn "co canh bao - doc cac dong [!] o tren"
  else
    ok "khong thay van de ro rang trong pham vi script kiem tra"
  fi

  info "script chi doc - khong thay doi cau hinh, khong restart service"
  info "so lieu chi de tham khao; luon kiem chung voi phpinfo() va log thuc te"
}

main() {
  printf '%s\n' "DirectAdmin PHP audit (read-only)"
  printf 'Thoi gian: %s\n' "$(date -Is 2>/dev/null || date)"
  printf 'Host: %s\n' "$(hostname 2>/dev/null || echo unknown)"

  if [ "$(id -u 2>/dev/null || echo 1)" -ne 0 ]; then
    warn "khong chay bang root - mot so file/log co the khong doc duoc"
  fi

  detect_directadmin
  collect_php_bins

  if [ "$DA_FOUND" -eq 1 ]; then
    audit_directadmin
  else
    section "DirectAdmin / CustomBuild"
    info "khong tim thay DirectAdmin tren may nay"
    info "chi chay phan kiem tra PHP tong quat (neu co)"
  fi

  if [ ${#PHP_BINS[@]} -eq 0 ]; then
    section "PHP"
    info "khong tim thay binary PHP nao trong /usr/local/php*/bin, /usr/bin"
    info "neu day la may chu web, kiem tra duong dan cai dat PHP"
  else
    local b
    for b in "${PHP_BINS[@]}"; do
      audit_php_bin "$b"
    done
  fi

  if [ "$DA_FOUND" -eq 1 ]; then
    audit_fpm_services
    audit_sockets
    audit_pools
    audit_logs
  fi

  audit_system
  summary

  if [ "$CRIT" -gt 0 ] || [ "$WARN" -gt 0 ]; then
    return 1
  fi
  return 0
}

main "$@"
