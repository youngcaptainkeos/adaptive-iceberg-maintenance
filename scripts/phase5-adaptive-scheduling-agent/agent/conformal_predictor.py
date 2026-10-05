import numpy as np

class ConformalPredictor:
    def __init__(self, model, alpha=0.05):
        """
        model: a fitted sklearn model with a .predict() method
        alpha: miscoverage rate (0.05 = 95% coverage target)
        """
        self.model = model
        self.alpha = alpha
        self.q_hat = None
        
    def calibrate(self, X_cal, y_cal):
        """
        Compute q_hat from calibration residuals.
        X_cal, y_cal must be STRICTLY from the validation set (never used for training).
        """
        preds = self.model.predict(X_cal)
        residuals = np.abs(y_cal - preds)
        n = len(residuals)
        q_level = np.ceil((n + 1) * (1 - self.alpha)) / n
        q_level = min(q_level, 1.0)
        self.q_hat = np.quantile(residuals, q_level, method='higher')
        return self.q_hat
        
    def predict_with_bounds(self, X):
        """Returns (point_prediction, upper_bound, lower_bound)"""
        point = self.model.predict(X)
        return point, point + self.q_hat, np.maximum(point - self.q_hat, 0)

def load_and_calibrate(model_path, X_cal, y_cal, alpha=0.05) -> ConformalPredictor:
    """Load a joblib model and calibrate it. Returns ready-to-use ConformalPredictor."""
    import joblib
    model = joblib.load(model_path)
    predictor = ConformalPredictor(model, alpha)
    predictor.calibrate(X_cal, y_cal)
    return predictor
