"""
Scraper consistency checker utility.

This script provides tools to verify and improve consistency across all scraper implementations.
It checks for common issues and provides guidance for updates.

Usage:
    python -m scrapers.consistency_checker

Or import and use the functions directly:

    from scrapers.consistency_checker import check_all_scrapers
    issues = check_all_scrapers()
    print(f"Found {len(issues)} consistency issues")
"""

import inspect
import logging
import re
import importlib
import sys
from typing import Dict, List, Any, Set, Optional, Tuple, Type, cast

from scrapers.base import EventScraper
from scrapers.factory import SCRAPER_REGISTRY, get_scraper_class

logger = logging.getLogger('explorastur')

# Types of inconsistencies to check for
CONSISTENCY_CHECKS = [
    "missing_type_annotations",
    "inconsistent_error_handling",
    "missing_base_methods",
    "incomplete_docstrings",
    "custom_helper_duplication"
]

def check_all_scrapers() -> Dict[str, List[str]]:
    """
    Check all registered scrapers for consistency issues.

    Returns:
        Dictionary mapping scraper IDs to lists of found issues
    """
    issues = {}

    for scraper_id in SCRAPER_REGISTRY:
        scraper_class = get_scraper_class(scraper_id)
        if not scraper_class:
            logger.error(f"Could not load scraper class for ID: {scraper_id}")
            continue

        logger.info(f"Checking consistency for {scraper_id}")
        scraper_issues = check_scraper_consistency(scraper_class)

        if scraper_issues:
            issues[scraper_id] = scraper_issues
            logger.warning(f"Found {len(scraper_issues)} issues in {scraper_id}")
        else:
            logger.info(f"No consistency issues found in {scraper_id}")

    return issues

def check_scraper_consistency(scraper_class: Type[EventScraper]) -> List[str]:
    """
    Check a single scraper class for consistency issues.

    Args:
        scraper_class: The scraper class to check

    Returns:
        List of found issues
    """
    issues = []

    # Get all methods from the scraper class (excluding those from base class)
    scraper_methods = {name: method for name, method in inspect.getmembers(scraper_class, predicate=inspect.isfunction)
                      if method.__qualname__.startswith(scraper_class.__name__)}

    # Check for missing type annotations
    issues.extend(check_type_annotations(scraper_class, scraper_methods))

    # Check for inconsistent error handling
    issues.extend(check_error_handling(scraper_class, scraper_methods))

    # Check for incomplete docstrings
    issues.extend(check_docstrings(scraper_class, scraper_methods))

    # Check for custom helper duplication
    issues.extend(check_helper_duplication(scraper_class, scraper_methods))

    return issues

def check_type_annotations(scraper_class: Type[EventScraper], methods: Dict[str, Any]) -> List[str]:
    """
    Check for missing or inconsistent type annotations.

    Args:
        scraper_class: The scraper class to check
        methods: Dictionary of method names to method objects

    Returns:
        List of type annotation issues
    """
    issues = []

    for name, method in methods.items():
        signature = inspect.signature(method)

        # Skip __init__ method
        if name == "__init__":
            continue

        # Check return type annotation
        if signature.return_annotation == inspect.Signature.empty:
            issues.append(f"Missing return type annotation in method: {name}")

        # Check parameter type annotations
        for param_name, param in signature.parameters.items():
            # Skip self parameter
            if param_name == "self":
                continue

            if param.annotation == inspect.Signature.empty:
                issues.append(f"Missing type annotation for parameter '{param_name}' in method: {name}")

    return issues

def check_error_handling(scraper_class: Type[EventScraper], methods: Dict[str, Any]) -> List[str]:
    """
    Check for inconsistent or missing error handling.

    Args:
        scraper_class: The scraper class to check
        methods: Dictionary of method names to method objects

    Returns:
        List of error handling issues
    """
    issues = []

    # Check scrape method for standard error handling
    if "scrape" in methods:
        source = inspect.getsource(methods["scrape"])
        if "try:" not in source or "except Exception as e:" not in source:
            issues.append("Missing try-except block in scrape method")
        if "self.handle_error(" not in source:
            issues.append("Not using self.handle_error() for error handling in scrape method")

    # Check for extraction methods not using try-except
    for name, method in methods.items():
        if name.startswith("_extract_") and not name.endswith("_from_page"):
            source = inspect.getsource(method)
            if "try:" not in source or "except" not in source:
                issues.append(f"Missing try-except block in extraction method: {name}")

    return issues

