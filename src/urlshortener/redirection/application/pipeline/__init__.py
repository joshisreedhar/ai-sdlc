"""Redirect pipeline - the platform's primary extension point.

    RedirectContext -> [interceptor 1] -> ... -> [terminal handler] -> RedirectDecision

**Phase 1 registers ZERO interceptors.** The pipeline still exists and the router still
goes through it, so that every later change to redirect behaviour is an *addition*:

* ``ExpirationInterceptor``       (Phase 3) - may yield ``LinkExpired``
* ``PasswordGateInterceptor``     (Phase 3) - may yield ``ServeInterstitial`` (auth page)
* ``GeoDeviceRoutingInterceptor`` (Phase 3) - may override the destination URL
* ``PixelInterstitialInterceptor``(Phase 4) - may yield ``ServeInterstitial`` (pixel page)

IP/bot filtering is *not* an interceptor: it runs earlier, as FastAPI middleware in
``urlshortener.redirection.api.middleware``, so that abusive traffic is rejected before
any lookup happens at all.

RULES FOR PHASE 1:

* Do NOT implement any interceptor (architecture rule P-02).
* Do NOT let the router call ``LinkResolutionService`` directly - it must go through
  ``RedirectPipeline`` (architecture rule P-04), otherwise Phase 3's interceptors would
  be silently bypassed on the code path that matters most.
* Do NOT modify the files in this package. Register into the pipeline from
  ``urlshortener.apps.redirection_engine.container`` instead.
"""

from urlshortener.redirection.application.pipeline.redirect_handler import (
    RedirectHandler,
)
from urlshortener.redirection.application.pipeline.redirect_interceptor import (
    RedirectInterceptor,
)
from urlshortener.redirection.application.pipeline.redirect_pipeline import (
    RedirectPipeline,
)

__all__ = ["RedirectHandler", "RedirectInterceptor", "RedirectPipeline"]
