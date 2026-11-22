import { describe, expect, it } from "vitest";
import { parseMappings } from "../components/AdvancedSeoPanels";

describe("parseMappings", () => {
  it("accepts =>, -> and → and skips lines without a separator", () => {
    expect(parseMappings("https://a.de/alt => https://a.de/neu\nhttps://a.de/x->https://a.de/y\n https://a.de/p → https://a.de/q \nkaputt\n")).toEqual([
      { old_url: "https://a.de/alt", new_url: "https://a.de/neu" },
      { old_url: "https://a.de/x", new_url: "https://a.de/y" },
      { old_url: "https://a.de/p", new_url: "https://a.de/q" },
    ]);
  });
});
