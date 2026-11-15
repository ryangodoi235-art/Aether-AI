"""Local household goals and explicitly fictional energy sandbox."""
import json
from pathlib import Path
from fastapi import HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal

class Profile(BaseModel):
    model_config = ConfigDict(extra='forbid')
    residence_type: Literal['house', 'apartment'] = 'house'
    residents: int = Field(strict=True, ge=1, le=100)
    monthly_bill: float = Field(gt=0, le=100000, allow_inf_nan=False)
    reduction_percent: int = Field(strict=True, ge=1, le=80)
    appliances: list[Literal['shower','ac','lights','fridge','washer','tv','stove','microwave','fan']] = Field(max_length=9)
    monthly_kwh: float | None = Field(default=None, gt=0, le=100000, allow_inf_nan=False)

TIPS = {
 'shower': ('Banhos', 'Combine com os moradores uma redução gradual no tempo de banho elétrico. Comece registrando a duração atual e teste dois minutos a menos, se for confortável.'),
 'ac': ('Climatização', 'Evite climatizar ambientes vazios e mantenha portas e janelas fechadas durante o uso. Siga a limpeza e manutenção indicadas pelo fabricante.'),
 'lights': ('Iluminação', 'Aproveite a luz natural e apague as luzes de cômodos vazios. Observe quais ficam acesas sem necessidade.'),
 'fridge': ('Geladeira', 'Verifique a vedação da porta e evite abri-la repetidamente. Mantenha a ventilação indicada pelo fabricante; não desligue a geladeira para economizar.'),
 'washer': ('Lavanderia', 'Agrupe roupas em cargas compatíveis com a capacidade da máquina e escolha o ciclo adequado.'),
 'tv': ('Televisão', 'Use o temporizador quando costuma adormecer com a televisão ligada e desligue-a quando ninguém estiver assistindo.'),
}

TIPS.update({
 'stove':('Fogão elétrico','Planeje o preparo das refeições e utilize panelas compatíveis com o aparelho. O fogão do exemplo é elétrico; fogão a gás não entra neste cálculo.'),
 'microwave':('Micro-ondas','Use somente o tempo necessário e recipientes adequados, conforme as instruções do aparelho.'),
 'fan':('Ventilador','Desligue o ventilador quando o ambiente estiver vazio e faça a manutenção recomendada pelo fabricante.')
})

def plan(p):
    saving = round(p.monthly_bill * p.reduction_percent / 100, 2)
    tips = [dict(id=k, title=TIPS[k][0], text=TIPS[k][1]) for k in dict.fromkeys(p.appliances)]
    if not tips:
        tips = [dict(id='observe', title='Primeiro, observe', text='Anote por uma semana os aparelhos utilizados e seus horários. Edite o perfil para receber sugestões mais específicas.')]
    annual_saving = round(saving * 12, 2)
    energy_goal = None if p.monthly_kwh is None else dict(current_kwh=p.monthly_kwh, target_kwh=round(p.monthly_kwh*(1-p.reduction_percent/100), 3), reduction_kwh=round(p.monthly_kwh*p.reduction_percent/100, 3))
    speech_segments = [
        f"Vamos trabalhar com uma meta de reduzir {p.reduction_percent}% da sua conta: cerca de {saving:.2f} reais por mês. Se atingir essa meta todos os meses, seriam {annual_saving:.2f} reais poupados em doze meses. Para os {p.residents} moradores, estas são as sugestões.",
        *[tip['title'] + '. ' + tip['text'] for tip in tips],
        'Isso é uma meta, não uma economia garantida. Acompanhe seus hábitos e compare o consumo nas próximas contas.'
    ]
    return dict(profile=p.model_dump(), target_saving=saving, target_bill=round(p.monthly_bill-saving, 2),
        tips=tips, annual_target_saving=annual_saving, energy_goal=energy_goal, source='user_reported', method='goal_arithmetic_v1',
        answer=' '.join(speech_segments), speech_segments=speech_segments,
        notice='Valores informados pelo morador. A meta não é uma previsão. Tarifas, clima, dias faturados e hábitos podem mudar a conta.')

def setup(api, connect, root):
    from .energy_scene import setup as setup_scene
    add_profile_devices = setup_scene(api, connect)
    with connect() as c:
        c.execute('CREATE TABLE IF NOT EXISTS energy_coach_profile (id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL)')

    @api.get('/energy-home.js', include_in_schema=False)
    def home_script():
        return FileResponse(Path(root)/'frontend/energy_home.js', media_type='application/javascript', headers={'Cache-Control':'no-store'})

    @api.get('/economia', include_in_schema=False)
    def page(request:Request):
        # AETHER_HOME_PLAN_V15
        if request.query_params.get('embed')!='plan':return RedirectResponse('/painel#economy-plan',status_code=307)
        return FileResponse(Path(root)/'frontend/energy_coach.html', headers={'Cache-Control':'no-store'})

    @api.get('/api/v1/energy-coach/profile')
    def get_profile():
        with connect() as c:
            row=c.execute('SELECT payload FROM energy_coach_profile WHERE id=1').fetchone()
        return plan(Profile(**json.loads(row[0]))) if row else {'profile': None}

    @api.put('/api/v1/energy-coach/profile')
    def save_profile(body: Profile):
        with connect() as c:
            c.execute('INSERT OR REPLACE INTO energy_coach_profile VALUES (1,?)', (body.model_dump_json(),))
        add_profile_devices(body.appliances)
        return plan(body)

    @api.delete('/api/v1/energy-coach/profile')
    def delete_profile():
        with connect() as c:
            c.execute('DELETE FROM energy_coach_profile WHERE id=1')
        return {'status':'removed'}
