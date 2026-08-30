# Authentication is identity; authorization is permission over an object

Vary actor, role, tenant, ownership, object state, and operation independently. A denial oracle includes unchanged protected state, no downstream call, no secret-bearing response, and appropriate audit evidence where required.

Test horizontal access (peer object), vertical access (higher privilege), indirect references, bulk operations, cached permissions, revoked access, and alternate routes. A 403 alone is weak if the side effect already occurred.

Use synthetic accounts and non-production targets. Active probing beyond repository-local tests requires explicit scope and authorization.
