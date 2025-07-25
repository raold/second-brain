"""
Anomaly detection service for v2.8.3 Intelligence features.

This service implements multiple anomaly detection algorithms to identify
unusual patterns in metrics, user behavior, and system performance.
"""

import asyncio
import logging
import statistics
from datetime import datetime, timedelta
from uuid import uuid4

import numpy as np

from app.database import Database
from app.models.intelligence.analytics_models import (
    Anomaly,
    AnomalyType,
    MetricSeries,
    MetricType,
)

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """Base class for anomaly detection algorithms."""

    def detect(self, series: MetricSeries) -> list[Anomaly]:
        """Detect anomalies in a metric series."""
        raise NotImplementedError


class StatisticalAnomalyDetector(AnomalyDetector):
    """Statistical anomaly detection using z-scores and IQR."""

    def __init__(self, z_threshold: float = 3.0, iqr_multiplier: float = 1.5):
        self.z_threshold = z_threshold
        self.iqr_multiplier = iqr_multiplier

    def detect(self, series: MetricSeries) -> list[Anomaly]:
        """Detect anomalies using statistical methods."""
        if len(series.data_points) < 10:
            return []

        anomalies = []
        values = [p.value for p in series.data_points]

        # Z-score based detection
        z_anomalies = self._detect_z_score(series, values)
        anomalies.extend(z_anomalies)

        # IQR based detection
        iqr_anomalies = self._detect_iqr(series, values)
        anomalies.extend(iqr_anomalies)

        # Remove duplicates
        seen = set()
        unique_anomalies = []
        for anomaly in anomalies:
            key = (anomaly.timestamp, anomaly.actual_value)
            if key not in seen:
                seen.add(key)
                unique_anomalies.append(anomaly)

        return unique_anomalies

    def _detect_z_score(self, series: MetricSeries, values: list[float]) -> list[Anomaly]:
        """Detect anomalies using z-score method."""
        mean = statistics.mean(values)
        std = statistics.stdev(values)

        if std == 0:
            return []

        anomalies = []
        for i, point in enumerate(series.data_points):
            z_score = abs((point.value - mean) / std)

            if z_score > self.z_threshold:
                anomaly_type = AnomalyType.SPIKE if point.value > mean else AnomalyType.DROP

                anomalies.append(Anomaly(
                    id=uuid4(),
                    metric_type=series.metric_type,
                    anomaly_type=anomaly_type,
                    timestamp=point.timestamp,
                    severity=min(z_score / (self.z_threshold * 2), 1.0),
                    expected_value=mean,
                    actual_value=point.value,
                    confidence=0.8,
                    description=f"Value deviates {z_score:.1f} standard deviations from mean",
                    metadata={"z_score": z_score, "method": "z_score"}
                ))

        return anomalies

    def _detect_iqr(self, series: MetricSeries, values: list[float]) -> list[Anomaly]:
        """Detect anomalies using IQR method."""
        q1 = np.percentile(values, 25)
        q3 = np.percentile(values, 75)
        iqr = q3 - q1

        lower_bound = q1 - self.iqr_multiplier * iqr
        upper_bound = q3 + self.iqr_multiplier * iqr

        anomalies = []
        for point in series.data_points:
            if point.value < lower_bound or point.value > upper_bound:
                anomaly_type = AnomalyType.SPIKE if point.value > upper_bound else AnomalyType.DROP
                expected = (q1 + q3) / 2  # Median of quartiles

                anomalies.append(Anomaly(
                    id=uuid4(),
                    metric_type=series.metric_type,
                    anomaly_type=anomaly_type,
                    timestamp=point.timestamp,
                    severity=self._calculate_iqr_severity(point.value, lower_bound, upper_bound),
                    expected_value=expected,
                    actual_value=point.value,
                    confidence=0.75,
                    description=f"Value outside IQR bounds [{lower_bound:.2f}, {upper_bound:.2f}]",
                    metadata={"method": "iqr", "bounds": [lower_bound, upper_bound]}
                ))

        return anomalies

    def _calculate_iqr_severity(self, value: float, lower: float, upper: float) -> float:
        """Calculate severity based on how far outside IQR bounds."""
        if lower <= value <= upper:
            return 0.0

        if value < lower:
            distance = lower - value
            range_size = upper - lower
        else:
            distance = value - upper
            range_size = upper - lower

        return min(distance / range_size, 1.0)


