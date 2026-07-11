<!--
============================================================================
SECTION 5 — CONCLUSION  (deliverable 5 of the body)
Concise; no new numbers beyond those established in Sections 3. English text.
============================================================================
-->

# 5. Conclusion

TRAK-AI is an offline-first Edge–Fog–Cloud decision-support system for winter wheat and sunflower in
Trakya, Türkiye, whose distinguishing feature is that it embeds validation rigour into its operational
logic. A low-cost ESP32 rover acquires in-situ data; a laptop-class fog tier performs vegetation-index
forecasting, layered yield estimation, crop-health image classification and a Turkish-language
retrieval-augmented advisory with a locally hosted language model; and the cloud tier is used only for
cache-backed acquisition, so the full decision loop runs on CPU-only hardware without a network once inputs
are cached, completing in about 27 s end-to-end. Guided by a companion cross-validation audit, the system
defaults winter-wheat yield to a climatology baseline, presents machine-learning estimates with their
forward-skill caveats, and transparently reports both a forward-validation result in which a naïve
persistence baseline is not beaten and the prototype or placeholder status of its edge-vision components.
Its contribution is therefore less a new high-accuracy model than an honest, deployable integration:
a demonstration that an agricultural decision-support system for low-connectivity smallholder settings can
be built to be transparent about what it does — and does not — reliably do. Completing the pending advisory
evaluations, realising the full tri-modal consensus, and extending the single-parcel field reconnaissance
to multi-site trials are the clear next steps toward operational deployment.
