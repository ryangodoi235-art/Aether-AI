"""Integra previsão histórica ao backend sem depender do modelo na inicialização."""
import json
from pathlib import Path
from fastapi import HTTPException, Query
from .ml.forecast_adapter import forecast
from .ml.inference import load_model, ModelUnavailableError

def setup(api, connect):
    with connect() as con:
        con.execute('CREATE TABLE IF NOT EXISTS forecasts (id TEXT PRIMARY KEY, payload TEXT NOT NULL, result TEXT NOT NULL)')

    @api.get('/api/v1/forecasts/status')
    def model_status():
        try:
            _,meta=load_model()
            return dict(status='ready',model_version=meta['model_version'],mode='historical_demo',message='Modelo local disponível. Demonstração com dados históricos UCI.')
        except ModelUnavailableError:
            return dict(status='unavailable',mode='historical_demo',message='Modelo indisponível. Instale requirements-forecast.txt em ambiente compatível e confira os artefatos. Os controles da casa continuam disponíveis.')

    @api.get('/api/v1/forecasts/demo-inputs')
    def demo_inputs():
        return json.loads((Path(__file__).parent/'ml/demo_windows.json').read_text(encoding='utf-8'))

    @api.get('/api/v1/forecasts')
    def history(limit:int=Query(20,ge=1,le=100),offset:int=Query(0,ge=0)):
        with connect() as con:
            rows=con.execute('SELECT result FROM forecasts ORDER BY rowid DESC LIMIT ? OFFSET ?',(limit,offset)).fetchall()
        return [json.loads(r['result']) for r in rows]

    @api.post('/api/v1/forecasts')
    def predict(body:dict):
        rid=body.get('request_id')
        if not isinstance(rid,str) or not rid.strip() or len(rid)>100:raise HTTPException(422,'request_id obrigatório, até 100 caracteres.')
        # This first adapter explicitly handles historical data, never live house readings.
        if body.get('dataset_id')!='uci235-hourly':raise HTTPException(422,'Nesta versão use dataset_id uci235-hourly com histórico desse dataset.')
        try:payload=json.dumps(body,sort_keys=True,allow_nan=False)
        except (ValueError,TypeError):raise HTTPException(422,'Entrada contém valores não finitos ou inválidos.')
        with connect() as con:
            cached=con.execute('SELECT payload,result FROM forecasts WHERE id=?',(rid,)).fetchone()
        if cached:
            if cached['payload']!=payload:raise HTTPException(409,'request_id já usado com outro conteúdo.')
            return json.loads(cached['result'])
        result=forecast(body)
        if result['status']!='ok':raise HTTPException(503 if result['error_code']=='model_unavailable' else 422,detail=result)
        with connect() as con:
            con.execute('BEGIN IMMEDIATE')
            cached=con.execute('SELECT payload,result FROM forecasts WHERE id=?',(rid,)).fetchone()
            if cached:
                if cached['payload']!=payload:raise HTTPException(409,'request_id já usado com outro conteúdo.')
                return json.loads(cached['result'])
            con.execute('INSERT INTO forecasts VALUES (?,?,?)',(rid,payload,json.dumps(result,allow_nan=False)))
        return result

    def summary():
        rows=history(limit=1,offset=0)
        if not rows:return dict(status='no_reading',message='Ainda não há previsão. Use Gerar previsão no cartão de energia histórica.')
        r=rows[0]
        return dict(status='answered',message=f"Na demonstração histórica, a previsão salva é de {r['prediction_kwh']:.3f} kWh para {r['target_start']} até {r['target_end']} (relógio local do dataset). Não é o consumo atual da casa simulada.",forecast=r)
    return summary
