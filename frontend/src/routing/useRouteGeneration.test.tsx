import { StrictMode, type PropsWithChildren } from "react";
import { renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { useRouteGeneration } from "./useRouteGeneration";

function StrictWrapper({ children }: PropsWithChildren) {
  return <StrictMode>{children}</StrictMode>;
}

describe("useRouteGeneration", () => {
  it("invalidates old tokens after the route changes", () => {
    const { result, rerender } = renderHook(({ routeKey }) => useRouteGeneration(routeKey), {
      initialProps: { routeKey: "exam-1" },
    });
    const oldToken = result.current.capture();

    rerender({ routeKey: "exam-2" });

    expect(result.current.isCurrent(oldToken)).toBe(false);
    expect(result.current.isCurrent(result.current.capture())).toBe(true);
  });

  it("invalidates tokens after unmount", () => {
    const { result, unmount } = renderHook(() => useRouteGeneration("exam-1"));
    const token = result.current.capture();

    unmount();

    expect(result.current.isCurrent(token)).toBe(false);
  });

  it("keeps the active route usable after StrictMode effect replay", () => {
    const { result } = renderHook(() => useRouteGeneration("exam-1"), { wrapper: StrictWrapper });

    expect(result.current.isCurrent(result.current.capture())).toBe(true);
  });
});
