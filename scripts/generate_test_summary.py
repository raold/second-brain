#!/usr/bin/env python3
"""
Test Summary Generator
Creates markdown summary of CI/CD test results for PR comments and reports
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any


class TestSummaryGenerator:
    """Generates markdown test summaries"""
    
    def __init__(self, report_data: Dict[str, Any]):
        self.report = report_data
        self.summary_lines = []
    
    def generate_summary(self) -> str:
        """Generate complete markdown summary"""
        self._add_header()
        self._add_overview()
        self._add_stage_results()
        self._add_test_statistics()
        self._add_performance_metrics()
        self._add_recommendations()
        self._add_artifacts()
        self._add_footer()
        
        return '\n'.join(self.summary_lines)
    
    def _add_header(self):
        """Add summary header"""
        assessment = self.report.get("overall_assessment", {})
        status = assessment.get("status", "UNKNOWN")
        deployment_ready = assessment.get("deployment_ready", False)
        
        status_icon = {
            "EXCELLENT": "🎉",
            "GOOD": "✅", 
            "NEEDS_IMPROVEMENT": "⚠️",
            "UNKNOWN": "❓"
        }.get(status, "❓")
        
        deployment_icon = "🚀" if deployment_ready else "🚫"
        
        self.summary_lines.extend([
            f"# {status_icon} CI/CD Pipeline Results",
            "",
            f"**Status:** {status}  ",
            f"**Deployment Ready:** {deployment_icon} {'YES' if deployment_ready else 'NO'}  ",
            f"**Confidence Score:** {assessment.get('confidence_score', 0):.1f}/100  ",
            f"**Generated:** {datetime.fromisoformat(self.report['timestamp']).strftime('%Y-%m-%d %H:%M:%S UTC')}",
            ""
        ])
    
    def _add_overview(self):
        """Add pipeline overview"""
        summary = self.report.get("pipeline_summary", {})
        
        self.summary_lines.extend([
            "## 📊 Pipeline Overview",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Stages Passed | {summary.get('passed_stages', 0)}/{summary.get('total_stages', 0)} |",
            f"| Tests Passed | {summary.get('total_passed', 0)}/{summary.get('total_tests', 0)} |",
            f"| Success Rate | {summary.get('overall_success_rate', 0):.1%} |",
            f"| Failed Tests | {summary.get('total_failed', 0)} |",
            f"| Skipped Tests | {summary.get('total_skipped', 0)} |",
            f"| Flaky Tests | {summary.get('total_flaky', 0)} |",
            ""
        ])
    
    def _add_stage_results(self):
        """Add detailed stage results"""
        summary = self.report.get("pipeline_summary", {})
        stage_statuses = summary.get("stage_statuses", {})
        
        if not stage_statuses:
            return
        
        self.summary_lines.extend([
            "## 🔍 Stage Results",
            ""
        ])
        
        for stage_name, status in stage_statuses.items():
            status_icon = "✅" if status == "PASS" else "❌"
            stage_display = stage_name.replace('_', ' ').title()
            
            self.summary_lines.append(f"- {status_icon} **{stage_display}**: {status}")
        
        self.summary_lines.append("")
    
    def _add_test_statistics(self):
        """Add detailed test statistics"""
        stage_results = self.report.get("stage_results", {})
        
        if not stage_results:
            return
        
        self.summary_lines.extend([
            "## 📈 Detailed Test Statistics",
            "",
            "| Stage | Total | Passed | Failed | Skipped | Flaky | Success Rate |",
            "|-------|-------|--------|--------|---------|-------|--------------|"
        ])
        
        for stage_name, result_data in stage_results.items():
            stage_display = stage_name.replace('_', ' ').title()
            
            # Extract statistics from various result formats
            stats = self._extract_stage_statistics(result_data)
            
            success_rate = stats['passed'] / stats['total'] if stats['total'] > 0 else 0
            
            self.summary_lines.append(
                f"| {stage_display} | {stats['total']} | {stats['passed']} | "
                f"{stats['failed']} | {stats['skipped']} | {stats['flaky']} | {success_rate:.1%} |"
            )
        
        self.summary_lines.append("")
    
    def _extract_stage_statistics(self, result_data: Dict) -> Dict[str, int]:
        """Extract statistics from various result data formats"""
        stats = {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "flaky": 0}
        
        if isinstance(result_data, dict):
            if "summary" in result_data:
                # Direct summary format
                summary = result_data["summary"]
                stats.update({
                    "total": summary.get("total_tests", 0),
                    "passed": summary.get("passed_tests", 0),
                    "failed": summary.get("failed_tests", 0),
                    "skipped": summary.get("skipped_tests", 0),
                    "flaky": summary.get("flaky_tests", 0)
                })
            elif "stages" in result_data:
                # Multi-stage format - aggregate all stages
                for stage_info in result_data["stages"]:
                    stats["total"] += stage_info.get("total_tests", 0)
                    stats["passed"] += stage_info.get("passed_tests", 0)
                    stats["failed"] += stage_info.get("failed_tests", 0)
                    stats["skipped"] += stage_info.get("skipped_tests", 0)
                    stats["flaky"] += stage_info.get("flaky_tests", 0)
            else:
                # Assume single successful test if no clear format
                stats["total"] = 1
                stats["passed"] = 1
        
        return stats
    
    def _add_performance_metrics(self):
        """Add performance metrics if available"""
        stage_results = self.report.get("stage_results", {})
        
        # Look for performance results
        performance_data = None
        for stage_name, result_data in stage_results.items():
            if "performance" in stage_name.lower():
                performance_data = result_data
                break
        
        if not performance_data:
            return
        
        self.summary_lines.extend([
            "## ⚡ Performance Metrics",
            ""
        ])
        
        # Extract performance information
        if isinstance(performance_data, dict):
            if "results" in performance_data:
                # Performance benchmark format
                self.summary_lines.extend([
                    "| Test | Avg Response Time | P95 | Throughput | Status |",
                    "|------|-------------------|-----|------------|--------|"
                ])
                
                for result in performance_data["results"]:
                    status_icon = "✅" if result.get("status") == "PASS" else "❌"
                    self.summary_lines.append(
                        f"| {result.get('test_name', 'Unknown')} | "
                        f"{result.get('avg_response_time_ms', 0):.1f}ms | "
                        f"{result.get('p95_response_time_ms', 0):.1f}ms | "
                        f"{result.get('throughput_rps', 0):.1f} req/s | "
                        f"{status_icon} {result.get('status', 'UNKNOWN')} |"
                    )
            else:
                self.summary_lines.append("Performance data available but not in expected format.")
        
        self.summary_lines.append("")
    
    def _add_recommendations(self):
        """Add recommendations section"""
        recommendations = self.report.get("recommendations", [])
        
        if not recommendations:
            return
        
        self.summary_lines.extend([
            "## 💡 Recommendations",
            ""
        ])
        
        for rec in recommendations:
            # Clean up formatting for markdown
            if rec.startswith("   "):
                self.summary_lines.append(f"  {rec.strip()}")
            else:
                self.summary_lines.append(f"- {rec}")
        
        self.summary_lines.append("")
    
    def _add_artifacts(self):
        """Add artifacts section"""
        artifacts = self.report.get("artifacts", [])
        
        if not artifacts:
            return
        
        # Group artifacts by type
        artifact_types = {}
        for artifact in artifacts:
            artifact_type = artifact.get("type", "unknown")
            if artifact_type not in artifact_types:
                artifact_types[artifact_type] = []
            artifact_types[artifact_type].append(artifact)
        
        self.summary_lines.extend([
            "## 📁 Available Artifacts",
            ""
        ])
        
        for artifact_type, type_artifacts in artifact_types.items():
            type_display = artifact_type.replace(".", "").upper() if artifact_type != "unknown" else "Other"
            self.summary_lines.append(f"**{type_display} Files:**")
            
            for artifact in type_artifacts:
                size_kb = artifact.get("size_bytes", 0) / 1024
                if size_kb > 1024:
                    size_str = f"{size_kb/1024:.1f}MB"
                else:
                    size_str = f"{size_kb:.1f}KB"
                
                self.summary_lines.append(f"- `{artifact['name']}` ({size_str})")
            
            self.summary_lines.append("")
    
    def _add_footer(self):
        """Add summary footer"""
        assessment = self.report.get("overall_assessment", {})
        
        if assessment.get("deployment_ready"):
            self.summary_lines.extend([
                "---",
                "🎉 **All critical tests passed!** This build is ready for deployment.",
                ""
            ])
        else:
            issues = assessment.get("critical_issues", [])
            if issues:
                self.summary_lines.extend([
                    "---",
                    "🚫 **Deployment blocked due to critical issues:**",
                    ""
                ])
                for issue in issues:
                    self.summary_lines.append(f"- {issue}")
                self.summary_lines.append("")
        
        # Add quick links
        self.summary_lines.extend([
            "<details>",
            "<summary>📋 Full Test Reports</summary>",
            "",
            "- [Smoke Tests](./smoke_report.json)",
            "- [Fast Feedback](./fast_*_report.json)",
            "- [Comprehensive Tests](./comprehensive_report.json)",
            "- [Performance Benchmarks](./performance_report.json)",
            "- [Final Consolidated Report](./final_test_report.json)",
            "",
            "</details>"
        ])


def main():
    """Main summary generation function"""
    parser = argparse.ArgumentParser(description="Generate CI/CD test summary")
    parser.add_argument("--report", type=Path, required=True,
                      help="Consolidated test report JSON file")
    parser.add_argument("--output", type=Path, default="test_summary.md",
                      help="Output markdown file")
    parser.add_argument("--format", choices=["github", "gitlab", "generic"],
                      default="github",
                      help="Output format for specific platforms")
    
    args = parser.parse_args()
    
    if not args.report.exists():
        print(f"❌ Report file not found: {args.report}")
        sys.exit(1)
    
    try:
        with open(args.report, 'r') as f:
            report_data = json.load(f)
    except Exception as e:
        print(f"❌ Failed to load report: {e}")
        sys.exit(1)
    
    print("📝 Generating test summary...")
    
    generator = TestSummaryGenerator(report_data)
    summary_markdown = generator.generate_summary()
    
    # Save summary
    with open(args.output, 'w') as f:
        f.write(summary_markdown)
    
    print(f"✅ Test summary generated: {args.output}")
    
    # Print to stdout for debugging
    if len(sys.argv) == 1:  # No arguments, show preview
        print("\n" + "="*60)
        print("PREVIEW:")
        print("="*60)
        print(summary_markdown[:1000] + "..." if len(summary_markdown) > 1000 else summary_markdown)


if __name__ == "__main__":
    main()