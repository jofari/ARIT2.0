// Verification du rapport genere, SANS navigateur : le script de la page est execute
// contre un DOM minimal qui leve des qu'un attribut vaut NaN/undefined ou qu'un innerHTML
// contient "undefined"/"NaN". C'est ce test qui a attrape la cloture forcee hors plage de
// donnees (trade #12 clos le 2026-07-13 alors que la macro s'arrete au 12/07).
//
//   node research/_reporting/check_report.js research/macro_flip/RAPPORT_TRADES.html

const fs = require('fs');

const file = process.argv[2];
if (!file) { console.error('usage: node check_report.js <rapport.html>'); process.exit(2); }
const html = fs.readFileSync(file, 'utf8');

const payload = html.split('<script id="payload" type="application/json">')[1].split('</scr' + 'ipt>')[0];
const script = html.split('<script>').pop().replace(/<\/scr[i]pt>[\s\S]*$/, '');

class Node {
  constructor(tag) { this.tag = tag; this.attrs = {}; this.children = []; this.style = {};
    this._t = ''; this._h = ''; this.classList = { add() {} }; }
  setAttribute(k, v) {
    if (v === undefined || (typeof v === 'number' && !isFinite(v)))
      throw new Error(`attribut invalide ${this.tag}.${k} = ${v}`);
    this.attrs[k] = v;
  }
  appendChild(c) { this.children.push(c); return c; }
  querySelector() { return new Node('div'); }
  set textContent(v) { this._t = String(v); } get textContent() { return this._t; }
  set innerHTML(v) {
    if (/undefined|NaN/.test(v)) throw new Error('innerHTML pollue : ' + String(v).slice(0, 180));
    this._h = String(v);
  }
  get innerHTML() { return this._h; }
}

const store = {};
global.document = {
  createElementNS: (_, t) => new Node(t),
  createElement: t => new Node(t),
  getElementById: id => (store[id] = store[id] || new Node('div')),
};
store['payload'] = new Node('script');
Object.defineProperty(store['payload'], 'textContent', { get: () => payload });

eval(script);

// Toute coordonnee doit rester dans le cadre : un graphe qui deborde ne se voit pas
// sur un compte de noeuds, seulement a l'oeil — et on n'a pas de navigateur ici.
const COORDS = ['x', 'y', 'cx', 'cy', 'x1', 'x2', 'y1', 'y2', 'width', 'height'];
function coords(n, out = []) {
  COORDS.forEach(k => { if (n.attrs[k] !== undefined && n.attrs[k] !== '') out.push([n.tag + '.' + k, Number(n.attrs[k])]); });
  if (n.attrs.d) (String(n.attrs.d).match(/-?\d+\.?\d*/g) || []).forEach(v => out.push([n.tag + '.d', Number(v)]));
  n.children.forEach(c => coords(c, out));
  return out;
}
for (const id of ['overview', 'equity', 'fiches']) {
  const hors = coords(store[id]).filter(([, v]) => !isFinite(v) || v < -80 || v > 1200);
  if (hors.length) throw new Error(`${id} : ${hors.length} coordonnee(s) hors cadre, ex. ${hors[0]}`);
}

const nodes = n => 1 + n.children.reduce((a, c) => a + nodes(c), 0);
const nbFiches = store['fiches'].children.length;
const nbChips = store['index-grid'].children.length;
const attendu = JSON.parse(payload).trades.length;

if (nbFiches !== attendu || nbChips !== attendu)
  throw new Error(`incoherent : ${attendu} trades, ${nbFiches} fiches, ${nbChips} entrees d'index`);
if (nodes(store['overview']) < 50) throw new Error("vue d'ensemble quasi vide");

console.log(`OK — ${nbFiches} fiches, ${nbChips} entrees d'index, ${nodes(store['overview'])} noeuds dans la vue d'ensemble`);
