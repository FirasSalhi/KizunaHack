import json
from pathlib import Path

# Load compiled model
model_path = Path("outputs/post_harvest_model.json")
if not model_path.exists():
    raise FileNotFoundError("outputs/post_harvest_model.json not found")

model_json = model_path.read_text(encoding="utf-8")

dashboard_code = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>HarvestGuard AI · Smart Cold Storage Digital Twin</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
<style>
:root {{
  --bg-dark: #0a110e;
  --bg-card: #121c17;
  --bg-card-hover: #16241e;
  --border: #1f3329;
  --border-light: #2c473a;
  --text-main: #f0f7f3;
  --text-muted: #8ba396;
  --text-dim: #556e62;
  --primary: #10b981;
  --primary-glow: rgba(16, 185, 129, 0.25);
  --low: #10b981;
  --low-bg: rgba(16, 185, 129, 0.12);
  --med: #f59e0b;
  --med-bg: rgba(245, 158, 11, 0.12);
  --high: #ef4444;
  --high-bg: rgba(239, 68, 68, 0.12);
  --cold: #06b6d4;
  --cold-glow: rgba(6, 182, 212, 0.25);
  --heat: #ff5722;
  --heat-glow: rgba(255, 87, 34, 0.35);
  --radius-lg: 16px;
  --radius-md: 10px;
  --radius-sm: 6px;
  --shadow: 0 10px 30px -5px rgba(0,0,0,0.5);
}}

* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  background: var(--bg-dark);
  color: var(--text-main);
  font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
  line-height: 1.5;
  min-height: 100vh;
  padding: 20px;
  background-image: 
    radial-gradient(circle at 15% 15%, rgba(16, 185, 129, 0.05) 0%, transparent 40%),
    radial-gradient(circle at 85% 85%, rgba(6, 182, 212, 0.04) 0%, transparent 40%);
}}

.app-container {{
  max-width: 1420px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}}

/* Top Navigation Bar */
header.top-bar {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow);
}}
.brand {{
  display: flex;
  align-items: center;
  gap: 12px;
}}
.brand-logo {{
  width: 42px;
  height: 42px;
  background: linear-gradient(135deg, #10b981, #059669);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  box-shadow: 0 0 15px var(--primary-glow);
}}
.brand-text h1 {{
  font-size: 19px;
  font-weight: 800;
  letter-spacing: -0.02em;
  background: linear-gradient(to right, #ffffff, #a7f3d0);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}}
.brand-text p {{
  font-size: 12px;
  color: var(--text-muted);
  font-weight: 500;
}}
.top-status-pills {{
  display: flex;
  align-items: center;
  gap: 12px;
}}
.status-pill {{
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border);
  padding: 6px 14px;
  border-radius: 99px;
  font-size: 13px;
  font-weight: 600;
}}
.status-pill .indicator {{
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--primary);
  box-shadow: 0 0 8px var(--primary);
  animation: pulse 2s infinite;
}}
@keyframes pulse {{
  0%, 100% {{ transform: scale(1); opacity: 1; }}
  50% {{ transform: scale(1.3); opacity: 0.6; }}
}}

.meteo-bar {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 10px 18px;
  margin-bottom: 20px;
  flex-wrap: wrap;
  box-shadow: var(--shadow);
}}
.meteo-location {{
  display: flex;
  align-items: center;
  gap: 10px;
}}
.meteo-label {{
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
}}
.meteo-select {{
  background: var(--bg-dark);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
  color: #a7f3d0;
  font-weight: 600;
  font-size: 12px;
  padding: 5px 12px;
  outline: none;
  cursor: pointer;
}}
.meteo-select:focus {{
  border-color: var(--primary);
}}
.meteo-telemetry {{
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}}
.meteo-pill {{
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 14px;
  background: var(--bg-dark);
  border: 1px solid var(--border);
  border-radius: 99px;
  font-size: 12px;
}}
.meteo-badge {{
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 4px;
  background: rgba(16, 185, 129, 0.15);
  color: var(--primary);
  border: 1px solid rgba(16, 185, 129, 0.3);
}}

/* Main Dashboard Grid */
.dashboard-grid {{
  display: grid;
  grid-template-columns: 340px 1fr 340px;
  gap: 20px;
}}
@media (max-width: 1200px) {{
  .dashboard-grid {{ grid-template-columns: 340px 1fr; }}
  .dashboard-right {{ grid-column: span 2; }}
}}
@media (max-width: 860px) {{
  .dashboard-grid {{ grid-template-columns: 1fr; }}
  .dashboard-right {{ grid-column: span 1; }}
}}

.card {{
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: var(--shadow);
  display: flex;
  flex-direction: column;
  gap: 16px;
}}
.card-header {{
  display: flex;
  justify-content: space-between;
  align-items: center;
}}
.card-title {{
  font-size: 14px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  gap: 8px;
}}

/* Left Column: Farm & Sensor Controls */
.crop-grid-select {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}}
.crop-btn {{
  background: var(--bg-dark);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 10px 4px;
  color: var(--text-main);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  font-weight: 600;
  transition: all 0.2s;
}}
.crop-btn .icon {{ font-size: 22px; }}
.crop-btn:hover {{
  background: var(--bg-card-hover);
  border-color: var(--border-light);
}}
.crop-btn.active {{
  background: rgba(16, 185, 129, 0.15);
  border-color: var(--primary);
  color: #a7f3d0;
  box-shadow: 0 0 12px rgba(16, 185, 129, 0.2);
}}

.crop-specs-pill {{
  background: var(--bg-dark);
  border: 1px dashed var(--border-light);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
  font-size: 12px;
  line-height: 1.6;
  color: var(--text-muted);
}}
.crop-specs-pill b {{ color: var(--text-main); }}

/* Sliders & Controls */
.control-group {{
  display: flex;
  flex-direction: column;
  gap: 6px;
}}
.control-label {{
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  font-weight: 600;
}}
.control-val {{
  font-family: 'JetBrains Mono', monospace;
  font-weight: 700;
  color: var(--primary);
}}
input[type=range] {{
  -webkit-appearance: none;
  width: 100%;
  height: 8px;
  background: #1b2d24;
  border-radius: 4px;
  outline: none;
  cursor: pointer;
}}
input[type=range]::-webkit-slider-thumb {{
  -webkit-appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--primary);
  cursor: pointer;
  box-shadow: 0 0 10px var(--primary-glow);
  transition: transform 0.1s;
}}
input[type=range]::-webkit-slider-thumb:hover {{
  transform: scale(1.15);
}}

.preset-buttons {{
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 6px;
  margin-top: 4px;
}}
.btn-preset {{
  padding: 8px 4px;
  border-radius: var(--radius-sm);
  border: 1px solid transparent;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
  text-align: center;
}}
.btn-preset.opt {{ background: var(--low-bg); color: var(--low); border-color: rgba(16, 185, 129, 0.3); }}
.btn-preset.room {{ background: var(--med-bg); color: var(--med); border-color: rgba(245, 158, 11, 0.3); }}
.btn-preset.cold {{ background: rgba(6, 182, 212, 0.15); color: var(--cold); border-color: rgba(6, 182, 212, 0.3); }}
.btn-preset.hot {{ background: var(--high-bg); color: var(--high); border-color: rgba(239, 68, 68, 0.3); }}
.btn-preset:hover {{ filter: brightness(1.2); }}

/* Center Column: Digital Twin 3D Storage Chamber */
.chamber-card {{
  position: relative;
  overflow: hidden;
  background: radial-gradient(circle at 50% 40%, #15271f 0%, #0c1712 100%);
  border: 1px solid var(--border);
}}

.chamber-viewport {{
  position: relative;
  width: 100%;
  height: 380px;
  border-radius: var(--radius-md);
  overflow: hidden;
  background: #0d1a15;
  border: 1px solid rgba(255, 255, 255, 0.05);
}}

/* Room Ambient Glow Overlay */
.room-ambient {{
  position: absolute;
  inset: 0;
  pointer-events: none;
  transition: background 0.8s ease;
  z-index: 10;
}}
.room-ambient.safe {{
  background: radial-gradient(circle at 50% 50%, rgba(16, 185, 129, 0.05) 0%, transparent 80%);
}}
.room-ambient.warning {{
  background: radial-gradient(circle at 50% 50%, rgba(245, 158, 11, 0.12) 0%, transparent 80%);
}}
.room-ambient.danger {{
  background: radial-gradient(circle at 50% 50%, rgba(239, 68, 68, 0.18) 0%, transparent 80%);
}}
.room-ambient.chilling {{
  background: radial-gradient(circle at 50% 50%, rgba(6, 182, 212, 0.18) 0%, transparent 80%);
}}

/* Chamber Status Pill (Top Left) */
.chamber-status-pill {{
  position: absolute;
  top: 14px;
  left: 16px;
  background: rgba(10, 24, 18, 0.85);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
  padding: 6px 12px;
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 8px;
  z-index: 6;
}}
.chamber-status-pill .status-dot {{
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--primary);
  box-shadow: 0 0 8px var(--primary);
}}

