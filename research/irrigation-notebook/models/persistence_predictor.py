"""
Portable Persistence Predictor for Soil Moisture Forecasting.
Compatible with scikit-learn API and independent subprocess execution.
"""
import numpy as np
import pandas as pd

class PersistencePredictor:
    """Standard physical persistence predictor for soil moisture time series."""
    def __init__(self, current_col='VWC_10cm'):
        self.current_col = current_col
        self.model_name = "Persistence Baseline"

    def fit(self, X, y=None):
        return self

    def predict(self, X):
        if isinstance(X, pd.DataFrame):
            if self.current_col in X.columns:
                return X[self.current_col].values
            return X.iloc[:, 0].values
        elif isinstance(X, np.ndarray):
            return X[:, 0]
        return np.array(X)
