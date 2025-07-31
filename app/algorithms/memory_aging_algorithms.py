#!/usr/bin/env python3
"""
Advanced Memory Aging Algorithms for Second Brain
Implements multiple cognitive science-based memory aging models with sophisticated temporal decay
"""

import asyncio
from app.utils.logging_config import get_logger
from typing import List
from typing import Any
from datetime import datetime
from datetime import timedelta
from enum import Enum
from dataclasses import dataclass
logger = get_logger(__name__)


class AgingModel(Enum):
    """Different memory aging models based on cognitive science"""

    EBBINGHAUS = "ebbinghaus"  # Classic forgetting curve
    POWER_LAW = "power_law"  # Power law decay
    EXPONENTIAL = "exponential"  # Simple exponential decay
    SPACING_EFFECT = "spacing_effect"  # Spaced repetition based
    INTERFERENCE = "interference"  # Memory interference model
    CONSOLIDATION = "consolidation"  # Memory consolidation theory


class MemoryStrength(Enum):
    """Memory strength levels affecting aging rates"""

    WEAK = "weak"  # 0.0-0.3 - High decay rate
    MODERATE = "moderate"  # 0.3-0.6 - Standard decay rate
    STRONG = "strong"  # 0.6-0.8 - Reduced decay rate
    CRYSTAL = "crystal"  # 0.8-1.0 - Minimal decay rate


@dataclass
class AgingParameters:
    """Parameters for memory aging calculations"""

    model: AgingModel
    half_life_days: float = 30.0
    decay_rate: float = 0.1
    strength_threshold: dict[str, float] = None
    interference_factor: float = 0.05
    consolidation_period_days: int = 7
    spacing_intervals: list[int] = None

    def __post_init__(self):
        if self.strength_threshold is None:
            self.strength_threshold = {"weak": 0.3, "moderate": 0.6, "strong": 0.8, "crystal": 1.0}
        if self.spacing_intervals is None:
            self.spacing_intervals = [1, 3, 7, 14, 30, 90]


@dataclass
class MemoryAccess:
    """Represents a memory access event"""

    timestamp: datetime
    access_type: str
    success_rate: float = 1.0
    retrieval_time_ms: int | None = None
    context_similarity: float = 0.5


@dataclass
class AgingResult:
    """Result of memory aging calculation"""

    current_strength: float
    decay_factor: float
    model_used: AgingModel
    strength_category: MemoryStrength
    predicted_half_life: float
    next_optimal_review: datetime | None
    confidence: float
    explanation: str


