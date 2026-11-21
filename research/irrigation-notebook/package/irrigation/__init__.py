"""Crop-aware FAO-56 irrigation decision support (Module 5 upgrade).

Modules
-------
crop_database  : crop parameters (Kc, Zr, p) with per-value provenance
soil           : soil / irrigation-system parameters, multi-depth sensor handling
eto            : FAO-56 Penman-Monteith and Hargreaves-Samani ETo
water_balance  : daily root-zone water balance and scheduling simulation
decision       : single-day operational recommendation + data-quality flags
dashboard      : matplotlib dashboard for the crop-specific section
"""
__version__ = "1.0.0"