/* ACTUATOR: Industrial Ventilation & Cooling Fan (Top Right) */
.actuator-fan {{
  position: absolute;
  top: 20px;
  right: 24px;
  width: 76px;
  height: 76px;
  background: #101c17;
  border: 3px solid #284436;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: inset 0 0 15px rgba(0,0,0,0.8), 0 4px 12px rgba(0,0,0,0.4);
  z-index: 5;
}}
.fan-blades {{
  width: 58px;
  height: 58px;
  transform-origin: center;
  transition: transform 0.2s;
}}
.actuator-fan.spinning .fan-blades {{
  animation: spinFan 0.35s linear infinite;
}}
@keyframes spinFan {{
  100% {{ transform: rotate(360deg); }}
}}
.fan-indicator {{
  position: absolute;
  bottom: -22px;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(0,0,0,0.6);
  color: var(--text-dim);
  white-space: nowrap;
}}
.actuator-fan.spinning .fan-indicator {{
  color: var(--cold);
  text-shadow: 0 0 8px var(--cold-glow);
}}
.wind-streaks {{
  position: absolute;
  top: 36px;
  right: 105px;
  width: 90px;
  height: 40px;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.4s;
}}
.actuator-fan.spinning ~ .wind-streaks {{
  opacity: 1;
}}
.wind-line {{
  height: 2px;
  background: linear-gradient(to left, rgba(6, 182, 212, 0.8), transparent);
  border-radius: 2px;
  margin: 6px 0;
  animation: windBlow 0.7s linear infinite;
}}
.wind-line:nth-child(2) {{ animation-delay: 0.2s; width: 70%; }}
.wind-line:nth-child(3) {{ animation-delay: 0.4s; width: 85%; }}
@keyframes windBlow {{
  0% {{ transform: translateX(20px); opacity: 0; }}
  50% {{ opacity: 1; }}
  100% {{ transform: translateX(-40px); opacity: 0; }}
}}

/* ACTUATOR: Ultrasonic Mist Spray Nozzles (Top Left) */
.actuator-mister {{
  position: absolute;
  top: 60px;
  left: 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  z-index: 5;
}}
.nozzle-head {{
  width: 28px;
  height: 16px;
  background: #2a3d34;
  border-radius: 4px 4px 8px 8px;
  border: 1px solid var(--border-light);
  display: flex;
  align-items: center;
  justify-content: center;
}}
.nozzle-hole {{
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #000;
}}
.mist-clouds {{
  width: 100px;
  height: 80px;
  margin-top: 4px;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.5s;
}}
.actuator-mister.spraying .mist-clouds {{
  opacity: 0.85;
}}
.mist-p {{
  position: absolute;
  background: radial-gradient(circle, rgba(200, 240, 255, 0.4) 0%, transparent 70%);
  border-radius: 50%;
  animation: mistFall 1.6s ease-out infinite;
}}
@keyframes mistFall {{
  0% {{ transform: translateY(0) scale(0.4); opacity: 0; }}
  30% {{ opacity: 0.9; }}
  100% {{ transform: translateY(100px) scale(2.2); opacity: 0; }}
}}
.mister-indicator {{
  margin-top: 4px;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(0,0,0,0.6);
  color: var(--text-dim);
}}
.actuator-mister.spraying .mister-indicator {{
  color: #38bdf8;
  text-shadow: 0 0 8px rgba(56, 189, 248, 0.5);
}}

/* ACTUATOR: Radiant Infrared Heating Element (Top Center) */
.actuator-heater {{
  position: absolute;
  top: 14px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  z-index: 5;
  opacity: 0.35;
  transition: opacity 0.4s, filter 0.4s;
}}
.actuator-heater.heating {{
  opacity: 1;
  filter: drop-shadow(0 0 16px var(--heat-glow));
}}
.heater-coils {{
  width: 110px;
  height: 22px;
  background: #1a1614;
  border: 2px solid #3d2a24;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: space-around;
  padding: 0 8px;
}}
.coil-wire {{
  width: 14px;
  height: 12px;
  border-radius: 50%;
  border: 2px solid #553328;
  transition: border-color 0.4s, background 0.4s;
}}
.actuator-heater.heating .coil-wire {{
  border-color: #ff5722;
  background: #ff7043;
  box-shadow: 0 0 8px #ff5722;
  animation: heatGlow 1.2s ease-in-out infinite alternate;
}}
@keyframes heatGlow {{
  from {{ filter: brightness(1); }}
  to {{ filter: brightness(1.4); }}
}}
.heater-indicator {{
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  padding: 2px 8px;
  border-radius: 4px;
  background: rgba(0,0,0,0.7);
  color: var(--text-dim);
}}
.actuator-heater.heating .heater-indicator {{
  color: #ff7043;
  text-shadow: 0 0 8px var(--heat-glow);
}}

/* Chiller Control Unit (Bottom Left) */
.chiller-unit {{
  position: absolute;
  bottom: 14px;
  left: 16px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 12px;
  background: rgba(10, 20, 16, 0.85);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  z-index: 6;
  font-size: 11px;
}}
.chiller-led {{
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #334e40;
}}
.chiller-unit.cooling .chiller-led {{
  background: var(--cold);
  box-shadow: 0 0 10px var(--cold);
  animation: pulse 1.5s infinite;
}}

/* Central Fruit Stage (Visual Spoilage Engine) */
.fruit-stage {{
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -36%);
  display: flex;
  flex-direction: column;
  align-items: center;
  z-index: 4;
}}
.wooden-crate {{
  width: 210px;
  height: 46px;
  background: linear-gradient(180deg, #6d4c41 0%, #4e342e 100%);
  border-radius: 6px;
  border: 3px solid #3e2723;
  box-shadow: 0 20px 25px -5px rgba(0,0,0,0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  margin-top: -24px;
}}
.crate-label {{
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.1em;
  color: #d7ccc8;
  text-transform: uppercase;
  background: rgba(0,0,0,0.3);
  padding: 2px 10px;
  border-radius: 4px;
}}

/* Produce Visual SVG Canvas */
.produce-container {{
  width: 170px;
  height: 170px;
  position: relative;
  transition: transform 0.3s;
}}
.produce-svg {{
  width: 100%;
  height: 100%;
  filter: drop-shadow(0 15px 20px rgba(0,0,0,0.6));
  transition: all 0.5s ease;
}}

/* Simulation Action Bar (Inside Center Card) */
.timeline-bar {{
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px 18px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
}}
.timeline-header {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}}
.timeline-timestamp {{
  display: flex;
  align-items: center;
  gap: 8px;
}}
.live-dot {{
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--primary);
  box-shadow: 0 0 8px var(--primary);
  animation: pulse 1.8s infinite;
}}
.timeline-time-label {{
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--text-muted);
  letter-spacing: 0.05em;
}}
.timeline-clock {{
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  font-weight: 700;
  color: #a7f3d0;
  background: #0d1e16;
  border: 1px solid rgba(16, 185, 129, 0.3);
  padding: 2px 8px;
  border-radius: 4px;
}}
.timeline-status {{
  font-size: 12px;
  color: var(--text-main);
  flex: 1;
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}
.btn-timeline-toggle {{
  padding: 5px 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-light);
  background: var(--bg-dark);
  color: var(--text-main);
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s;
}}
.btn-timeline-toggle:hover {{
  background: var(--bg-card-hover);
  border-color: var(--primary);
  color: #a7f3d0;
}}
.timeline-slider-wrap {{
  display: flex;
  flex-direction: column;
  gap: 6px;
}}
.timeline-slider {{
  -webkit-appearance: none;
  width: 100%;
  height: 6px;
  background: linear-gradient(90deg, #1b2d24 0%, #17384e 16%, #1b2d24 35%, #423020 52%, #1b2d24 68%, #1b2d24 100%);
  border-radius: 3px;
  outline: none;
  cursor: pointer;
}}
.timeline-slider::-webkit-slider-thumb {{
  -webkit-appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--primary);
  cursor: pointer;
  box-shadow: 0 0 10px var(--primary-glow);
  border: 2px solid #fff;
}}
.timeline-ticks {{
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  font-weight: 600;
  color: var(--text-dim);
}}

/* Simple Farmer-Friendly Right Column */
.farmer-status-card {{
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 20px 16px;
  background: var(--bg-dark);
  border: 2px solid rgba(16, 185, 129, 0.3);
  border-radius: var(--radius-lg);
  gap: 6px;
  transition: all 0.3s ease;
}}
.farmer-status-card.safe {{
  border-color: rgba(16, 185, 129, 0.4);
  background: radial-gradient(circle at 50% 20%, rgba(16, 185, 129, 0.12) 0%, var(--bg-dark) 80%);
}}
.farmer-status-card.warning {{
  border-color: rgba(245, 158, 11, 0.4);
  background: radial-gradient(circle at 50% 20%, rgba(245, 158, 11, 0.12) 0%, var(--bg-dark) 80%);
}}
.farmer-status-card.danger {{
  border-color: rgba(239, 68, 68, 0.4);
  background: radial-gradient(circle at 50% 20%, rgba(239, 68, 68, 0.15) 0%, var(--bg-dark) 80%);
}}
.status-icon {{
  font-size: 38px;
  line-height: 1;
}}
.status-main-text {{
  font-size: 19px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--low);
  transition: color 0.3s;
}}
.shelf-days-big {{
  font-family: 'JetBrains Mono', monospace;
  font-size: 68px;
  font-weight: 900;
  line-height: 1;
  color: var(--primary);
  margin: 4px 0;
  transition: color 0.3s;
}}
.shelf-days-label {{
  font-size: 13px;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--text-muted);
  letter-spacing: 0.05em;
}}
.freshness-bar-wrap {{
  width: 100%;
  height: 10px;
  background: #11231a;
  border-radius: 99px;
  margin-top: 8px;
  overflow: hidden;
  border: 1px solid var(--border);
}}
.freshness-bar-fill {{
  height: 100%;
  background: linear-gradient(90deg, #10b981, #34d399);
  border-radius: 99px;
  transition: width 0.4s ease, background 0.4s ease;
}}

.farmer-advice-card {{
  background: var(--bg-dark);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}}
.advice-header {{
  font-size: 13px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-main);
  display: flex;
  align-items: center;
  gap: 6px;
}}
.advice-body {{
  font-size: 14px;
  line-height: 1.5;
  color: #e2e8f0;
  font-weight: 500;
}}

