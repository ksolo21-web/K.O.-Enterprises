"""Property-description inventory: facts to document even when no issue is found.
A checklist prompt is not a claim that a system was inspected or present.
"""
REQUIRED_FEATURES = {
 'site': ('grading_drainage', 'surface_water_management', 'walks_drives_retaining'),
 'foundation': ('foundation_type', 'foundation_material', 'support_configuration', 'visible_foundation_condition'),
 'subfloor': ('floor_platform_type', 'subfloor_material', 'visible_floor_supports'),
 'framing': ('exterior_wall_structure', 'floor_structure', 'roof_structure'),
 'exterior': ('cladding_type', 'flashing_openings', 'trim_decks_and_attached_features'),
 'roof': ('roof_covering', 'roof_geometry_and_structure', 'roof_drainage', 'roof_access_method'),
 'attic': ('attic_access', 'visible_roof_framing', 'insulation_type', 'ventilation_design'),
 'interior': ('walls_ceilings_floors', 'windows_doors_stairs', 'life_safety_observations'),
 'electrical': ('service_entry_type', 'panel_and_overcurrent', 'branch_wiring_visible', 'tested_devices_and_limitations'),
 'plumbing': ('visible_supply_materials', 'visible_drain_waste_vent', 'fixtures_and_water_controls'),
 'water_heating': ('heater_type_and_energy', 'rating_plate_make_model_serial', 'venting_and_safety', 'visible_condition'),
 'hvac': ('heating_type', 'cooling_type', 'distribution_type', 'rating_plate_make_model_serial', 'operation_and_access_limitations'),
 'crawlspace': ('space_type_and_access', 'soil_moisture_and_vapor_control', 'supports_and_observed_structure')
}

def missing_features(document:dict, system:str)->list[str]:
    required=REQUIRED_FEATURES[system]
    covered={o.get('feature_code') for o in document.get('observations',[]) if o.get('system')==system}
    return [x for x in required if x not in covered]
