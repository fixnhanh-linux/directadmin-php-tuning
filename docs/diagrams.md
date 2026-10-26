# Sơ đồ kiến trúc & luồng vận hành

Bộ sơ đồ cho playbook [tối ưu PHP trên DirectAdmin](../README.md). Tất cả vẽ bằng **Mermaid** — GitHub render thành hình ngay trong trang, không cần cài gì. Muốn sửa thì sửa text, không phải sửa ảnh.

| # | Sơ đồ | Trả lời câu hỏi |
|---|---|---|
| 1 | [Luồng request](#1-luồng-request-từ-trình-duyệt-đến-database) | Request đi qua những tầng nào? |
| 2 | [Nguồn và kết quả cấu hình](#2-nguồn-và-kết-quả-cấu-hình) | Sửa file nào thì không bị ghi đè? |
| 3 | [Pool PHP-FPM theo user](#3-pool-php-fpm-theo-user) | Vì sao 12 domain chia nhau 4 worker? |
| 4 | [Vòng đời worker `ondemand`](#4-vòng-đời-worker-ondemand) | Worker sinh ra và chết khi nào? |
| 5 | [OPcache nằm ở đâu](#5-opcache-nằm-ở-đâu) | Vì sao bật 4 phiên bản PHP lại tốn 1 GB RAM? |
| 6 | [Cây quyết định `max_children`](#6-cây-quyết-định-max_children) | Tính số worker theo RAM thế nào? |
| 7 | [Chuỗi timeout lồng nhau](#7-chuỗi-timeout-lồng-nhau) | Vì sao có 504 dù PHP vẫn đang chạy? |
| 8 | [Vòng lặp tối ưu](#8-vòng-lặp-tối-ưu) | Quy trình đo — đổi — đo — rollback |
| 9 | [Ba tầng cache](#9-ba-tầng-cache) | OPcache, Redis và page cache khác nhau ở đâu? |
| 10 | [Kế hoạch 60 phút](#10-kế-hoạch-60-phút) | Làm gì, theo thứ tự nào? |

---

## 1. Luồng request: từ trình duyệt đến database

```mermaid
flowchart LR
    U["Người dùng"] --> CDN["CDN / WAF"]
    CDN --> NG["nginx<br/>static + proxy"]
    NG -->|proxy_read_timeout 65s| AP["Apache<br/>nginx_apache"]
    AP -->|fastcgi| FP["PHP-FPM<br/>pool USER"]
    FP --> DB[("MySQL / MariaDB")]
    FP --> RD[("Redis")]
    NG -.->|file tĩnh| DSK[("NVMe")]

    classDef client fill:#FFF4E5,stroke:#F59E0B,color:#7C2D12
    classDef web fill:#E0F2FE,stroke:#0284C7,color:#0C4A6E
    classDef php fill:#EDE9FE,stroke:#7C3AED,color:#3B0764
    classDef data fill:#DCFCE7,stroke:#16A34A,color:#052E16
    class U,CDN client
    class NG,AP web
    class FP php
    class DB,RD,DSK data
```

Đọc sơ đồ này theo hai hướng:

- **Đi từ trái sang phải**: đó là đường đi của một request. Tầng nào cũng có timeout, buffer và giới hạn kích thước riêng.
- **Nhìn từ phải sang trái khi có lỗi**: 502/504 hiếm khi do tầng người dùng nhìn thấy. Nó thường do tầng **sau** đã chết hoặc đã cắt kết nối.

Nếu server dùng `nginx` thuần, bỏ nhánh Apache. Nếu dùng LiteSpeed/OpenLiteSpeed, thay `PHP-FPM` bằng `LSPHP` và bỏ Apache — cơ chế tính worker cũng khác, đừng áp công thức FPM.

---

## 2. Nguồn và kết quả cấu hình

Đây là sơ đồ quan trọng nhất để không mất công chỉnh sửa. DirectAdmin là hệ thống **sinh cấu hình từ template**: sửa nhầm phía "kết quả" thì lần `da build` tiếp theo sẽ xoá sạch.

```mermaid
flowchart LR
    subgraph SRC["NGUỒN — sửa ở đây"]
        direction TB
        O["options.conf<br/>phiên bản, handler"]
        TC["templates/custom/"]
        PD["php.conf.d/99-*.ini"]
        OC["custom/opcache/opcache.ini"]
        CC["CUSTOM1 / CUSTOM2"]
    end

    C1["da build php"]
    C2["da build rewrite_confs"]
    C3["da build opcache"]

    subgraph GEN["KẾT QUẢ — đừng sửa"]
        direction TB
        B1["php.ini"]
        B2["10-directadmin.ini"]
        B3["php-fpm83.conf<br/>pool theo user"]
        B4["vhost nginx / httpd"]
    end

    O --> C1
    O --> C2
    PD --> C1
    OC --> C3
    TC --> C2
    CC --> C2

    C1 --> B1
    C1 --> B2
    C3 --> B2
    C2 --> B3
    C2 --> B4

    classDef src fill:#DCFCE7,stroke:#16A34A,color:#052E16
    classDef cmd fill:#E0F2FE,stroke:#0284C7,color:#0C4A6E
    classDef gen fill:#FEE2E2,stroke:#DC2626,color:#7F1D1D
    class O,TC,PD,OC,CC src
    class C1,C2,C3 cmd
    class B1,B2,B3,B4 gen

```

Quy tắc rút ra:

- Cần bền qua rebuild → sửa **cột xanh**.
- Đã sửa cột đỏ và thấy mất sau `da build` → đó là hành vi đúng của hệ thống, không phải bug.
- `php.ini` nằm ở giữa: bền nếu `php_ini=no`, có thể bị ghi đè nếu `php_ini=yes`.

---

## 3. Pool PHP-FPM theo user

DirectAdmin sinh **một pool cho mỗi user, cho mỗi phiên bản PHP**. Không phải mỗi domain.

```mermaid
flowchart TB
    WEB["nginx / Apache"] -->|unix socket| M["Master php-fpm83"]

    M --> PA["Pool alice<br/>max_children 4"]
    M --> PB["Pool bob<br/>max_children 4"]
    M --> PC["Pool carol (Woo)<br/>max_children 12"]

    PA --> WA["worker 0..4"]
    PB --> WB["worker 0..4"]
    PC --> WC["worker 0..12"]

    M -.- OPC["OPcache<br/>shared theo master"]

    classDef web fill:#E0F2FE,stroke:#0284C7,color:#0C4A6E
    classDef master fill:#FEF3C7,stroke:#D97706,color:#78350F
    classDef pool fill:#EDE9FE,stroke:#7C3AED,color:#3B0764
    classDef worker fill:#F1F5F9,stroke:#64748B,color:#0F172A
    class WEB web
    class M master
    class PA,PB,PC pool
    class WA,WB,WC worker
```

Ba điều sơ đồ này nói rõ:

1. **Tất cả domain của alice dùng chung 4 worker.** Một site bị crawl → 11 site còn lại xếp hàng.
2. **`max_children` là trần đồng thời, không phải số worker luôn chạy.** Với `ondemand`, lúc rảnh pool có 0 worker.
3. **OPcache dùng chung theo master**, không theo pool. Đây là lý do cách ly OPcache chỉ có được khi tách master (isolated FPM).

Muốn cách ly theo domain: tách tài khoản, hoặc bật isolated FPM (mỗi user một master, tốn thêm ~20 MB/user khi rảnh).

---

## 4. Vòng đời worker `ondemand`

```mermaid
stateDiagram-v2
    direction LR
    [*] --> Ranh: pool khởi động
    Ranh --> Ban: request đến
    Ban --> Ranh: xử lý xong
    Ranh --> [*]: rảnh quá 20s
    Ban --> [*]: đủ 500 request
```

Hai tham số quyết định vòng đời:

| Tham số | Mặc định DA | Ý nghĩa |
|---|---|---|
| `pm.process_idle_timeout` | `20` giây | Worker rảnh bao lâu thì bị đóng |
| `pm.max_requests` | `500` | Worker phục vụ bao nhiêu request thì tự tái sinh |

`max_requests` giới hạn rò rỉ bộ nhớ: worker chết định kỳ và sinh lại với bộ nhớ sạch. Đặt quá cao (10000) thì worker phình dần; quá thấp (50) thì spawn liên tục, tốn CPU.

Hệ quả của `ondemand`: request đầu tiên sau thời gian rảnh phải chờ spawn — thường 20–80 ms. Trên shared hosting, đây là đánh đổi đúng: tiết kiệm RAM hơn nhiều so với việc giữ worker thường trực cho 180 tài khoản ít traffic.

---

## 5. OPcache nằm ở đâu

```mermaid
flowchart LR
    subgraph V83["PHP 8.3 — một master"]
        direction TB
        P83A["Pool alice"]
        P83B["Pool bob"]
        O83["OPcache 256 MB"]
        P83A --> O83
        P83B --> O83
    end

    subgraph V84["PHP 8.4 — một master khác"]
        direction TB
        P84A["Pool alice"]
        O84["OPcache 256 MB"]
        P84A --> O84
    end

    subgraph ISO["Isolated FPM — mỗi user một master"]
        direction TB
        I1["alice: OPcache riêng 64 MB"]
        I2["bob: OPcache riêng 64 MB"]
        I3["carol: OPcache riêng 64 MB"]
    end

    V83 ~~~ V84
    V84 ~~~ ISO

    classDef cache fill:#FEF3C7,stroke:#D97706,color:#78350F
    classDef pool fill:#EDE9FE,stroke:#7C3AED,color:#3B0764
    classDef iso fill:#FCE7F3,stroke:#DB2777,color:#831843
    class O83,O84 cache
    class P83A,P83B,P84A pool
    class I1,I2,I3 iso
```

Phép tính cần nhớ:

| Cấu hình | OPcache dùng |
|---|---|
| 1 phiên bản, shared pool | 256 MB |
| 3 phiên bản, shared pool | 3 × 256 MB = **768 MB** |
| 180 user, isolated FPM, 64 MB mỗi master | 180 × 64 MB = **11.5 GB** |

Dòng cuối là cái bẫy thật: bật isolated FPM rồi giữ nguyên OPcache 256 MB/user sẽ OOM ngay. Isolated FPM phải đi kèm giảm mạnh `opcache.memory_consumption` (32–64 MB) hoặc chỉ bật cho nhóm user thật sự cần.

---

## 6. Cây quyết định `max_children`

```mermaid
flowchart TD
    A["Đo RSS trung bình 1 worker"] --> B["RAM_cho_PHP = tổng − OS − DB − Redis − dự phòng"]
    B --> C["workers_tối_đa = RAM_cho_PHP ÷ RSS"]
    C --> D{"Số user hoạt động<br/>đồng thời?"}
    D -->|ít, dưới 30| E["max_children = workers ÷ 30"]
    D -->|nhiều, trên 200| F["max_children 3–5<br/>override user busy"]
    E --> G{"max_children × RSS<br/>vượt 80% RAM?"}
    F --> G
    G -->|Có| H["Giảm tiếp<br/>hoặc thêm RAM"]
    G -->|Không| I["Áp dụng<br/>theo dõi 10 phút"]
    H --> I
    I --> J{"Log còn<br/>max_children?"}
    J -->|Có, và RAM còn| K["Tăng riêng user đó<br/>bằng MAX_CHILDREN"]
    J -->|Không| L["Giữ cấu hình<br/>ghi change log"]

    classDef step fill:#E0F2FE,stroke:#0284C7,color:#0C4A6E
    classDef dec fill:#FEF3C7,stroke:#D97706,color:#78350F
    classDef ok fill:#DCFCE7,stroke:#16A34A,color:#052E16
    class A,B,C,E,F,H step
    class D,G,J dec
    class I,K,L ok
```

Lưu ý: nhánh "nhiều user" **không** có nghĩa là đặt 1 cho tất cả. Nó có nghĩa là mặc định thấp, rồi nâng riêng cho user thật sự cần — vì `max_children` là trần lý thuyết nhân với số pool.

---

## 7. Chuỗi timeout lồng nhau

```mermaid
flowchart LR
    subgraph N["nginx — 65s"]
        subgraph A["Apache — 65s"]
            subgraph F["FPM — request_terminate_timeout 60s"]
                subgraph P["PHP — max_execution_time 60s"]
                    APP["Ứng dụng"]
                end
            end
        end
    end

    classDef app fill:#DCFCE7,stroke:#16A34A,color:#052E16
    class APP app
```

Nguyên tắc: **tầng ngoài phải kiên nhẫn hơn tầng trong**. Nếu nginx cắt ở 30s trong khi PHP cần 50s, người dùng nhận 504, còn PHP vẫn chạy tiếp và vẫn chiếm worker — tệ nhất trong cả hai thế giới: khách thấy lỗi, server vẫn tải.

Một điểm dễ nhầm: `max_execution_time` tính **CPU time**, không phải thời gian thực. Request chờ MySQL 5 phút có thể không bị nó kill. Vì vậy cần thêm `request_terminate_timeout` của FPM (wall clock) làm lưới an toàn.

---

## 8. Vòng lặp tối ưu

```mermaid
flowchart TD
    A["1. Vá bảo mật"] --> B["2. Đo baseline"]
    B --> C["3. Đổi MỘT thứ"]
    C --> D["4. Theo dõi 10 phút"]
    D --> E{"p95 và tỷ lệ lỗi<br/>tốt hơn?"}
    E -->|Không| G["Rollback"]
    E -->|Có| F["5. Ghi change log<br/>đo lại sau 24h / 7 ngày"]
    F --> H{"Ổn định?"}
    H -->|Không| G
    H -->|Có| I["Sang thay đổi tiếp theo"]
    G --> C
    I --> C

    classDef step fill:#E0F2FE,stroke:#0284C7,color:#0C4A6E
    classDef dec fill:#FEF3C7,stroke:#D97706,color:#78350F
    classDef ok fill:#DCFCE7,stroke:#16A34A,color:#052E16
    classDef bad fill:#FEE2E2,stroke:#DC2626,color:#7F1D1D
    class A,B,C,D,F,I step
    class E,H dec
    class G bad

```

Vòng lặp này giải thích vì sao "tối ưu một lần cho xong" không tồn tại: mỗi thay đổi cần một phép đo riêng, và mỗi phép đo cần thời gian để lộ vấn đề (10 phút cho lỗi rõ, 24 giờ cho xu hướng, 7 ngày cho rò rỉ bộ nhớ).

---

## 9. Ba tầng cache

```mermaid
flowchart LR
    R["Request"] --> PC["Page cache<br/>CDN / LSCache / nginx"]
    PC -->|miss| OC["OPcache<br/>bytecode PHP"]
    OC --> EX["PHP thực thi"]
    EX --> OB["Object cache<br/>Redis / APCu"]
    OB -->|miss| DB[("MySQL")]
    EX --> SS["Session<br/>Redis / file"]

    classDef layer fill:#E0F2FE,stroke:#0284C7,color:#0C4A6E
    classDef data fill:#DCFCE7,stroke:#16A34A,color:#052E16
    class PC,OC,OB,SS layer
    class DB data
```

| Tầng | Cache cái gì | Không cache được | Nếu tắt |
|---|---|---|---|
| Page cache | HTML cuối cùng | Trang đăng nhập, giỏ hàng | TTFB cao, CPU tăng |
| OPcache | Bytecode đã biên dịch | Kết quả query | CPU tăng mạnh, rõ nhất với WP |
| Object cache | Kết quả query/object | Toàn bộ trang | DB chịu tải lặp lại |
| Session store | Session id → dữ liệu | — | User mất đăng nhập khi scale ngang |

Ba tầng này **bổ sung**, không thay thế nhau. Một lỗi phổ biến: bật Redis object cache rồi tưởng đã có page cache, trong khi mỗi request vẫn chạy toàn bộ WordPress.

---

## 10. Kế hoạch 60 phút

```mermaid
flowchart LR
    subgraph P1["0-10 phút — Kiểm tra"]
        direction TB
        A1["Vá bảo mật PHP"] --> A2["Chạy audit chỉ-đọc"] --> A3["Chụp baseline"]
    end

    subgraph P2["10-55 phút — Mỗi lần một thay đổi"]
        direction TB
        B1["10-20: OPcache"] --> B2["20-30: FPM max_children"] --> B3["30-40: php.ini"] --> B4["40-50: Redis"] --> B5["50-55: Timeout"]
    end

    subgraph P3["55-60 phút — Xác nhận"]
        direction TB
        C1["Benchmark lại"] --> C2{"Giữ hay rollback?"}
    end

    P1 --> P2 --> P3

    classDef phase fill:#E0F2FE,stroke:#0284C7,color:#0C4A6E
    classDef dec fill:#FEF3C7,stroke:#D97706,color:#78350F
    class A1,A2,A3,B1,B2,B3,B4,B5,C1 phase
    class C2 dec

```

Nếu server đông user, đừng nén tất cả vào 60 phút. Chia theo đêm: đêm 1 OPcache + FPM, đêm 2 php.ini, đêm 3 Redis. Mỗi đêm vẫn giữ nguyên tắc **một thay đổi, một phép đo**.

---

## Bản ASCII (đọc offline, không cần Mermaid)

```text
                        ┌──────────────┐
                        │  Người dùng  │
                        └──────┬───────┘
                               │
                        ┌──────▼───────┐
                        │  CDN / WAF   │
                        └──────┬───────┘
                               │
                        ┌──────▼───────┐        ┌──────────┐
                        │    nginx     │───────►│  NVMe    │
                        │ static+proxy │        │ file tĩnh│
                        └──────┬───────┘        └──────────┘
                               │ proxy 65s
                        ┌──────▼───────┐
                        │    Apache    │
                        └──────┬───────┘
                               │ fastcgi
                        ┌──────▼───────────────────────┐
                        │  PHP-FPM  (1 master/version) │
                        │  ┌────────┐ ┌────────┐       │
                        │  │ alice  │ │  bob   │  ...  │
                        │  │ max 4  │ │ max 4  │       │
                        │  └───┬────┘ └───┬────┘       │
                        │      └────┬─────┘            │
                        │      OPcache (shared)        │
                        └───────────┼──────────────────┘
                                    │
                     ┌──────────────┴──────────────┐
                     │                             │
              ┌──────▼───────┐             ┌───────▼──────┐
              │    MySQL     │             │    Redis     │
              │  (query)     │             │ object+session│
              └──────────────┘             └──────────────┘
```

---

> [!TIP]
> Khi trình bày sự cố với đồng nghiệp hoặc khách hàng, gửi kèm sơ đồ 1 và sơ đồ 3.
> Hai hình đó trả lời được 80% câu hỏi "vì sao web chậm / vì sao 502" mà không cần
> giải thích dài.