.farmer-outlook-card {{
  background: var(--bg-dark);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}}
.outlook-grid {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}}
.outlook-day {{
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 10px 4px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  text-align: center;
}}
.day-name {{
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--text-muted);
}}
.day-status-pill {{
  font-size: 11px;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: 99px;
  white-space: nowrap;
}}
.day-status-pill.safe {{
  background: rgba(16, 185, 129, 0.15);
  color: #a7f3d0;
  border: 1px solid rgba(16, 185, 129, 0.4);
}}
.day-status-pill.warning {{
  background: rgba(245, 158, 11, 0.15);
  color: #fde68a;
  border: 1px solid rgba(245, 158, 11, 0.4);
}}
.day-status-pill.danger {{
  background: rgba(239, 68, 68, 0.15);
  color: #fca5a5;
  border: 1px solid rgba(239, 68, 68, 0.4);
}}
</style>
</head>
<body>

<div class="app-container">

  <!-- Top Navigation Header -->
  <header class="top-bar">
    <div class="brand">
      <div class="brand-logo">🌾</div>
      <div class="brand-text">
        <h1>HarvestGuard AI</h1>
        <p>Post-Harvest Cold Storage Digital Twin & Autonomous Decision Intelligence</p>
      </div>
    </div>
    <div class="top-status-pills">
      <div class="status-pill">
        <div class="indicator"></div>
        <span>IoT Sensors: Online</span>
      </div>
      <div class="status-pill" style="border-color: rgba(6, 182, 212, 0.3); color: var(--cold)">
        <span>Digital Twin: Chamber #1</span>
      </div>
    </div>
  </header>

  <!-- Real-Time Meteorological Ambient Feed (Open-Meteo Integration) -->
  <div class="meteo-bar">
    <div class="meteo-location">
      <span style="font-size: 14px;">📍</span>
      <span class="meteo-label">Farm Location:</span>
      <select id="weatherLocationSelect" class="meteo-select">
        <option value="0.3136,32.5811" selected>Kampala, Uganda (Central Hub)</option>
        <option value="-1.2921,36.8219">Nairobi, Kenya</option>
        <option value="36.8065,10.1815">Tunis / Carthage, Tunisia</option>
        <option value="35.8256,10.6084">Sousse, Tunisia</option>
        <option value="9.0320,38.7482">Addis Ababa, Ethiopia</option>
        <option value="30.0444,31.2357">Cairo, Egypt</option>
        <option value="4.7110,-74.0721">Bogota, Colombia</option>
        <option value="gps">📡 Use Device GPS</option>
      </select>
    </div>
    <div class="meteo-telemetry">
      <div class="meteo-pill" id="weatherPill">
        <span id="weatherIcon" style="font-size: 14px;">⛅</span>
        <span id="weatherText" style="font-weight: 600;">Outdoor: Fetching Open-Meteo...</span>
        <span class="meteo-badge" id="weatherBadge">Open-Meteo API</span>
      </div>
      <div class="meteo-pill" style="border-color: rgba(16, 185, 129, 0.3);">
        <span style="color: var(--primary);">🛡️ Warehouse Insulation:</span>
        <span style="color: var(--text-main); font-weight: 600;">PU Panel (R-4.5)</span>
      </div>
    </div>
  </div>

  <!-- 3-Column Dashboard Body -->
  <div class="dashboard-grid">

    <!-- LEFT COLUMN: SENSOR INPUTS & CROP SELECTOR -->
    <div class="card">
      <div class="card-header">
        <span class="card-title">📦 Selected Produce</span>
      </div>

      <!-- Quick Crop Buttons (10 Crops) -->
      <div class="crop-grid-select" id="cropButtons"></div>

      <!-- Crop Target Specs Info -->
      <div class="crop-specs-pill" id="cropSpecs">
        Loading crop specifications...
      </div>

      <div class="card-header" style="margin-top: 6px;">
        <span class="card-title">🌡️ Storage Climate Sensors</span>
      </div>

      <!-- Quick Preset Buttons -->
      <div class="preset-buttons">
        <button class="btn-preset opt" id="btnOpt">❄️ Optimal</button>
        <button class="btn-preset room" id="btnRoom">⛅ Room 22°</button>
        <button class="btn-preset cold" id="btnCold">🧊 Cold 0°</button>
        <button class="btn-preset hot" id="btnHot">🔥 Hot 32°</button>
      </div>

      <!-- Temperature Slider -->
      <div class="control-group">
        <div class="control-label">
          <span>Current Room Temp:</span>
          <span class="control-val" id="tempDisplay">12.0 °C</span>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 11px; color: var(--text-dim); margin-top: -3px; margin-bottom: 2px;">
          <span>Target: <b id="tempTargetDisplay" style="color: var(--text-muted);">12.0 °C</b></span>
          <span>Cumulative Avg: <b id="tempAvgDisplay" style="color: #60a5fa;">12.0 °C</b></span>
        </div>
        <input type="range" id="tempSlider" min="-5" max="45" step="0.5" value="12">
      </div>

      <!-- Humidity Slider -->
      <div class="control-group">
        <div class="control-label">
          <span>Current Humidity:</span>
          <span class="control-val" id="rhDisplay">90 %</span>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 11px; color: var(--text-dim); margin-top: -3px; margin-bottom: 2px;">
          <span>Target: <b id="rhTargetDisplay" style="color: var(--text-muted);">90 %</b></span>
          <span>Cumulative Avg: <b id="rhAvgDisplay" style="color: #60a5fa;">90 %</b></span>
        </div>
        <input type="range" id="rhSlider" min="30" max="100" step="1" value="90">
      </div>

      <!-- Harvest Date Picker -->
      <div class="control-group">
        <div class="control-label">
          <span>Harvest Date:</span>
          <span class="control-val" id="ageDisplay" style="color: var(--text-muted); font-size: 11px;">1.0d ago</span>
        </div>
        <input type="date" id="harvestDateInput" style="padding: 8px; background: var(--bg-dark); border: 1px solid var(--border); border-radius: var(--radius-sm); color: #fff; font-family: inherit;">
      </div>

    </div>

    <!-- CENTER COLUMN: DIGITAL TWIN COLD STORAGE CHAMBER -->
    <div class="card chamber-card">
      <div class="card-header">
        <span class="card-title">🏢 Digital Twin · Storage Chamber Simulation</span>
        <span id="chamberBadge" class="status-pill" style="font-size: 11px; padding: 3px 10px;">Chamber Nominal</span>
      </div>

      <div class="chamber-viewport" id="chamberViewport">
        <!-- Chamber Status Badge (Top Left, Non-intrusive) -->
        <div class="chamber-status-pill" id="chamberStatusPill">
          <div class="status-dot" id="statusDot"></div>
          <span id="chamberStatusText">Climate: Optimal</span>
        </div>

        <!-- Dynamic Room Ambient Light -->
        <div class="room-ambient safe" id="roomAmbient"></div>

        <!-- ACTUATOR: Industrial Ventilation & Cooling Fan (Top Right) -->
        <div class="actuator-fan" id="fanActuator">
          <svg class="fan-blades" viewBox="0 0 100 100">
            <circle cx="50" cy="50" r="14" fill="#374151" stroke="#4b5563" stroke-width="2"/>
            <path d="M50 36 C45 20 55 5 62 8 C68 12 60 28 50 36 Z" fill="#9ca3af"/>
            <path d="M64 50 C80 45 95 55 92 62 C88 68 72 60 64 50 Z" fill="#9ca3af"/>
            <path d="M50 64 C55 80 45 95 38 92 C32 88 40 72 50 64 Z" fill="#9ca3af"/>
            <path d="M36 50 C20 55 5 45 8 38 C12 32 28 40 36 50 Z" fill="#9ca3af"/>
            <circle cx="50" cy="50" r="6" fill="#10b981"/>
          </svg>
          <div class="fan-indicator" id="fanIndicator">FAN IDLE</div>
        </div>
        <div class="wind-streaks">
          <div class="wind-line"></div>
          <div class="wind-line"></div>
          <div class="wind-line"></div>
        </div>

        <!-- ACTUATOR: Ultrasonic Mist Spray Nozzles (Top Left) -->
        <div class="actuator-mister" id="misterActuator">
          <div class="nozzle-head">
            <div class="nozzle-hole"></div>
          </div>
          <div class="mist-clouds">
            <div class="mist-p" style="width: 20px; height: 20px; left: 8px; animation-delay: 0s;"></div>
            <div class="mist-p" style="width: 28px; height: 28px; left: 35px; animation-delay: 0.4s;"></div>
            <div class="mist-p" style="width: 24px; height: 24px; left: 65px; animation-delay: 0.8s;"></div>
          </div>
          <div class="mister-indicator" id="misterIndicator">MISTER IDLE</div>
        </div>

        <!-- ACTUATOR: Radiant Infrared Heating Element (Top Center) -->
        <div class="actuator-heater" id="heaterActuator">
          <div class="heater-coils">
            <div class="coil-wire"></div>
            <div class="coil-wire"></div>
            <div class="coil-wire"></div>
            <div class="coil-wire"></div>
            <div class="coil-wire"></div>
          </div>
          <div class="heater-indicator" id="heaterIndicator">HEATER OFF</div>
        </div>

        <!-- Chiller Control Unit (Bottom Left) -->
        <div class="chiller-unit" id="chillerUnit">
          <div class="chiller-led"></div>
          <div>
            <span style="font-weight: 700; display: block;">INVERTER CHILLER</span>
            <span id="chillerStateText" style="color: var(--text-muted);">READY (ECO)</span>
          </div>
        </div>

        <!-- CENTRAL PRODUCE VISUAL STAGE -->
        <div class="fruit-stage">
          <div class="produce-container" id="produceContainer">
            <svg class="produce-svg" id="produceSvg" viewBox="0 0 200 200"></svg>
          </div>
          <div class="wooden-crate">
            <span class="crate-label" id="crateLabel">TOMATO · BATCH #4</span>
          </div>
        </div>
      </div>

      <!-- LOGICAL TIMELINE TELEMETRY BAR -->
      <div class="timeline-bar">
        <div class="timeline-header">
          <div class="timeline-timestamp">
            <div class="live-dot"></div>
            <span class="timeline-time-label">SIMULATED TIME:</span>
            <span class="timeline-clock" id="simClockDisplay">09:00 AM</span>
          </div>
          <div class="timeline-status" id="timelineStatusText">
            Morning baseline · Facility climate optimal
          </div>
          <button class="btn-timeline-toggle" id="btnTimelineToggle">⏸ Pause</button>
        </div>
        <div class="timeline-slider-wrap">
          <input type="range" class="timeline-slider" id="timelineSlider" min="0" max="1440" step="10" value="540">
          <div class="timeline-ticks">
            <span>03:00 (Night Frost & Heater)</span>
            <span>06:30 (Target Restored)</span>
            <span>10:30 (Midday Sun Rising)</span>
            <span>12:45 (Peak Heat & Fan)</span>
            <span>16:30 (Target Restored)</span>
            <span>22:00 (Night)</span>
          </div>
        </div>
      </div>

    </div>

    <!-- RIGHT COLUMN: SIMPLE FARMER HARVEST STATUS -->
    <div class="card">
      <div class="card-header">
        <span class="card-title">🌱 Crop Health & Freshness</span>
      </div>

      <!-- Big Friendly Shelf Life Status -->
      <div class="farmer-status-card safe" id="farmerStatusCard">
        <div class="status-icon" id="farmerStatusIcon">🟢</div>
        <div class="status-main-text" id="farmerStatusText">Safe & Fresh</div>
        <div class="shelf-days-big" id="farmerDaysDisplay">15</div>
        <div class="shelf-days-label">Days of Freshness Left</div>

        <!-- Visual Freshness Meter -->
        <div class="freshness-bar-wrap">
          <div class="freshness-bar-fill" id="freshnessBarFill" style="width: 85%;"></div>
        </div>
      </div>

      <!-- One Simple Action Advice for the Farmer -->
      <div class="farmer-advice-card" id="farmerAdviceCard">
        <div class="advice-header">📢 What Should You Do?</div>
        <div class="advice-body" id="farmerAdviceText">
          👍 Storage climate is optimal. Your produce is well preserved.
        </div>
      </div>

      <!-- Simple 3-Day Outlook (Visual, no confusing graphs!) -->
      <div class="farmer-outlook-card">
        <div class="advice-header">📅 3-Day Freshness Outlook</div>
        <div class="outlook-grid">
          <div class="outlook-day">
            <span class="day-name">Today</span>
            <span class="day-status-pill safe" id="dayPill1">🟢 Fresh</span>
          </div>
          <div class="outlook-day">
            <span class="day-name">Tomorrow</span>
            <span class="day-status-pill safe" id="dayPill2">🟢 Fresh</span>
          </div>
          <div class="outlook-day">
            <span class="day-name">Day 3</span>
            <span class="day-status-pill safe" id="dayPill3">🟢 Fresh</span>
          </div>
        </div>
      </div>

    </div>

  </div>
