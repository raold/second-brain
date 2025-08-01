"""
import pytest

pytestmark = pytest.mark.unit

Test suite for memory aging algorithms module.
Tests the sophisticated memory aging system with multiple cognitive science models.
"""

from datetime import datetime, timedelta

from app.algorithms.memory_aging_algorithms import (
    AdvancedMemoryAging,
    AgingModel,
    AgingParameters,
    AgingResult,
    MemoryAccess,
    MemoryStrength,
)


class TestAgingModel:
    """Test AgingModel enum."""

    def test_aging_model_values(self):
        assert AgingModel.EBBINGHAUS.value == "ebbinghaus"
        assert AgingModel.POWER_LAW.value == "power_law"
        assert AgingModel.EXPONENTIAL.value == "exponential"
        assert AgingModel.SPACING_EFFECT.value == "spacing_effect"
        assert AgingModel.INTERFERENCE.value == "interference"
        assert AgingModel.CONSOLIDATION.value == "consolidation"

    def test_aging_model_count(self):
        assert len(AgingModel) == 6


class TestMemoryStrength:
    """Test MemoryStrength enum."""

    def test_memory_strength_values(self):
        assert MemoryStrength.CRYSTAL.value == "crystal"
        assert MemoryStrength.STRONG.value == "strong"
        assert MemoryStrength.MODERATE.value == "moderate"
        assert MemoryStrength.WEAK.value == "weak"

    def test_memory_strength_count(self):
        assert len(MemoryStrength) == 4


class TestAgingParameters:
    """Test AgingParameters dataclass."""

    def test_aging_parameters_creation(self):
        params = AgingParameters(
            model=AgingModel.EBBINGHAUS,
            half_life_days=20.0,
            decay_rate=0.15,
            spacing_intervals=[1, 2, 4, 8, 16, 32],
            interference_factor=0.1,
            consolidation_period_days=14
        )

        assert params.model == AgingModel.EBBINGHAUS
        assert params.half_life_days == 20.0
        assert params.decay_rate == 0.15
        assert params.spacing_intervals == [1, 2, 4, 8, 16, 32]
        assert params.interference_factor == 0.1
        assert params.consolidation_period_days == 14

    def test_aging_parameters_minimal(self):
        params = AgingParameters(
            model=AgingModel.POWER_LAW,
            half_life_days=30.0,
            decay_rate=0.1
        )

        assert params.model == AgingModel.POWER_LAW
        assert params.half_life_days == 30.0
        assert params.decay_rate == 0.1
        # __post_init__ sets defaults for these
        assert params.spacing_intervals == [1, 3, 7, 14, 30, 90]
        assert params.strength_threshold == {"weak": 0.3, "moderate": 0.6, "strong": 0.8, "crystal": 1.0}


class TestMemoryAccess:
    """Test MemoryAccess dataclass."""

    def test_memory_access_creation(self):
        now = datetime.now()
        access = MemoryAccess(
            timestamp=now,
            access_type="retrieval",
            success_rate=0.9,
            retrieval_time_ms=150,
            context_similarity=0.8
        )

        assert access.timestamp == now
        assert access.access_type == "retrieval"
        assert access.success_rate == 0.9
        assert access.retrieval_time_ms == 150
        assert access.context_similarity == 0.8

    def test_memory_access_defaults(self):
        access = MemoryAccess(
            timestamp=datetime.now(),
            access_type="review"
        )

        assert access.success_rate == 1.0
        assert access.retrieval_time_ms is None
        assert access.context_similarity == 0.5


class TestAgingResult:
    """Test AgingResult dataclass."""

    def test_aging_result_creation(self):
        result = AgingResult(
            current_strength=0.75,
            decay_factor=0.1,
            model_used=AgingModel.EBBINGHAUS,
            strength_category=MemoryStrength.STRONG,
            predicted_half_life=30.0,
            next_optimal_review=datetime.now() + timedelta(days=7),
            confidence=0.85,
            explanation="Memory aging calculated using Ebbinghaus curve"
        )

        assert result.current_strength == 0.75
        assert result.decay_factor == 0.1
        assert result.model_used == AgingModel.EBBINGHAUS
        assert result.strength_category == MemoryStrength.STRONG
        assert result.predicted_half_life == 30.0
        assert result.next_optimal_review is not None
        assert result.confidence == 0.85
        assert "Ebbinghaus" in result.explanation

    def test_aging_result_minimal(self):
        result = AgingResult(
            current_strength=0.4,
            decay_factor=0.2,
            model_used=AgingModel.POWER_LAW,
            strength_category=MemoryStrength.WEAK,
            predicted_half_life=15.0,
            next_optimal_review=None,
            confidence=0.7,
            explanation="Power law decay model applied"
        )

        assert result.current_strength == 0.4
        assert result.strength_category == MemoryStrength.WEAK
        assert result.next_optimal_review is None


