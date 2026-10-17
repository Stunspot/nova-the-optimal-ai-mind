import { describe, expect, it, vi } from "vitest";
import { cancelSubscription, type Subscription } from "../input/src/subscriptionService";

describe("cancellation boundaries", () => {
  it("denies a cross-tenant request without remote or local effects", async () => {
    const record: Subscription = { id: "sub-1", tenantId: "tenant-a", state: "active" };
    const repository = { get: vi.fn().mockResolvedValue(record), save: vi.fn() };
    const provider = { cancel: vi.fn() };
    const events = { publish: vi.fn() };

    await expect(cancelSubscription("tenant-b", "sub-1", repository, provider, events)).rejects.toThrow("not found");
    expect(repository.save).not.toHaveBeenCalled();
    expect(provider.cancel).not.toHaveBeenCalled();
    expect(events.publish).not.toHaveBeenCalled();
  });

  it("does not repeat a remote effect after an ambiguous provider timeout", async () => {
    let stored: Subscription = { id: "sub-1", tenantId: "tenant-a", state: "active" };
    const repository = { get: vi.fn(async () => stored), save: vi.fn(async (next: Subscription) => { stored = next; }) };
    let remoteEffects = 0;
    const provider = { cancel: vi.fn(async () => { remoteEffects += 1; if (remoteEffects === 1) throw new Error("timeout after commit"); }) };
    const events = { publish: vi.fn() };

    await expect(cancelSubscription("tenant-a", "sub-1", repository, provider, events)).rejects.toThrow("timeout after commit");
    await cancelSubscription("tenant-a", "sub-1", repository, provider, events);

    expect(remoteEffects).toBe(1);
    expect(stored.state).toBe("cancelled");
    expect(events.publish).toHaveBeenCalledTimes(1);
  });
});