def check_docstrings(scraper_class: Type[EventScraper], methods: Dict[str, Any]) -> List[str]:
    """
    Check for missing or incomplete docstrings.

    Args:
        scraper_class: The scraper class to check
        methods: Dictionary of method names to method objects

    Returns:
        List of docstring issues
    """
    issues = []

    # Check class docstring
    if not scraper_class.__doc__:
        issues.append("Missing class docstring")

    # Essential methods that should have docstrings
    essential_methods = ["scrape", "__init__"]
    essential_method_patterns = ["_extract_", "process_", "_parse_"]

    for name, method in methods.items():
        # Check if it's an essential method or matches a pattern for essential methods
        is_essential = name in essential_methods or any(pattern in name for pattern in essential_method_patterns)

        if is_essential and not method.__doc__:
            issues.append(f"Missing docstring for method: {name}")
            continue

        if not method.__doc__:
            continue

        # Check docstring format for essential methods
        if is_essential:
            doc = method.__doc__

            # Check for Args section in methods with parameters
            signature = inspect.signature(method)
            has_params = any(param_name != "self" for param_name in signature.parameters)

            if has_params and "Args:" not in doc:
                issues.append(f"Missing Args section in docstring for method: {name}")

            # Check for Returns section in methods with return values
            if signature.return_annotation != inspect.Signature.empty and signature.return_annotation != None and "Returns:" not in doc:
                issues.append(f"Missing Returns section in docstring for method: {name}")

    return issues

def check_helper_duplication(scraper_class: Type[EventScraper], methods: Dict[str, Any]) -> List[str]:
    """
    Check for potential method duplication that could use base class helpers.

    Args:
        scraper_class: The scraper class to check
        methods: Dictionary of method names to method objects

    Returns:
        List of potential duplication issues
    """
    issues = []

    # Helper methods from base class that might be reimplemented
    base_helpers = [
        ("clean_date_text", ["clean_date", "format_date", "parse_date", "extract_date"]),
        ("extract_location_from_text", ["extract_location", "get_location", "parse_location"]),
        ("get_spanish_month", ["month_name", "get_month_name"]),
    ]

    for base_helper, similar_names in base_helpers:
        for name, method in methods.items():
            # Check for methods with similar functionality to base helpers
            if name != base_helper and any(similar in name for similar in similar_names):
                issues.append(f"Method '{name}' might duplicate base class helper '{base_helper}'")

    return issues

def fix_common_issues(scraper_id: str) -> List[str]:
    """
    Attempt to fix common consistency issues in a scraper.
    This is an experimental feature and might need manual review.

    Args:
        scraper_id: ID of the scraper to fix

    Returns:
        List of changes made
    """
    scraper_class = get_scraper_class(scraper_id)
    if not scraper_class:
        logger.error(f"Could not load scraper class for ID: {scraper_id}")
        return []

    # This is just a placeholder - actual implementation would be more complex
    logger.warning("Auto-fixing is not fully implemented. Please manually fix issues.")
    return []

def print_usage():
    """Print usage information for the script."""
    print("\nUsage:")
    print("  python -m scrapers.consistency_checker [check|fix] [scraper_id]")
    print("\nExamples:")
    print("  python -m scrapers.consistency_checker check            # Check all scrapers")
    print("  python -m scrapers.consistency_checker check telecable  # Check specific scraper")
    print("  python -m scrapers.consistency_checker fix telecable    # Try to fix scraper issues")
    print("\nOptions:")
    print("  check            Check for consistency issues")
    print("  fix              Try to fix consistency issues (experimental)")
    print("  scraper_id       Optional scraper ID to check/fix")

def main():
    """Main function when script is run directly."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Parse command line arguments
    if len(sys.argv) < 2:
        action = "check"
        scraper_id = None
    else:
        action = sys.argv[1]
        scraper_id = sys.argv[2] if len(sys.argv) > 2 else None

    if action not in ["check", "fix"]:
        print(f"Unknown action: {action}")
        print_usage()
        sys.exit(1)

    # Run the requested action
    if action == "check":
        if scraper_id:
            scraper_class = get_scraper_class(scraper_id)
            if not scraper_class:
                logger.error(f"Could not load scraper class for ID: {scraper_id}")
                sys.exit(1)

            issues = check_scraper_consistency(scraper_class)
            if issues:
                print(f"\nFound {len(issues)} consistency issues in {scraper_id}:")
                for issue in issues:
                    print(f"  - {issue}")
            else:
                print(f"\nNo consistency issues found in {scraper_id}")
        else:
            all_issues = check_all_scrapers()
            if all_issues:
                print(f"\nFound consistency issues in {len(all_issues)} scrapers:")
                for scraper_id, issues in all_issues.items():
                    print(f"\n{scraper_id} ({len(issues)} issues):")
                    for issue in issues:
                        print(f"  - {issue}")
            else:
                print("\nNo consistency issues found in any scraper")

    elif action == "fix":
        if not scraper_id:
            print("Scraper ID is required for the 'fix' action")
            print_usage()
            sys.exit(1)

        changes = fix_common_issues(scraper_id)
        if changes:
            print(f"\nMade {len(changes)} changes to {scraper_id}:")
            for change in changes:
                print(f"  - {change}")
        else:
            print(f"\nNo changes made to {scraper_id}")

    sys.exit(0)

if __name__ == "__main__":
    main()