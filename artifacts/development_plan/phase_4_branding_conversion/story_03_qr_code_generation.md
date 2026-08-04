# P4-03: Branded QR Code Generation & Styling

## 📖 User Story (Valuable)
*The core requirement focused on the value delivered to the user.*
- **As a** marketing user running offline or print campaigns,
- **I want to** generate a customizable QR code for any short link,
- **So that** I can distribute it in print/offline channels while keeping the visual design on-brand.

---

## 🗣️ Context & Goals (Negotiable)
*Provide the background. Why are we doing this? Outline the "What" and the "Why", but leave the "How" open for team discussion and technical negotiation.*
- QR codes must encode the short URL, never the raw destination, so that the destination can be changed later without invalidating a printed QR code. Styling (colors, module shape, optional logo) is a visual convenience on top of that core guarantee. The exact library and image pipeline are open for negotiation, but the architecture guidance names `segno`/`qrcode` with storage in object storage (S3-compatible) as the expected direction.

## ✅ Acceptance Criteria (Testable)
*Precise, verifiable conditions that must be met for the story to be considered "Done".*

**Scenario 1: Default QR generation**
- **Given** I have created a short link
- **When** I request a QR code for that link without specifying style options
- **Then** the system generates a default-style PNG QR code encoding the short URL and returns a persistent asset URL

**Scenario 2: Styled QR generation**
- **Given** I have a short link
- **When** I request a QR code specifying foreground/background colors and a module shape style
- **Then** the system generates a QR code reflecting the requested styling, stores it in object storage, and returns the asset URL

**Scenario 3: QR remains valid after destination change**
- **Given** a QR code was generated for short link `brand.com/promo` pointing to destination A
- **When** the link owner updates the destination URL to B
- **Then** the previously generated QR code image continues to scan correctly and now redirects visitors to destination B, with no regeneration required

**Scenario 4: Invalid style parameters rejected**
- **Given** I submit a QR style request with an unsupported color format or shape value
- **When** the request is processed
- **Then** the API returns a `422` validation error describing the accepted parameters

## 🔗 Scope & Dependencies (Independent & Small)
*Define the boundaries to ensure the story is small enough for a single sprint and can be deployed without waiting on other concurrent stories.*
- **In Scope:** QR generation endpoint, styling parameters (foreground/background color, module shape, optional logo overlay), persistence to object storage, returning a public/CDN-servable asset URL.
- **Out of Scope:** Scan-level analytics beyond the standard click analytics already captured by the Phase 2 pipeline, animated/GIF QR codes, print-ready vector (SVG/EPS) export beyond a basic SVG option.
- **Upstream Dependencies:** Phase 1 link creation (the QR always encodes the short URL, which is why destination changes never require regeneration); Phase 2 object storage / cloud-native infrastructure for asset persistence.

## 🛠️ Implementation Notes (Estimable)
*Provide enough technical context so the development team has the clarity needed to accurately size/estimate the effort.*
- **Design Links:** None provided; style parameters (color pickers, shape presets) to be finalized with design during sprint planning.
- **Technical Context:** Use `segno` (preferred per architecture guidance Section 2.1: PNG/SVG output, minimal dependencies) or `qrcode` as fallback; store generated assets under a bucket path such as `qr/{link_id}/{style_hash}.png`; owned by the API & Management Service per architecture guidance Section 2.1; expose styling via a `QRStyleRequest` Pydantic model (`fg_color`, `bg_color`, `shape` enum, optional `logo_url`).

---
