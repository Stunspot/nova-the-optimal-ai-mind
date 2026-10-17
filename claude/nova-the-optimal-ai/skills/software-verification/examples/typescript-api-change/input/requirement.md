# Subscription cancellation change

Add cancellation through the billing provider. A tenant may cancel only its own active subscription. Repeated cancellation or provider retry must not duplicate a remote cancellation. Persist the cancelled state and publish one `subscription.cancelled` event after provider success.
