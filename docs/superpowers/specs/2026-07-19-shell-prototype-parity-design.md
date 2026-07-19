# Thiết kế đồng bộ khung giao diện (sidebar + login) theo prototype

## Mục tiêu

`docs/engineering/DEVELOPMENT_PLAN.vi.md` mục 1B ghi rõ: "Không port pixel-perfect giao diện prototype — ưu tiên đủ chức năng, style tối giản" — quyết định tạm thời cho giai đoạn đầu. Chủ dự án nay muốn quay lại đúng nguyên tắc gốc của PRD: "Prototype là đặc tả hành vi UI — code thật phải tái hiện đúng, không sáng tạo lại".

Phạm vi lần này: **chỉ phần khung** — sidebar, thanh điều hướng theo vai trò, user card, và màn đăng nhập — theo đúng thị giác của `prototype/index.html` + `prototype/styles.css`. Các trang bên trong (builder, review, export, admin dashboard 6 card...) **giữ nguyên tạm thời**, để task riêng sau nhằm tránh một PR quá lớn.

Đã xác nhận với chủ dự án: **vẫn dùng 1 form đăng nhập chung** (không tách `/login` riêng cho Admin/Giáo viên) — hành vi redirect theo vai trò sau khi đăng nhập đã đúng từ nhánh `fix/teacher-only-exams`, không đổi.

## Khảo sát prototype

Prototype không có màn đăng nhập thật — chỉ có nút "Chuyển vai trò xem thử" trong sidebar để demo cả 2 giao diện trên cùng 1 trang tĩnh. Phần này **không** đưa vào code thật (không có ý nghĩa với auth thật). Phần đáng port:

- `.app-shell`: grid 2 cột `236px` (sidebar) + phần còn lại.
- `.sidebar`: nền gradient tối, sticky full-height, chứa brand, main-nav, user-card.
- `.main-nav .nav-item`: icon + label, trạng thái `.active` có vạch chỉ thị bên trái.
- `.user-card`: avatar tròn (chữ cái đầu tên), tên + vai trò.
- `.workspace`: khung nội dung `max-width:1420px`, padding, thay cho khung `max-width:960` hiện tại — cho phép trang trong rộng hơn khi làm lại sau.
- Bộ token màu/spacing/shadow đầy đủ trong `:root` của `styles.css`.

Nav item theo vai trò (dùng route đang có, không phải danh sách đầy đủ trong prototype vì nhiều mục chưa có trang thật — kho kiến thức/dạng bài/thư viện ảnh/cấu hình AI dời sang 1D):

| Vai trò | Nav item | Route |
|---|---|---|
| Giáo viên | Đề của tôi | `/exams` |
| Admin | Tổng quan | `/admin` |
| Admin | Quản lý giáo viên | `/admin/teachers` |
| Admin | Audit log | `/admin/audit-logs` |

Audit log không có trong prototype (tính năng phát sinh sau) — dùng icon khác (bank) để không trùng icon với "Tổng quan" (layers) và "Quản lý giáo viên" (users).

## Thay đổi

### CSS (`frontend/src/index.css`)
Đưa nguyên token màu (`--surface-soft`, `--border-strong`, `--primary-soft`, `--success*`, `--shadow-*`, `--radius`) và các khối class sau từ `prototype/styles.css`, giữ nguyên tên class để trang trong port sau này dùng lại được không cần đổi tên: `.app-shell`, `.sidebar`, `.brand*`, `.main-nav`, `.nav-item(.active)`, `.user-card`, `.avatar`, `.user-meta`, `.icon`, `.workspace`, `.button(.primary/.secondary/.compact/.large)`, reset `label/select/input/textarea` cơ bản. Không đưa các class chỉ dùng cho trang trong (`.builder-grid`, `.q-card`, `.admin-grid`...) — để lại cho task port từng trang sau.

Bỏ `#root { padding: 24px }` (sidebar cần full-bleed); `.center-screen` (màn đăng nhập/loading) tự có `padding: 24px` riêng để không bị dính mép màn hình nhỏ.

Vì toàn bộ trang hiện tại dùng inline style (`style={{...}}`), thêm CSS global cho `label/select/input` không phá gì — inline style luôn thắng CSS ngoài cho cùng thuộc tính.

### Icon (`frontend/src/icons/Icon.tsx`, mới)
Prototype dùng SVG sprite (`<symbol>` + `<use>`). Port sang React tự nhiên hơn: mỗi icon là 1 component nhỏ trả về `<svg className="icon">` với path/circle giữ nguyên tọa độ gốc — cùng thị giác, đúng idiom React, không cần mount sprite `<defs>` toàn cục. Chỉ tạo 4 icon cần cho lần này: `DocIcon`, `LayersIcon`, `UsersIcon`, `BankIcon`. Icon khác (pencil/trash/plus/sparkle/grip...) để dành khi port trang trong.

### `frontend/src/Layout.tsx`
Viết lại theo `.app-shell`: sidebar (brand → `homePath`, nav theo vai trò dùng bảng route trên, user-card avatar+tên+vai trò), badge số lượt còn lại cho Giáo viên (giữ tính năng cũ, chuyển vị trí vào sidebar), nút "Đăng xuất" trong sidebar (prototype không có sẵn vì không phải auth thật — thêm mới, phong cách tối giản khớp bảng màu sidebar). `<Outlet />` bọc trong `.main-content > .workspace` thay cho khung `max-width:960` cũ.

Không đổi bất kỳ logic route guard nào trong `App.tsx` (`teacherOnly`, redirect theo `isAdmin`) — chỉ đổi phần hiển thị của `Layout`.

### `frontend/src/LoginForm.tsx`
Đổi từ inline style sang dùng `.button.primary.large`, giữ nguyên toàn bộ logic (state, gọi API, xử lý lỗi) không đổi. Thêm `brand-mark` ở đầu card cho nhất quán thị giác với sidebar.

## Không thuộc phạm vi

- Không tách 2 trang login riêng cho Admin/Giáo viên (đã xác nhận giữ 1 form chung).
- Không port `ExamListPage`, `ExamBuilderPage`, `ExamReviewPage`, `ExamExportPage`, `AdminOverviewPage`, `AdminTeachersPage`, `AdminAuditLogsPage` sang style mới — để task riêng.
- Không thêm topbar theo trang (title/autosave động) — prototype có nhưng gắn với nội dung từng trang, để cùng lúc port trang đó.
- Không đổi hành vi routing/redirect theo vai trò.

## Test

- Cập nhật `frontend/src/Layout.test.tsx` và `frontend/src/App.test.tsx` hiện có: giữ nguyên assertion về route/redirect/nav label theo vai trò, chỉ cần chúng vẫn pass sau khi đổi cấu trúc DOM (không dựa vào cấu trúc DOM cụ thể ngoài text/role đã test).
- Kiểm thử thủ công bằng trình duyệt (Playwright MCP hoặc mở dev server): đăng nhập Giáo viên → thấy sidebar tối, nav "Đề của tôi"; đăng nhập Admin → nav 3 mục quản trị; responsive ở màn hẹp sidebar co lại còn icon.

## Tiêu chí hoàn thành

- `npm test -- --run`, `npm run lint`, `npm run build` đều pass.
- Giao diện sau khi đăng nhập có sidebar tối giống thị giác prototype (màu, bo góc, nav active indicator, avatar).
- Màn đăng nhập vẫn 1 form chung, style nhất quán với sidebar mới.