class MovingAverageDetector(AnomalyDetector):
    """Anomaly detection using moving averages and deviation bands."""

    def __init__(self, window_size: int = 10, deviation_multiplier: float = 2.0):
        self.window_size = window_size
        self.deviation_multiplier = deviation_multiplier

    def detect(self, series: MetricSeries) -> list[Anomaly]:
        """Detect anomalies using moving average method."""
        if len(series.data_points) < self.window_size:
            return []

        anomalies = []
        values = [p.value for p in series.data_points]

        # Calculate moving averages and standard deviations
        for i in range(self.window_size, len(values)):
            window = values[i-self.window_size:i]
            ma = statistics.mean(window)
            std = statistics.stdev(window) if len(window) > 1 else 0

            upper_band = ma + self.deviation_multiplier * std
            lower_band = ma - self.deviation_multiplier * std

            current_value = values[i]
            current_point = series.data_points[i]

            if current_value > upper_band or current_value < lower_band:
                anomaly_type = AnomalyType.SPIKE if current_value > upper_band else AnomalyType.DROP

                anomalies.append(Anomaly(
                    id=uuid4(),
                    metric_type=series.metric_type,
                    anomaly_type=anomaly_type,
                    timestamp=current_point.timestamp,
                    severity=self._calculate_band_severity(current_value, ma, std),
                    expected_value=ma,
                    actual_value=current_value,
                    confidence=0.7,
                    description=f"Value outside {self.deviation_multiplier}σ bands of moving average",
                    metadata={
                        "method": "moving_average",
                        "window_size": self.window_size,
                        "ma": ma,
                        "bands": [lower_band, upper_band]
                    }
                ))

        return anomalies

    def _calculate_band_severity(self, value: float, ma: float, std: float) -> float:
        """Calculate severity based on deviation from moving average."""
        if std == 0:
            return 0.5

        deviation = abs(value - ma) / std
        return min(deviation / (self.deviation_multiplier * 2), 1.0)


