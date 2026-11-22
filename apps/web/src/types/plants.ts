// Plant scanner API (services/api/app/routers/plants.py, ported from is9ini).

export interface CareItem {
  key: string;
  title: string;
  value: string;
  detail: string;
}

export interface DiseaseSheet {
  id: string;
  name: string;
  symptoms: string;
  prevention: string;
  treatment: string[];
}

export interface RecommendedSettings {
  plant_profile: string;
  soil_dry_pct: number;
  soil_wet_pct: number;
  temp_min_c: number;
  temp_max_c: number;
}

export interface SpeciesSheet {
  id: string;
  common_name: string;
  scientific_name: string;
  family: string;
  type: string;
  category?: string;
  care: CareItem[];
  possible_diseases: DiseaseSheet[];
  recommended_settings: RecommendedSettings | null;
  sources: string[];
  note?: string;
  leaf_crop?: string | null;
}

export interface Alternative {
  id: string;
  common_name: string;
  scientific_name: string;
  confidence: number;
}

export interface HealthEntry {
  code: string;
  name: string;
  scientific: string;
  score: number;
  sheet: DiseaseSheet | null;
}

export type HealthStatus = "possible_disease" | "healthy_looking" | "uncertain" | "unavailable";

export interface Health {
  engine: string | null;
  status: HealthStatus;
  confidence: number | null;
  top: HealthEntry | null;
  others: HealthEntry[];
  message: string;
}

export interface LeafHealth {
  applicable: boolean;
  beta?: boolean;
  crop?: string;
  sure?: boolean;
  healthy?: boolean | null;
  label?: string;
  confidence?: number;
  disease?: DiseaseSheet | null;
  note?: string;
}

export interface ScanResult {
  engine: string;
  sure: boolean;
  confidence: number;
  genus: { name: string | null; confidence: number; sure: boolean };
  species: SpeciesSheet;
  alternatives: Alternative[];
  leaf_health: LeafHealth;
  health: Health;
  engine_errors: string[];
  ms: number;
  plantnet_remaining_today?: number;
  chosen?: boolean;
  saved?: boolean;
  scan_id?: string;
}

export interface ScanSummary {
  id: string;
  created_at: string;
  common_name: string;
  scientific_name: string;
  confidence: number;
  sure: boolean;
  engine: string;
  health_status: HealthStatus | null;
}

export interface ScannerStatus {
  installed: boolean;
  engines: { plantnet: boolean; bioclip: boolean; verdant: boolean };
}

export interface PlantSearchHit {
  id: string;
  common_name: string;
  scientific_name: string;
}