</div>

<!-- Embedded Compiled AI Model Engine & Digital Twin Script -->
<script>
const M = {model_json};

// Produce SVG Generator Templates for all 10 Crops
const FRUIT_SVGS = {{
  tomato: (spoilFactor) => {{
    const baseColor = spoilFactor > 0.6 ? '#6d231b' : spoilFactor > 0.3 ? '#b71c1c' : '#e53935';
    const highlightOpacity = Math.max(0, 0.7 - spoilFactor * 0.7);
    const rotSpotsOpacity = spoilFactor > 0.3 ? (spoilFactor - 0.3) * 1.4 : 0;
    const moldOpacity = spoilFactor > 0.6 ? (spoilFactor - 0.6) * 2.5 : 0;
    const calyxColor = spoilFactor > 0.5 ? '#4e342e' : '#2e7d32';
    return `
      <ellipse cx="100" cy="115" rx="68" ry="62" fill="${{baseColor}}" stroke="#8b1812" stroke-width="2"/>
      <ellipse cx="80" cy="95" rx="30" ry="18" fill="#ff7961" opacity="${{highlightOpacity}}" transform="rotate(-15 80 95)"/>
      <ellipse cx="70" cy="90" rx="12" ry="6" fill="#ffffff" opacity="${{highlightOpacity}}"/>
      <g opacity="${{rotSpotsOpacity}}">
        <circle cx="120" cy="130" r="14" fill="#3e2723" opacity="0.85"/>
        <circle cx="75" cy="140" r="10" fill="#2d1c16" opacity="0.85"/>
        <circle cx="135" cy="105" r="8" fill="#3e2723" opacity="0.75"/>
      </g>
      <g opacity="${{moldOpacity}}">
        <circle cx="120" cy="130" r="10" fill="#a1a1aa" opacity="0.75"/>
        <circle cx="122" cy="128" r="6" fill="#e4e4e7" opacity="0.9"/>
      </g>
      <path d="M100 68 L100 50" stroke="#1b5e20" stroke-width="6" stroke-linecap="round"/>
      <path d="M100 68 Q115 52 135 60 Q120 70 100 68 Z" fill="${{calyxColor}}"/>
      <path d="M100 68 Q85 52 65 60 Q80 70 100 68 Z" fill="${{calyxColor}}"/>
    `;
  }},

  avocado: (spoilFactor) => {{
    const skinColor = spoilFactor > 0.5 ? '#1a1815' : spoilFactor > 0.25 ? '#24341f' : '#2e4922';
    const rotSpots = spoilFactor > 0.3 ? (spoilFactor - 0.3) * 1.5 : 0;
    const moldOpacity = spoilFactor > 0.6 ? (spoilFactor - 0.6) * 2.5 : 0;
    return `
      <path d="M100 50 C70 50 60 90 55 120 C50 155 70 175 100 175 C130 175 150 155 145 120 C140 90 130 50 100 50 Z" 
            fill="${{skinColor}}" stroke="#152410" stroke-width="3"/>
      <circle cx="85" cy="110" r="1.5" fill="#3e5f2e" opacity="0.6"/>
      <circle cx="115" cy="130" r="1.5" fill="#3e5f2e" opacity="0.6"/>
      <path d="M80 75 Q70 105 70 135" stroke="rgba(255,255,255,0.15)" stroke-width="4" stroke-linecap="round" fill="none"/>
      <g opacity="${{rotSpots}}">
        <ellipse cx="115" cy="135" rx="14" ry="10" fill="#0d0d0d" opacity="0.85"/>
        <ellipse cx="80" cy="145" rx="10" ry="8" fill="#0d0d0d" opacity="0.8"/>
      </g>
      <g opacity="${{moldOpacity}}">
        <circle cx="115" cy="135" r="7" fill="#71717a" opacity="0.8"/>
        <circle cx="116" cy="134" r="4" fill="#d4d4d8" opacity="0.9"/>
      </g>
    `;
  }},

  banana: (spoilFactor) => {{
    const peelColor = spoilFactor > 0.6 ? '#4e342e' : spoilFactor > 0.3 ? '#c0a020' : '#fbc02d';
    const spotOpacity = Math.min(1, spoilFactor * 1.8);
    return `
      <path d="M45 70 C80 50 140 70 160 140 C145 145 130 140 120 125 C100 80 65 78 45 70 Z" 
            fill="${{peelColor}}" stroke="#8d6e63" stroke-width="2"/>
      <path d="M45 70 L35 75 L40 82 L48 76 Z" fill="#2e7d32"/>
      <g opacity="${{spotOpacity}}">
        <ellipse cx="95" cy="85" rx="4" ry="2" fill="#2d1c16"/>
        <ellipse cx="110" cy="95" rx="6" ry="3" fill="#2d1c16"/>
        <ellipse cx="125" cy="110" rx="8" ry="4" fill="#2d1c16"/>
        <ellipse cx="138" cy="125" rx="7" ry="5" fill="#2d1c16"/>
      </g>
    `;
  }},

  apple: (spoilFactor) => {{
    const bodyColor = spoilFactor > 0.6 ? '#4a1e17' : spoilFactor > 0.3 ? '#991b1b' : '#dc2626';
    const rotOpacity = spoilFactor > 0.3 ? (spoilFactor - 0.3) * 1.5 : 0;
    return `
      <path d="M100 70 C75 55 50 75 50 110 C50 150 85 168 100 168 C115 168 150 150 150 110 C150 75 125 55 100 70 Z" 
            fill="${{bodyColor}}" stroke="#7f1d1d" stroke-width="2"/>
      <ellipse cx="75" cy="95" rx="20" ry="12" fill="#f87171" opacity="0.5" transform="rotate(-20 75 95)"/>
      <path d="M100 70 Q95 50 108 42" stroke="#5c4033" stroke-width="4" stroke-linecap="round" fill="none"/>
      <g opacity="${{rotOpacity}}">
        <circle cx="120" cy="125" r="16" fill="#261714" opacity="0.85"/>
        <circle cx="75" cy="130" r="12" fill="#261714" opacity="0.8"/>
      </g>
    `;
  }},

  potato: (spoilFactor) => {{
    const skinColor = spoilFactor > 0.6 ? '#3e2723' : spoilFactor > 0.3 ? '#6d4c41' : '#8d6e63';
    const rotOpacity = spoilFactor > 0.3 ? (spoilFactor - 0.3) * 1.5 : 0;
    return `
      <ellipse cx="100" cy="115" rx="65" ry="48" fill="${{skinColor}}" stroke="#4e342e" stroke-width="2" transform="rotate(-8 100 115)"/>
      <ellipse cx="80" cy="95" rx="4" ry="2" fill="#3e2723"/>
      <ellipse cx="125" cy="105" rx="5" ry="2.5" fill="#3e2723"/>
      <ellipse cx="90" cy="135" rx="4" ry="2" fill="#3e2723"/>
      <g opacity="${{rotOpacity}}">
        <circle cx="115" cy="115" r="15" fill="#1b120c" opacity="0.85"/>
        <path d="M125 105 L135 95" stroke="#4ade80" stroke-width="2" stroke-linecap="round"/>
      </g>
    `;
  }},

  orange: (spoilFactor) => {{
    const skinColor = spoilFactor > 0.6 ? '#794017' : spoilFactor > 0.3 ? '#d87010' : '#ff9800';
    const rotOpacity = spoilFactor > 0.3 ? (spoilFactor - 0.3) * 1.5 : 0;
    const moldOpacity = spoilFactor > 0.6 ? (spoilFactor - 0.6) * 2.5 : 0;
    return `
      <circle cx="100" cy="115" r="62" fill="${{skinColor}}" stroke="#b26a00" stroke-width="2"/>
      <ellipse cx="80" cy="90" rx="22" ry="14" fill="#ffb74d" opacity="0.5" transform="rotate(-20 80 90)"/>
      <circle cx="100" cy="54" r="5" fill="#388e3c"/>
      <g opacity="${{rotOpacity}}">
        <circle cx="120" cy="130" r="16" fill="#3e2723" opacity="0.85"/>
        <circle cx="75" cy="140" r="12" fill="#2d1c16" opacity="0.8"/>
      </g>
      <g opacity="${{moldOpacity}}">
        <circle cx="120" cy="130" r="11" fill="#43a047" opacity="0.85"/>
        <circle cx="120" cy="130" r="6" fill="#e0e0e0" opacity="0.9"/>
      </g>
    `;
  }},

  strawberry: (spoilFactor) => {{
    const berryColor = spoilFactor > 0.6 ? '#561914' : spoilFactor > 0.3 ? '#a81c1c' : '#e53935';
    const moldOpacity = spoilFactor > 0.4 ? (spoilFactor - 0.4) * 2.0 : 0;
    return `
      <path d="M100 65 C60 65 48 95 62 135 C72 165 92 180 100 180 C108 180 128 165 138 135 C152 95 140 65 100 65 Z" 
            fill="${{berryColor}}" stroke="#8b1812" stroke-width="2"/>
      <circle cx="85" cy="95" r="1.8" fill="#ffe082"/>
      <circle cx="115" cy="95" r="1.8" fill="#ffe082"/>
      <circle cx="100" cy="115" r="1.8" fill="#ffe082"/>
      <circle cx="80" cy="130" r="1.8" fill="#ffe082"/>
      <circle cx="120" cy="130" r="1.8" fill="#ffe082"/>
      <path d="M100 65 Q115 50 130 55 Q115 68 100 65 Z" fill="#2e7d32"/>
      <path d="M100 65 Q85 50 70 55 Q85 68 100 65 Z" fill="#2e7d32"/>
      <g opacity="${{moldOpacity}}">
        <ellipse cx="100" cy="130" rx="25" ry="18" fill="#9e9e9e" opacity="0.85" filter="blur(1px)"/>
        <ellipse cx="100" cy="130" rx="15" ry="10" fill="#f5f5f5" opacity="0.9"/>
      </g>
    `;
  }},

  lettuce: (spoilFactor) => {{
    const leafColor = spoilFactor > 0.6 ? '#4e3b2b' : spoilFactor > 0.3 ? '#827717' : '#43a047';
    const wiltOpacity = Math.min(1, spoilFactor * 1.5);
    return `
      <path d="M60 130 C40 100 60 70 100 70 C140 70 160 100 140 130 C120 160 80 160 60 130 Z" 
            fill="${{leafColor}}" stroke="#2e7d32" stroke-width="2"/>
      <path d="M75 110 C65 85 85 75 100 78 C115 75 135 85 125 110 C115 135 85 135 75 110 Z" 
            fill="#66bb6a" opacity="0.85"/>
      <g opacity="${{wiltOpacity}}">
        <path d="M50 110 Q58 135 75 145" stroke="#3e2723" stroke-width="5" fill="none" opacity="0.85"/>
        <path d="M150 110 Q142 135 125 145" stroke="#3e2723" stroke-width="5" fill="none" opacity="0.85"/>
      </g>
    `;
  }},

  carrot: (spoilFactor) => {{
    const rootColor = spoilFactor > 0.6 ? '#5d2b15' : spoilFactor > 0.3 ? '#b74716' : '#f57c00';
    const rotOpacity = spoilFactor > 0.3 ? (spoilFactor - 0.3) * 1.5 : 0;
    return `
      <path d="M80 70 L120 70 L104 175 C102 180 98 180 96 175 L80 70 Z" 
            fill="${{rootColor}}" stroke="#d84315" stroke-width="2"/>
      <line x1="86" y1="95" x2="114" y2="95" stroke="#bf360c" stroke-width="2" opacity="0.6"/>
      <line x1="90" y1="120" x2="110" y2="120" stroke="#bf360c" stroke-width="2" opacity="0.6"/>
      <path d="M100 70 L100 45 L92 55 L100 45 L108 55 Z" stroke="#2e7d32" stroke-width="3" fill="none"/>
      <g opacity="${{rotOpacity}}">
        <circle cx="100" cy="165" r="10" fill="#1b120c" opacity="0.9"/>
      </g>
    `;
  }},

  onion: (spoilFactor) => {{
    const bulbColor = spoilFactor > 0.6 ? '#4e342e' : spoilFactor > 0.3 ? '#8d6e63' : '#d7ccc8';
    const rotOpacity = spoilFactor > 0.3 ? (spoilFactor - 0.3) * 1.5 : 0;
    return `
      <path d="M100 65 C70 65 55 90 55 125 C55 155 75 170 100 170 C125 170 145 155 145 125 C145 90 130 65 100 65 Z" 
            fill="${{bulbColor}}" stroke="#8d6e63" stroke-width="2"/>
      <path d="M100 65 Q80 115 80 160" stroke="#a1887f" stroke-width="1.5" fill="none"/>
      <path d="M100 65 Q120 115 120 160" stroke="#a1887f" stroke-width="1.5" fill="none"/>
      <path d="M95 170 L93 182 M100 170 L100 185 M105 170 L107 182" stroke="#8d6e63" stroke-width="2"/>
      <path d="M100 65 L100 48" stroke="#388e3c" stroke-width="3"/>
      <g opacity="${{rotOpacity}}">
        <ellipse cx="100" cy="85" rx="18" ry="12" fill="#212121" opacity="0.9"/>
      </g>
    `;
  }}
}};