class PatternBreakDetector(AnomalyDetector):
    """Detect breaks in regular patterns (e.g., daily/weekly cycles)."""

    def __init__(self, pattern_threshold: float = 0.3):
        self.pattern_threshold = pattern_threshold

    def detect(self, series: MetricSeries) -> list[Anomaly]:
        """Detect pattern breaks in time series."""
        if len(series.data_points) < 48:  # Need at least 2 days of hourly data
            return []

        anomalies = []

        # Detect daily pattern breaks
        daily_anomalies = self._detect_daily_pattern_breaks(series)
        anomalies.extend(daily_anomalies)

        # Detect weekly pattern breaks if enough data
        if len(series.data_points) >= 168:  # 7 days of hourly data
            weekly_anomalies = self._detect_weekly_pattern_breaks(series)
            anomalies.extend(weekly_anomalies)

        return anomalies

    def _detect_daily_pattern_breaks(self, series: MetricSeries) -> list[Anomaly]:
        """Detect breaks in daily patterns."""
        anomalies = []

        # Group by hour of day
        hourly_values = {}
        for point in series.data_points:
            hour = point.timestamp.hour
            if hour not in hourly_values:
                hourly_values[hour] = []
            hourly_values[hour].append(point.value)

        # Calculate expected pattern
        hourly_patterns = {}
        for hour, values in hourly_values.items():
            if len(values) > 1:
                hourly_patterns[hour] = {
                    'mean': statistics.mean(values),
                    'std': statistics.stdev(values)
                }

        # Check for pattern breaks
        for point in series.data_points:
            hour = point.timestamp.hour
            if hour in hourly_patterns and hourly_patterns[hour]['std'] > 0:
                pattern = hourly_patterns[hour]
                z_score = abs((point.value - pattern['mean']) / pattern['std'])

                if z_score > 3:  # 3 standard deviations
                    anomalies.append(Anomaly(
                        id=uuid4(),
                        metric_type=series.metric_type,
                        anomaly_type=AnomalyType.PATTERN_BREAK,
                        timestamp=point.timestamp,
                        severity=min(z_score / 5, 1.0),
                        expected_value=pattern['mean'],
                        actual_value=point.value,
                        confidence=0.65,
                        description=f"Breaks expected daily pattern for hour {hour}",
                        metadata={
                            "method": "daily_pattern",
                            "hour": hour,
                            "z_score": z_score
                        }
                    ))

        return anomalies

    def _detect_weekly_pattern_breaks(self, series: MetricSeries) -> list[Anomaly]:
        """Detect breaks in weekly patterns."""
        anomalies = []

        # Group by day of week and hour
        weekly_values = {}
        for point in series.data_points:
            key = (point.timestamp.weekday(), point.timestamp.hour)
            if key not in weekly_values:
                weekly_values[key] = []
            weekly_values[key].append(point.value)

        # Calculate patterns
        weekly_patterns = {}
        for key, values in weekly_values.items():
            if len(values) > 2:
                weekly_patterns[key] = {
                    'mean': statistics.mean(values),
                    'std': statistics.stdev(values)
                }

        # Check for pattern breaks
        for point in series.data_points:
            key = (point.timestamp.weekday(), point.timestamp.hour)
            if key in weekly_patterns and weekly_patterns[key]['std'] > 0:
                pattern = weekly_patterns[key]
                z_score = abs((point.value - pattern['mean']) / pattern['std'])

                if z_score > 3:
                    day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
                    anomalies.append(Anomaly(
                        id=uuid4(),
                        metric_type=series.metric_type,
                        anomaly_type=AnomalyType.PATTERN_BREAK,
                        timestamp=point.timestamp,
                        severity=min(z_score / 5, 1.0),
                        expected_value=pattern['mean'],
                        actual_value=point.value,
                        confidence=0.6,
                        description=f"Breaks weekly pattern for {day_names[key[0]]} {key[1]:02d}:00",
                        metadata={
                            "method": "weekly_pattern",
                            "day": key[0],
                            "hour": key[1],
                            "z_score": z_score
                        }
                    ))

        return anomalies


class FrequencyAnomalyDetector(AnomalyDetector):
    """Detect anomalies in event frequency."""

    def __init__(self, window_minutes: int = 60):
        self.window_minutes = window_minutes

    def detect(self, series: MetricSeries) -> list[Anomaly]:
        """Detect unusual frequency patterns."""
        if len(series.data_points) < 10:
            return []

        anomalies = []

        # Calculate event frequencies
        frequencies = self._calculate_frequencies(series)

        if len(frequencies) < 3:
            return []

        # Detect frequency anomalies
        freq_values = list(frequencies.values())
        mean_freq = statistics.mean(freq_values)
        std_freq = statistics.stdev(freq_values) if len(freq_values) > 1 else 0

        for timestamp, freq in frequencies.items():
            if std_freq > 0:
                z_score = abs((freq - mean_freq) / std_freq)

                if z_score > 2.5:
                    anomaly_type = AnomalyType.UNUSUAL_FREQUENCY

                    anomalies.append(Anomaly(
                        id=uuid4(),
                        metric_type=series.metric_type,
                        anomaly_type=anomaly_type,
                        timestamp=timestamp,
                        severity=min(z_score / 4, 1.0),
                        expected_value=mean_freq,
                        actual_value=freq,
                        confidence=0.7,
                        description=f"Unusual event frequency: {freq:.1f} events per window",
                        metadata={
                            "method": "frequency",
                            "window_minutes": self.window_minutes,
                            "z_score": z_score
                        }
                    ))

        return anomalies

    def _calculate_frequencies(self, series: MetricSeries) -> dict[datetime, float]:
        """Calculate event frequencies in time windows."""
        frequencies = {}
        window_delta = timedelta(minutes=self.window_minutes)

        # Sort points by timestamp
        sorted_points = sorted(series.data_points, key=lambda p: p.timestamp)

        if not sorted_points:
            return frequencies

        current_window_start = sorted_points[0].timestamp
        current_window_end = current_window_start + window_delta
        window_events = []

        for point in sorted_points:
            if point.timestamp < current_window_end:
                window_events.append(point)
            else:
                # Calculate frequency for completed window
                if window_events:
                    frequencies[current_window_start] = len(window_events)

                # Move to next window
                current_window_start = current_window_end
                current_window_end = current_window_start + window_delta
                window_events = [point]

        # Handle last window
        if window_events:
            frequencies[current_window_start] = len(window_events)

        return frequencies


