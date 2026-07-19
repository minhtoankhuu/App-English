# Exam Page Route Race Protection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ngăn fetch và mutation của đề cũ ghi đè state, lock, lỗi hoặc điều hướng của đề mới trên Review và Export.

**Architecture:** Một hook nhỏ quản lý route generation token dùng chung, còn từng page giữ state nghiệp vụ riêng. Mỗi async operation capture token và chỉ tiếp tục set state, reload, refresh quota hoặc navigate khi token và operation lock vẫn thuộc route hiện hành.

**Tech Stack:** React 19, TypeScript 6, React Router, Vitest, Testing Library.

## Global Constraints

- Chỉ thay frontend; không thay backend, migration hoặc API contract.
- Bao phủ toàn bộ fetch và mutation của `ExamReviewPage` và `ExamExportPage`.
- Dữ liệu chỉ render khi `exam.id === examId`.
- Route đổi hoặc component unmount phải invalidate token cũ.
- StrictMode setup/cleanup/setup phải để route hiện hành hoạt động.
- Sau mỗi `await`, kiểm tra token trước mọi state update, reload, quota refresh hoặc navigate.
- `finally` cũ không được mở khóa operation mới.
- Mutation server đã hoàn tất không bị retry hoặc đảo; client chỉ bỏ continuation stale.
- Commit dùng `doc:` hoặc `fix:`; branch là `fix/exam-page-route-races`.

---

### Task 1: Hook route-generation dùng chung

**Files:**
- Create: `frontend/src/routing/useRouteGeneration.ts`
- Create: `frontend/src/routing/useRouteGeneration.test.tsx`

**Interfaces:**
- Produces: `RouteGenerationToken`, `RouteGeneration`, `useRouteGeneration(routeKey)` với `capture()` và `isCurrent(token)`.
- Consumes: React `useEffect`, `useRef`.

- [ ] **Step 1: Viết test RED cho route change, unmount và StrictMode**

```tsx
function Harness({ routeKey, onValue }: { routeKey?: string; onValue(value: RouteGeneration): void }) {
  const generation = useRouteGeneration(routeKey);
  useEffect(() => onValue(generation), [generation, onValue]);
  return null;
}

it("invalidates old tokens after route changes", () => {
  let current!: RouteGeneration;
  const { rerender } = render(<Harness routeKey="exam-1" onValue={(value) => { current = value; }} />);
  const oldToken = current.capture();
  rerender(<Harness routeKey="exam-2" onValue={(value) => { current = value; }} />);
  expect(current.isCurrent(oldToken)).toBe(false);
  expect(current.isCurrent(current.capture())).toBe(true);
});

it("invalidates tokens on unmount and survives StrictMode replay", () => {
  let current!: RouteGeneration;
  const view = render(<StrictMode><Harness routeKey="exam-1" onValue={(value) => { current = value; }} /></StrictMode>);
  const token = current.capture();
  expect(current.isCurrent(token)).toBe(true);
  view.unmount();
  expect(current.isCurrent(token)).toBe(false);
});
```

- [ ] **Step 2: Chạy RED**

Run: `cd frontend; npm test -- --run src/routing/useRouteGeneration.test.tsx`
Expected: FAIL vì hook chưa tồn tại.

- [ ] **Step 3: Cài hook tối thiểu**

```typescript
export interface RouteGenerationToken { routeKey: string | undefined; generation: number }

export function useRouteGeneration(routeKey: string | undefined): RouteGeneration {
  const state = useRef({ routeKey, generation: 0, mounted: false });
  if (state.current.routeKey !== routeKey) {
    state.current = { routeKey, generation: state.current.generation + 1, mounted: state.current.mounted };
  }
  useEffect(() => {
    state.current.mounted = true;
    state.current.generation += 1;
    return () => { state.current.mounted = false; state.current.generation += 1; };
  }, [routeKey]);
  return useMemo(() => ({
    capture: () => ({ routeKey: state.current.routeKey, generation: state.current.generation }),
    isCurrent: (token) => state.current.mounted && token.routeKey === state.current.routeKey && token.generation === state.current.generation,
  }), [routeKey]);
}
```

Nếu StrictMode test cho thấy effect timing cần khác, giữ public interface và điều chỉnh internals bằng ref/effect; không thêm state framework.

- [ ] **Step 4: Chạy GREEN**

Run: `cd frontend; npm test -- --run src/routing/useRouteGeneration.test.tsx`
Expected: toàn bộ hook tests PASS.

- [ ] **Step 5: Commit hook**

```bash
git add frontend/src/routing
git commit -m "fix: thêm route generation guard dùng chung"
```

