"""
Contract test for VisaEvidence schema.
Ensures that immigration intelligence output contains legal disclaimer,
valid confidence enum, route information, and rule verification tracking.
"""

from jobpilot.core.schemas import VisaEvidence, VisaStatus, ConfidenceLevel


def test_visa_evidence_domestic_india():
    """Verify domestic assessment for Indian citizen."""
    ve = VisaEvidence(
        country="India",
        visa_status=VisaStatus.INDIA,
        route="Citizen / Domestic Authorization",
        confidence=ConfidenceLevel.HIGH,
        threshold_met=True,
        threshold_details={"salary_threshold_met": True, "domestic": True},
        sponsor_status="Not applicable (Citizen)",
        evidence_snippets=["Candidate holds citizenship and domestic authorization."],
        verified_rule=True,
    )
    assert ve.visa_status == VisaStatus.INDIA
    assert ve.confidence == ConfidenceLevel.HIGH
    assert "legal immigration advice" in ve.disclaimer
    assert ve.verified_rule is True


def test_visa_evidence_international_unverified_rule():
    """Verify foreign assessment with unverified rule caps confidence appropriately."""
    ve = VisaEvidence(
        country="Germany",
        visa_status=VisaStatus.SPONSORSHIP_POSSIBLE,
        route="EU Blue Card (§ 18g AufenthG)",
        confidence=ConfidenceLevel.LOW,
        threshold_met=None,
        threshold_details={"salary_stated": False, "requires_verification": True},
        sponsor_status="Unknown",
        evidence_snippets=["Role requires university degree in STEM/IT."],
        verified_rule=False,
    )
    assert ve.visa_status == VisaStatus.SPONSORSHIP_POSSIBLE
    assert ve.confidence == ConfidenceLevel.LOW
    assert ve.verified_rule is False
    assert len(ve.disclaimer) > 0


def test_visa_evidence_serialization():
    """Verify JSON roundtrip preservation."""
    ve = VisaEvidence(
        country="UK",
        visa_status=VisaStatus.SPONSORSHIP_LIKELY,
        route="Skilled Worker Visa",
        confidence=ConfidenceLevel.MEDIUM,
        threshold_met=True,
        threshold_details={"stated_salary": 45000, "threshold": 38700},
        sponsor_status="Licensed A-rated Sponsor",
        verified_rule=False,
    )
    dumped = ve.model_dump()
    assert dumped["country"] == "UK"
    assert dumped["visa_status"] == "SPONSORSHIP_LIKELY"
    assert dumped["confidence"] == "MEDIUM"

    restored = VisaEvidence(**dumped)
    assert restored.country == "UK"
    assert restored.visa_status == VisaStatus.SPONSORSHIP_LIKELY
