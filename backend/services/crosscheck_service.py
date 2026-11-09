"""
Cross-Check Service - Field-to-Satellite evidence correlation
SIH 26015 Hero Feature

Uses transparent, deterministic rules (NOT AI/ML) to check consistency
between field observations and satellite evidence.
"""


class CrossCheckService:
    """Performs field-to-satellite cross-checks using transparent rules."""

    # Status constants
    CONSISTENT = "Consistent"
    INCONCLUSIVE = "Inconclusive"
    FIELD_VERIFICATION = "Field verification recommended"

    def crosscheck(self, record: dict, raster_values: dict, location_valid: bool) -> dict:
        """
        Perform a field-satellite cross-check.

        Args:
            record: DRISHTI record dict with intervention_category, intervention_type, etc.
            raster_values: Dict from raster_service.sample_point() with ndvi_current, ndwi_current, etc.
            location_valid: Whether the point is inside the watershed.

        Returns:
            Dict with status, evidence list, summary, and provenance.
        """
        evidence = []
        status = self.INCONCLUSIVE

        intervention_type = record.get("intervention_type", "")
        intervention_category = record.get("intervention_category", "")
        intervention_stage = record.get("intervention_stage", "")

        ndvi = raster_values.get("ndvi_current")
        ndwi = raster_values.get("ndwi_current")
        water = raster_values.get("water_current")
        ndvi_change = raster_values.get("ndvi_change")
        ndwi_change = raster_values.get("ndwi_change")

        water_detected = water is not None and water == 1

        # ----- Location Check -----
        if not location_valid:
            evidence.append({
                "check": "Location Validation",
                "result": "OUTSIDE",
                "detail": "GPS coordinates fall outside the Gundlakamma watershed boundary.",
                "severity": "warning"
            })
            return {
                "status": self.FIELD_VERIFICATION,
                "evidence": evidence,
                "summary": "Location is outside the watershed boundary. Cannot perform satellite cross-check. Field verification recommended.",
                "data_provenance": "Watershed boundary: approximate prototype boundary (not official SLNA).",
            }

        evidence.append({
            "check": "Location Validation",
            "result": "INSIDE",
            "detail": "GPS coordinates are within the Gundlakamma watershed boundary.",
            "severity": "ok"
        })

        # ----- NDVI Evidence -----
        if ndvi is not None:
            if ndvi > 0.4:
                ndvi_desc = f"Healthy vegetation detected (NDVI: {ndvi:.2f})"
                ndvi_severity = "ok"
            elif ndvi > 0.2:
                ndvi_desc = f"Moderate vegetation (NDVI: {ndvi:.2f})"
                ndvi_severity = "info"
            else:
                ndvi_desc = f"Low vegetation / bare soil detected (NDVI: {ndvi:.2f})"
                ndvi_severity = "warning"

            evidence.append({
                "check": "Vegetation Index (NDVI)",
                "result": f"{ndvi:.2f}",
                "detail": ndvi_desc,
                "severity": ndvi_severity
            })
        else:
            evidence.append({
                "check": "Vegetation Index (NDVI)",
                "result": "N/A",
                "detail": "NDVI data unavailable at this location (NODATA pixel).",
                "severity": "info"
            })

        # ----- Water Evidence -----
        if water_detected:
            evidence.append({
                "check": "Surface Water Detection",
                "result": "DETECTED",
                "detail": "Surface water detected at this location in current imagery.",
                "severity": "ok"
            })
        elif ndwi is not None and ndwi > 0:
            evidence.append({
                "check": "Surface Water Detection",
                "result": "MOISTURE",
                "detail": f"No standing water, but elevated moisture signal (NDWI: {ndwi:.2f}).",
                "severity": "info"
            })
        else:
            evidence.append({
                "check": "Surface Water Detection",
                "result": "NOT DETECTED",
                "detail": "No surface water detected at this location in current imagery.",
                "severity": "info"
            })

        # ----- Change Evidence -----
        if ndvi_change is not None:
            if ndvi_change > 0.05:
                change_desc = f"Vegetation has increased since 2025 (NDVI change: +{ndvi_change:.2f})"
                change_sev = "ok"
            elif ndvi_change < -0.05:
                change_desc = f"Vegetation has decreased since 2025 (NDVI change: {ndvi_change:.2f})"
                change_sev = "warning"
            else:
                change_desc = f"Vegetation is relatively stable compared to 2025 (NDVI change: {ndvi_change:.2f})"
                change_sev = "info"

            evidence.append({
                "check": "Vegetation Change (2025-2026)",
                "result": f"{ndvi_change:+.2f}",
                "detail": change_desc,
                "severity": change_sev
            })

        # ----- Category-specific Cross-Check -----
        if intervention_category == "Water Harvesting":
            status, summary = self._check_water_harvesting(
                intervention_type, water_detected, ndwi, ndwi_change, intervention_stage
            )
        elif intervention_category == "Vegetation/Biomass":
            status, summary = self._check_vegetation(
                intervention_type, ndvi, ndvi_change, intervention_stage
            )
        elif intervention_category == "Soil Conservation":
            status, summary = self._check_soil_conservation(
                intervention_type, ndvi, ndvi_change, intervention_stage
            )
        else:
            status = self.INCONCLUSIVE
            summary = f"Cross-check rules not defined for category '{intervention_category}'. Manual review recommended."

        evidence.append({
            "check": "Cross-Check Verdict",
            "result": status,
            "detail": summary,
            "severity": "ok" if status == self.CONSISTENT else ("warning" if status == self.FIELD_VERIFICATION else "info")
        })

        return {
            "status": status,
            "evidence": evidence,
            "summary": summary,
            "data_provenance": (
                "Satellite data: Sentinel-2 L2A (July 2026, ~10 m resolution). "
                "Cross-check uses transparent deterministic rules, not AI prediction. "
                "Satellite evidence provides supporting context but field verification is recommended."
            ),
        }

    def _check_water_harvesting(self, intervention_type, water_detected, ndwi, ndwi_change, stage):
        """Cross-check rules for water harvesting structures."""
        if water_detected:
            return (
                self.CONSISTENT,
                f"Satellite evidence supports water presence at the {intervention_type} site. "
                "Surface water was detected in current imagery, consistent with a functioning water harvesting structure."
            )
        elif ndwi is not None and ndwi > 0:
            return (
                self.INCONCLUSIVE,
                f"Elevated moisture signal detected near {intervention_type} site (NDWI: {ndwi:.2f}), "
                "but no confirmed standing water. Structure may have partial water or be below detection threshold."
            )
        else:
            if stage == "Pre-treatment":
                return (
                    self.CONSISTENT,
                    f"No water detected at {intervention_type} site, which is expected for a pre-treatment observation. "
                    "Baseline conditions documented."
                )
            else:
                return (
                    self.INCONCLUSIVE,
                    f"No surface water detected at {intervention_type} site at the time of satellite observation. "
                    "Structure may be dry due to seasonal conditions, or below detection resolution (~111 m)."
                )

    def _check_vegetation(self, intervention_type, ndvi, ndvi_change, stage):
        """Cross-check rules for vegetation/biomass interventions."""
        if ndvi is None:
            return self.INCONCLUSIVE, "NDVI data unavailable at this location. Cannot assess vegetation status."

        if stage == "Pre-treatment":
            return (
                self.CONSISTENT,
                f"Pre-treatment baseline recorded. Current vegetation index (NDVI: {ndvi:.2f}) "
                "documents conditions before intervention."
            )

        if ndvi > 0.4:
            if ndvi_change is not None and ndvi_change > 0.05:
                return (
                    self.CONSISTENT,
                    f"Healthy vegetation detected (NDVI: {ndvi:.2f}) with positive change since 2025 "
                    f"(+{ndvi_change:.2f}). Satellite evidence is consistent with {intervention_type} activity."
                )
            else:
                return (
                    self.CONSISTENT,
                    f"Healthy vegetation detected (NDVI: {ndvi:.2f}). Consistent with expected outcomes for "
                    f"{intervention_type}, though change detection is within the stable range."
                )
        elif ndvi > 0.2:
            return (
                self.INCONCLUSIVE,
                f"Moderate vegetation detected (NDVI: {ndvi:.2f}). {intervention_type} effects may not yet be "
                "fully visible, or the area may have mixed land cover at current resolution (~111 m)."
            )
        else:
            return (
                self.FIELD_VERIFICATION,
                f"Low vegetation / bare soil detected (NDVI: {ndvi:.2f}). This may indicate that "
                f"{intervention_type} has not yet taken effect, or site conditions differ from expectations. "
                "Field verification recommended."
            )

    def _check_soil_conservation(self, intervention_type, ndvi, ndvi_change, stage):
        """Cross-check rules for soil conservation structures."""
        note = (
            f"Note: {intervention_type} structures are typically small-scale features "
            "that may not be directly detectable at current satellite resolution (~111 m). "
        )

        if stage == "Pre-treatment":
            return (
                self.CONSISTENT,
                f"Pre-treatment baseline documented for {intervention_type}. " + note +
                "Indirect effects (e.g., downstream vegetation improvement) may become visible in future comparisons."
            )

        if ndvi_change is not None and ndvi_change > 0.05:
            return (
                self.INCONCLUSIVE,
                note + f"Positive vegetation trend detected nearby (NDVI change: +{ndvi_change:.2f}), "
                "which could indicate indirect benefits of soil conservation, but attribution cannot be confirmed "
                "from satellite data alone."
            )
        else:
            return (
                self.INCONCLUSIVE,
                note + "No clear indirect satellite signal detected. This does not indicate failure; "
                "soil conservation benefits may take time to manifest or occur at finer scales."
            )