class AnomalyDetectionService:
    """Main service for anomaly detection across all metrics."""

    def __init__(self, database: Database):
        self.db = database

        # Initialize detectors
        self.detectors = [
            StatisticalAnomalyDetector(),
            MovingAverageDetector(),
            PatternBreakDetector(),
            FrequencyAnomalyDetector()
        ]

    async def detect_anomalies(
        self,
        metrics: dict[MetricType, MetricSeries],
        sensitivity: float = 1.0
    ) -> list[Anomaly]:
        """Detect anomalies across all metrics using ensemble methods."""
        all_anomalies = []

        # Run detection for each metric
        tasks = []
        for metric_type, series in metrics.items():
            task = self._detect_metric_anomalies(metric_type, series, sensitivity)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Error detecting anomalies: {result}")
                continue
            all_anomalies.extend(result)

        # Merge and rank anomalies
        merged_anomalies = self._merge_anomalies(all_anomalies)

        # Sort by severity and timestamp
        merged_anomalies.sort(key=lambda a: (a.severity, a.timestamp), reverse=True)

        return merged_anomalies

    async def _detect_metric_anomalies(
        self,
        metric_type: MetricType,
        series: MetricSeries,
        sensitivity: float
    ) -> list[Anomaly]:
        """Detect anomalies for a specific metric."""
        anomalies = []

        # Run all detectors
        for detector in self.detectors:
            try:
                detected = detector.detect(series)
                anomalies.extend(detected)
            except Exception as e:
                logger.error(f"Error in {detector.__class__.__name__}: {e}")

        # Adjust confidence based on sensitivity
        for anomaly in anomalies:
            anomaly.confidence *= sensitivity

        return anomalies

    def _merge_anomalies(self, anomalies: list[Anomaly]) -> list[Anomaly]:
        """Merge similar anomalies from different detectors."""
        if not anomalies:
            return []

        # Group by timestamp and metric
        grouped = {}
        for anomaly in anomalies:
            key = (
                anomaly.metric_type,
                anomaly.timestamp,
                anomaly.anomaly_type
            )
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(anomaly)

        # Merge groups
        merged = []
        for key, group in grouped.items():
            if len(group) == 1:
                merged.append(group[0])
            else:
                # Combine multiple detections
                combined = self._combine_anomalies(group)
                merged.append(combined)

        return merged

    def _combine_anomalies(self, anomalies: list[Anomaly]) -> Anomaly:
        """Combine multiple anomaly detections into one."""
        # Use the anomaly with highest confidence as base
        base = max(anomalies, key=lambda a: a.confidence)

        # Average severity and confidence
        avg_severity = statistics.mean(a.severity for a in anomalies)
        avg_confidence = statistics.mean(a.confidence for a in anomalies)

        # Combine descriptions
        methods = []
        for a in anomalies:
            if 'method' in a.metadata:
                methods.append(a.metadata['method'])

        base.severity = avg_severity
        base.confidence = min(avg_confidence * 1.2, 1.0)  # Boost confidence for multiple detections
        base.description = f"Detected by {len(anomalies)} methods: {', '.join(set(methods))}"
        base.metadata['detection_count'] = len(anomalies)

        return base
