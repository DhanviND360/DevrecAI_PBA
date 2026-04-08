"""
DevRecAI LLM Prompt Templates.

All system prompts and user prompt builder functions.
"""
from __future__ import annotations

import json

# ─── System Prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = (
    "You are DevRecAI, an expert DevOps architect with 15+ years of experience across "
    "startups, scaleups, and enterprises. You have deep hands-on knowledge of the entire "
    "DevOps toolchain including CI/CD, observability, security, IaC, and cloud platforms. "
    "When explaining tool recommendations: (1) Be specific and reference the user's actual "
    "project context, (2) Quantify tradeoffs where possible, (3) Acknowledge uncertainty "
    "honestly, (4) Flag vendor lock-in risks explicitly, (5) Never recommend tools you are "
    "uncertain about. Always structure your explanations clearly."
)

# ─── Prompt Builders ──────────────────────────────────────────────────────────


def build_recommendation_explanation_prompt(profile: dict, scored_tools: dict) -> str:
    return (
        f"Project Profile:\n{json.dumps(profile, indent=2)}\n\n"
        f"Scoring Engine Output:\n{json.dumps(scored_tools, indent=2)}\n\n"
        "For the top 3 tools in each category, write a structured explanation covering: "
        "(1) Why this tool fits this specific project, "
        "(2) Key integration considerations with their existing stack, "
        "(3) Risks and honest tradeoffs, "
        "(4) What maturity level is needed to operate it well. "
        "Be concise but specific. Format as JSON with an object per tool_name containing: "
        "fit_summary, integration_notes, risks, maturity_required, confidence_level fields. "
        "Return ONLY valid JSON, no markdown code blocks."
    )


def build_single_tool_deep_dive_prompt(profile: dict, tool_name: str, score: float) -> str:
    return (
        f"Project Profile:\n{json.dumps(profile, indent=2)}\n\n"
        f"The user wants a deep dive on: {tool_name} (Score: {score}/100)\n\n"
        "Provide: (1) Detailed explanation of fit, (2) Step-by-step integration path with their stack, "
        "(3) Estimated time to productive use, (4) Real-world usage examples from similar companies, "
        "(5) Top 3 alternatives and why this beats them for this profile. "
        "Be honest about weaknesses. Format as JSON with keys: "
        "fit_summary, integration_path, time_to_productive, real_world_examples, "
        "alternatives, risks, confidence_level."
        "Return ONLY valid JSON."
    )


def build_comparison_prompt(profile: dict, tool_list: list[str]) -> str:
    return (
        f"Project Profile:\n{json.dumps(profile, indent=2)}\n\n"
        f"Compare these tools side by side for this project:\n{json.dumps(tool_list)}\n\n"
        "Return a JSON comparison matrix where the top-level keys are tool names, "
        "and each tool has scores and justifications for: "
        "setup_complexity, team_fit, cost_at_scale, community_support, "
        "cloud_integration, security_posture, learning_curve, vendor_risk. "
        "Score each 1-10 and add one sentence justification per criterion per tool. "
        "Return ONLY valid JSON."
    )


def build_report_generation_prompt(profile: dict, full_results: dict) -> str:
    return (
        f"Project Profile:\n{json.dumps(profile, indent=2)}\n\n"
        f"Full Recommendations:\n{json.dumps(full_results, indent=2)}\n\n"
        "Generate a complete professional Markdown report for this DevOps tool selection. "
        "Include: Executive Summary, Project Requirements Analysis, "
        "Recommended Toolchain (all categories), Tool-by-Tool Justifications, "
        "Risk Register, Implementation Roadmap (phased 0-30-60-90 days), "
        "Cost Estimate, Next Steps. "
        "Write for a technical audience. Use Markdown formatting with headers, tables, and bullet points. "
        "Return the full Markdown text only."
    )
