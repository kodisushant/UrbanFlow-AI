---
name: ml-engineer
description: >-
  Specialized Machine Learning Engineer skill for dataset exploration, preprocessing, feature engineering,
  model training, evaluation, debugging, and metric verification. Enforces strict scientific guardrails against
  data leakage, forbids fabricated benchmark or evaluation numbers, and explains ML concepts in clear,
  beginner-friendly terms.
---

# Machine Learning Engineer Skill

This skill guides the agent through end-to-end Machine Learning and Computer Vision workflows with production-grade rigor. It ensures models are trained ethically, evaluated without data leakage, and communicated clearly to technical and non-technical stakeholders alike.

---

## 1. Core Principles & Non-Negotiable Guardrails

### A. Zero Hallucination of Metrics (Absolute Rule)
- **Never fabricate or assume performance metrics.** Do not state accuracy, precision, recall, F1, ROC-AUC, MAE, MSE, RMSE, or mAP scores unless they were directly computed by running a script or reading recorded benchmark output logs.
- If evaluation code has not yet been executed, explicitly state: *"Metrics are pending execution. We must run the evaluation script against the test split to measure actual performance."*

### B. Strict Prevention of Data Leakage
- **Temporal / Time-Series Leakage:** Never use random K-Fold cross-validation or random `train_test_split` on temporal or time-series data (e.g., traffic speed, sensor counts, congestion indices). Always use chronological splits or Walk-Forward / TimeSeriesSplit validation.
- **Preprocessor Leakage:** Always fit transformers (`StandardScaler`, `MinMaxScaler`, `OneHotEncoder`, imputer) **strictly on training splits only**. Transform validation/test splits using the fitted parameters. Never call `fit_transform` on the entire dataset prior to splitting.
- **Feature Leakage:** Ensure target variables, future observations, or proxy columns containing ground truth are not included in feature matrices.
- See the detailed [Leakage & Metrics Guide](./references/leakage_and_metrics.md) for complete checklists.

### C. Beginner-Friendly Explanations
- Translate complex mathematical and statistical jargon into intuitive analogies (e.g., explaining overfitting as "memorizing practice exam questions rather than learning concepts", or precision vs. recall as "avoiding false alarms vs. not missing genuine emergencies").
- Clarify trade-offs when making modeling recommendations.

---

## 2. End-to-End ML Workflow

### Step 1: Exploratory Data Analysis (EDA) & Data Sanity
1. Inspect shapes, data types, missing value percentages, and duplicate records.
2. Check class balance (classification) or target distribution / skewness (regression).
3. Identify outliers and assess whether they represent sensor glitches, anomalies, or legitimate extreme events (e.g., traffic gridlock or highway accidents).
4. Verify timestamp consistency, frequency, and missing time intervals in time-series data.

### Step 2: Preprocessing & Feature Engineering
- **Missing Data:** Impute missing values using forward-fill / rolling median for time-series, or domain-appropriate median/mode for tabular features.
- **Cyclical Features:** Encode cyclical time data (hour of day, day of week) using sine and cosine transformations:
  $$\text{hour\_sin} = \sin\left(\frac{2\pi \times \text{hour}}{24}\right), \quad \text{hour\_cos} = \cos\left(\frac{2\pi \times \text{hour}}{24}\right)$$
- **Lag & Rolling Features:** For traffic/sensor series, generate historical lags ($t-15\text{m}$, $t-30\text{m}$) and moving averages without peeking into future timestamps ($t+k$).
- **Spatial & Graph Features:** Incorporate road segment lengths, upstream sensor readings, and intersection node degrees.

### Step 3: Baselines Before Complex Models
1. **Rule of Simplicity:** Always establish a trivial baseline before jumping to complex neural architectures:
   - Regression: Historical moving average, last-known-value persistence, or Ridge/Lasso linear regression.
   - Classification: Majority class baseline or simple decision tree.
2. Progress to gradient boosting (`LightGBM`, `XGBoost`, `CatBoost`) for tabular/structured data.
3. Use deep learning (`PyTorch`, `LSTM`, `Temporal Fusion Transformers`, `Graph Neural Networks`) only when simpler baselines demonstrate clear limitations.

### Step 4: Computer Vision & Incident Detection (UrbanFlow AI)
- For object detection (vehicles, pedestrians) on CCTV video feeds:
  - Use lightweight, fast models (e.g., YOLOv8n / YOLOv8s) suitable for real-time inference during demonstrations.
  - Track vehicles across frames using simple SORT/ByteTrack algorithms.
  - Detect stopped vehicles or abnormal speed drops to flag **candidate incident events**.
  - **Caution:** Label events as *potential* incidents with an associated confidence score; never claim absolute certainty from unverified camera footage.

### Step 5: Evaluation & Validation Protocols
1. Evaluate models using appropriate domain metrics:
   - **Continuous Traffic Forecasting:** Mean Absolute Error (MAE), Root Mean Squared Error (RMSE), Mean Absolute Percentage Error (MAPE).
   - **Incident Classification:** Precision, Recall, F1-Score, PR-AUC (especially under extreme class imbalance).
2. Slicing Analysis: Evaluate model performance across subsets (e.g., peak rush hour vs. midnight, rainy weather vs. clear skies, highway vs. arterial roads).

---

## 3. Reference Documentation
- [Leakage & Evaluation Protocols](./references/leakage_and_metrics.md)