const CROP_ICONS = {{
  tomato: '🍅',
  avocado: '🥑',
  banana: '🍌',
  apple: '🍎',
  potato: '🥔',
  orange: '🍊',
  strawberry: '🍓',
  lettuce: '🥬',
  carrot: '🥕',
  onion: '🧅'
}};

const $ = id => document.getElementById(id);

// Feature Extraction & Prediction
function feats(c, T, RH, a, Th_val, Rh_val) {{
  const p = M.crops[c], d = p.dry;
  const Th = Th_val !== undefined ? Th_val : +$('tempSlider').value;
  const Rh = Rh_val !== undefined ? Rh_val : +$('rhSlider').value;
  const g = r => d ? r - p.rhlim : p.rhlim - r;
  return [T, RH, Th, Rh, a, p.Topt, p.rhlim, p.L0, p.Tmin, p.Q10, d, T - p.Topt, g(RH), Th - p.Topt, g(Rh), a / p.L0];
}}

function predict(c, T, RH, a, Th_val, Rh_val) {{
  const x = feats(c, T, RH, a, Th_val, Rh_val);
  let s = M.init;
  for (const t of M.trees) {{
    let n = 0;
    while (t.l[n] >= 0) n = x[t.f[n]] <= t.t[n] ? t.l[n] : t.r[n];
    s += M.lr * t.v[n];
  }}
  return Math.max(0, Math.expm1(s));
}}