class AdvancedMemoryAging:
    """
    Advanced memory aging system implementing multiple cognitive science models.

    Features:
    - Multiple aging algorithms (Ebbinghaus, Power Law, Interference, etc.)
    - Adaptive decay rates based on memory strength
    - Spaced repetition optimization
    - Memory consolidation modeling
    - Interference-based forgetting
    - Predictive aging forecasts
    """

    def __init__(self, default_model: AgingModel = AgingModel.EBBINGHAUS):
        self.default_model = default_model
        self.aging_parameters = self._initialize_aging_parameters()

    def _initialize_aging_parameters(self) -> dict[AgingModel, AgingParameters]:
        """Initialize parameters for different aging models"""
        return {
            AgingModel.EBBINGHAUS: AgingParameters(
                model=AgingModel.EBBINGHAUS,
                half_life_days=20.0,
                decay_rate=0.15,
                spacing_intervals=[1, 2, 4, 8, 16, 32],
            ),
            AgingModel.POWER_LAW: AgingParameters(
                model=AgingModel.POWER_LAW, half_life_days=30.0, decay_rate=0.1, spacing_intervals=[1, 3, 9, 27, 81]
            ),
            AgingModel.EXPONENTIAL: AgingParameters(model=AgingModel.EXPONENTIAL, half_life_days=25.0, decay_rate=0.12),
            AgingModel.SPACING_EFFECT: AgingParameters(
                model=AgingModel.SPACING_EFFECT,
                half_life_days=45.0,
                decay_rate=0.08,
                spacing_intervals=[1, 2, 5, 12, 30, 75, 180],
            ),
            AgingModel.INTERFERENCE: AgingParameters(
                model=AgingModel.INTERFERENCE, half_life_days=15.0, decay_rate=0.2, interference_factor=0.1
            ),
            AgingModel.CONSOLIDATION: AgingParameters(
                model=AgingModel.CONSOLIDATION, half_life_days=60.0, decay_rate=0.05, consolidation_period_days=14
            ),
        }

    def calculate_memory_aging(
        self,
        memory_id: str,
        creation_date: datetime,
        access_history: list[MemoryAccess],
        current_importance: float = 0.5,
        memory_type: str = "semantic",
        content_complexity: float = 0.5,
        model: AgingModel | None = None,
    ) -> AgingResult:
        """
        Calculate comprehensive memory aging using specified or adaptive model.

        Args:
            memory_id: Unique memory identifier
            creation_date: When the memory was created
            access_history: List of access events
            current_importance: Current importance score (0-1)
            memory_type: Type of memory (semantic, episodic, procedural)
            content_complexity: Complexity score of content (0-1)
            model: Specific aging model to use (or auto-select)

        Returns:
            AgingResult with detailed aging analysis
        """
        # Select optimal aging model if not specified
        if model is None:
            model = self._select_optimal_model(memory_type, access_history, content_complexity)

        params = self.aging_parameters[model]

        # Calculate base aging factors
        age_days = (datetime.now() - creation_date).days
        last_access = access_history[-1].timestamp if access_history else creation_date
        days_since_access = (datetime.now() - last_access).days

        # Apply specific aging model
        if model == AgingModel.EBBINGHAUS:
            result = self._calculate_ebbinghaus_aging(age_days, days_since_access, access_history, params)
        elif model == AgingModel.POWER_LAW:
            result = self._calculate_power_law_aging(age_days, days_since_access, access_history, params)
        elif model == AgingModel.EXPONENTIAL:
            result = self._calculate_exponential_aging(age_days, days_since_access, access_history, params)
        elif model == AgingModel.SPACING_EFFECT:
            result = self._calculate_spacing_effect_aging(age_days, access_history, params)
        elif model == AgingModel.INTERFERENCE:
            result = self._calculate_interference_aging(age_days, access_history, params, content_complexity)
        elif model == AgingModel.CONSOLIDATION:
            result = self._calculate_consolidation_aging(age_days, days_since_access, access_history, params)
        else:
            # Fallback to Ebbinghaus
            result = self._calculate_ebbinghaus_aging(age_days, days_since_access, access_history, params)

        # Apply memory type modifiers
        result = self._apply_memory_type_modifiers(result, memory_type)

        # Calculate strength category and predictions
        strength_category = self._categorize_memory_strength(result.current_strength)
        next_review = self._predict_optimal_review_time(result, access_history, params)

        return AgingResult(
            current_strength=result.current_strength,
            decay_factor=result.decay_factor,
            model_used=model,
            strength_category=strength_category,
            predicted_half_life=result.predicted_half_life,
            next_optimal_review=next_review,
            confidence=result.confidence,
            explanation=self._generate_aging_explanation(result, model, strength_category),
        )

    def _select_optimal_model(
        self, memory_type: str, access_history: list[MemoryAccess], content_complexity: float
    ) -> AgingModel:
        """Intelligently select the best aging model based on memory characteristics"""

        access_count = len(access_history)

        # High-frequency procedural memories -> Spacing Effect
        if memory_type == "procedural" and access_count > 10:
            return AgingModel.SPACING_EFFECT

        # Complex technical content -> Consolidation model
        if content_complexity > 0.7:
            return AgingModel.CONSOLIDATION

        # Episodic memories with interference -> Interference model
        if memory_type == "episodic" and access_count > 5:
            return AgingModel.INTERFERENCE

        # Regular semantic memories -> Ebbinghaus (classic)
        if memory_type == "semantic":
            return AgingModel.EBBINGHAUS

        # Simple content with few accesses -> Power Law
        if access_count < 3:
            return AgingModel.POWER_LAW

        # Default to Ebbinghaus
        return AgingModel.EBBINGHAUS

    def _calculate_ebbinghaus_aging(
        self, age_days: int, days_since_access: int, access_history: list[MemoryAccess], params: AgingParameters
    ) -> AgingResult:
        """
        Implement Ebbinghaus forgetting curve: R = e^(-t/S)
        Where R = retention, t = time, S = strength factor
        """
        # Calculate strength factor from access patterns
        access_count = len(access_history)
        strength_factor = params.half_life_days * (1 + math.log1p(access_count))

        # Apply Ebbinghaus formula
        retention = math.exp(-days_since_access / strength_factor)

        # Calculate decay factor
        base_decay = math.exp(-days_since_access / params.half_life_days)

        # Boost from recent accesses
        recent_accesses = sum(1 for a in access_history if (datetime.now() - a.timestamp).days <= 7)
        recent_boost = min(0.3, recent_accesses * 0.05)

        current_strength = min(1.0, retention + recent_boost)
        decay_factor = base_decay + recent_boost

        # Predict half-life based on access pattern
        predicted_half_life = strength_factor * 0.693  # ln(2)

        confidence = min(1.0, 0.5 + (access_count * 0.05))

        return AgingResult(
            current_strength=current_strength,
            decay_factor=decay_factor,
            model_used=AgingModel.EBBINGHAUS,
            strength_category=MemoryStrength.WEAK,  # Will be updated
            predicted_half_life=predicted_half_life,
            next_optimal_review=None,  # Will be calculated
            confidence=confidence,
            explanation="Ebbinghaus forgetting curve with access-based strength",
        )

    def _calculate_power_law_aging(
        self, age_days: int, days_since_access: int, access_history: list[MemoryAccess], params: AgingParameters
    ) -> AgingResult:
        """
        Implement Power Law forgetting: R = (1 + t)^(-d)
        Where d is the decay parameter
        """
        access_count = len(access_history)

        # Adaptive decay parameter based on access frequency
        decay_param = params.decay_rate * (1 - min(0.5, access_count / 20))

        # Power law calculation
        retention = math.pow(1 + days_since_access, -decay_param)

        # Frequency protection
        frequency_protection = min(0.4, access_count * 0.02)

        current_strength = min(1.0, retention + frequency_protection)
        decay_factor = retention

        # Power law has slower initial decay but faster long-term decay
        predicted_half_life = math.pow(2, 1 / decay_param) - 1

        confidence = min(1.0, 0.6 + (access_count * 0.03))

        return AgingResult(
            current_strength=current_strength,
            decay_factor=decay_factor,
            model_used=AgingModel.POWER_LAW,
            strength_category=MemoryStrength.WEAK,
            predicted_half_life=predicted_half_life,
            next_optimal_review=None,
            confidence=confidence,
            explanation="Power law decay with frequency protection",
        )

    def _calculate_spacing_effect_aging(
        self, age_days: int, access_history: list[MemoryAccess], params: AgingParameters
    ) -> AgingResult:
        """
        Implement spacing effect model based on spaced repetition intervals
        """
        if not access_history:
            return self._calculate_exponential_aging(age_days, age_days, [], params)

        # Calculate optimal spacing intervals
        intervals = params.spacing_intervals
        access_times = [a.timestamp for a in access_history]
        access_times.sort()

        # Determine current spacing level
        current_level = 0
        last_access = access_times[-1]

        for i, _interval in enumerate(intervals):
            expected_time = access_times[0] + timedelta(days=sum(intervals[: i + 1]))
            if last_access >= expected_time:
                current_level = i + 1
            else:
                break

        # Calculate strength based on spacing adherence
        optimal_spacing_score = current_level / len(intervals)

        # Time since last optimal review
        days_since_last = (datetime.now() - last_access).days
        next_interval = intervals[min(current_level, len(intervals) - 1)]

        # Spacing effect strength calculation
        if days_since_last <= next_interval:
            # Within optimal range
            strength = 0.8 + (optimal_spacing_score * 0.2)
        else:
            # Beyond optimal range - apply decay
            overflow_days = days_since_last - next_interval
            decay = math.exp(-overflow_days / (next_interval * 2))
            strength = (0.8 + (optimal_spacing_score * 0.2)) * decay

        decay_factor = strength
        predicted_half_life = next_interval * 1.5

        confidence = min(1.0, 0.7 + (len(access_history) * 0.03))

        return AgingResult(
            current_strength=strength,
            decay_factor=decay_factor,
            model_used=AgingModel.SPACING_EFFECT,
            strength_category=MemoryStrength.WEAK,
            predicted_half_life=predicted_half_life,
            next_optimal_review=None,
            confidence=confidence,
            explanation=f"Spacing effect model - level {current_level}/{len(intervals)}",
        )

    def _calculate_interference_aging(
        self, age_days: int, access_history: list[MemoryAccess], params: AgingParameters, content_complexity: float
    ) -> AgingResult:
        """
        Implement interference-based forgetting model
        Accounts for memory interference from similar content
        """
        base_decay = math.exp(-age_days / params.half_life_days)

        # Simulate interference from similar memories
        # Higher complexity content is more resistant to interference
        interference_resistance = content_complexity

        # Calculate interference factor based on access frequency of "similar" memories
        # In real implementation, this would analyze actual memory similarity
        estimated_similar_accesses = len(access_history) * 0.3  # Simplified
        interference_effect = params.interference_factor * estimated_similar_accesses
        interference_decay = interference_effect * (1 - interference_resistance)

        # Recent access protection
        days_since_last = (datetime.now() - access_history[-1].timestamp).days if access_history else age_days
        recency_protection = math.exp(-days_since_last / 7.0)

        # Combined strength calculation
        strength = base_decay - interference_decay + (recency_protection * 0.2)
        strength = max(0.05, min(1.0, strength))

        decay_factor = base_decay - interference_decay
        predicted_half_life = params.half_life_days / (1 + interference_decay)

        confidence = min(1.0, 0.4 + (len(access_history) * 0.06))

        return AgingResult(
            current_strength=strength,
            decay_factor=decay_factor,
            model_used=AgingModel.INTERFERENCE,
            strength_category=MemoryStrength.WEAK,
            predicted_half_life=predicted_half_life,
            next_optimal_review=None,
            confidence=confidence,
            explanation=f"Interference model with {interference_decay:.2f} interference factor",
        )

    def _calculate_consolidation_aging(
        self, age_days: int, days_since_access: int, access_history: list[MemoryAccess], params: AgingParameters
    ) -> AgingResult:
        """
        Implement memory consolidation model
        Recent memories are more fragile, older memories become more stable
        """
        consolidation_period = params.consolidation_period_days

        if age_days <= consolidation_period:
            # Memory still consolidating - more vulnerable to decay
            consolidation_factor = age_days / consolidation_period
            base_strength = 0.3 + (consolidation_factor * 0.4)
            decay_rate = params.decay_rate * (2 - consolidation_factor)
        else:
            # Memory consolidated - more stable
            base_strength = 0.7
            decay_rate = params.decay_rate * 0.5

        # Apply temporal decay
        temporal_decay = math.exp(-days_since_access * decay_rate / params.half_life_days)

        # Access frequency boosts consolidation
        access_count = len(access_history)
        consolidation_boost = min(0.3, access_count * 0.03)

        strength = min(1.0, (base_strength * temporal_decay) + consolidation_boost)
        decay_factor = temporal_decay

        # Consolidated memories have longer half-life
        if age_days > consolidation_period:
            predicted_half_life = params.half_life_days * 1.5
        else:
            predicted_half_life = params.half_life_days * consolidation_factor

        confidence = min(1.0, 0.6 + (access_count * 0.04))

        phase = "consolidating" if age_days <= consolidation_period else "consolidated"

        return AgingResult(
            current_strength=strength,
            decay_factor=decay_factor,
            model_used=AgingModel.CONSOLIDATION,
            strength_category=MemoryStrength.WEAK,
            predicted_half_life=predicted_half_life,
            next_optimal_review=None,
            confidence=confidence,
            explanation=f"Consolidation model - {phase} phase ({age_days}/{consolidation_period} days)",
        )

    def _calculate_exponential_aging(
        self, age_days: int, days_since_access: int, access_history: list[MemoryAccess], params: AgingParameters
    ) -> AgingResult:
        """Simple exponential decay model"""
        decay_factor = math.exp(-days_since_access / params.half_life_days)

        # Access frequency protection
        access_protection = min(0.3, len(access_history) * 0.02)

        strength = min(1.0, decay_factor + access_protection)
        predicted_half_life = params.half_life_days
        confidence = min(1.0, 0.5 + (len(access_history) * 0.05))

        return AgingResult(
            current_strength=strength,
            decay_factor=decay_factor,
            model_used=AgingModel.EXPONENTIAL,
            strength_category=MemoryStrength.WEAK,
            predicted_half_life=predicted_half_life,
            next_optimal_review=None,
            confidence=confidence,
            explanation="Simple exponential decay with access protection",
        )

    def _apply_memory_type_modifiers(self, result: AgingResult, memory_type: str) -> AgingResult:
        """Apply memory type-specific aging modifiers"""
        modifiers = {
            "procedural": {"strength_boost": 0.1, "decay_slowdown": 0.8},
            "semantic": {"strength_boost": 0.0, "decay_slowdown": 1.0},
            "episodic": {"strength_boost": -0.05, "decay_slowdown": 1.2},
        }

        modifier = modifiers.get(memory_type, modifiers["semantic"])

        # Apply modifiers
        result.current_strength = min(1.0, result.current_strength + modifier["strength_boost"])
        result.decay_factor *= modifier["decay_slowdown"]
        result.predicted_half_life *= modifier["decay_slowdown"]

        return result

    def _categorize_memory_strength(self, strength: float) -> MemoryStrength:
        """Categorize memory strength level"""
        if strength >= 0.8:
            return MemoryStrength.CRYSTAL
        elif strength >= 0.6:
            return MemoryStrength.STRONG
        elif strength >= 0.3:
            return MemoryStrength.MODERATE
        else:
            return MemoryStrength.WEAK

    def _predict_optimal_review_time(
        self, result: AgingResult, access_history: list[MemoryAccess], params: AgingParameters
    ) -> datetime | None:
        """Predict when memory should be reviewed next for optimal retention"""
        if result.model_used == AgingModel.SPACING_EFFECT:
            # Use spacing intervals
            current_level = len(access_history)
            if current_level < len(params.spacing_intervals):
                days_to_review = params.spacing_intervals[current_level]
                return datetime.now() + timedelta(days=days_to_review)

        # For other models, predict when strength drops to 0.5
        target_strength = 0.5
        current_strength = result.current_strength

        if current_strength <= target_strength:
            return datetime.now() + timedelta(days=1)  # Review soon

        # Calculate time to reach target strength
        decay_rate = -math.log(result.decay_factor) if result.decay_factor > 0 else 0.1

        if decay_rate > 0:
            days_to_target = math.log(target_strength / current_strength) / (-decay_rate)
            days_to_target = max(1, min(365, days_to_target))  # Reasonable bounds
            return datetime.now() + timedelta(days=days_to_target)

        return None

    def _generate_aging_explanation(
        self, result: AgingResult, model: AgingModel, strength_category: MemoryStrength
    ) -> str:
        """Generate human-readable explanation of aging calculation"""
        explanations = [f"{model.value.replace('_', ' ').title()} aging model"]

        if strength_category == MemoryStrength.CRYSTAL:
            explanations.append("crystallized memory with minimal decay")
        elif strength_category == MemoryStrength.STRONG:
            explanations.append("strong memory with slow decay")
        elif strength_category == MemoryStrength.MODERATE:
            explanations.append("moderate strength with standard decay")
        else:
            explanations.append("weak memory requiring attention")

        if result.predicted_half_life > 60:
            explanations.append("long-term stability")
        elif result.predicted_half_life > 20:
            explanations.append("medium-term retention")
        else:
            explanations.append("short-term retention")

        return ", ".join(explanations)

    def get_aging_analytics(self, memory_aging_data: list[tuple[str, AgingResult]]) -> dict[str, Any]:
        """Generate analytics about memory aging patterns"""
        if not memory_aging_data:
            return {"error": "No aging data available"}

        # Group by strength category
        strength_distribution = {}
        model_usage = {}
        avg_half_life_by_model = {}

        for _memory_id, aging_result in memory_aging_data:
            # Strength distribution
            strength = aging_result.strength_category.value
            strength_distribution[strength] = strength_distribution.get(strength, 0) + 1

            # Model usage
            model = aging_result.model_used.value
            model_usage[model] = model_usage.get(model, 0) + 1

            # Half-life tracking
            if model not in avg_half_life_by_model:
                avg_half_life_by_model[model] = []
            avg_half_life_by_model[model].append(aging_result.predicted_half_life)

        # Calculate averages
        for model in avg_half_life_by_model:
            values = avg_half_life_by_model[model]
            avg_half_life_by_model[model] = sum(values) / len(values)

        total_memories = len(memory_aging_data)

        return {
            "total_memories": total_memories,
            "strength_distribution": strength_distribution,
            "model_usage": model_usage,
            "average_half_life_by_model": avg_half_life_by_model,
            "insights": self._generate_aging_insights(
                strength_distribution, model_usage, avg_half_life_by_model, total_memories
            ),
        }

    def _generate_aging_insights(
        self, strength_dist: dict[str, int], model_usage: dict[str, int], half_life_data: dict[str, float], total: int
    ) -> list[str]:
        """Generate insights from aging analytics"""
        insights = []

        # Strength insights
        weak_percent = (strength_dist.get("weak", 0) / total) * 100
        crystal_percent = (strength_dist.get("crystal", 0) / total) * 100

        if weak_percent > 30:
            insights.append(f"{weak_percent:.1f}% of memories are weak - consider review scheduling")
        if crystal_percent > 20:
            insights.append(f"{crystal_percent:.1f}% of memories are crystallized - excellent retention")

        # Model insights
        most_used_model = max(model_usage.items(), key=lambda x: x[1])[0]
        insights.append(f"Most effective aging model: {most_used_model.replace('_', ' ').title()}")

        # Half-life insights
        best_model = max(half_life_data.items(), key=lambda x: x[1])
        insights.append(f"Longest retention with {best_model[0]}: {best_model[1]:.1f} days average")

        return insights