class TestAdvancedMemoryAging:
    """Test AdvancedMemoryAging class."""

    def setup_method(self):
        self.aging = AdvancedMemoryAging()

    def test_initialization_default(self):
        aging = AdvancedMemoryAging()
        assert aging.default_model == AgingModel.EBBINGHAUS
        assert aging.aging_parameters is not None
        assert len(aging.aging_parameters) == 6  # All aging models

    def test_initialization_custom_model(self):
        aging = AdvancedMemoryAging(AgingModel.POWER_LAW)
        assert aging.default_model == AgingModel.POWER_LAW

    def test_aging_parameters_complete(self):
        aging = AdvancedMemoryAging()
        assert AgingModel.EBBINGHAUS in aging.aging_parameters
        assert AgingModel.POWER_LAW in aging.aging_parameters
        assert AgingModel.EXPONENTIAL in aging.aging_parameters
        assert AgingModel.SPACING_EFFECT in aging.aging_parameters
        assert AgingModel.INTERFERENCE in aging.aging_parameters
        assert AgingModel.CONSOLIDATION in aging.aging_parameters

    def test_calculate_memory_aging_basic(self):
        now = datetime.now()
        creation_date = now - timedelta(days=7)
        access_history = [
            MemoryAccess(
                timestamp=now - timedelta(days=3),
                access_type="retrieval",
                success_rate=0.9,
                retrieval_time_ms=150,
                context_similarity=0.8
            )
        ]

        result = self.aging.calculate_memory_aging(
            memory_id="test1",
            creation_date=creation_date,
            access_history=access_history
        )

        assert isinstance(result, AgingResult)
        assert 0 <= result.current_strength <= 1
        assert isinstance(result.decay_factor, float)
        assert result.model_used in AgingModel
        assert result.strength_category in MemoryStrength

    def test_calculate_memory_aging_with_recent_access(self):
        now = datetime.now()
        creation_date = now - timedelta(days=10)
        access_history = [
            MemoryAccess(
                timestamp=now - timedelta(days=1),
                access_type="review",
                success_rate=0.95,
                retrieval_time_ms=120
            )
        ]

        result = self.aging.calculate_memory_aging(
            memory_id="test2",
            creation_date=creation_date,
            access_history=access_history,
            current_importance=0.8
        )

        assert result.current_strength > 0.5  # Recent access should boost strength

    def test_calculate_memory_aging_with_specific_model(self):
        now = datetime.now()
        creation_date = now - timedelta(days=5)
        access_history = [
            MemoryAccess(
                timestamp=now - timedelta(days=2),
                access_type="retrieval",
                success_rate=0.8
            )
        ]

        result = self.aging.calculate_memory_aging(
            memory_id="test3",
            creation_date=creation_date,
            access_history=access_history,
            model=AgingModel.POWER_LAW
        )

        assert result.model_used == AgingModel.POWER_LAW

    def test_calculate_memory_aging_empty_history(self):
        now = datetime.now()
        creation_date = now - timedelta(days=15)

        result = self.aging.calculate_memory_aging(
            memory_id="test4",
            creation_date=creation_date,
            access_history=[]
        )

        assert isinstance(result, AgingResult)
        assert result.current_strength < 0.8  # Should decay without access

    def test_calculate_memory_aging_with_memory_type(self):
        now = datetime.now()
        creation_date = now - timedelta(days=8)
        access_history = [
            MemoryAccess(
                timestamp=now - timedelta(days=4),
                access_type="review"
            )
        ]

        result = self.aging.calculate_memory_aging(
            memory_id="test5",
            creation_date=creation_date,
            access_history=access_history,
            memory_type="procedural"
        )

        assert isinstance(result, AgingResult)

    def test_calculate_memory_aging_complex_content(self):
        now = datetime.now()
        creation_date = now - timedelta(days=12)
        access_history = [
            MemoryAccess(
                timestamp=now - timedelta(days=6),
                access_type="study",
                success_rate=0.7
            )
        ]

        result = self.aging.calculate_memory_aging(
            memory_id="test6",
            creation_date=creation_date,
            access_history=access_history,
            content_complexity=0.9
        )

        assert isinstance(result, AgingResult)
        # Complex content might use consolidation model

    def test_model_selection_procedural_high_access(self):
        """Test automatic model selection for procedural memories with high access"""
        now = datetime.now()
        creation_date = now - timedelta(days=30)

        # Create high-frequency access history
        access_history = []
        for i in range(15):
            access_history.append(
                MemoryAccess(
                    timestamp=now - timedelta(days=i),
                    access_type="practice"
                )
            )

        result = self.aging.calculate_memory_aging(
            memory_id="procedural_test",
            creation_date=creation_date,
            access_history=access_history,
            memory_type="procedural"
        )

        # Should select SPACING_EFFECT model for high-frequency procedural
        assert result.model_used == AgingModel.SPACING_EFFECT

    def test_model_selection_complex_content(self):
        """Test automatic model selection for complex content"""
        now = datetime.now()
        creation_date = now - timedelta(days=10)
        access_history = [
            MemoryAccess(timestamp=now - timedelta(days=3), access_type="study")
        ]

        result = self.aging.calculate_memory_aging(
            memory_id="complex_test",
            creation_date=creation_date,
            access_history=access_history,
            content_complexity=0.8
        )

        # Should select CONSOLIDATION for complex content
        assert result.model_used == AgingModel.CONSOLIDATION

    def test_model_selection_episodic_interference(self):
        """Test automatic model selection for episodic memories with interference"""
        now = datetime.now()
        creation_date = now - timedelta(days=20)

        # Create moderate access history
        access_history = []
        for i in range(8):
            access_history.append(
                MemoryAccess(
                    timestamp=now - timedelta(days=i*2),
                    access_type="recall"
                )
            )

        result = self.aging.calculate_memory_aging(
            memory_id="episodic_test",
            creation_date=creation_date,
            access_history=access_history,
            memory_type="episodic"
        )

        # Should select INTERFERENCE for episodic with many accesses
        assert result.model_used == AgingModel.INTERFERENCE

    def test_model_selection_semantic_default(self):
        """Test automatic model selection for semantic memories"""
        now = datetime.now()
        creation_date = now - timedelta(days=7)
        access_history = [
            MemoryAccess(timestamp=now - timedelta(days=2), access_type="review")
        ]

        result = self.aging.calculate_memory_aging(
            memory_id="semantic_test",
            creation_date=creation_date,
            access_history=access_history,
            memory_type="semantic"
        )

        # Should select EBBINGHAUS for semantic memories
        assert result.model_used == AgingModel.EBBINGHAUS

    def test_model_selection_few_accesses(self):
        """Test automatic model selection for memories with few accesses"""
        now = datetime.now()
        creation_date = now - timedelta(days=14)
        access_history = [
            MemoryAccess(timestamp=now - timedelta(days=7), access_type="view")
        ]

        result = self.aging.calculate_memory_aging(
            memory_id="few_access_test",
            creation_date=creation_date,
            access_history=access_history,
            memory_type="episodic"  # Non-semantic to trigger access count logic
        )

        # Should select POWER_LAW for few accesses (< 3)
        assert result.model_used == AgingModel.POWER_LAW

    def test_all_aging_models_functional(self):
        """Test that all aging models can be used successfully"""
        now = datetime.now()
        creation_date = now - timedelta(days=10)
        access_history = [
            MemoryAccess(
                timestamp=now - timedelta(days=5),
                access_type="review",
                success_rate=0.8
            )
        ]

        for model in AgingModel:
            result = self.aging.calculate_memory_aging(
                memory_id=f"test_{model.value}",
                creation_date=creation_date,
                access_history=access_history,
                model=model
            )

            assert isinstance(result, AgingResult)
            assert result.model_used == model
            assert 0 <= result.current_strength <= 1
            assert isinstance(result.explanation, str)
            assert len(result.explanation) > 0

    def test_aging_parameters_initialization(self):
        """Test that aging parameters are properly initialized for all models"""
        aging = AdvancedMemoryAging()

        for model in AgingModel:
            assert model in aging.aging_parameters
            params = aging.aging_parameters[model]
            assert isinstance(params, AgingParameters)
            assert params.model == model
            assert params.half_life_days > 0
            assert 0 < params.decay_rate < 1

    def test_edge_case_very_old_memory(self):
        """Test aging calculation for very old memories"""
        now = datetime.now()
        creation_date = now - timedelta(days=365)  # 1 year old
        access_history = [
            MemoryAccess(
                timestamp=creation_date + timedelta(days=30),
                access_type="initial_review"
            )
        ]

        result = self.aging.calculate_memory_aging(
            memory_id="old_memory",
            creation_date=creation_date,
            access_history=access_history
        )

        assert isinstance(result, AgingResult)
        assert result.current_strength < 0.5  # Should be significantly decayed

    def test_edge_case_new_memory_no_access(self):
        """Test aging calculation for very new memories with no access"""
        now = datetime.now()
        creation_date = now - timedelta(hours=1)  # 1 hour old

        result = self.aging.calculate_memory_aging(
            memory_id="new_memory",
            creation_date=creation_date,
            access_history=[]
        )

        assert isinstance(result, AgingResult)
        assert result.current_strength > 0.8  # Should still be strong

    def test_edge_case_high_frequency_access(self):
        """Test aging calculation for memories with very high access frequency"""
        now = datetime.now()
        creation_date = now - timedelta(days=30)

        # Create very high-frequency access pattern
        access_history = []
        for i in range(50):  # 50 accesses
            access_history.append(
                MemoryAccess(
                    timestamp=now - timedelta(hours=i*12),  # Every 12 hours
                    access_type="frequent_review",
                    success_rate=0.95
                )
            )

        result = self.aging.calculate_memory_aging(
            memory_id="frequent_memory",
            creation_date=creation_date,
            access_history=access_history
        )

        assert isinstance(result, AgingResult)
        assert result.current_strength > 0.7  # Should be well-maintained
