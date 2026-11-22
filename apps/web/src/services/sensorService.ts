import { apiClient } from "./apiClient";

/** Field-unit readings (services/api/app/sensors/feed.py, firmware/README.md). */
export type FieldStatus = "good" | "low" | "critical" | "sensor_fault";

export interface SensorReading {
  device_id: string;
  ts: number;
  soil_moisture: number | null;
  air_temp: number | null;
  air_humidity: number | null;
  /** 0–100 %, same scale as the field unit's screen */
  light: number | null;
  field_status: FieldStatus | null;
}

export type Trend = Record<"soil_moisture" | "air_temp" | "air_humidity" | "light", number | null>;

export interface SensorDevice {
  device_id: string;
  gateway: "online" | "offline" | "unknown";
  latest: SensorReading | null;
  age_s: number | null;
  trend: Trend;
}

export interface SensorSnapshot {
  broker_connected: boolean;
  devices: SensorDevice[];
}

export const sensorService = {
  latest(): Promise<SensorSnapshot> {
    return apiClient<SensorSnapshot>("/sensors/latest");
  },
};
