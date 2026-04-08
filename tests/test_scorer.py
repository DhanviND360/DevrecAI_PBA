"""
Unit tests for the rule-based scorer.
"""
import pytest
from devrecai.engine.rules import (
    compute_rule_score,
    compute_per_criterion,
    score_stack_compatibility,
    score_budget_fit,
    score_compliance_fit,
    score_learning_curve,
    score_lock_in_risk,
)


# ─── Sample Tool Fixtures ─────────────────────────────────────────────────────

@pytest.fixture
def github_actions():
    return {
        "name": "GitHub Actions",
        "category": "CI/CD",
        "license": "commercial",
        "cloud_native": True,
        "cloud_compatibility": ["aws", "gcp", "azure", "all"],
        "language_compatibility": ["python", "go", "java", "node.js", "ruby", "rust", ".net", "php"],
        "team_size_fit": ["solo", "small", "mid", "large", "enterprise"],
        "learning_curve": 2,
        "community_health_score": 95,
        "vendor_lock_in_risk": "medium",
        "compliance_certifications": ["soc2", "iso27001"],
        "integrations": ["docker", "kubernetes", "aws", "gcp", "azure", "terraform"],
        "pricing_tier": "freemium",
        "cve_count_last_12mo": 2,
    }


@pytest.fixture
def jenkins():
    return {
        "name": "Jenkins",
        "category": "CI/CD",
        "license": "oss",
        "cloud_native": False,
        "cloud_compatibility": ["aws", "gcp", "azure", "on-premise"],
        "language_compatibility": ["python", "go", "java", "node.js"],
        "team_size_fit": ["mid", "large", "enterprise"],
        "learning_curve": 4,
        "community_health_score": 75,
        "vendor_lock_in_risk": "low",
        "compliance_certifications": [],
        "integrations": ["docker", "kubernetes", "aws", "terraform"],
        "pricing_tier": "free",
        "cve_count_last_12mo": 8,
    }


@pytest.fixture
def basic_profile():
    return {
        "project_name": "Test Project",
        "project_type": "greenfield",
        "team_size": "small",
        "devops_maturity": "intermediate",
        "budget_tier": "low",
        "cloud_provider": ["aws"],
        "languages": ["python"],
        "compliance": ["none"],
        "existing_tools": "",
        "deployment_style": "kubernetes",
    }


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestStackCompatibility:
    def test_perfect_match(self, github_actions, basic_profile):
        score = score_stack_compatibility(github_actions, basic_profile)
        assert score >= 0.9, "GitHub Actions + AWS/Python should score very high"

    def test_cloud_mismatch(self, github_actions):
        profile = {"cloud_provider": ["on-premise"], "languages": ["go"]}
        score = score_stack_compatibility(github_actions, profile)
        # GitHub Actions supports all clouds so should still be decent
        assert score >= 0.5

    def test_no_profile_data(self, github_actions):
        score = score_stack_compatibility(github_actions, {})
        assert 0.0 <= score <= 1.0


class TestBudgetFit:
    def test_free_tool_always_fits(self, jenkins, basic_profile):
        # Jenkins is free — should always fit any budget
        score = score_budget_fit(jenkins, basic_profile)
        assert score == 1.0

    def test_paid_tool_oss_budget(self, github_actions):
        profile = {"budget_tier": "oss"}
        # freemium tier with oss budget → partial fit
        score = score_budget_fit(github_actions, profile)
        assert 0.0 <= score <= 1.0

    def test_enterprise_budget_fits_all(self, github_actions):
        profile = {"budget_tier": "enterprise"}
        score = score_budget_fit(github_actions, profile)
        assert score == 1.0


class TestComplianceFit:
    def test_no_compliance_required(self, github_actions, basic_profile):
        score = score_compliance_fit(github_actions, basic_profile)
        assert score == 1.0  # no compliance = any tool fits

    def test_soc2_match(self, github_actions):
        profile = {"compliance": ["soc2"]}
        score = score_compliance_fit(github_actions, profile)
        assert score == 1.0

    def test_hipaa_no_cert(self, jenkins):
        profile = {"compliance": ["hipaa"]}
        score = score_compliance_fit(jenkins, profile)
        assert score < 0.5  # Jenkins has no compliance certs


class TestLearningCurve:
    def test_beginner_easy_tool(self, github_actions):
        profile = {"devops_maturity": "beginner"}
        score = score_learning_curve(github_actions, profile)
        assert score == 1.0  # curve=2 <= maturity=1? No — 2 > 1, slight penalty

    def test_beginner_hard_tool(self, jenkins):
        profile = {"devops_maturity": "beginner"}
        score = score_learning_curve(jenkins, profile)
        assert score < 0.5  # Jenkins curve=4, beginner=1 → heavy penalty

    def test_sre_hard_tool(self, jenkins):
        profile = {"devops_maturity": "sre"}
        score = score_learning_curve(jenkins, profile)
        assert score == 1.0


class TestLockInRisk:
    def test_low_risk(self, jenkins):
        score = score_lock_in_risk(jenkins, {})
        assert score == 1.0

    def test_medium_risk(self, github_actions):
        score = score_lock_in_risk(github_actions, {})
        assert score == 0.6


class TestComputeRuleScore:
    def test_score_range(self, github_actions, basic_profile):
        score = compute_rule_score(github_actions, basic_profile)
        assert 0 <= score <= 100

    def test_github_beats_jenkins_for_small_team(self, github_actions, jenkins, basic_profile):
        gh_score = compute_rule_score(github_actions, basic_profile)
        j_score = compute_rule_score(jenkins, basic_profile)
        assert gh_score > j_score, "GitHub Actions should score higher for small beginner team"

    def test_per_criterion_returns_all_keys(self, github_actions, basic_profile):
        criteria = compute_per_criterion(github_actions, basic_profile)
        expected = {
            "stack_compatibility", "team_size_fit", "budget_fit",
            "compliance_fit", "community_health", "learning_curve",
            "lock_in_risk", "integration_breadth",
        }
        assert expected == set(criteria.keys())

    def test_per_criterion_range(self, github_actions, basic_profile):
        criteria = compute_per_criterion(github_actions, basic_profile)
        for k, v in criteria.items():
            assert 0 <= v <= 100, f"{k} score out of range: {v}"