let currentCrop = 'tomato';
let simTime = 540; // Starts at 09:00 AM (Morning baseline)
let simInterval = null;
let isSimRunning = true;

// OPEN-METEO WEATHER INTEGRATION
let liveWeather = {{
  isLive: false,
  locationName: 'Kampala, Uganda',
  currentT: 20.0,
  currentRH: 85,
  weatherCode: 1,
  hourlyTime: [],
  hourlyT: [],
  hourlyRH: []
}};

function getWeatherDescription(code) {{
  if (code === 0) return {{ text: 'Clear Sky', icon: '☀️' }};
  if (code <= 3) return {{ text: 'Partly Cloudy', icon: '⛅' }};
  if (code === 45 || code === 48) return {{ text: 'Fog / Mist', icon: '🌫️' }};
  if (code >= 51 && code <= 67) return {{ text: 'Rain / Drizzle', icon: '🌧️' }};
  if (code >= 71 && code <= 77) return {{ text: 'Snow Flurries', icon: '❄️' }};
  if (code >= 80 && code <= 82) return {{ text: 'Rain Showers', icon: '🌦️' }};
  if (code >= 95) return {{ text: 'Thunderstorm', icon: '⛈️' }};
  return {{ text: 'Fair Weather', icon: '🌤️' }};
}}

