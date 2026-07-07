# MinIO evidence bucket WORM retention (audit §3).
# Run once after MinIO is up: `mc alias set local http://localhost:9000 verge vergeverge`
#   mc mb --with-lock local/verge-evidence
#   mc retention set --default COMPLIANCE 30d local/verge-evidence
#
# Object Lock requires bucket versioning; use COMPLIANCE mode for regulator-grade immutability.