# Example usage and testing
async def demo_memory_aging():
    """Demonstrate advanced memory aging algorithms"""
    print("🧠 Advanced Memory Aging Algorithms Demo")
    print("=" * 50)

    aging_system = AdvancedMemoryAging()

    # Create sample memory access history
    now = datetime.now()
    creation_date = now - timedelta(days=30)

    access_history = [
        MemoryAccess(creation_date + timedelta(days=1), "initial_access"),
        MemoryAccess(creation_date + timedelta(days=3), "review"),
        MemoryAccess(creation_date + timedelta(days=7), "search_result"),
        MemoryAccess(creation_date + timedelta(days=15), "direct_access"),
        MemoryAccess(creation_date + timedelta(days=25), "api_call"),
    ]

    # Test different aging models
    models_to_test = [
        AgingModel.EBBINGHAUS,
        AgingModel.POWER_LAW,
        AgingModel.SPACING_EFFECT,
        AgingModel.INTERFERENCE,
        AgingModel.CONSOLIDATION,
    ]

    print("\n📊 Testing Different Aging Models:")
    print("-" * 40)

    for model in models_to_test:
        result = aging_system.calculate_memory_aging(
            memory_id="test-memory",
            creation_date=creation_date,
            access_history=access_history,
            current_importance=0.7,
            memory_type="procedural",
            content_complexity=0.8,
            model=model,
        )

        print(f"\n🔬 {model.value.title().replace('_', ' ')} Model:")
        print(f"   Current Strength: {result.current_strength:.3f}")
        print(f"   Strength Category: {result.strength_category.value.title()}")
        print(f"   Predicted Half-life: {result.predicted_half_life:.1f} days")
        print(f"   Confidence: {result.confidence:.3f}")
        print(f"   Explanation: {result.explanation}")

        if result.next_optimal_review:
            days_to_review = (result.next_optimal_review - now).days
            print(f"   Next Review: {days_to_review} days")

    print("\n🎯 Automatic Model Selection:")
    print("-" * 40)

    # Test automatic model selection for different memory types
    memory_types = ["semantic", "episodic", "procedural"]

    for mem_type in memory_types:
        result = aging_system.calculate_memory_aging(
            memory_id=f"test-{mem_type}",
            creation_date=creation_date,
            access_history=access_history,
            memory_type=mem_type,
            content_complexity=0.6,
        )

        print(f"\n📚 {mem_type.title()} Memory:")
        print(f"   Selected Model: {result.model_used.value.title().replace('_', ' ')}")
        print(f"   Current Strength: {result.current_strength:.3f}")
        print(f"   Explanation: {result.explanation}")


if __name__ == "__main__":
    asyncio.run(demo_memory_aging())
