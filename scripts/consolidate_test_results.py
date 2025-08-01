#!/usr/bin/env python3
"""
Test Results Consolidation Script
Combines results from all CI/CD test stages into unified report
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any


class TestResultsConsolidator:
    """Consolidates test results from multiple stages"""
    
    def __init__(self, results_dir: Path):
        self.results_dir = results_dir
        self.consolidated_report = {
            "timestamp": datetime.now().isoformat(),
            "pipeline_summary": {},
            "stage_results": {},
            "overall_assessment": {},
            "recommendations": [],
            "artifacts": []
        }
    
    def consolidate_results(self) -> Dict[str, Any]:
        """Consolidate all test results into unified report"""
        print("🔄 Consolidating test results from all stages...")
        
        # Find all test result files
        result_files = self._find_result_files()
        
        if not result_files:
            print("⚠️  No test result files found")
            return self._create_empty_report()
        
        # Process each result file
        stage_results = {}
        for file_path, stage_name in result_files:
            try:
                with open(file_path, 'r') as f:
                    result_data = json.load(f)
                    stage_results[stage_name] = result_data
                    print(f"✅ Loaded {stage_name} results from {file_path.name}")
            except Exception as e:
                print(f"❌ Failed to load {file_path}: {e}")
                continue
        
        # Generate consolidated report
        self.consolidated_report["stage_results"] = stage_results
        self.consolidated_report["pipeline_summary"] = self._create_pipeline_summary(stage_results)
        self.consolidated_report["overall_assessment"] = self._assess_overall_status(stage_results)
        self.consolidated_report["recommendations"] = self._generate_recommendations(stage_results)
        self.consolidated_report["artifacts"] = self._catalog_artifacts()
        
        return self.consolidated_report
    
    def _find_result_files(self) -> List[tuple]:
        """Find all test result JSON files"""
        result_files = []
        
        # Search patterns for different stages
        patterns = {
            "smoke": ["smoke_report.json", "smoke-test-results"],
            "fast_unit": ["fast_unit_report.json", "fast-feedback-results-unit"],
            "fast_integration": ["fast_integration-basic_report.json", "fast-feedback-results-integration-basic"],
            "fast_api": ["fast_api-core_report.json", "fast-feedback-results-api-core"],
            "comprehensive": ["comprehensive_report.json", "comprehensive-test-results"],
            "performance": ["performance_report.json", "performance-test-results"]
        }
        
        for stage_name, file_patterns in patterns.items():
            for pattern in file_patterns:
                # Check direct files
                direct_file = self.results_dir / pattern
                if direct_file.exists() and direct_file.is_file():
                    result_files.append((direct_file, stage_name))
                    break
                    
                # Check in subdirectories
                for subdir in self.results_dir.iterdir():
                    if subdir.is_dir() and pattern in subdir.name:
                        for json_file in subdir.glob("*.json"):
                            result_files.append((json_file, stage_name))
                            break
                        break
        
        return result_files
    
    def _create_empty_report(self) -> Dict[str, Any]:
        """Create empty report when no results found"""
        return {
            "timestamp": datetime.now().isoformat(),
            "pipeline_summary": {
                "status": "NO_RESULTS",
                "total_stages": 0,
                "passed_stages": 0,
                "failed_stages": 0,
                "deployment_ready": False
            },
            "stage_results": {},
            "overall_assessment": {
                "status": "UNKNOWN",
                "deployment_ready": False,
                "critical_issues": ["No test results found"]
            },
            "recommendations": [
                "Investigate why no test results were generated",
                "Check CI/CD pipeline configuration",
                "Verify test execution completed"
            ],
            "artifacts": []
        }
    
    def _create_pipeline_summary(self, stage_results: Dict) -> Dict[str, Any]:
        """Create high-level pipeline summary"""
        total_stages = len(stage_results)
        passed_stages = 0
        failed_stages = 0
        total_tests = 0
        total_passed = 0
        total_failed = 0
        total_skipped = 0
        total_flaky = 0
        
        stage_statuses = {}
        
        for stage_name, result_data in stage_results.items():
            if isinstance(result_data, dict):
                # Check if this is a stage result or consolidated report
                if "summary" in result_data:
                    summary = result_data["summary"]
                    stage_passed = summary.get("deployment_ready", False) or summary.get("success_rate", 0) >= 0.8
                    
                    total_tests += summary.get("total_tests", 0)
                    total_passed += summary.get("passed_tests", 0)
                    total_failed += summary.get("failed_tests", 0)
                    total_skipped += summary.get("skipped_tests", 0)
                    total_flaky += summary.get("flaky_tests", 0)
                    
                elif "stages" in result_data:
                    # This is a nested report with multiple stages
                    for stage_info in result_data["stages"]:
                        stage_passed = not stage_info.get("should_block", True)
                        total_tests += stage_info.get("total_tests", 0)
                        total_passed += stage_info.get("passed_tests", 0)
                        total_failed += stage_info.get("failed_tests", 0)
                        total_skipped += stage_info.get("skipped_tests", 0)
                        total_flaky += stage_info.get("flaky_tests", 0)
                else:
                    # Assume passed if no clear failure indicators
                    stage_passed = True
                
                if stage_passed:
                    passed_stages += 1
                    stage_statuses[stage_name] = "PASS"
                else:
                    failed_stages += 1
                    stage_statuses[stage_name] = "FAIL"
        
        overall_success_rate = total_passed / total_tests if total_tests > 0 else 0
        deployment_ready = failed_stages == 0 and overall_success_rate >= 0.8
        
        return {
            "status": "PASS" if deployment_ready else "FAIL",
            "total_stages": total_stages,
            "passed_stages": passed_stages,
            "failed_stages": failed_stages,
            "stage_statuses": stage_statuses,
            "total_tests": total_tests,
            "total_passed": total_passed,
            "total_failed": total_failed,
            "total_skipped": total_skipped,
            "total_flaky": total_flaky,
            "overall_success_rate": overall_success_rate,
            "deployment_ready": deployment_ready
        }
    
    def _assess_overall_status(self, stage_results: Dict) -> Dict[str, Any]:
        """Assess overall pipeline status and readiness"""
        summary = self.consolidated_report["pipeline_summary"]
        
        critical_issues = []
        warnings = []
        
        # Check for critical failures
        if summary["failed_stages"] > 0:
            critical_issues.append(f"{summary['failed_stages']} stage(s) failed")
        
        if summary["overall_success_rate"] < 0.8:
            critical_issues.append(f"Success rate ({summary['overall_success_rate']:.1%}) below threshold (80%)")
        
        # Check for warnings
        if summary["total_flaky"] > 0:
            warnings.append(f"{summary['total_flaky']} flaky tests detected")
        
        if summary["total_skipped"] > summary["total_tests"] * 0.1:
            warnings.append(f"High skip rate: {summary['total_skipped']} skipped tests")
        
        # Determine overall status
        if not critical_issues:
            if not warnings:
                status = "EXCELLENT"
                readiness_level = "Production Ready"
            else:
                status = "GOOD"
                readiness_level = "Staging Ready"
        else:
            status = "NEEDS_IMPROVEMENT"
            readiness_level = "Development Only"
        
        return {
            "status": status,
            "readiness_level": readiness_level,
            "deployment_ready": summary["deployment_ready"],
            "critical_issues": critical_issues,
            "warnings": warnings,
            "confidence_score": self._calculate_confidence_score(summary)
        }
    
    def _calculate_confidence_score(self, summary: Dict) -> float:
        """Calculate confidence score (0-100)"""
        base_score = summary["overall_success_rate"] * 100
        
        # Penalize failures
        failure_penalty = summary["failed_stages"] * 20
        
        # Penalize flaky tests
        flaky_penalty = min(summary["total_flaky"] * 2, 20)
        
        # Reward comprehensive testing
        coverage_bonus = min(summary["total_stages"] * 5, 20)
        
        confidence = max(0, base_score - failure_penalty - flaky_penalty + coverage_bonus)
        return min(100, confidence)
    
    def _generate_recommendations(self, stage_results: Dict) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        assessment = self.consolidated_report["overall_assessment"]
        
        if assessment["deployment_ready"]:
            recommendations.extend([
                "✅ All critical tests passed - Ready for deployment",
                "Consider setting up production monitoring",
                "Review performance benchmarks for optimization opportunities"
            ])
        else:
            if assessment["critical_issues"]:
                recommendations.append("🚨 Address critical issues before deployment:")
                for issue in assessment["critical_issues"]:
                    recommendations.append(f"   - {issue}")
            
            if assessment["warnings"]:
                recommendations.append("⚠️  Address these warnings for better reliability:")
                for warning in assessment["warnings"]:
                    recommendations.append(f"   - {warning}")
        
        # Specific recommendations based on stage failures
        for stage_name, result_data in stage_results.items():
            if isinstance(result_data, dict) and "stages" in result_data:
                for stage_info in result_data["stages"]:
                    if stage_info.get("should_block", False):
                        failed_tests = [t for t in stage_info.get("tests", []) if t.get("status") == "FAIL"]
                        if failed_tests:
                            recommendations.append(f"🔧 Fix {len(failed_tests)} failed tests in {stage_info['stage']} stage")
        
        return recommendations
    
    def _catalog_artifacts(self) -> List[Dict]:
        """Catalog all available artifacts"""
        artifacts = []
        
        for item in self.results_dir.rglob("*"):
            if item.is_file():
                artifacts.append({
                    "name": item.name,
                    "path": str(item.relative_to(self.results_dir)),
                    "size_bytes": item.stat().st_size,
                    "type": item.suffix or "unknown"
                })
        
        return artifacts
    
    def save_report(self, output_path: Path):
        """Save consolidated report to file"""
        with open(output_path, 'w') as f:
            json.dump(self.consolidated_report, f, indent=2, default=str)
        
        print(f"📄 Consolidated report saved to: {output_path}")
    
    def print_summary(self):
        """Print consolidated results summary"""
        print("\n" + "=" * 80)
        print("📋 CI/CD PIPELINE RESULTS SUMMARY")
        print("=" * 80)
        
        summary = self.consolidated_report["pipeline_summary"]
        assessment = self.consolidated_report["overall_assessment"]
        
        print(f"Overall Status: {assessment['status']}")
        print(f"Readiness Level: {assessment['readiness_level']}")
        print(f"Confidence Score: {assessment['confidence_score']:.1f}/100")
        print(f"Deployment Ready: {'✅ YES' if assessment['deployment_ready'] else '❌ NO'}")
        
        print(f"\n📊 Test Statistics:")
        print(f"   Stages: {summary['passed_stages']}/{summary['total_stages']} passed")
        print(f"   Tests: {summary['total_passed']}/{summary['total_tests']} passed")
        print(f"   Success Rate: {summary['overall_success_rate']:.1%}")
        
        if summary['total_failed'] > 0:
            print(f"   ❌ Failed: {summary['total_failed']}")
        if summary['total_skipped'] > 0:
            print(f"   ⏭️  Skipped: {summary['total_skipped']}")
        if summary['total_flaky'] > 0:
            print(f"   🔄 Flaky: {summary['total_flaky']}")
        
        # Print stage-by-stage results
        print(f"\n🔍 Stage Results:")
        for stage_name, status in summary['stage_statuses'].items():
            status_icon = "✅" if status == "PASS" else "❌"
            print(f"   {status_icon} {stage_name}: {status}")
        
        # Print recommendations
        if self.consolidated_report["recommendations"]:
            print(f"\n💡 Recommendations:")
            for rec in self.consolidated_report["recommendations"]:
                print(f"   {rec}")
        
        print("=" * 80)


def main():
    """Main consolidation function"""
    parser = argparse.ArgumentParser(description="Consolidate CI/CD test results")
    parser.add_argument("--results-dir", type=Path, required=True,
                      help="Directory containing test result artifacts")
    parser.add_argument("--output", type=Path, default="final_test_report.json",
                      help="Output file for consolidated report")
    
    args = parser.parse_args()
    
    if not args.results_dir.exists():
        print(f"❌ Results directory not found: {args.results_dir}")
        sys.exit(1)
    
    print("🔄 Starting test results consolidation...")
    
    consolidator = TestResultsConsolidator(args.results_dir)
    consolidated_report = consolidator.consolidate_results()
    
    consolidator.print_summary()
    consolidator.save_report(args.output)
    
    # Exit with appropriate code for CI/CD
    if consolidated_report["pipeline_summary"]["deployment_ready"]:
        print("\n✅ Consolidation complete - Pipeline ready for deployment!")
        sys.exit(0)
    else:
        print("\n❌ Consolidation complete - Critical issues found")
        sys.exit(1)


if __name__ == "__main__":
    main()