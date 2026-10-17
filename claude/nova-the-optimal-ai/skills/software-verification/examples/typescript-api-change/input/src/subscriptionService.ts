export type Subscription = { id: string; tenantId: string; state: "active" | "cancelled" };

export interface Repository {
  get(id: string): Promise<Subscription | undefined>;
  save(subscription: Subscription): Promise<void>;
}

export interface BillingProvider {
  cancel(subscriptionId: string): Promise<void>;
}

export interface Events {
  publish(name: string, payload: object): Promise<void>;
}

export async function cancelSubscription(
  actorTenantId: string,
  subscriptionId: string,
  repository: Repository,
  provider: BillingProvider,
  events: Events,
): Promise<Subscription> {
  const subscription = await repository.get(subscriptionId);
  if (!subscription || subscription.tenantId !== actorTenantId) throw new Error("not found");
  if (subscription.state === "cancelled") return subscription;

  // Planted defect: a provider can complete remotely and then time out. The local
  // active state permits a retry to perform the remote cancellation again.
  await provider.cancel(subscription.id);
  const cancelled = { ...subscription, state: "cancelled" as const };
  await repository.save(cancelled);
  await events.publish("subscription.cancelled", { subscriptionId });
  return cancelled;
}
