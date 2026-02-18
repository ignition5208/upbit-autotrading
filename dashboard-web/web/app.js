const API = "http://127.0.0.1:8000";

async function apiGet(path){
  const r = await fetch(API + path);
  if(!r.ok) throw new Error(await r.text());
  return await r.json();
}
async function apiPost(path, body){
  const r = await fetch(API + path, {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify(body || {})
  });
  const txt = await r.text();
  if(!r.ok) throw new Error(txt);
  return txt ? JSON.parse(txt) : {};
}
async function apiDelete(path){
  const r = await fetch(API + path, { method: "DELETE" });
  const txt = await r.text();
  if(!r.ok) throw new Error(txt);
  return txt ? JSON.parse(txt) : {};
}
function qs(k){
  return new URLSearchParams(location.search).get(k);
}
