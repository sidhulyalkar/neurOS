# neuros/ml/training_pipeline.py
"""
Comprehensive ML Training Pipeline for BCI Applications
Supports motor imagery, P300, and SSVEP classification with advanced evaluation
"""

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.model_selection import (
    train_test_split, cross_val_score, GridSearchCV, 
    StratifiedKFold, TimeSeriesSplit
)
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.feature_selection import SelectKBest, f_classif, RFE
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import (
    classification_report, confusion_matrix, roc_auc_score,
    accuracy_score, precision_recall_fscore_support
)
import xgboost as xgb
from typing import Dict, Any, List, Tuple, Optional, Union
import logging
import joblib
import json
from datetime import datetime
from dataclasses import dataclass, field
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Import our signal processing modules
from neuros.signal_processing.advanced_features import (
    MotorImageryFeatures, P300Features, SSVEPFeatures, 
    BCITask, SignalConfig
)

@dataclass
class TrainingConfig:
    """Configuration for ML training pipeline"""
    task_type: BCITask = BCITask.MOTOR_IMAGERY
    test_size: float = 0.2
    validation_size: float = 0.2
    cv_folds: int = 5
    random_state: int = 42
    
    # Feature selection
    feature_selection: bool = True
    max_features: int = 500
    feature_selection_method: str = 'rfe'  # 'rfe', 'selectkbest', 'none'
    
    # Model selection
    models_to_test: List[str] = field(default_factory=lambda: [
        'rf', 'svm', 'xgb', 'lr', 'mlp'
    ])
    
    # Hyperparameter tuning
    hyperparameter_tuning: bool = True
    tuning_scoring: str = 'accuracy'
    
    # Output
    save_models: bool = True
    output_dir: str = 'models'
    
    # Advanced options
    class_weight: str = 'balanced'  # Handle class imbalance
    ensemble_methods: bool = True

@dataclass
class ModelResults:
    """Results from model training and evaluation"""
    model_name: str
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    auc_score: float
    cv_scores: np.ndarray
    confusion_matrix: np.ndarray
    feature_importance: Optional[np.ndarray] = None
    training_time: float = 0.0
    best_params: Dict[str, Any] = field(default_factory=dict)

class BCIClassifier(BaseEstimator, ClassifierMixin):
    """Custom BCI classifier with integrated feature extraction"""
    
    def __init__(self, task_type: BCITask = BCITask.MOTOR_IMAGERY, 
                 sample_rate: int = 250, channels: int = 64,
                 classifier_name: str = 'rf', **classifier_params):
        self.task_type = task_type
        self.sample_rate = sample_rate
        self.channels = channels
        self.classifier_name = classifier_name
        self.classifier_params = classifier_params
        
        # Initialize feature extractor based on task
        if task_type == BCITask.MOTOR_IMAGERY:
            self.feature_extractor = MotorImageryFeatures(sample_rate, channels)
        elif task_type == BCITask.P300:
            self.feature_extractor = P300Features(sample_rate, channels)
        elif task_type == BCITask.SSVEP:
            self.feature_extractor = SSVEPFeatures(sample_rate, channels)
        else:
            raise ValueError(f"Unsupported task type: {task_type}")
        
        self.scaler = StandardScaler()
        self.classifier = None
        self.is_fitted = False
    
    def _get_classifier(self):
        """Get classifier based on name"""
        classifiers = {
            'rf': RandomForestClassifier(random_state=42, **self.classifier_params),
            'svm': SVC(probability=True, random_state=42, **self.classifier_params),
            'xgb': xgb.XGBClassifier(random_state=42, **self.classifier_params),
            'lr': LogisticRegression(random_state=42, **self.classifier_params),
            'mlp': MLPClassifier(random_state=42, **self.classifier_params)
        }
        return classifiers.get(self.classifier_name, RandomForestClassifier())
    
    def fit(self, X: np.ndarray, y: np.ndarray):
        """Fit the BCI classifier"""
        # Extract features
        self.feature_extractor.fit(X, y)
        X_features = self.feature_extractor.transform(X)
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X_features)
        
        # Train classifier
        self.classifier = self._get_classifier()
        self.classifier.fit(X_scaled, y)
        
        self.is_fitted = True
        return self
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict classes"""
        if not self.is_fitted:
            raise ValueError("Classifier must be fitted before prediction")
        
        X_features = self.feature_extractor.transform(X)
        X_scaled = self.scaler.transform(X_features)
        return self.classifier.predict(X_scaled)
    
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Predict class probabilities"""
        if not self.is_fitted:
            raise ValueError("Classifier must be fitted before prediction")
        
        X_features = self.feature_extractor.transform(X)
        X_scaled = self.scaler.transform(X_features)
        return self.classifier.predict_proba(X_scaled)

