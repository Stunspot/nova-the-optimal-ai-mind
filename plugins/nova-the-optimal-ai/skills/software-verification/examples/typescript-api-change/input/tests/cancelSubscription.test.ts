import { describe, expect, it, vi } from "vitest";
import { cancelSubscription } from "../src/subscriptionService";

describe("cancelSubscription", () => {
  it("returns cancelled after provider success", async () => {
    const record = { id: "sub-1", tenantId: "tenant-a", state: "active" as const };
    const repository = { get: vi.fn().mockResolvedValue(record), save: vi.fn() };
    const provider = { cancel: vi.fn() };
    const events = { publish: vi.fn() };

    const result = await cancelSubscription("tenant-a", "sub-1", repository, provider, events);

    expect(result.state).toBe("cancelled");
    expect(provider.cancel).toHaveBeenCalledTimes(1);
  });
});