### Task 2: Bảo vệ ExamReviewPage

**Files:**
- Modify: `frontend/src/pages/ExamReviewPage.tsx`
- Create: `frontend/src/pages/ExamReviewPage.test.tsx`

**Interfaces:**
- Consumes: `useRouteGeneration(examId)` từ Task 1.
- Produces: Review fetch/mutations cô lập theo route và operation lock.

- [ ] **Step 1: Viết test RED cho fetch stale và route reset**

```tsx
it("ignores an old exam response after navigation", async () => {
  const oldExam = deferred<ExamDetailOut>();
  getExam.mockImplementation((id) => id === "exam-1" ? oldExam.promise : Promise.resolve(examTwo));
  const { navigate } = renderReview("exam-1");
  navigate("/exams/exam-2/review");
  expect(await screen.findByText(examTwo.title)).toBeInTheDocument();
  oldExam.resolve(examOne);
  expect(screen.queryByText(examOne.title)).not.toBeInTheDocument();
});

it("removes old question controls immediately when route changes", async () => {
  const { navigate } = renderReview("exam-1");
  expect(await screen.findByText(examOne.blocks[0].questions[0].prompt_text)).toBeInTheDocument();
  navigate("/exams/exam-2/review");
  expect(screen.queryByText(examOne.blocks[0].questions[0].prompt_text)).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Chạy RED**

Run: `cd frontend; npm test -- --run src/pages/ExamReviewPage.test.tsx`
Expected: stale exam/question assertions FAIL.

- [ ] **Step 3: Guard route load và render identity**

```tsx
const routeGeneration = useRouteGeneration(examId);
useEffect(() => {
  setExam(null); setError(null); setBusyQuestionId(null); setFinishing(false);
  if (!examId) return;
  const token = routeGeneration.capture();
  void getExam(examId).then((detail) => {
    if (routeGeneration.isCurrent(token) && detail.id === examId) setExam(detail);
  }).catch((err) => {
    if (routeGeneration.isCurrent(token)) setError(errorMessage(err, "Không tải được đề"));
  });
}, [examId, routeGeneration]);

if (!exam || exam.id !== examId) return loadingOrError;
```

- [ ] **Step 4: Viết test RED cho mutation stale, lock và navigation**

```tsx
it("does not reload or refresh usage when old regeneration resolves", async () => {
  const oldRegenerate = deferred<QuestionOut>();
  regenerateQuestion.mockReturnValueOnce(oldRegenerate.promise);
  const { navigate } = renderReview("exam-1");
  await user.click(await screen.findByRole("button", { name: "Sinh lại" }));
  navigate("/exams/exam-2/review");
  oldRegenerate.resolve(examOne.blocks[0].questions[0]);
  await waitFor(() => expect(refreshUsage).not.toHaveBeenCalled());
  expect(getExam).toHaveBeenCalledTimes(2);
});

it("does not navigate when old complete-review resolves", async () => {
  const oldComplete = deferred<ExamDetailOut>();
  completeReview.mockReturnValueOnce(oldComplete.promise);
  const { navigate } = renderReview("exam-1");
  await user.click(await screen.findByRole("button", { name: /Hoàn tất/ }));
  navigate("/exams/exam-2/review");
  oldComplete.resolve(examOne);
  expect(screen.getByText(examTwo.title)).toBeInTheDocument();
});
```

Thêm test approve/lock stale, finally cũ không mở lock mới, reload current thất bại giữ data và hiện `ApiError.message`, StrictMode replay tải được.

- [ ] **Step 5: Cài operation token/lock tối thiểu**

```typescript
interface ReviewOperation { id: number; route: RouteGenerationToken }
const activeOperation = useRef<ReviewOperation | null>(null);

function beginOperation(): ReviewOperation | null {
  if (activeOperation.current) return null;
  const operation = { id: ++nextOperationId.current, route: routeGeneration.capture() };
  activeOperation.current = operation;
  return operation;
}

