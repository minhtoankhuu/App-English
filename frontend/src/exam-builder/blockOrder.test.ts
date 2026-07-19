import { describe, expect, it } from "vitest";
import { moveBlock } from "./blockOrder";

const blocks = [{ id: "a" }, { id: "b" }, { id: "c" }];

describe("moveBlock", () => {
  it("moves a block before an earlier target", () => {
    expect(moveBlock(blocks, "c", "a").map((block) => block.id)).toEqual(["c", "a", "b"]);
  });

  it("moves a block before a later target", () => {
    expect(moveBlock(blocks, "a", "c").map((block) => block.id)).toEqual(["b", "a", "c"]);
  });

  it("returns the original array when the source and target match", () => {
    expect(moveBlock(blocks, "b", "b")).toBe(blocks);
  });
});