class BCITrainingPipeline:
    """Complete training pipeline for BCI models"""
    
    def __init__(self, config: TrainingConfig):
        self.config = config
        self.logger = logging.getLogger("neurOS.ml.training")
        self.results: Dict[str, ModelResults] = {}
        self.best_model = None
        self.best_score = 0.0
        
        # Create output directory
        Path(config.output_dir).mkdir(parents=True, exist_ok=True)
    
    def prepare_data(self, X: np.ndarray, y: np.ndarray) -> Tuple[np.ndarray, ...]:
        """Prepare data for training"""
        self.logger.info(f"Preparing data: {X.shape} samples, {len(np.unique(y))} classes")
        
        # Split data
        X_temp, X_test, y_temp, y_test = train_test_split(
            X, y, test_size=self.config.test_size, 
            stratify=y, random_state=self.config.random_state
        )
        
        X_train, X_val, y_train, y_val = train_test_split(
            X_temp, y_temp, test_size=self.config.validation_size / (1 - self.config.test_size),
            stratify=y_temp, random_state=self.config.random_state
        )
        
        self.logger.info(f"Train: {X_train.shape[0]}, Val: {X_val.shape[0]}, Test: {X_test.shape[0]}")
        
        return X_train, X_val, X_test, y_train, y_val, y_test
    
    def get_model_configs(self) -> Dict[str, Dict[str, Any]]:
        """Get model configurations for hyperparameter tuning"""
        configs = {
            'rf': {
                'model': RandomForestClassifier(random_state=42, class_weight=self.config.class_weight),
                'params': {
                    'n_estimators': [100, 200, 300],
                    'max_depth': [10, 20, None],
                    'min_samples_split': [2, 5, 10],
                    'min_samples_leaf': [1, 2, 4]
                }
            },
            'svm': {
                'model': SVC(probability=True, random_state=42, class_weight=self.config.class_weight),
                'params': {
                    'C': [0.1, 1, 10, 100],
                    'gamma': ['scale', 'auto', 0.001, 0.01],
                    'kernel': ['rbf', 'poly', 'sigmoid']
                }
            },
            'xgb': {
                'model': xgb.XGBClassifier(random_state=42),
                'params': {
                    'n_estimators': [100, 200, 300],
                    'max_depth': [3, 6, 10],
                    'learning_rate': [0.01, 0.1, 0.2],
                    'subsample': [0.8, 0.9, 1.0]
                }
            },
            'lr': {
                'model': LogisticRegression(random_state=42, class_weight=self.config.class_weight, max_iter=1000),
                'params': {
                    'C': [0.01, 0.1, 1, 10, 100],
                    'penalty': ['l1', 'l2', 'elasticnet'],
                    'solver': ['liblinear', 'saga']
                }
            },
            'mlp': {
                'model': MLPClassifier(random_state=42, max_iter=1000),
                'params': {
                    'hidden_layer_sizes': [(50,), (100,), (100, 50), (200, 100)],
                    'activation': ['relu', 'tanh'],
                    'alpha': [0.0001, 0.001, 0.01],
                    'learning_rate': ['constant', 'adaptive']
                }
            }
        }
        
        return {k: v for k, v in configs.items() if k in self.config.models_to_test}
    
    def extract_features(self, X: np.ndarray, y: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Extract features using task-specific extractor"""
        self.logger.info(f"Extracting features for {self.config.task_type.value}")
        
        # Initialize feature extractor
        if self.config.task_type == BCITask.MOTOR_IMAGERY:
            extractor = MotorImageryFeatures()
        elif self.config.task_type == BCITask.P300:
            extractor = P300Features()
        elif self.config.task_type == BCITask.SSVEP:
            extractor = SSVEPFeatures()
        else:
            raise ValueError(f"Unsupported task: {self.config.task_type}")
        
        # Fit and transform
        extractor.fit(X, y)
        X_features = extractor.transform(X)
        
        self.logger.info(f"Extracted features shape: {X_features.shape}")
        self.feature_extractor = extractor  # Store for later use
        
        return X_features, extractor.get_feature_names()
    
    def feature_selection(self, X: np.ndarray, y: np.ndarray, 
                         feature_names: List[str]) -> Tuple[np.ndarray, List[str]]:
        """Perform feature selection"""
        if not self.config.feature_selection:
            return X, feature_names
        
        self.logger.info(f"Performing feature selection: {self.config.feature_selection_method}")
        
        n_features = min(self.config.max_features, X.shape[1])
        
        if self.config.feature_selection_method == 'selectkbest':
            selector = SelectKBest(f_classif, k=n_features)
            X_selected = selector.fit_transform(X, y)
            selected_indices = selector.get_support(indices=True)
            
        elif self.config.feature_selection_method == 'rfe':
            estimator = RandomForestClassifier(n_estimators=50, random_state=42)
            selector = RFE(estimator, n_features_to_select=n_features)
            X_selected = selector.fit_transform(X, y)
            selected_indices = selector.get_support(indices=True)
        
        else:
            return X, feature_names
        
        selected_features = [feature_names[i] for i in selected_indices]
        self.logger.info(f"Selected {len(selected_features)} features")
        
        return X_selected, selected_features
    
    def train_model(self, model_name: str, X_train: np.ndarray, y_train: np.ndarray,
                   X_val: np.ndarray, y_val: np.ndarray) -> ModelResults:
        """Train a single model with hyperparameter tuning"""
        self.logger.info(f"Training {model_name}")
        
        start_time = datetime.now()
        model_configs = self.get_model_configs()
        
        if model_name not in model_configs:
            raise ValueError(f"Unknown model: {model_name}")
        
        base_model = model_configs[model_name]['model']
        param_grid = model_configs[model_name]['params']
        
        # Create pipeline with scaling
        pipeline = Pipeline([
            ('scaler', StandardScaler()),
            ('classifier', base_model)
        ])
        
        # Hyperparameter tuning
        if self.config.hyperparameter_tuning:
            # Adjust parameter names for pipeline
            param_grid_pipeline = {f'classifier__{k}': v for k, v in param_grid.items()}
            
            cv = StratifiedKFold(n_splits=self.config.cv_folds, shuffle=True, random_state=42)
            grid_search = GridSearchCV(
                pipeline, param_grid_pipeline, 
                cv=cv, scoring=self.config.tuning_scoring,
                n_jobs=-1, verbose=0
            )
            
            grid_search.fit(X_train, y_train)
            best_model = grid_search.best_estimator_
            best_params = grid_search.best_params_
            
        else:
            best_model = pipeline
            best_model.fit(X_train, y_train)
            best_params = {}
        
        # Validation predictions
        y_val_pred = best_model.predict(X_val)
        y_val_proba = best_model.predict_proba(X_val)
        
        # Cross-validation scores
        cv_scores = cross_val_score(
            best_model, X_train, y_train, 
            cv=StratifiedKFold(n_splits=self.config.cv_folds, shuffle=True, random_state=42),
            scoring='accuracy'
        )
        
        # Calculate metrics
        accuracy = accuracy_score(y_val, y_val_pred)
        precision, recall, f1, _ = precision_recall_fscore_support(y_val, y_val_pred, average='weighted')
        
        # AUC score (handle multiclass)
        if len(np.unique(y_val)) == 2:
            auc = roc_auc_score(y_val, y_val_proba[:, 1])
        else:
            auc = roc_auc_score(y_val, y_val_proba, multi_class='ovr', average='weighted')
        
        cm = confusion_matrix(y_val, y_val_pred)
        
        # Feature importance (if available)
        feature_importance = None
        try:
            if hasattr(best_model.named_steps['classifier'], 'feature_importances_'):
                feature_importance = best_model.named_steps['classifier'].feature_importances_
            elif hasattr(best_model.named_steps['classifier'], 'coef_'):
                feature_importance = np.abs(best_model.named_steps['classifier'].coef_[0])
        except:
            pass
        
        training_time = (datetime.now() - start_time).total_seconds()
        
        # Store best model
        if accuracy > self.best_score:
            self.best_score = accuracy
            self.best_model = best_model
        
        result = ModelResults(
            model_name=model_name,
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1,
            auc_score=auc,
            cv_scores=cv_scores,
            confusion_matrix=cm,
            feature_importance=feature_importance,
            training_time=training_time,
            best_params=best_params
        )
        
        self.logger.info(f"{model_name} - Accuracy: {accuracy:.3f}, F1: {f1:.3f}, AUC: {auc:.3f}")
        
        return result
    
    def evaluate_models(self, X_test: np.ndarray, y_test: np.ndarray) -> Dict[str, Any]:
        """Evaluate all trained models on test set"""
        self.logger.info("Evaluating models on test set")
        
        test_results = {}
        
        for model_name, result in self.results.items():
            # Get the trained model (simplified - in practice, load from saved models)
            if model_name == 'best_model' and self.best_model is not None:
                model = self.best_model
            else:
                continue  # Skip if model not available
            
            # Test predictions
            y_pred = model.predict(X_test)
            y_proba = model.predict_proba(X_test)
            
            # Calculate test metrics
            test_accuracy = accuracy_score(y_test, y_pred)
            test_precision, test_recall, test_f1, _ = precision_recall_fscore_support(
                y_test, y_pred, average='weighted'
            )
            
            if len(np.unique(y_test)) == 2:
                test_auc = roc_auc_score(y_test, y_proba[:, 1])
            else:
                test_auc = roc_auc_score(y_test, y_proba, multi_class='ovr', average='weighted')
            
            test_results[model_name] = {
                'accuracy': test_accuracy,
                'precision': test_precision,
                'recall': test_recall,
                'f1_score': test_f1,
                'auc_score': test_auc,
                'confusion_matrix': confusion_matrix(y_test, y_pred).tolist(),
                'classification_report': classification_report(y_test, y_pred, output_dict=True)
            }
        
        return test_results
    
    def save_results(self, test_results: Dict[str, Any] = None):
        """Save training results and models"""
        if not self.config.save_models:
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save model results
        results_dict = {}
        for name, result in self.results.items():
            results_dict[name] = {
                'accuracy': result.accuracy,
                'precision': result.precision,
                'recall': result.recall,
                'f1_score': result.f1_score,
                'auc_score': result.auc_score,
                'cv_scores': result.cv_scores.tolist(),
                'confusion_matrix': result.confusion_matrix.tolist(),
                'training_time': result.training_time,
                'best_params': result.best_params
            }
        
        # Add test results if available
        if test_results:
            results_dict['test_results'] = test_results
        
        # Save to JSON
        results_file = Path(self.config.output_dir) / f"training_results_{timestamp}.json"
        with open(results_file, 'w') as f:
            json.dump(results_dict, f, indent=2)
        
        # Save best model
        if self.best_model is not None:
            model_file = Path(self.config.output_dir) / f"best_model_{timestamp}.pkl"
            joblib.dump(self.best_model, model_file)
        
        self.logger.info(f"Results saved to {results_file}")
        self.logger.info(f"Best model saved to {model_file if self.best_model else 'None'}")
    
    def run_training(self, X: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        """Run complete training pipeline"""
        self.logger.info("Starting BCI model training pipeline")
        
        # 1. Prepare data
        X_train, X_val, X_test, y_train, y_val, y_test = self.prepare_data(X, y)
        
        # 2. Extract features
        X_train_features, feature_names = self.extract_features(X_train, y_train)
        X_val_features = self.feature_extractor.transform(X_val)
        X_test_features = self.feature_extractor.transform(X_test)
        
        # 3. Feature selection
        X_train_selected, selected_features = self.feature_selection(
            X_train_features, y_train, feature_names
        )
        
        # Apply same selection to validation and test sets
        if len(selected_features) < len(feature_names):
            selected_indices = [feature_names.index(f) for f in selected_features]
            X_val_selected = X_val_features[:, selected_indices]
            X_test_selected = X_test_features[:, selected_indices]
        else:
            X_val_selected = X_val_features
            X_test_selected = X_test_features
        
        # 4. Train models
        for model_name in self.config.models_to_test:
            try:
                result = self.train_model(model_name, X_train_selected, y_train, 
                                        X_val_selected, y_val)
                self.results[model_name] = result
            except Exception as e:
                self.logger.error(f"Failed to train {model_name}: {e}")
        
        # 5. Evaluate on test set
        test_results = self.evaluate_models(X_test_selected, y_test)
        
        # 6. Save results
        self.save_results(test_results)
        
        # 7. Generate summary
        summary = self.generate_summary(test_results)
        
        return summary
    
    def generate_summary(self, test_results: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate training summary"""
        summary = {
            'config': {
                'task_type': self.config.task_type.value,
                'models_tested': self.config.models_to_test,
                'feature_selection': self.config.feature_selection,
                'hyperparameter_tuning': self.config.hyperparameter_tuning
            },
            'validation_results': {},
            'best_model': None,
            'best_validation_score': self.best_score
        }
        
        # Validation results
        for name, result in self.results.items():
            summary['validation_results'][name] = {
                'accuracy': result.accuracy,
                'f1_score': result.f1_score,
                'auc_score': result.auc_score,
                'cv_mean': np.mean(result.cv_scores),
                'cv_std': np.std(result.cv_scores)
            }
        
        # Find best model
        if self.results:
            best_model_name = max(self.results.keys(), 
                                key=lambda x: self.results[x].accuracy)
            summary['best_model'] = best_model_name
        
        # Test results
        if test_results:
            summary['test_results'] = test_results
        
        return summary

# Example usage and CLI integration
def create_training_cli():
    """Create CLI commands for model training"""
    import click
    
    @click.group()
    def train():
        """Model training commands"""
        pass
    
    @train.command('bci')
    @click.option('--task', type=click.Choice(['motor_imagery', 'p300', 'ssvep']), 
                  default='motor_imagery', help='BCI task type')
    @click.option('--data-file', required=True, help='Path to training data')
    @click.option('--labels-file', help='Path to labels file')
    @click.option('--models', default='rf,svm,xgb', help='Models to train (comma-separated)')
    @click.option('--output-dir', default='models', help='Output directory')
    @click.option('--cv-folds', default=5, help='Cross-validation folds')
    def train_bci(task, data_file, labels_file, models, output_dir, cv_folds):
        """Train BCI classification models"""
        click.echo(f"🧠 Training BCI models for {task}")
        
        # Load data (mock for demo)
        click.echo(f"📁 Loading data from {data_file}")
        
        # Create synthetic data for demo
        np.random.seed(42)
        n_trials, n_channels, n_times = 200, 32, 500
        X = np.random.randn(n_trials, n_channels, n_times)
        y = np.random.randint(0, 2, n_trials)
        
        # Configure training
        config = TrainingConfig(
            task_type=BCITask(task),
            models_to_test=models.split(','),
            output_dir=output_dir,
            cv_folds=cv_folds
        )
        
        # Run training
        pipeline = BCITrainingPipeline(config)
        summary = pipeline.run_training(X, y)
        
        # Display results
        click.echo("\n📊 Training Results:")
        click.echo("=" * 50)
        
        for model_name, metrics in summary['validation_results'].items():
            click.echo(f"{model_name:>10}: Acc={metrics['accuracy']:.3f}, "
                      f"F1={metrics['f1_score']:.3f}, AUC={metrics['auc_score']:.3f}")
        
        click.echo(f"\n🏆 Best model: {summary['best_model']} "
                  f"(Accuracy: {summary['best_validation_score']:.3f})")
    
    return train

# Testing the training pipeline
if __name__ == "__main__":
    # Test the training pipeline
    print("🧠 Testing BCI Training Pipeline")
    
    # Generate synthetic data
    np.random.seed(42)
    n_trials, n_channels, n_times = 100, 32, 500  # Small dataset for testing
    sample_rate = 250
    
    # Motor imagery data
    X = np.random.randn(n_trials, n_channels, n_times)
    y = np.random.randint(0, 2, n_trials)  # Binary classification
    
    print(f"Data shape: {X.shape}, Labels: {len(np.unique(y))} classes")
    
    # Configure training
    config = TrainingConfig(
        task_type=BCITask.MOTOR_IMAGERY,
        models_to_test=['rf', 'svm'],  # Test subset for speed
        hyperparameter_tuning=False,  # Disable for speed
        cv_folds=3  # Reduced for speed
    )
    
    # Run training
    pipeline = BCITrainingPipeline(config)
    summary = pipeline.run_training(X, y)
    
    print("\n📊 Training Summary:")
    print(json.dumps(summary, indent=2, default=str))
    
    print("\n✅ Training pipeline test completed!")