function isCurrentOperation(operation: ReviewOperation) {
  return routeGeneration.isCurrent(operation.route) && activeOperation.current?.id === operation.id;
}
```

Mọi handler capture `targetExamId` và operation; sau mỗi await guard. Reload nhận `(targetExamId, token)` tường minh. `finally` chỉ clear nếu `isCurrentOperation`; route effect invalidate ref cũ. Disable tất cả mutation buttons khi có active operation của route hiện hành.

- [ ] **Step 6: Chạy GREEN và commit Review**

Run: `cd frontend; npm test -- --run src/pages/ExamReviewPage.test.tsx src/routing/useRouteGeneration.test.tsx`
Expected: PASS.

```bash
git add frontend/src/pages/ExamReviewPage.tsx frontend/src/pages/ExamReviewPage.test.tsx
git commit -m "fix: cô lập trạng thái trang kiểm duyệt theo đề"
```

### Task 3: Bảo vệ ExamExportPage

**Files:**
- Modify: `frontend/src/pages/ExamExportPage.tsx`
- Create: `frontend/src/pages/ExamExportPage.test.tsx`

**Interfaces:**
- Consumes: `useRouteGeneration(examId)`.
- Produces: Export load/save/form/link cô lập theo route.

- [ ] **Step 1: Viết test RED cho fetch/form stale**

```tsx
it("ignores old load and resets form on route change", async () => {
  const oldLoad = deferred<ExamDetailOut>();
  getExam.mockImplementation((id) => id === "exam-1" ? oldLoad.promise : Promise.resolve(examTwo));
  const { navigate } = renderExport("exam-1");
  navigate("/exams/exam-2/export");
  expect(await screen.findByText(examTwo.title)).toBeInTheDocument();
  oldLoad.resolve(examOne);
  expect(screen.queryByText(examOne.title)).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Mã đề A" })).toHaveAttribute("href", expect.stringContaining("exam-2"));
});
```

- [ ] **Step 2: Chạy RED và guard load/render**

Run: `cd frontend; npm test -- --run src/pages/ExamExportPage.test.tsx`
Expected: FAIL stale title/form/link.

Áp hook, reset `exam/error/saving/exportMode/variantCount`, guard response/error và chỉ render khi `exam.id === examId`.

- [ ] **Step 3: Viết test RED cho stale save và reload error**

```tsx
it("does not let an old save unlock or reload the new route", async () => {
  const oldSave = deferred<ExamDetailOut>();
  saveExportConfig.mockReturnValueOnce(oldSave.promise);
  const { navigate } = renderExport("exam-1");
  await user.click(await screen.findByRole("button", { name: "Lưu vào Đề của tôi" }));
  navigate("/exams/exam-2/export");
  oldSave.resolve(examOne);
  expect(getExam).toHaveBeenCalledTimes(2);
  expect(screen.getByText(examTwo.title)).toBeInTheDocument();
});

it("keeps current form and shows reload failure after save", async () => {
  getExam.mockResolvedValueOnce(examOne).mockRejectedValueOnce(new ApiError(500, "Không tải lại được đề"));
  renderExport("exam-1");
  await user.click(await screen.findByRole("button", { name: "Lưu vào Đề của tôi" }));
  expect(await screen.findByText("Không tải lại được đề")).toBeInTheDocument();
  expect(screen.getByText(examOne.title)).toBeInTheDocument();
});
```

Thêm stale rejection không hiện lỗi, old finally không mở save mới và StrictMode replay.

- [ ] **Step 4: Cài save operation guard và chạy GREEN**

Capture token, target ID và form values. Guard từng continuation; reload tường minh trả boolean; clear error chỉ sau reload thành công; finally chỉ clear saving của operation current.

Run: `cd frontend; npm test -- --run src/pages/ExamExportPage.test.tsx src/routing/useRouteGeneration.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit Export**

```bash
git add frontend/src/pages/ExamExportPage.tsx frontend/src/pages/ExamExportPage.test.tsx
git commit -m "fix: cô lập trạng thái trang xuất đề theo route"
```

### Task 4: Verification, review và publish

**Files:**
- Modify only if a regression fix is required by a failing test.

**Interfaces:**
- Consumes: Tasks 1–3.
- Produces: verified clean branch and Draft PR.

- [ ] **Step 1: Chạy toàn bộ frontend verification**

Run: `cd frontend; npm test -- --run; npm run lint; npm run build`
Expected: tất cả Vitest PASS, lint không warning/error, TypeScript/Vite build thành công.

- [ ] **Step 2: Review phạm vi**

Run: `git status --short; git diff --check main...HEAD; git log --oneline main..HEAD`
Expected: worktree sạch; chỉ spec, plan, hook, Review/Export và tests; không backend/package dependency change.

- [ ] **Step 3: Whole-branch review**

Reviewer kiểm tra token correctness, StrictMode, mutation lock/finally, stale error, reload failure và link identity. Mọi Critical/Important phải được sửa và re-review trước publish.

- [ ] **Step 4: Push và tạo Draft PR**

Run: `git push -u origin fix/exam-page-route-races`
Expected: push thành công. Tạo Draft PR title `fix: chống ghi đè trạng thái khi đổi đề` vào `main`, ghi kết quả test/lint/build; không merge.
