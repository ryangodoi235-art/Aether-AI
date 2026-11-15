"""Inferência local sem retreino; valida entrada antes de carregar o modelo."""
import json,math,warnings
from functools import lru_cache
from pathlib import Path
FEATURES=['energy_kwh_t','energy_kwh_t_minus_1','energy_kwh_t_minus_24','mean_kwh_last_24h','hour_of_day','day_of_week']
ROOT=Path(__file__).resolve().parent
ARTIFACT_DIR=ROOT/'artifacts'

class ModelUnavailableError(RuntimeError):pass

def validate_features(payload):
    if not isinstance(payload,dict):raise TypeError('Entrada deve ser um objeto JSON.')
    if set(payload)!=set(FEATURES):raise ValueError('Informe exatamente as seis features permitidas.')
    row={}
    for name in FEATURES:
        value=payload[name]
        if isinstance(value,bool) or not isinstance(value,(int,float)):raise TypeError(f'{name} deve ser numérico.')
        try:finite=math.isfinite(value)
        except OverflowError:finite=False
        if not finite:raise ValueError(f'{name} deve ser finito.')
        if name in FEATURES[:4] and value<0:raise ValueError(f'{name} não pode ser negativo.')
        if name in FEATURES[4:]:
            limit=23 if name=='hour_of_day' else 6
            if not isinstance(value,int) or not 0<=value<=limit:raise ValueError(f'{name} deve ser inteiro entre 0 e {limit}.')
        row[name]=value
    return row

@lru_cache(maxsize=1)
def load_model():
    try:
        import joblib
        from sklearn.exceptions import InconsistentVersionWarning
        metadata=json.loads((ARTIFACT_DIR/'model_metadata.json').read_text(encoding='utf-8'))
        if metadata['feature_order']!=FEATURES:raise ValueError('Ordem de features incompatível.')
        with warnings.catch_warnings():
            warnings.simplefilter('error',InconsistentVersionWarning)
            model=joblib.load(ARTIFACT_DIR/'model_hist_gradient_boosting.joblib')
        return model,metadata
    except Exception as e:raise ModelUnavailableError('Modelo não pôde ser carregado. Confira artefatos e versões do ambiente.') from e

def predict_next_hour(payload):
    row=validate_features(payload)
    model,metadata=load_model()
    try:
        import pandas as pd
        raw=float(model.predict(pd.DataFrame([row],columns=FEATURES))[0])
    except Exception as e:raise ModelUnavailableError('Falha na execução do modelo.') from e
    if not math.isfinite(raw):raise ModelUnavailableError('Modelo retornou previsão não finita.')
    return {'model_version':metadata['model_version'],'predicted_next_hour_kwh':max(0.0,raw),'raw_prediction_kwh':raw,'clipped_to_zero':raw<0,'target_definition':'energy consumed during hour t+1, in kWh','input_features_used':FEATURES}

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('input_json');args=ap.parse_args()
    print(json.dumps(predict_next_hour(json.loads(Path(args.input_json).read_text(encoding='utf-8'))),indent=2,ensure_ascii=False,allow_nan=False))
