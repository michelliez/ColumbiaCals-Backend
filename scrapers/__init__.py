"""
scrapers package

This file exists to make the `scrapers` directory a proper Python package so
that individual scraper modules can import common helpers like `base_scraper`.
"""

__all__ = ["base_scraper", "scraper_factory"]
