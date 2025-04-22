import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
import joblib
import os

class ModeleClassification:
    def __init__(self):
        self.model = Pipeline([
            ('tfidf', TfidfVectorizer(lowercase=True, stop_words='french')),
            ('clf', LogisticRegression(max_iter=1000))
        ])
        
    def entrainer(self, df):
        """Entraîne le modèle sur les données historiques"""
        X = df['Description']  # Utilise Description au lieu de Commerçant
        y = df['Catégorie']
        self.model.fit(X, y)
        joblib.dump(self.model, 'modele_depenses.joblib')
        
    def predire(self, description):
        """Prédit la catégorie pour une nouvelle description"""
        if os.path.exists('modele_depenses.joblib'):
            self.model = joblib.load('modele_depenses.joblib')
        return self.model.predict([description])[0]