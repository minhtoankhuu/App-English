import { describe, expect, it, vi } from "vitest";
import { apiGet } from "./client";

describe("API client", () => {
  it("uses detail.message for structured errors", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: { message: "Đã hết lượt", remaining: 0 } }), {
        status: 429,
        headers: { "content-type": "application/json" },
      }),
    );

    await expect(apiGet("/test")).rejects.toMatchObject({ status: 429, message: "Đã hết lượt" });
  });
});
