"""Adaptador de contrato; não registra uma rota HTTP no Aether ainda."""
import math,time
from datetime import datetime,timedelta,timezone
from .inference import predict_next_hour,ModelUnavailableError

def forecast(request):
    request_id=request.get('request_id') if isinstance(request,dict) else None
    start=time.perf_counter()
    try:
        expected={'schema_version','request_id','dataset_id','time_basis','as_of','history'}
        if not isinstance(request,dict) or set(request)!=expected:raise ValueError('Envelope inválido.')
        if request['schema_version']!='1.0' or request['time_basis']!='dataset_local_naive':raise ValueError('Versão/base temporal não suportada.')
        for name in ['request_id','dataset_id']:
            if not isinstance(request[name],str) or not request[name].strip():raise ValueError(f'{name} obrigatório.')
        def stamp(value):
            if not isinstance(value,str):raise ValueError('Timestamp deve ser texto ISO.')
            dt=datetime.fromisoformat(value)
            if dt.tzinfo is not None or dt.minute or dt.second or dt.microsecond:raise ValueError('Use horas inteiras locais sem offset neste dataset.')
            return dt
        end=stamp(request['as_of']);history=request['history']
        if not isinstance(history,list) or len(history)!=25:raise ValueError('São necessárias exatamente 25 horas consecutivas, de t-24 até t.')
        vals=[]
        for i,item in enumerate(history):
            if not isinstance(item,dict) or set(item)!={'interval_start','interval_end','energy_kwh'}:raise ValueError('Registro de histórico inválido.')
            a=stamp(item['interval_start']);b=stamp(item['interval_end'])
            if a!=end-timedelta(hours=25-i) or b!=a+timedelta(hours=1):raise ValueError('Histórico fora de ordem, com lacunas ou além do corte.')
            v=item['energy_kwh']
            if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0:raise ValueError('Energia deve ser finita, não negativa e em kWh.')
            vals.append(v)
        t=end-timedelta(hours=1)
        result=predict_next_hour(dict(energy_kwh_t=vals[-1],energy_kwh_t_minus_1=vals[-2],energy_kwh_t_minus_24=vals[0],mean_kwh_last_24h=sum(vals[-24:])/24,hour_of_day=t.hour,day_of_week=t.weekday()))
        return dict(request_id=request_id,status='ok',target_start=end.isoformat(),target_end=(end+timedelta(hours=1)).isoformat(),prediction_kwh=result['predicted_next_hour_kwh'],model_version=result['model_version'],data_origin='historical_dataset',dataset_id=request['dataset_id'],time_basis=request['time_basis'],generated_at=datetime.now(timezone.utc).isoformat(),latency_ms=round((time.perf_counter()-start)*1000,3),clipped_to_zero=result['clipped_to_zero'])
    except (ValueError,TypeError,KeyError,OverflowError) as e:return dict(request_id=request_id,status='error',error_code='invalid_input',message=str(e))
    except ModelUnavailableError as e:return dict(request_id=request_id,status='error',error_code='model_unavailable',message=str(e))
