# FARMLINK · Post-Harvest Shelf-Life & Cold Storage Digital Twin 🌾📦

Autonomous post-harvest preservation intelligence and interactive digital twin chamber for smallholder and commercial farmers across Tunisia and Africa.

---

## 🌟 Key Capabilities

1. **Machine Learning Shelf-Life Prediction**:
   - Predicts remaining produce shelf life in real time based on crop physiology, storage temperature, relative humidity, cumulative historical thermal averages, and harvest age.
   - Calibrated against empirical post-harvest datasets (10,995 observations from Uganda and temperature-controlled avocado ripening trials) using Arrhenius / $Q_{10}$ biochemical decay dynamics ($Q_{10} = 2.43$).
   - Trained Gradient Boosting Regressor (200 decision trees, learning rate 0.05, max depth 4) exported into a **zero-dependency portable JSON format** that executes entirely client-side inside the browser in $< 1\text{ ms}$.

2. **Physically-Coupled Digital Twin Chamber**:
   - **Visual Degradation Engine**: 10 custom vector produce models (🍅 Tomato, 🥑 Avocado, 🍌 Banana, 🍎 Apple, 🥔 Potato, 🍊 Orange, 🍓 Strawberry, 🥬 Lettuce, 🥕 Carrot, 🧅 Onion) that dynamically wrinkle, discolor, and exhibit rot spots as storage risk increases.
   - **Automated Physical Actuators**:
     - 🌀 **Industrial Ventilation Fan & Inverter Chiller**: Automatically engages when ambient heat threatens the produce, actively cooling the room back to the target setpoint.
     - 🔥 **Radiant Infrared Heating Coils**: Automatically glows warm orange-red when overnight chill approaches the chilling-injury threshold ($T_{\text{min}}$), warming the room back to target.
     - 💨 **Ultrasonic Mist Nozzles**: Sprays micro-droplets when humidity drops to prevent moisture loss and shriveling.

3. **Live Open-Meteo Meteorological Coupling**:
   - Connects directly to the **Open-Meteo API** (free, no API key required) for real-time outdoor temperature, humidity, and 72-hour hourly forecasts.
   - Regional presets for major agricultural hubs:
     - 📍 **Kampala, Uganda** (Central Market dataset origin)
     - 📍 **Tunis / Carthage, Tunisia**
     - 📍 **Sousse, Tunisia** (Chott Meriam agricultural region)
     - 📍 **Nairobi, Kenya**
     - 📍 **Cairo, Egypt**
     - 📍 **Addis Ababa, Ethiopia**
     - 📍 **Bogota, Colombia**
     - 📡 **Live Device GPS** via `navigator.geolocation`
   - Incorporates realistic cold-room thermal transfer through polyurethane sandwich panels ($R = 4.5$).
   - **100% Offline Safe**: Silently falls back to calibrated physical diurnal cycles if internet is disconnected.

4. **Elderly Farmer-Friendly UI/UX**:
   - High-contrast visual traffic-light indicators:
     - 🟢 **Safe & Fresh** (Produce in peak condition)
     - 🟡 **Ripening Fast** (Prepare for market)
     - 🔴 **Sell Immediately** (Take immediate action to avoid waste)
   - Large, clear number display (**Days of Freshness Left**) with a color-coded health meter.
   - **Plain Action Advice** (e.g. *“👍 All good! Facility climate is optimal. Your tomato is in peak fresh condition.”*).
   - **Simple 3-Day Outlook** without intimidating coordinate plots or mathematical jargon.

---

## 📁 Repository Structure

```
research/post-harvest-model/
├── README.md                              # Comprehensive model & system documentation
├── farmer_dashboard.html                  # Standalone, interactive browser-ready dashboard
├── dashboard/
│   ├── farmer_dashboard.html              # Mirror of the interactive digital twin
│   └── post_harvest_preview.html          # Analytical 72-hour horizon forecast preview
├── models/
│   ├── post_harvest_model.joblib          # Scikit-learn GradientBoostingRegressor weights
│   └── post_harvest_model.json            # 200 portable decision trees (standalone browser evaluator)
├── notebooks/
│   └── post_harvest_training.ipynb        # End-to-end data preparation, training & evaluation notebook
├── data/
│   ├── uganda/
│   │   └── Dataset.csv                    # 10,995 observations of tomato post-harvest storage
│   └── avocado/
│       └── Avocado Ripening Dataset.xlsx  # Empirical multi-temperature firmness & decay dataset
└── scripts/
    └── build_farmer_dashboard.py          # Python compiler script embedding weights & assets into HTML
```

---

## 🚀 How to Run the Dashboard

The dashboard is completely self-contained with embedded vector assets and client-side decision trees. **No backend server, Python environment, or npm packages are needed to run it!**

1. Simply double-click or open **[`farmer_dashboard.html`](farmer_dashboard.html)** in any web browser (Chrome, Firefox, Safari, Edge).
2. Use the **Crop Selector** to pick produce (e.g. Tomato, Avocado, Orange, Lettuce).
3. Watch the **Logical 24-Hour Diurnal Timeline** play automatically:
   - Scrub to **12:30 PM** to observe midday heat drift and autonomous cooling fan intervention.
   - Scrub to **03:00 AM** to observe night frost and radiant heater warming.
4. Select your **Farm Region** or click **📡 Use Device GPS** to pull live ambient weather from Open-Meteo.

---

## 🧠 Model Architecture & Validation

- **Algorithm**: Gradient Boosting Regressor (`scikit-learn`)
- **Objective**: Predict $\log(1 + \text{Remaining Shelf Life Days})$
- **Loss Function**: Squared error with early stopping
- **Hyperparameters**: $N_{\text{estimators}} = 200$, $\text{Learning Rate} = 0.05$, $\text{Max Depth} = 4$
- **Biochemical Calibration**: $Q_{10} = 2.43$ temperature coefficient fitted across avocado and tomato trials
- **Validation Metrics**:
  - $R^2 \ge 0.98$
  - $\text{Mean Absolute Error (MAE)} < 0.45 \text{ days}$
  - Tree parity between Python scikit-learn and JavaScript evaluator: Difference $< 0.00012\text{ days}$

---

## 👥 Authors & Team
- **Farmlink / KizunaHack Team**
- Post-Harvest Preservation & Digital Twin Module
