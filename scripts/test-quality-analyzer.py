#!/usr/bin/env python3
"""
Test Quality Analyzer for Second Brain v2.6.0-dev

Analyzes test results and generates quality reports for regular review.
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

import xml.etree.ElementTree as ET


class TestQualityAnalyzer:
    """Analyzes test quality and generates reports"""
    
    def __init__(self):
        self.base_path = Path(".")
        self.report_data = {
            "timestamp": datetime.now().isoformat(),
            "coverage": {},
            "test_results": {},
            "quality_metrics": {},
            "recommendations": []
        }
    
    def analyze_coverage(self):
        """Analyze test coverage from coverage.xml"""
        coverage_file = self.base_path / "coverage.xml"
        if not coverage_file.exists():
            print("❌ No coverage.xml found")
            return
        
        try:
            tree = ET.parse(coverage_file)
            root = tree.getroot()
            
            # Overall coverage
            coverage_elem = root.find("coverage")
            if coverage_elem is not None:
                line_rate = float(coverage_elem.get("line-rate", 0))
                branch_rate = float(coverage_elem.get("branch-rate", 0))
                
                self.report_data["coverage"] = {
                    "line_coverage": round(line_rate * 100, 2),
                    "branch_coverage": round(branch_rate * 100, 2),
                    "timestamp": coverage_elem.get("timestamp")
                }
            
            # Per-module coverage
            packages = root.find("packages")
            if packages is not None:
                module_coverage = {}
                for package in packages.findall("package"):
                    package_name = package.get("name", "")
                    
                    for class_elem in package.findall("classes/class"):
                        filename = class_elem.get("filename", "")
                        line_rate = float(class_elem.get("line-rate", 0))
                        
                        module_coverage[filename] = {
                            "coverage": round(line_rate * 100, 2),
                            "lines": len(class_elem.findall("lines/line"))
                        }
                
                self.report_data["coverage"]["modules"] = module_coverage
                
        except Exception as e:
            print(f"❌ Error parsing coverage.xml: {e}")
    
    def analyze_test_results(self):
        """Analyze test results from pytest JSON report"""
        results_file = self.base_path / "test-results.json"
        if not results_file.exists():
            print("❌ No test-results.json found")
            return
        
        try:
            with open(results_file) as f:
                data = json.load(f)
            
            summary = data.get("summary", {})
            
            self.report_data["test_results"] = {
                "total": summary.get("total", 0),
                "passed": summary.get("passed", 0),
                "failed": summary.get("failed", 0),
                "skipped": summary.get("skipped", 0),
                "error": summary.get("error", 0),
                "duration": data.get("duration", 0),
                "success_rate": round(summary.get("passed", 0) / max(summary.get("total", 1), 1) * 100, 2)
            }
            
            # Analyze slow tests
            tests = data.get("tests", [])
            slow_tests = sorted(
                [t for t in tests if t.get("duration", 0) > 1.0],
                key=lambda x: x.get("duration", 0),
                reverse=True
            )[:10]
            
            self.report_data["test_results"]["slow_tests"] = [
                {
                    "name": t.get("nodeid", ""),
                    "duration": round(t.get("duration", 0), 3)
                }
                for t in slow_tests
            ]
            
            # Analyze failed tests
            failed_tests = [t for t in tests if t.get("outcome") == "failed"]
            self.report_data["test_results"]["failed_tests"] = [
                {
                    "name": t.get("nodeid", ""),
                    "error": t.get("call", {}).get("longrepr", "")[:200] + "..."
                }
                for t in failed_tests[:5]  # Top 5 failures
            ]
            
        except Exception as e:
            print(f"❌ Error parsing test-results.json: {e}")
    
    def analyze_test_files(self):
        """Analyze test file quality"""
        test_dir = self.base_path / "tests"
        if not test_dir.exists():
            return
        
        test_files = list(test_dir.rglob("test_*.py"))
        
        quality_metrics = {
            "total_test_files": len(test_files),
            "test_lines": 0,
            "test_functions": 0,
            "test_classes": 0,
            "async_tests": 0,
            "parameterized_tests": 0,
            "fixture_usage": 0,
            "mock_usage": 0,
            "files_without_docstrings": [],
            "files_with_long_functions": [],
            "files_with_few_assertions": []
        }
        
        for test_file in test_files:
            try:
                content = test_file.read_text()
                lines = content.split('\n')
                
                quality_metrics["test_lines"] += len(lines)
                
                # Count patterns
                quality_metrics["test_functions"] += len(re.findall(r'def test_', content))
                quality_metrics["test_classes"] += len(re.findall(r'class Test', content))
                quality_metrics["async_tests"] += len(re.findall(r'async def test_', content))
                quality_metrics["parameterized_tests"] += len(re.findall(r'@pytest.mark.parametrize', content))
                quality_metrics["fixture_usage"] += len(re.findall(r'@pytest.fixture', content))
                quality_metrics["mock_usage"] += len(re.findall(r'Mock\(|patch\(|AsyncMock\(', content))
                
                # Quality checks
                if '"""' not in content and "'''" not in content:
                    quality_metrics["files_without_docstrings"].append(str(test_file.name))
                
                # Check for long test functions (>50 lines)
                in_function = False
                function_lines = 0
                function_name = ""
                
                for line in lines:
                    if line.strip().startswith('def test_'):
                        if in_function and function_lines > 50:
                            quality_metrics["files_with_long_functions"].append(
                                f"{test_file.name}::{function_name} ({function_lines} lines)"
                            )
                        in_function = True
                        function_lines = 0
                        function_name = line.strip().split('(')[0].replace('def ', '')
                    elif in_function:
                        if line.strip() and not line.startswith(' '):
                            # End of function
                            if function_lines > 50:
                                quality_metrics["files_with_long_functions"].append(
                                    f"{test_file.name}::{function_name} ({function_lines} lines)"
                                )
                            in_function = False
                        else:
                            function_lines += 1
                
                # Check for few assertions (functions with <2 assertions)
                test_functions = re.findall(r'def (test_\w+).*?(?=def |\Z)', content, re.DOTALL)
                for func_match in test_functions:
                    func_content = func_match if isinstance(func_match, str) else func_match[0]
                    assert_count = len(re.findall(r'assert ', func_content))
                    if assert_count < 2:
                        quality_metrics["files_with_few_assertions"].append(
                            f"{test_file.name}::{func_content.split('(')[0]} ({assert_count} assertions)"
                        )
                        
            except Exception as e:
                print(f"❌ Error analyzing {test_file}: {e}")
        
        self.report_data["quality_metrics"] = quality_metrics
    
    def generate_recommendations(self):
        """Generate recommendations based on analysis"""
        recommendations = []
        
        # Coverage recommendations
        coverage = self.report_data.get("coverage", {})
        line_coverage = coverage.get("line_coverage", 0)
        
        if line_coverage < 85:
            recommendations.append(
                f"📊 **Coverage Below Target**: Current coverage is {line_coverage}%. "
                f"Target is 85%. Add {85 - line_coverage:.1f}% more coverage."
            )
        
        if line_coverage < 70:
            recommendations.append(
                "🚨 **Critical Coverage Gap**: Coverage is critically low. "
                "Prioritize adding tests for core functionality."
            )
        
        # Module-specific coverage
        modules = coverage.get("modules", {})
        low_coverage_modules = [
            (module, data["coverage"]) 
            for module, data in modules.items() 
            if data["coverage"] < 70
        ]
        
        if low_coverage_modules:
            recommendations.append(
                f"📂 **Low Coverage Modules**: {len(low_coverage_modules)} modules below 70% coverage: "
                f"{', '.join([f'{Path(m).name} ({c}%)' for m, c in low_coverage_modules[:5]])}"
            )
        
        # Test results recommendations
        test_results = self.report_data.get("test_results", {})
        success_rate = test_results.get("success_rate", 100)
        
        if success_rate < 100:
            failed = test_results.get("failed", 0)
            recommendations.append(
                f"❌ **Test Failures**: {failed} tests failing. "
                f"Success rate: {success_rate}%. Fix failing tests immediately."
            )
        
        # Performance recommendations
        slow_tests = test_results.get("slow_tests", [])
        if slow_tests:
            slowest = slow_tests[0]
            recommendations.append(
                f"⏱️ **Slow Tests**: {len(slow_tests)} tests >1s. "
                f"Slowest: {slowest['name']} ({slowest['duration']}s). Consider optimization."
            )
        
        # Quality recommendations
        quality = self.report_data.get("quality_metrics", {})
        
        if quality.get("files_without_docstrings"):
            count = len(quality["files_without_docstrings"])
            recommendations.append(
                f"📝 **Missing Docstrings**: {count} test files lack docstrings. "
                f"Add documentation for better maintainability."
            )
        
        if quality.get("files_with_long_functions"):
            count = len(quality["files_with_long_functions"])
            recommendations.append(
                f"🔧 **Long Test Functions**: {count} test functions >50 lines. "
                f"Consider breaking into smaller, focused tests."
            )
        
        # Test pattern recommendations
        total_tests = quality.get("test_functions", 0)
        async_tests = quality.get("async_tests", 0)
        parameterized_tests = quality.get("parameterized_tests", 0)
        
        if total_tests > 0:
            async_ratio = async_tests / total_tests
            if async_ratio < 0.3:
                recommendations.append(
                    f"🔄 **Low Async Test Coverage**: Only {async_ratio:.1%} of tests are async. "
                    f"Consider testing more async functionality."
                )
            
            param_ratio = parameterized_tests / total_tests
            if param_ratio < 0.1:
                recommendations.append(
                    f"🎯 **Limited Parameterized Tests**: Only {param_ratio:.1%} use parametrization. "
                    f"Consider using parametrized tests for multiple scenarios."
                )
        
        self.report_data["recommendations"] = recommendations
    
    def generate_report(self):
        """Generate markdown report"""
        report = []
        
        # Header
        report.append("# 🧪 Test Quality Report")
        report.append(f"**Generated**: {self.report_data['timestamp']}")
        report.append("")
        
        # Summary
        coverage = self.report_data.get("coverage", {})
        test_results = self.report_data.get("test_results", {})
        
        line_coverage = coverage.get("line_coverage", 0)
        success_rate = test_results.get("success_rate", 0)
        total_tests = test_results.get("total", 0)
        
        # Status badges
        coverage_status = "🟢" if line_coverage >= 85 else "🟡" if line_coverage >= 70 else "🔴"
        test_status = "🟢" if success_rate == 100 else "🟡" if success_rate >= 95 else "🔴"
        
        report.append("## 📊 Summary")
        report.append("")
        report.append(f"| Metric | Value | Status |")
        report.append(f"|--------|-------|--------|")
        report.append(f"| Test Coverage | {line_coverage}% | {coverage_status} |")
        report.append(f"| Test Success Rate | {success_rate}% | {test_status} |")
        report.append(f"| Total Tests | {total_tests} | - |")
        report.append(f"| Test Duration | {test_results.get('duration', 0):.2f}s | - |")
        report.append("")
        
        # Coverage details
        if coverage:
            report.append("## 📈 Coverage Analysis")
            report.append("")
            report.append(f"- **Line Coverage**: {line_coverage}%")
            report.append(f"- **Branch Coverage**: {coverage.get('branch_coverage', 0)}%")
            
            modules = coverage.get("modules", {})
            if modules:
                low_coverage = [(m, d["coverage"]) for m, d in modules.items() if d["coverage"] < 80]
                if low_coverage:
                    report.append("")
                    report.append("### 🎯 Modules Needing Attention")
                    for module, cov in sorted(low_coverage, key=lambda x: x[1])[:10]:
                        report.append(f"- `{Path(module).name}`: {cov}%")
            report.append("")
        
        # Test results
        if test_results:
            report.append("## 🧪 Test Results")
            report.append("")
            report.append(f"- **Passed**: {test_results.get('passed', 0)}")
            report.append(f"- **Failed**: {test_results.get('failed', 0)}")
            report.append(f"- **Skipped**: {test_results.get('skipped', 0)}")
            report.append(f"- **Errors**: {test_results.get('error', 0)}")
            
            # Failed tests
            failed_tests = test_results.get("failed_tests", [])
            if failed_tests:
                report.append("")
                report.append("### ❌ Failed Tests")
                for test in failed_tests:
                    report.append(f"- `{test['name']}`")
                    report.append(f"  ```")
                    report.append(f"  {test['error']}")
                    report.append(f"  ```")
            
            # Slow tests
            slow_tests = test_results.get("slow_tests", [])
            if slow_tests:
                report.append("")
                report.append("### ⏱️ Slow Tests (>1s)")
                for test in slow_tests:
                    report.append(f"- `{test['name']}`: {test['duration']}s")
            
            report.append("")
        
        # Quality metrics
        quality = self.report_data.get("quality_metrics", {})
        if quality:
            report.append("## 🔍 Quality Metrics")
            report.append("")
            report.append(f"- **Total Test Files**: {quality.get('total_test_files', 0)}")
            report.append(f"- **Test Functions**: {quality.get('test_functions', 0)}")
            report.append(f"- **Test Classes**: {quality.get('test_classes', 0)}")
            report.append(f"- **Async Tests**: {quality.get('async_tests', 0)}")
            report.append(f"- **Parameterized Tests**: {quality.get('parameterized_tests', 0)}")
            report.append(f"- **Fixtures Used**: {quality.get('fixture_usage', 0)}")
            report.append(f"- **Mock Usage**: {quality.get('mock_usage', 0)}")
            report.append("")
        
        # Recommendations
        recommendations = self.report_data.get("recommendations", [])
        if recommendations:
            report.append("## 💡 Recommendations")
            report.append("")
            for i, rec in enumerate(recommendations, 1):
                report.append(f"{i}. {rec}")
            report.append("")
        
        # Footer
        report.append("---")
        report.append("*This report was generated automatically. Review and address recommendations to improve test quality.*")
        
        return "\n".join(report)
    
    def run_analysis(self):
        """Run complete analysis"""
        print("🔍 Starting test quality analysis...")
        
        self.analyze_coverage()
        print("✅ Coverage analysis complete")
        
        self.analyze_test_results()
        print("✅ Test results analysis complete")
        
        self.analyze_test_files()
        print("✅ Test file analysis complete")
        
        self.generate_recommendations()
        print("✅ Recommendations generated")
        
        report = self.generate_report()
        
        # Save report
        report_file = self.base_path / "test-quality-report.md"
        report_file.write_text(report)
        print(f"📝 Report saved to {report_file}")
        
        # Save JSON data
        json_file = self.base_path / "test-quality-data.json"
        with open(json_file, 'w') as f:
            json.dump(self.report_data, f, indent=2)
        print(f"📊 Data saved to {json_file}")
        
        return report


if __name__ == "__main__":
    analyzer = TestQualityAnalyzer()
    report = analyzer.run_analysis()
    print("\n" + "="*50)
    print("TEST QUALITY REPORT")
    print("="*50)
    print(report)