async function fetchOpenMeteoWeather(lat, lon, locName) {{
  const badge = $('weatherBadge');
  const text = $('weatherText');
  const icon = $('weatherIcon');
  if (text) text.textContent = `Connecting to Open-Meteo for ${{locName}}...`;

  try {{
    const url = `https://api.open-meteo.com/v1/forecast?latitude=${{lat}}&longitude=${{lon}}&hourly=temperature_2m,relative_humidity_2m,weather_code&current=temperature_2m,relative_humidity_2m,weather_code&forecast_days=3&timezone=auto`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${{res.status}}`);
    const data = await res.json();

    const curT = data.current.temperature_2m;
    const curRH = data.current.relative_humidity_2m;
    const code = data.current.weather_code;
    const desc = getWeatherDescription(code);

    liveWeather = {{
      isLive: true,
      locationName: locName,
      currentT: curT,
      currentRH: curRH,
      weatherCode: code,
      hourlyTime: data.hourly.time || [],
      hourlyT: data.hourly.temperature_2m || [],
      hourlyRH: data.hourly.relative_humidity_2m || []
    }};

    if (text) text.textContent = `Outdoor: ${{curT.toFixed(1)}} °C · ${{Math.round(curRH)}}% RH · ${{desc.text}}`;
    if (icon) icon.textContent = desc.icon;
    if (badge) {{
      badge.textContent = 'Open-Meteo Live';
      badge.style.color = 'var(--primary)';
      badge.style.borderColor = 'rgba(16, 185, 129, 0.4)';
    }}

    applySimTime(simTime);
    console.log(`Open-Meteo live feed connected for ${{locName}}: ${{curT}}°C, ${{curRH}}% RH`);
  }} catch (err) {{
    console.warn('Open-Meteo offline/unreachable, using physics fallback:', err.message);
    liveWeather.isLive = false;
    if (text) text.textContent = `Outdoor: 24.0 °C · 65% RH (Diurnal Fallback)`;
    if (badge) {{
      badge.textContent = 'Diurnal Physics';
      badge.style.color = '#f59e0b';
      badge.style.borderColor = 'rgba(245, 158, 11, 0.4)';
    }}
    applySimTime(simTime);
  }}
}}

// Initialize Date Picker to 1 day ago
const d0 = new Date();
d0.setDate(d0.getDate() - 1);
$('harvestDateInput').value = d0.toISOString().slice(0, 10);

function getAge() {{
  return Math.max(0.1, (Date.now() - new Date($('harvestDateInput').value)) / 864e5);
}}

function formatClock(minutes) {{
  const h24 = Math.floor(minutes / 60) % 24;
  const m = minutes % 60;
  const ampm = h24 >= 12 ? 'PM' : 'AM';
  const h12 = (h24 % 12) || 12;
  return `${{h12 < 10 ? '0' : ''}}${{h12}}:${{m < 10 ? '0' : ''}}${{m}} ${{ampm}}`;
}}

// COMPLETE 24-HOUR PHYSICAL DIURNAL CYCLE:
// 1. 00:00 - 01:30 (Midnight): Stable at setpoint (Topt).
// 2. 01:30 - 03:45 (Night Frost Chill): Outdoor frost drops storage temp below Tmin.
//    -> Radiant Infrared Heater automatically activates (heats coils, warms ambient).
// 3. 03:45 - 06:00 (Heater Restoration): Radiant heater warms facility smoothly back up to Topt.
//    -> Heater shuts down back to IDLE once setpoint restored.
// 4. 06:00 - 10:30 (Dawn & Morning): Mild, optimal baseline.
// 5. 10:30 - 13:00 (Midday Sun Peak): Sun warms warehouse (+3.8°C drift).
//    -> Industrial Ventilation Fan spins up & Inverter Chiller engages.
// 6. 13:00 - 16:30 (Fan & Chiller Regulation): Active cooling brings room smoothly back down to Topt.
//    -> Fan powers down back to IDLE.
// 7. 16:30 - 24:00 (Evening Preservation): Target restored and maintained.
function getDiurnalClimate(minutes, p) {{
  const Topt = p.Topt;
  const Tmin = p.Tmin;
  const rhlim = p.rhlim;
  let T = Topt;
  let RH = rhlim;
  let status = `Baseline storage · Climate optimal (${{Topt}}°C, ${{rhlim}}%)`;

  // Dynamically scale heat & cold amplitudes from live weather forecast (or calibrated physics)
  let heatAmp = 4.2;
  let coldAmp = Math.max(3.6, (Topt - Tmin) + 1.8);

  if (liveWeather.isLive && liveWeather.hourlyT && liveWeather.hourlyT.length >= 24) {{
    const maxOut = Math.max(...liveWeather.hourlyT.slice(0, 24));
    const minOut = Math.min(...liveWeather.hourlyT.slice(0, 24));
    heatAmp = Math.max(3.2, Math.min(6.5, 0.45 * (maxOut - Topt)));
    coldAmp = Math.max(3.0, Math.min(6.0, 0.45 * (Topt - minOut)));
  }}

  // 1. 00:00 - 03:00 (0 - 180 min): Night Chill Cooling Dip
  if (minutes <= 180) {{
    const prog = minutes / 180.0;
    const dip = coldAmp * Math.sin(prog * Math.PI / 2.0);
    T = Topt - dip;
    RH = Math.min(100, rhlim + 3.0 * prog);
    if (T < Tmin - 0.2) {{
      status = `Night chill (${{T.toFixed(1)}}°C < ${{Tmin}}°C min) → Radiant heater actively warming store`;
    }} else {{
      status = `Night ambient cooling (${{T.toFixed(1)}}°C) · Nominal`;
    }}
  }}
  // 2. 03:00 - 06:30 (180 - 390 min): Active Radiant Heater Warming ALL THE WAY back to Topt
  else if (minutes <= 390) {{
    const prog = (minutes - 180) / 210.0;
    const remainingDip = coldAmp * Math.cos(prog * Math.PI / 2.0);
    T = Topt - remainingDip;
    RH = Math.max(rhlim, (rhlim + 3.0) - 3.0 * prog);
    if (remainingDip > 0.2) {{
      status = `Radiant heater active (+${{(Topt - T).toFixed(1)}}°C) → Restoring setpoint ${{Topt}}°C`;
    }} else {{
      T = Topt;
      status = `Setpoint ${{Topt}}°C restored · Heater returned to standby`;
    }}
  }}
  // 3. 06:30 - 09:30 (390 - 570 min): Morning Mild Baseline
  else if (minutes <= 570) {{
    const prog = (minutes - 390) / 180.0;
    T = Topt + 0.6 * Math.sin(prog * Math.PI);
    RH = rhlim;
    status = `Morning baseline (${{T.toFixed(1)}}°C) · Storage climate optimal`;
  }}
  // 4. 09:30 - 12:45 (570 - 765 min): Midday Sun Heating Up Storage
  else if (minutes <= 765) {{
    const prog = (minutes - 570) / 195.0;
    const drift = heatAmp * Math.sin(prog * Math.PI / 2.0);
    T = Topt + drift;
    RH = Math.max(30, rhlim - 5.0 * prog);
    if (T > Topt + 1.2) {{
      status = `Midday heat (+${{drift.toFixed(1)}}°C) → Fan & Chiller actively cooling facility`;
    }} else {{
      status = `Midday mild warming (+${{drift.toFixed(1)}}°C) · Nominal`;
    }}
  }}
  // 5. 12:45 - 16:30 (765 - 990 min): Active Fan & Chiller Cooling ALL THE WAY back to Topt
  else if (minutes <= 990) {{
    const prog = (minutes - 765) / 225.0;
    const remainingDrift = heatAmp * Math.cos(prog * Math.PI / 2.0);
    T = Topt + remainingDrift;
    RH = Math.min(100, (rhlim - 5.0) + 5.0 * prog);
    if (remainingDrift > 0.2) {{
      status = `Fan cooling active (-${{(T - Topt).toFixed(1)}}°C) → Restoring setpoint ${{Topt}}°C`;
    }} else {{
      T = Topt;
      status = `Setpoint ${{Topt}}°C restored · Fan returned to idle`;
    }}
  }}
  // 6. 16:30 - 20:30 (990 - 1230 min): Evening Preservation Setpoint
  else if (minutes <= 1230) {{
    T = Topt;
    RH = rhlim;
    status = `Evening preservation · Target ${{Topt}}°C maintained`;
  }}
  // 7. 20:30 - 24:00 (1230 - 1440 min): Night Cooling Transition
  else {{
    const prog = (minutes - 1230) / 210.0;
    T = Topt - 0.8 * Math.sin(prog * Math.PI / 2.0);
    RH = rhlim;
    status = `Night cooling transition · Setpoint safe (${{T.toFixed(1)}}°C)`;
  }}

  return {{ T, RH, status }};
}}

// CUMULATIVE HISTORICAL AVERAGE:
// If harvest day is today, averages match current sensor inputs.
// If earlier, cumulative weighted average over elapsed storage time.
function getHistoricalAverages(curT, curRH, minutes, p) {{
  const ageDays = getAge();
  if (ageDays <= 0.1) {{
    return {{ avgT: curT, avgRH: curRH }};
  }}
  const priorHours = Math.max(0, ageDays - 1.0) * 24.0;
  const todayHours = Math.max(0.5, minutes / 60.0);
  const totalHours = priorHours + todayHours;

  const priorSumT = priorHours * p.Topt;
  const todaySumT = todayHours * ((p.Topt + curT) / 2.0);
  const avgT = (priorSumT + todaySumT) / totalHours;

  const priorSumRH = priorHours * p.rhlim;
  const todaySumRH = todayHours * ((p.rhlim + curRH) / 2.0);
  const avgRH = (priorSumRH + todaySumRH) / totalHours;

  return {{ avgT, avgRH }};
}}

function initCropButtons() {{
  const container = $('cropButtons');
  container.innerHTML = '';
  Object.keys(M.crops).slice(0, 10).forEach(k => {{
    const btn = document.createElement('button');
    btn.className = `crop-btn ${{k === currentCrop ? 'active' : ''}}`;
    btn.innerHTML = `<span class="icon">${{CROP_ICONS[k] || '🌱'}}</span><span>${{k[0].toUpperCase() + k.slice(1)}}</span>`;
    btn.onclick = () => selectCrop(k);
    container.appendChild(btn);
  }});
}}

function selectCrop(cropName) {{
  currentCrop = cropName;
  initCropButtons();
  applySimTime(simTime);
}}

// Update Visuals, Actuators & Model Output
function updateDashboard(source) {{
  const p = M.crops[currentCrop];
  if (!p) return;

  const T = +$('tempSlider').value;
  const RH = +$('rhSlider').value;
  const ageDays = getAge();

  const avgs = getHistoricalAverages(T, RH, simTime, p);
  const avgT = avgs.avgT;
  const avgRH = avgs.avgRH;

  $('tempDisplay').textContent = T.toFixed(1) + ' °C';
  $('tempAvgDisplay').textContent = avgT.toFixed(1) + ' °C';
  $('tempTargetDisplay').textContent = p.Topt.toFixed(1) + ' °C';

  $('rhDisplay').textContent = Math.round(RH) + ' %';
  $('rhAvgDisplay').textContent = Math.round(avgRH) + ' %';
  $('rhTargetDisplay').textContent = p.rhlim + ' %';

  $('ageDisplay').textContent = ageDays.toFixed(1) + 'd ago';

  $('cropSpecs').innerHTML = `
    <b>Target:</b> ${{p.Topt}} °C · <b>Min Safe:</b> ${{p.Tmin}} °C<br>
    <b>Humidity:</b> ${{p.rhlim}}% (${{p.dry ? 'Dry Store' : 'Humid Store'}}) · <b>Base Life:</b> ${{p.L0}} days
  `;

  // Model Evaluation passing current AND historical averages!
  const predDays = predict(currentCrop, T, RH, ageDays, avgT, avgRH);
  const roundedDays = Math.max(0, Math.round(predDays));
  const maxRef = Math.min(30, p.L0);
  const freshnessPct = Math.max(5, Math.min(100, Math.round((predDays / maxRef) * 100)));

  // Physical Actuators Trigger Logic
  const isTooHot = T > p.Topt + 1.2;
  const isTooCold = T < p.Tmin - 0.2;
  const isTooDry = p.dry ? false : RH < p.rhlim - 5;
  const isTooHumid = p.dry ? RH > p.rhlim + 5 : false;

  // Simple Farmer Risk Classification (Green / Yellow / Red)
  const riskTier = predDays <= 3 ? 2 : predDays <= 8 ? 1 : 0;
  const statusCard = $('farmerStatusCard');
  const statusIcon = $('farmerStatusIcon');
  const farmerStatusText = $('farmerStatusText');
  const daysDisplay = $('farmerDaysDisplay');
  const barFill = $('freshnessBarFill');
  const adviceText = $('farmerAdviceText');

  if (daysDisplay) {{
    daysDisplay.textContent = predDays >= 60 ? '60+' : roundedDays;
  }}
  if (barFill) {{
    barFill.style.width = freshnessPct + '%';
  }}

  if (riskTier === 0) {{
    // 🟢 SAFE & FRESH
    if (statusCard) statusCard.className = 'farmer-status-card safe';
    if (statusIcon) statusIcon.textContent = '🟢';
    if (farmerStatusText) {{
      farmerStatusText.textContent = 'Safe & Fresh';
      farmerStatusText.style.color = 'var(--low)';
    }}
    if (daysDisplay) daysDisplay.style.color = 'var(--primary)';
    if (barFill) barFill.style.background = 'linear-gradient(90deg, #10b981, #34d399)';

    if (isTooHot) {{
      if (adviceText) adviceText.innerHTML = `🌀 <b>Cooling in progress:</b> The automated fan is cooling the room to protect your ${{currentCrop}} from outdoor heat. Everything is safe!`;
    }} else if (isTooCold) {{
      if (adviceText) adviceText.innerHTML = `🔥 <b>Warming in progress:</b> The heater is warming the room to protect your ${{currentCrop}} from cold frost. Everything is safe!`;
    }} else {{
      if (adviceText) adviceText.innerHTML = `👍 <b>All good!</b> Facility climate is optimal. Your ${{currentCrop}} is in peak fresh condition.`;
    }}
  }} else if (riskTier === 1) {{
    // 🟡 RIPENING (PREPARE)
    if (statusCard) statusCard.className = 'farmer-status-card warning';
    if (statusIcon) statusIcon.textContent = '🟡';
    if (farmerStatusText) {{
      farmerStatusText.textContent = 'Ripening Fast';
      farmerStatusText.style.color = 'var(--med)';
    }}
    if (daysDisplay) daysDisplay.style.color = 'var(--med)';
    if (barFill) barFill.style.background = 'linear-gradient(90deg, #f59e0b, #fbbf24)';

    if (adviceText) adviceText.innerHTML = `⚠️ <b>Prepare for market:</b> Your ${{currentCrop}} is ripening. Plan to sell within the next week to get the best market price!`;
  }} else {{
    // 🔴 CRITICAL ACTION (SELL NOW)
    if (statusCard) statusCard.className = 'farmer-status-card danger';
    if (statusIcon) statusIcon.textContent = '🔴';
    if (farmerStatusText) {{
      farmerStatusText.textContent = 'Sell Immediately';
      farmerStatusText.style.color = 'var(--high)';
    }}
    if (daysDisplay) daysDisplay.style.color = 'var(--high)';
    if (barFill) barFill.style.background = 'linear-gradient(90deg, #ef4444, #f87171)';

    if (adviceText) adviceText.innerHTML = `🚨 <b>Take immediate action!</b> Produce is reaching full ripeness. Sell today or tomorrow to avoid spoil loss!`;
  }}

  // Update Simple 3-Day Outlook
  updateSimpleOutlook(predDays);

  // Produce Visual Shader
  $('crateLabel').textContent = `${{currentCrop.toUpperCase()}} · BATCH #4`;
  const spoilFactor = Math.max(0, Math.min(1.0, 1.0 - (predDays / maxRef)));
  const svgGen = FRUIT_SVGS[currentCrop] || FRUIT_SVGS.tomato;
  $('produceSvg').innerHTML = svgGen(spoilFactor);

  // Physical Actuators
  const fan = $('fanActuator');
  const mister = $('misterActuator');
  const heater = $('heaterActuator');
  const chiller = $('chillerUnit');
  const ambient = $('roomAmbient');
  const statusDot = $('statusDot');
  const statusText = $('chamberStatusText');

  // Ambient Chamber Room Glow
  if (isTooCold) {{
    ambient.className = 'room-ambient chilling';
  }} else {{
    ambient.className = 'room-ambient ' + (riskTier === 0 ? 'safe' : riskTier === 1 ? 'warning' : 'danger');
  }}

  // 1. Fan Actuator
  if (isTooHot || isTooHumid) {{
    fan.classList.add('spinning');
    $('fanIndicator').textContent = isTooHot ? 'VENTILATING' : 'DEHUMIDIFYING';
  }} else {{
    fan.classList.remove('spinning');
    $('fanIndicator').textContent = 'FAN IDLE';
  }}

  // 2. Misting Actuator
  if (isTooDry) {{
    mister.classList.add('spraying');
    $('misterIndicator').textContent = 'MISTING';
  }} else {{
    mister.classList.remove('spraying');
    $('misterIndicator').textContent = 'MISTER IDLE';
  }}

  // 3. Radiant Heater Actuator
  if (isTooCold) {{
    heater.classList.add('heating');
    $('heaterIndicator').textContent = 'HEATER ON';
  }} else {{
    heater.classList.remove('heating');
    $('heaterIndicator').textContent = 'HEATER OFF';
  }}

  // 4. Inverter Chiller Unit
  if (isTooHot) {{
    chiller.classList.add('cooling');
    $('chillerStateText').textContent = `ACTIVE (-${{(T - p.Topt).toFixed(1)}}°C)`;
  }} else {{
    chiller.classList.remove('cooling');
    $('chillerStateText').textContent = 'STANDBY (ECO)';
  }}

  // Clean, Quiet Chamber Status Indicator (Top-Left Pill)
  if (isTooHot) {{
    statusDot.style.background = 'var(--cold)';
    statusDot.style.boxShadow = '0 0 8px var(--cold)';
    statusText.textContent = `Cooling Store (-${{(T - p.Topt).toFixed(1)}}°C)`;
  }} else if (isTooCold) {{
    statusDot.style.background = 'var(--heat)';
    statusDot.style.boxShadow = '0 0 8px var(--heat)';
    statusText.textContent = `Heating Store (+${{(p.Topt - T).toFixed(1)}}°C)`;
  }} else if (isTooDry) {{
    statusDot.style.background = '#38bdf8';
    statusDot.style.boxShadow = '0 0 8px #38bdf8';
    statusText.textContent = 'Misting Active';
  }} else {{
    statusDot.style.background = 'var(--low)';
    statusDot.style.boxShadow = '0 0 8px var(--low)';
    statusText.textContent = `Climate: Optimal (${{p.Topt}}°C, ${{p.rhlim}}%)`;
  }}
}}

// Simple 3-Day Visual Outlook
function updateSimpleOutlook(curDays) {{
  const p1 = $('dayPill1');
  const p2 = $('dayPill2');
  const p3 = $('dayPill3');

  function getDayStatus(d) {{
    if (d > 8) return {{ text: '🟢 Fresh', cls: 'safe' }};
    if (d > 3) return {{ text: '🟡 Ripening', cls: 'warning' }};
    return {{ text: '🔴 Sell Now', cls: 'danger' }};
  }}

  const s1 = getDayStatus(curDays);
  const s2 = getDayStatus(curDays - 1.0);
  const s3 = getDayStatus(curDays - 2.5);

  if (p1) {{ p1.textContent = s1.text; p1.className = `day-status-pill ${{s1.cls}}`; }}
  if (p2) {{ p2.textContent = s2.text; p2.className = `day-status-pill ${{s2.cls}}`; }}
  if (p3) {{ p3.textContent = s3.text; p3.className = `day-status-pill ${{s3.cls}}`; }}
}}

// LOGICAL TIMELINE APPLICATION
function applySimTime(minutes) {{
  const p = M.crops[currentCrop];
  if (!p) return;

  const clockStr = formatClock(minutes);
  $('simClockDisplay').textContent = clockStr;
  $('timelineSlider').value = minutes;

  const climate = getDiurnalClimate(minutes, p);
  $('timelineStatusText').textContent = climate.status;

  $('tempSlider').value = climate.T.toFixed(1);
  $('rhSlider').value = Math.round(climate.RH);

  updateDashboard('timeline');
}}

function startSimLoop() {{
  if (simInterval) clearInterval(simInterval);
  isSimRunning = true;
  $('btnTimelineToggle').innerHTML = `<span>⏸ Pause</span>`;
  simInterval = setInterval(() => {{
    simTime = (simTime + 10) % 1440;
    applySimTime(simTime);
  }}, 200);
}}

function pauseSimLoop() {{
  if (simInterval) {{
    clearInterval(simInterval);
    simInterval = null;
  }}
  isSimRunning = false;
  $('btnTimelineToggle').innerHTML = `<span>▶ Play Timeline</span>`;
}}

$('btnTimelineToggle').onclick = () => {{
  if (isSimRunning) {{
    pauseSimLoop();
  }} else {{
    startSimLoop();
  }}
}};

$('timelineSlider').oninput = (e) => {{
  simTime = +e.target.value;
  applySimTime(simTime);
}};

// Preset Handlers
$('btnOpt').onclick = () => {{
  simTime = 540; // 09:00 AM baseline
  applySimTime(simTime);
}};
$('btnRoom').onclick = () => {{
  pauseSimLoop();
  $('tempSlider').value = 22;
  $('rhSlider').value = 65;
  $('timelineStatusText').textContent = 'Manual Preset: Room Ambient (22°C)';
  updateDashboard('preset');
}};
$('btnCold').onclick = () => {{
  pauseSimLoop();
  const p = M.crops[currentCrop];
  $('tempSlider').value = Math.max(-4, p.Tmin - 4);
  $('rhSlider').value = 75;
  $('timelineStatusText').textContent = 'Manual Preset: Cold Chilling (-4°C)';
  updateDashboard('preset');
}};
$('btnHot').onclick = () => {{
  pauseSimLoop();
  $('tempSlider').value = 32;
  $('rhSlider').value = 45;
  $('timelineStatusText').textContent = 'Manual Preset: Heat Spike (32°C)';
  updateDashboard('preset');
}};

// Event Listeners for manual sliders
$('tempSlider').oninput = () => {{
  pauseSimLoop();
  $('timelineStatusText').textContent = 'Manual Slider Override (Inspecting custom temperature)';
  updateDashboard('manual');
}};
$('rhSlider').oninput = () => {{
  pauseSimLoop();
  $('timelineStatusText').textContent = 'Manual Slider Override (Inspecting custom humidity)';
  updateDashboard('manual');
}};
$('harvestDateInput').onchange = () => updateDashboard('date');

// Location Selector Event Listener
const locSelect = $('weatherLocationSelect');
if (locSelect) {{
  locSelect.onchange = (e) => {{
    const val = e.target.value;
    if (val === 'gps') {{
      if (navigator.geolocation) {{
        $('weatherText').textContent = 'Locating farm via GPS...';
        navigator.geolocation.getCurrentPosition(
          pos => fetchOpenMeteoWeather(pos.coords.latitude, pos.coords.longitude, 'Local GPS Farm'),
          err => {{
            alert('GPS permission denied. Using Kampala, Uganda default.');
            fetchOpenMeteoWeather(0.3136, 32.5811, 'Kampala, Uganda');
          }}
        );
      }} else {{
        alert('Geolocation not supported by this browser.');
      }}
    }} else {{
      const [lat, lon] = val.split(',').map(Number);
      const selName = e.target.options[e.target.selectedIndex].text.split('(')[0].trim();
      fetchOpenMeteoWeather(lat, lon, selName);
    }}
  }};
}}

// Initialize
initCropButtons();
applySimTime(simTime);
startSimLoop();

// Fetch initial live meteorological data for Kampala, Uganda (Dataset Origin)
fetchOpenMeteoWeather(0.3136, 32.5811, 'Kampala, Uganda');
</script>
</body>
</html>
"""

Path("farmer_dashboard.html").write_text(dashboard_code, encoding="utf-8")
Path("outputs/farmer_dashboard.html").write_text(dashboard_code, encoding="utf-8")
print(f"Successfully generated clean farmer_dashboard.html ({len(dashboard_code)} bytes)!")
