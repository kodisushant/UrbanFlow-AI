# Machine Learning Guardrails: Data Leakage & Evaluation Protocols

This reference guide provides explicit checklists and prevention patterns for common machine learning evaluation errors, specifically tailored for tabular, time-series, and computer vision systems.

---

## 1. Data Leakage Checklist

Data leakage occurs when information from outside the training dataset is inadvertently used to create the model, resulting in overly optimistic evaluation scores that fail catastrophically in production.

### Type 1: Temporal / Time-Series Leakage (Critical in Traffic Data)
- **Problem:** Splitting time-series records randomly using `train_test_split(shuffle=True)`. This allows the model to predict traffic at time $t$ by interpolating between known observations at $t-1$ and $t+1$.
- **Prevention:**
  - Sort the dataset chronologically.
  - Split sequentially: older 70-80% for training, subsequent 10-15% for validation, latest 10-15% for testing.
  - When performing cross-validation, use `sklearn.model_selection.TimeSeriesSplit` or rolling walk-forward validation.

### Type 2: Preprocessing & Scaling Leakage
- **Problem:** Normalizing or scaling features using global min/max or mean/std before splitting:
  ```python
  # WRONG: Leaks test set distribution into scaler
  scaler = StandardScaler()
  X_scaled = scaler.fit_transform(X)
  X_train, X_test = split(X_scaled)
  ```
- **Prevention:**
  ```python
  # CORRECT: Fit on train, transform on test
  X_train, X_test = split(X)
  scaler = StandardScaler()
  X_train_scaled = scaler.fit_transform(X_train)
  X_test_scaled = scaler.transform(X_test)
  ```

### Type 3: Target Leakage in Feature Engineering
- **Problem:** Including features that are direct proxies or byproducts of the outcome event. For example, including `emergency_dispatch_time` as a feature to predict whether a traffic incident occurred.
- **Prevention:**
  - Audit all feature definitions.
  - Ask: *"Would this feature value be strictly available at the exact decision timestamp $T_0$ in production?"*

---

## 2. Metric Selection Matrix

| Problem Type | Recommended Metric | Inappropriate Metric | Why? |
| :--- | :--- | :--- | :--- |
| **Traffic Congestion Forecasting** | **MAE / RMSE** | $R^2$ alone | $R^2$ can obscure large localized errors during peak shock hours; MAE directly reflects average vehicle speed or count error in real-world units (e.g., km/h or cars/min). |
| **Incident Detection (Severe Imbalance)** | **PR-AUC, F1-Score, Recall** | **Raw Accuracy** | In an incident dataset where 99.5% of hours have no incident, a dummy model predicting "no incident" achieves 99.5% accuracy while detecting zero emergencies. |
| **Vehicle Detection (Vision)** | **mAP@50, mAP@50-95** | Raw Pixel Accuracy | Evaluates bounding box overlap (IoU) and class classification across thresholds. |

---

## 3. Beginner-Friendly Glossary

- **Overfitting:** When your model memorizes noise and specific peculiarities of the training data instead of learning general patterns—like memorizing practice exam answers word-for-word and failing the actual exam.
- **Precision:** Of all the alarms the system raised, how many were genuine incidents? (High precision = low false alarm rate).
- **Recall:** Of all actual incidents that occurred on the road, how many did the system catch? (High recall = no missed emergencies).
- **Walk-Forward Validation:** Testing a time-series model by training on past data (e.g., Day 1 to 10) and predicting the next day (Day 11), then advancing the window and repeating.

