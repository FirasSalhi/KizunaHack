"""Crop-aware irrigation recommendations (FAO-56) for the FARMLINK API.

`engine/` and `crop_knowledge/` are the FARMLINK Module 5 engine (v2.0.0), copied unchanged from
`research/irrigation-notebook/package/FARMLINK_Module5_Deliverables`. `service.py` is the typed
layer the API uses: live weather, then one call to `engine.farm_runner.run_farm`.
"""
