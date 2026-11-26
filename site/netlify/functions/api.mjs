import {access,authenticated,configured,sameOrigin} from '../lib/access.mjs';
import {projects} from '../lib/projects.mjs';
// Same-origin gateway. Backend secret remains in the Netlify function environment.
export const config = { path: '/api/*' };
const error = (status, detail) => Response.json({detail}, {status, headers:{'Cache-Control':'no-store'}});

export default async function handler(request) {
  const incoming = new URL(request.url);
  if(incoming.pathname==='/api/session')return access(request);
  if(!configured())return error(503,'Acesso de testes não configurado.');
  if(!authenticated(request))return error(401,'Entre para acessar a casa de testes.');
  if(request.method!=='GET'&&!sameOrigin(request))return error(403,'Origem não permitida.');
  if(incoming.pathname==='/api/v1/cloud/projects'||incoming.pathname.startsWith('/api/v1/cloud/projects/'))return projects(request);
  if (!incoming.pathname.startsWith('/api/v1/')) return error(404,'Rota não encontrada.');
  if (!['GET','POST','PUT','DELETE'].includes(request.method)) return error(405,'Método não permitido.');
  const base = process.env.AETHER_API_URL;
  const token = process.env.AETHER_API_TOKEN;
  if (!base || !token) return error(503,'Backend não configurado. Defina AETHER_API_URL e AETHER_API_TOKEN no Netlify e publique novamente.');
  let url;
  try {
    url = new URL(base);
    if (url.protocol !== 'https:' || url.username || url.password || url.search || url.hash || !['','/'].includes(url.pathname)) throw Error();
    // Never accept a backend URL from the client.
    url.pathname = incoming.pathname;url.search = incoming.search;
  } catch { return error(503,'Endereço do backend inválido. Configure uma origem HTTPS sem caminho.'); }
  try {
    const headers = {'X-Aether-Token':token};
    const contentType = request.headers.get('content-type');
    if (contentType) headers['Content-Type'] = contentType;
    const raw = ['GET','HEAD'].includes(request.method) ? undefined : await request.arrayBuffer();
    // Gateway limit is intentionally below platform payload limits.
    if (raw && raw.byteLength > 3_000_000) return error(413,'Arquivo muito grande para o teste online. Grave um áudio mais curto.');
    const result = await fetch(url, {method:request.method, headers, body:raw,
      redirect:'error', signal:AbortSignal.timeout(50000)});
    const data = await result.arrayBuffer();
    if (data.byteLength > 3_000_000) return error(502,'Resposta muito grande para o teste online. Solicite uma resposta mais curta.');
    return new Response([204,205,304].includes(result.status) ? null : data, {status:result.status, headers:{
      'Content-Type': result.headers.get('content-type') || 'application/json',
      'Cache-Control':'no-store'
    }});
  } catch {
    return error(502,'Backend indisponível ou resposta acima de 50 segundos. Confira o serviço Python. Se era um comando, consulte o estado antes de repetir.');
  }
}

