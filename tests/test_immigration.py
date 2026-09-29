"""
Tests for JobPilot AI Immigration Viability Layer.
Verifies domestic rights for India, country rules loader, signal scanning,
mandatory disclaimers, unverified rule confidence capping, and classifier pipeline stage.
"""

import pytest
from jobpilot.core.schemas import ConfidenceLevel, JobRecord, VisaStatus
from jobpilot.immigration.classifier import ImmigrationClassifier
from jobpilot.immigration.countries import (
    evaluate_australia,
    evaluate_canada,
    evaluate_germany,
    evaluate_india,
    evaluate_netherlands,
    evaluate_singapore,
    evaluate_uae,
    evaluate_uk,
    get_country_evaluator,
)
from jobpilot.immigration.evidence import extract_evidence_snippets, scan_sponsor_signals
from jobpilot.immigration.routes import RouteManager


def create_sample_job(
    title: str = "AI Engineer",
    company: str = "TechCorp",
    country: str = "India",
    location: str = "Mumbai",
    description: str = "Developing LLM applications.",
    salary_max: float = 1200000.0,
    currency: str = "INR",
) -> JobRecord:
    return JobRecord(
        job_id="test-job-imm-001",
        company=company,
        title=title,
        country=country,
        location=location,
        description=description,
        salary_max=salary_max,
        currency=currency,
        job_url="https://example.com/jobs/1",
        source="test",
        date_found="2026-09-29",
    )


class TestRouteManager:
    def test_load_default_rules(self):
        manager = RouteManager()
        rules = manager.load_rules()
        assert len(rules) >= 8
        assert "India" in rules
        assert "UK" in rules
        assert "Germany" in rules

    def test_india_rule_verified(self):
        manager = RouteManager()
        assert manager.is_rule_verified("India") is True
        rule = manager.get_country_rule("india")
        assert rule is not None
        assert rule["requires_sponsorship"] is False

    def test_foreign_rule_unverified_by_default(self):
        manager = RouteManager()
        assert manager.is_rule_verified("UK") is False
        assert manager.is_rule_verified("Germany") is False
        assert manager.is_rule_verified("Canada") is False

    def test_get_route_name(self):
        manager = RouteManager()
        assert "Domestic" in manager.get_route_name("India")
        assert "Skilled Worker" in manager.get_route_name("UK")
        assert "Blue Card" in manager.get_route_name("Germany")


class TestEvidenceAndSignals:
    def test_positive_sponsor_signal_detection(self):
        desc = "Great opportunity! We offer visa sponsorship and comprehensive relocation assistance for this role."
        pos, neg = scan_sponsor_signals(desc)
        assert len(pos) >= 1
        assert len(neg) == 0

    def test_negative_sponsor_signal_detection(self):
        desc = "Candidates must have existing right to work. No visa sponsorship is available."
        pos, neg = scan_sponsor_signals(desc)
        assert len(neg) >= 1
        assert len(pos) == 0

    def test_snippet_extraction(self):
        desc = "We build cutting edge AI. Applicants must already have work authorization in the UK. Competitive salary."
        snippets = extract_evidence_snippets(desc)
        assert len(snippets) > 0
        assert any("work authorization" in s.lower() for s in snippets)


class TestCountryEvaluators:
    def test_india_evaluator(self):
        job = create_sample_job(country="India", location="Mumbai")
        evidence = evaluate_india(job)
        assert evidence.country == "India"
        assert evidence.visa_status == VisaStatus.INDIA
        assert evidence.confidence == ConfidenceLevel.HIGH
        assert evidence.threshold_met is True
        assert "informational planning" in evidence.disclaimer.lower()

    def test_uk_evaluator_unverified_rule_caps_confidence_at_low(self):
        job = create_sample_job(
            country="UK",
            location="London",
            description="Visa sponsorship provided for qualifying candidates.",
        )
        # Unverified rule
        rule = {"route": "Skilled Worker Visa", "verified": False}
        evidence = evaluate_uk(job, rule=rule)

        assert evidence.country == "UK"
        assert evidence.visa_status == VisaStatus.SPONSORSHIP_LIKELY
        # Critical principle: unverified rule must cap confidence at LOW
        assert evidence.confidence == ConfidenceLevel.LOW
        assert evidence.verified_rule is False
        assert "informational planning" in evidence.disclaimer.lower()

    def test_uk_evaluator_verified_rule_allows_high_confidence(self):
        job = create_sample_job(
            country="UK",
            location="London",
            description="Visa sponsorship provided for qualifying candidates.",
        )
        rule = {"route": "Skilled Worker Visa", "verified": True}
        evidence = evaluate_uk(job, rule=rule)
        assert evidence.confidence == ConfidenceLevel.HIGH

    def test_germany_evaluator_negative_signal(self):
        job = create_sample_job(
            country="Germany",
            location="Berlin",
            description="Must already have valid work authorization in Germany. No visa sponsorship.",
        )
        evidence = evaluate_germany(job)
        assert evidence.visa_status == VisaStatus.NOT_SUITABLE
        assert "informational planning" in evidence.disclaimer.lower()

    def test_other_countries_registry(self):
        countries = ["Netherlands", "Canada", "Australia", "Singapore", "UAE"]
        for c in countries:
            evaluator = get_country_evaluator(c)
            job = create_sample_job(country=c, location=f"Capital of {c}")
            evidence = evaluator(job)
            assert evidence.country == c
            assert evidence.confidence == ConfidenceLevel.LOW  # because default rules are unverified
            assert evidence.disclaimer is not None


class TestImmigrationClassifierStage:
    def test_classify_india_job(self):
        classifier = ImmigrationClassifier()
        job = create_sample_job(country="India")
        evidence = classifier.classify(job)
        assert job.visa_status == VisaStatus.INDIA
        assert job.immigration_route is not None
        assert job.visa_evidence is not None
        assert job.visa_evidence["disclaimer"] is not None

    def test_infer_country_from_location(self):
        classifier = ImmigrationClassifier()
        job = create_sample_job(country="Unknown", location="London, UK")
        classifier.classify(job)
        assert job.visa_status in (VisaStatus.SPONSORSHIP_POSSIBLE, VisaStatus.UNCLEAR)
        assert "Skilled Worker" in (job.immigration_route or "")

    def test_classify_all_batch(self):
        classifier = ImmigrationClassifier()
        jobs = [
            create_sample_job(country="India"),
            create_sample_job(country="Germany", description="Visa sponsorship available"),
        ]
        results = classifier.classify_all(jobs)
        assert len(results) == 2
        assert results[0].visa_status == VisaStatus.INDIA
        assert results[1].visa_status == VisaStatus.SPONSORSHIP_LIKELY

    @pytest.mark.asyncio
    async def test_async_pipeline_run_and_health_check(self):
        classifier = ImmigrationClassifier()
        assert await classifier.health_check() is True

        job = create_sample_job(country="India")
        result = await classifier.run(job)
        assert result.visa_status == VisaStatus.INDIA
