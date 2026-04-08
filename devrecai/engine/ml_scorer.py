"""
DevRecAI ML Scorer — XGBoost inference and retraining pipeline.

Features:
- Loads trained XGBoost model from ~/.devrec/models/latest.json
- Encodes profile + tool features into model input vector
- Predicts outcome score (1-5) and normalizes to 0-100
- Retraining pipeline from DuckDB feedback data
- Model versioning (keeps last 3 versions)
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from devrecai.config.settings import get_settings, DEVREC_DIR

logger = logging.getLogger(__name__)

MODELS_DIR = DEVREC_DIR / "models"
FEATURE_VERSION = "v1"

# ─── Feature Encoding ─────────────────────────────────────────────────────────

TEAM_SIZE_ENC = {"solo": 0, "small": 1, "mid": 2, "large": 3, "enterprise": 4}
MATURITY_ENC = {"beginner": 0, "intermediate": 1, "advanced": 2, "sre": 3}
BUDGET_ENC = {"oss": 0, "low": 1, "medium": 2, "enterprise": 3}
PROJECT_TYPE_ENC = {
    "greenfield": 0, "migration": 1, "scaling": 2, "modernisation": 3, "disaster_recovery": 4
}
DEPLOY_STYLE_ENC = {
    "kubernetes": 0, "ecs": 1, "serverless": 2, "vms": 3, "bare_metal": 4, "hybrid": 5
}
UPTIME_ENC = {"99": 0, "99.9": 1, "99.95": 2, "99.99": 3, "99.999": 4}
CLOUD_OPTIONS = ["aws", "gcp", "azure", "on-premise", "hybrid", "multi-cloud"]
LOCK_IN_ENC = {"low": 1.0, "medium": 0.5, "high": 0.0}
PRICING_ENC = {"free": 1.0, "freemium": 0.75, "paid": 0.4, "enterprise": 0.2}


def _encode_profile_tool(tool: dict, profile: dict) -> np.ndarray:
    """Encode a (profile, tool) pair into a feature vector."""
    feats = []

    # Profile features
    feats.append(TEAM_SIZE_ENC.get(profile.get("team_size", "small"), 1))
    feats.append(MATURITY_ENC.get(profile.get("devops_maturity", "intermediate"), 1))
    feats.append(BUDGET_ENC.get(profile.get("budget_tier", "low"), 1))
    feats.append(PROJECT_TYPE_ENC.get(profile.get("project_type", "greenfield"), 0))
    feats.append(DEPLOY_STYLE_ENC.get(profile.get("deployment_style", "kubernetes"), 0))
    feats.append(UPTIME_ENC.get(profile.get("uptime_requirement", "99.9"), 1))

    # Cloud one-hot
    user_clouds = [c.lower() for c in profile.get("cloud_provider", [])]
    feats.extend([1 if c in user_clouds else 0 for c in CLOUD_OPTIONS])

    # Tool features
    feats.append(LOCK_IN_ENC.get(tool.get("vendor_lock_in_risk", "medium"), 0.5))
    feats.append(PRICING_ENC.get(tool.get("pricing_tier", "paid"), 0.4))
    feats.append(min(tool.get("community_health_score", 50) / 100.0, 1.0))
    feats.append(min(tool.get("cve_count_last_12mo", 0) / 50.0, 1.0))  # normalized CVE
    feats.append((5 - tool.get("learning_curve", 3)) / 4.0)  # inverted: easy = 1.0

    return np.array(feats, dtype=np.float32)


class MLScorer:
    """XGBoost-based tool scorer with feedback-driven retraining."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._model = None
        self._model_path: Optional[Path] = None
        self._load_model()

    def _load_model(self) -> None:
        """Attempt to load the latest trained model."""
        latest = MODELS_DIR / "latest.json"
        if not latest.exists():
            # Try .ubj format
            latest_ubj = MODELS_DIR / "latest.ubj"
            if not latest_ubj.exists():
                logger.debug("No trained model found — rule-based fallback will be used.")
                return

        try:
            import xgboost as xgb
            self._model = xgb.XGBRegressor()
            self._model.load_model(str(latest))
            self._model_path = latest
            logger.info(f"ML model loaded from {latest}")
        except Exception as e:
            logger.warning(f"Failed to load ML model: {e}")
            self._model = None

    def is_ready(self) -> bool:
        """Return True if a trained model is loaded."""
        return self._model is not None

    async def predict(self, tool: dict, profile: dict) -> float:
        """Predict outcome score for a tool+profile pair. Returns 0-100."""
        if not self._model:
            return 50.0
        try:
            features = _encode_profile_tool(tool, profile).reshape(1, -1)
            raw = float(self._model.predict(features)[0])
            # Model outputs 1-5 scale → normalize to 0-100
            return round(min(max((raw - 1) / 4.0 * 100, 0), 100), 1)
        except Exception as e:
            logger.warning(f"ML predict failed: {e}")
            return 50.0

    async def confidence(self, tool: dict, profile: dict) -> float:
        """
        Estimate model confidence. Uses prediction stability as proxy.
        Returns 0.0-1.0.
        """
        if not self._model:
            return 0.0
        # Simple heuristic: normalize community_health_score as confidence proxy
        health = tool.get("community_health_score", 50)
        return min(health / 100.0, 1.0)

    async def train(self, db) -> dict:
        """
        Retrain XGBoost on feedback data from DuckDB.
        Returns training metrics dict.
        """
        import xgboost as xgb
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import mean_squared_error

        # Load feedback data
        rows = await db.get_feedback_for_training()
        if not rows:
            raise ValueError("No feedback data available for training.")

        from devrecai.engine.tools_db import get_tool_by_name

        X_list, y_list = [], []
        for row in rows:
            tool = get_tool_by_name(row["tool_name"])
            if tool is None:
                continue
            profile = {
                "team_size": row.get("team_size", "small"),
                "devops_maturity": row.get("maturity", "intermediate"),
                "budget_tier": row.get("budget", "low"),
                "cloud_provider": row.get("cloud", "aws").split(","),
                "project_type": row.get("project_type", "greenfield"),
                "deployment_style": row.get("deployment", "kubernetes"),
                "uptime_requirement": row.get("uptime_sla", "99.9"),
            }
            feats = _encode_profile_tool(tool, profile)
            X_list.append(feats)
            # Map overall_score (1-5) as target
            y_list.append(float(row["overall_score"]))

        X = np.array(X_list, dtype=np.float32)
        y = np.array(y_list, dtype=np.float32)

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        model = xgb.XGBRegressor(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
        )
        model.fit(X_train, y_train)
        preds = model.predict(X_test)
        rmse = float(np.sqrt(mean_squared_error(y_test, preds)))

        # Save model
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_path = MODELS_DIR / f"model_{timestamp}.json"
        model.save_model(str(model_path))

        # Update latest symlink / copy
        latest_path = MODELS_DIR / "latest.json"
        import shutil
        shutil.copy(str(model_path), str(latest_path))

        # Prune old models (keep last 3)
        self._prune_old_models()

        # Reload
        self._load_model()

        # Feature importances
        importances = dict(zip(
            [f"feat_{i}" for i in range(X.shape[1])],
            model.feature_importances_.tolist(),
        ))

        # Log to DB
        await db.save_training_log(
            sample_count=len(X_list),
            rmse=rmse,
            model_path=str(model_path),
            feature_importances=importances,
        )

        return {
            "rmse": rmse,
            "model_path": str(model_path),
            "sample_count": len(X_list),
            "feature_importances": importances,
        }

    def _prune_old_models(self) -> None:
        """Keep only the 3 most recent model files."""
        models = sorted(MODELS_DIR.glob("model_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        for old in models[3:]:
            try:
                old.unlink()
            except Exception:
                pass
