"""Small trained neural nets. Standard-library inference; no network, pickle or sklearn."""
import json,re,math,unicodedata
from pathlib import Path
from functools import lru_cache
BASE=Path(__file__).parent/'neural_models'
class NeuralError(ValueError):pass
@lru_cache(maxsize=4)
def load(name):
 if name not in {'intent','energy','energy_demo','metrics'}:raise NeuralError('Modelo desconhecido.')
 try:return json.loads((BASE/(name+'.json')).read_text(encoding='utf-8'))
 except (OSError,ValueError):raise NeuralError('Artefato neural local indisponível. Reinstale o pacote v20.') from None

def normalize(text):
 s=''.join(c for c in unicodedata.normalize('NFD',text.lower()) if unicodedata.category(c)!='Mn')
 return re.sub(r'[^a-z0-9]+',' ',s).strip()
def hash32(s):
 n=2166136261
 for c in s:n=((n^ord(c))*16777619)&0xffffffff
 return n

def vector(text,dim):
 out=[0.0]*dim
 for word in normalize(text).split():
  tokens=['w:'+word];bound='^'+word+'$'
  for n in [3,4,5]:tokens.extend(bound[i:i+n] for i in range(len(bound)-n+1))
  for token in tokens:out[hash32(token)%dim]+=1
 length=math.sqrt(sum(v*v for v in out)) or 1
 return [v/length for v in out]

def forward(x,model):
 for layer,(matrix,bias) in enumerate(zip(model['weights'],model['biases'])):
  out=list(bias)
  for i,v in enumerate(x):
   if v:
    for j,w in enumerate(matrix[i]):out[j]+=v*w
  x=[max(0,v) for v in out] if layer<len(model['weights'])-1 else out
 return x

def classify(text):
 if not isinstance(text,str) or not 1<=len(text.strip())<=800:raise NeuralError('Informe 1–800 caracteres.')
 m=load('intent');scores=forward(vector(text,m['feature_dim']),m);maximum=max(scores);p=[math.exp(v-maximum) for v in scores];total=sum(p);p=[v/total for v in p];indices=sorted(range(len(p)),key=lambda i:p[i],reverse=True);i=indices[0]
 return dict(intent=m['classes'][i],score=p[i],margin=p[i]-p[indices[1]],accepted=p[i]>=m['threshold'] and p[i]-p[indices[1]]>=m['margin'],ranking=[{'intent':m['classes'][j],'score':p[j]} for j in indices[:3]],model=m['version'],notice='Pontuação não calibrada. Classificador experimental treinado com frases sintéticas; não é garantia de entendimento.')

def predict_energy(features):
 m=load('energy')
 if not isinstance(features,list) or len(features)!=len(m['features']) or any(type(v) not in (int,float) or not math.isfinite(v) for v in features):raise NeuralError('Informe exatamente as 11 variáveis numéricas finitas do modelo sintético.')
 x=[(v-mean)/std for v,mean,std in zip(features,m['input_mean'],m['input_std'])]
 raw=forward(x,m)[0]*m['target_std']+m['target_mean']
 return dict(prediction_kwh=max(0,raw),raw_prediction_kwh=raw,model=m['version'],source='synthetic_experiment',notice='Previsão de uma hora no experimento sintético; não é consumo medido, previsão validada da residência ou economia garantida.')
