# Đặc tả chống race-condition theo route cho Review và Export

## Mục tiêu

Ngăn response hoặc continuation của đề cũ cập nhật giao diện sau khi người dùng đã chuyển nhanh sang một `examId` khác trên `ExamReviewPage` hoặc `ExamExportPage`.

Fix bao phủ toàn bộ fetch và mutation của hai trang, không chỉ request tải đề. Backend và API contract không thay đổi.

## Nguyên nhân

Hai page hiện dùng `useEffect(reload, [examId])` và các handler async trực tiếp gọi `setState` sau `await`. React Router tái sử dụng component khi chỉ thay đổi param, nên trong khoảng request mới chưa hoàn tất:

- Dữ liệu đề cũ vẫn có thể render dưới URL mới.
- Response `getExam` cũ có thể ghi đè đề mới.
- Mutation cũ có thể reload sai đề, đổi busy/saving/error của route mới hoặc điều hướng từ route mới.
- `finally` của operation cũ có thể mở khóa state của operation mới.
- StrictMode effect setup/cleanup/setup có thể làm token sai nếu vòng đời không hỗ trợ replay.

## Kiến trúc

Tạo hook frontend dùng chung `useRouteGeneration(routeKey)` chỉ quản lý identity của vòng đời route. Hook không giữ exam data, loading, lỗi hoặc state nghiệp vụ.

Interface:

```typescript
export interface RouteGenerationToken {
  routeKey: string | undefined;
  generation: number;
}

export interface RouteGeneration {
  capture(): RouteGenerationToken;
  isCurrent(token: RouteGenerationToken): boolean;
}

export function useRouteGeneration(routeKey: string | undefined): RouteGeneration;
```

`capture()` lấy snapshot của route và generation hiện hành. `isCurrent(token)` chỉ trả true khi component còn mounted, `routeKey` chưa đổi và generation khớp.

Khi route key đổi, generation tăng và token cũ hết hiệu lực. Khi component unmount, token hiện hành hết hiệu lực. Hook phải hỗ trợ StrictMode effect replay: lần setup thứ hai của cùng route tạo một generation hoạt động mới thay vì để component vĩnh viễn invalid.

Hook nằm tại `frontend/src/routing/useRouteGeneration.ts` và được test độc lập.

## Nguyên tắc dùng token

Mỗi fetch hoặc mutation:

1. Capture token và `targetExamId` trước request.
2. Sau mỗi `await`, kiểm tra `isCurrent(token)` trước mọi `setState`, reload, refresh quota hoặc navigate.
3. `catch` chỉ hiển thị lỗi nếu token còn current.
4. `finally` chỉ xóa busy/saving nếu token còn current và state lock vẫn thuộc operation đó.

Mutation cũ có thể đã được server xử lý thành công; client không hủy hoặc đảo mutation. Fix chỉ đảm bảo continuation cũ không làm hỏng UI của route hiện hành.

## ExamReviewPage

Khi `examId` đổi, page reset ngay:

- `exam=null`
- `error=null`
- `busyQuestionId=null`
- `finishing=false`

Page chỉ render editor khi `exam.id === examId`; nếu không thì hiển thị loading/error. Vì vậy câu hỏi của đề cũ không còn tương tác được dưới URL mới.

Các operation được guard:

- `getExam`
- duyệt/bỏ duyệt câu
- khóa/mở khóa câu
- sinh lại câu
- refresh usage sau sinh lại
- reload sau mutation câu
- hoàn tất kiểm duyệt
- điều hướng sang `/exams/{examId}/export`

Trong lúc có mutation câu hỏi hoặc hoàn tất review đang chạy, khóa tất cả nút mutation khác của trang. Dùng operation ID/token riêng cho lock để `finally` cũ không mở khóa operation mới.

Reload sau mutation dùng đúng `targetExamId` đã capture, không đọc `examId` mới từ closure sau navigation. Nếu mutation của route hiện hành thành công nhưng reload lỗi, giữ dữ liệu hiện có và hiển thị lỗi reload; không xóa lỗi vô điều kiện.

## ExamExportPage

Khi `examId` đổi, page reset ngay:

- `exam=null`
- `error=null`
- `saving=false`
- `exportMode="plain"`
- `variantCount=1`

Page chỉ render form và link DOCX khi `exam.id === examId`.

Các operation được guard:

- `getExam`
- lưu `export_mode` và `variant_count`
- reload sau save
- error/finally của save

Save capture cả `targetExamId`, `exportMode` và `variantCount`. Nếu user chuyển route trước khi response về, response/lỗi/finally của save cũ không cập nhật route mới. Reload sau save dùng ID đã capture và chỉ áp dụng khi token current.

Nếu save hiện hành thành công nhưng reload lỗi, giữ form hiện tại và hiển thị lỗi tải; không xóa lỗi vô điều kiện. Các link DOCX luôn dùng `exam.id` đã xác minh khớp route.

## Xử lý lỗi

- Lỗi request hiện hành giữ copy hiện có: `Không tải được đề`, `Không sinh lại được câu này`, `Chưa thể hoàn tất kiểm duyệt`, `Chưa lưu được cấu hình xuất` hoặc `ApiError.message`.
- Lỗi của token cũ bị bỏ qua hoàn toàn.
- Không retry mutation tự động.
- Reload current route có thể retry thông qua mutation tiếp theo hoặc navigation; task không thêm nút retry mới.
- Guard lifecycle không nuốt lỗi đồng bộ phát sinh trước Promise; handler hiện hành vẫn hiển thị fallback tương ứng.

## Kiểm thử

### Hook

- Token current ngay sau capture.
- Đổi route làm token cũ false và token mới true.
- Unmount làm token false.
- StrictMode setup/cleanup/setup vẫn tạo token current cho route hiện hành.

### Review page

- `getExam` đề cũ resolve sau đề mới không ghi đè.
- Khi route đổi, câu hỏi cũ biến mất ngay và không còn nút mutation tương tác.
- Mutation duyệt/khóa cũ resolve sau navigation không reload hoặc đổi busy/error route mới.
- Sinh lại cũ không refresh quota hoặc reload route mới.
- Hoàn tất review cũ không navigate.
- `finally` cũ không mở khóa operation mới.
- Mutation hiện hành thành công + reload lỗi giữ dữ liệu và hiện lỗi.
- StrictMode replay vẫn tải được đề hiện hành.

### Export page

- `getExam` cũ resolve sau đề mới không ghi đè title/form.
- Save cũ resolve/reject sau navigation không reload, đổi form, error hoặc saving route mới.
- `finally` save cũ không mở khóa save route mới.
- Save hiện hành thành công + reload lỗi giữ form và hiện lỗi.
- Link DOCX dùng đúng ID của route hiện hành.
- StrictMode replay vẫn tải được đề hiện hành.

Verification cuối: toàn bộ `npm test -- --run`, `npm run lint`, `npm run build`. Vì không thay backend, không cần migration hoặc test backend mới.

## Git workflow

- Base: merge commit mới nhất trên `main`, sau `git pull --ff-only origin main`.
- Branch: `fix/exam-page-route-races`.
- Commit đặc tả: `doc: đặc tả chống race condition theo route`.
- Commit plan: `doc: lập kế hoạch chống race condition theo route`.
- Commit implementation: `fix: chống ghi đè trạng thái khi đổi đề`.
- Push branch và tạo Draft PR vào `main`; không tự merge.
