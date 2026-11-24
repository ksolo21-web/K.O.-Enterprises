/* GiftTally by OAKX — calculation, validation and export engine.
 * Pure functions, no DOM, no network. Money is always integer cents. */
(function(root){
 'use strict';

 const VERSION='1.0.0';
 const FORMAT='gifttally-backup';
 const STATUSES=['idea','bought','wrapped','shipped','delivered'];
 const STATUS_LABELS={idea:'Idea',bought:'Bought',wrapped:'Wrapped',shipped:'Shipped',delivered:'Delivered'};
 const GROUPS=['family','friends','work','kids','other'];
 const GROUP_LABELS={family:'Family',friends:'Friends',work:'Work',kids:'Kids',other:'Other'};
 const COST_CATEGORIES=['wrapping','shipping','cards','hosting','decor','travel','other'];
 const COST_LABELS={wrapping:'Wrapping & supplies',shipping:'Shipping & postage',cards:'Cards & stamps',hosting:'Hosting & food',decor:'Decorations',travel:'Travel',other:'Other'};
 const LIMITS={
  people:1000, gifts:10000, costs:500,
  priceCents:100000000,      // $1,000,000 per gift or cost line
  budgetCents:1000000000,    // $10,000,000 budget
  importBytes:5*1024*1024,
  name:60, title:120, store:60, tracking:64, notes:500, label:80
 };

 class InputError extends Error{constructor(msg,field){super(msg);this.name='InputError';this.field=field||null;}}

 function escape(s){
  return String(s??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
 }

 /** Parse a money amount typed by a person (or a JS number) into integer cents.
  *  Accepts "$1,299.99", "USD 24", "24.5", " 3 ". Rejects negatives, more than 2 decimals,
  *  exponents, hex, words, Infinity/NaN and anything above the cap. Blank -> null unless required. */
 function parseMoney(value,label,opts){
  const o=opts||{}; const name=label||'Amount'; const max=o.max||LIMITS.priceCents;
  if(value==null||(typeof value==='string'&&value.trim()==='')){
   if(o.required)throw new InputError(name+' is required.',o.field);
   return null;
  }
  let cents;
  if(typeof value==='number'){
   if(!Number.isFinite(value))throw new InputError(name+' must be a real amount.',o.field);
   if(value<0)throw new InputError(name+" can't be negative.",o.field);
   const scaled=value*100, rounded=Math.round(scaled);
   if(Math.abs(scaled-rounded)>1e-6)throw new InputError(name+' can have at most 2 decimal places.',o.field);
   cents=rounded;
  }else if(typeof value==='string'){
   let t=value.trim().replace(/\u00a0/g,' ');
   if(t.length>32)throw new InputError(name+' is too long to be an amount.',o.field);
   if(/^[-\u2212(]|^\$\s*-|^usd\s*-/i.test(t)||/\)$/.test(t))throw new InputError(name+" can't be negative.",o.field);
   t=t.replace(/^usd\s*/i,'').replace(/\s*usd$/i,'').replace(/^\$\s*/,'');
   if(/^\d{1,3}(,\d{3})+(\.\d*)?$/.test(t))t=t.replace(/,/g,'');
   if(!/^(\d+(\.\d*)?|\.\d+)$/.test(t)){
    throw new InputError(name+' “'+value.trim().slice(0,20)+'” isn\u2019t a valid amount. Use a number like 24.99.',o.field);
   }
   const parts=t.split('.');
   const frac=parts[1]||'';
   if(frac.length>2)throw new InputError(name+' can have at most 2 decimal places.',o.field);
   const whole=parts[0].replace(/^0+(?=\d)/,'')||'0';
   if(whole.length>12)throw new InputError(name+' is too large.',o.field);
   cents=Number(whole)*100+Number((frac+'00').slice(0,2));
  }else{
   throw new InputError(name+' must be a number.',o.field);
  }
  if(!Number.isSafeInteger(cents)||cents>max)throw new InputError(name+' is too large (max '+formatMoney(max)+').',o.field);
  return cents;
 }

 function checkCents(v,label,max,allowNull){
  if(v==null&&allowNull)return null;
  if(typeof v!=='number'||!Number.isSafeInteger(v)||v<0||v>max)throw new InputError(label+' must be a whole number of cents between 0 and '+max+'.');
  return v;
 }

 function formatMoney(cents){
  if(cents==null||!Number.isFinite(cents))return '—';
  const c=Math.round(cents); const neg=c<0; const abs=Math.abs(c);
  const dollars=Math.floor(abs/100).toString().replace(/\B(?=(\d{3})+(?!\d))/g,',');
  return (neg?'-':'')+'$'+dollars+'.'+String(abs%100).padStart(2,'0');
 }
 /** Plain numeric string for CSV: "-12.50", "1234.00" */
 function moneyPlain(cents){
  if(cents==null||!Number.isFinite(cents))return '';
  const c=Math.round(cents); const abs=Math.abs(c);
  return (c<0?'-':'')+Math.floor(abs/100)+'.'+String(abs%100).padStart(2,'0');
 }

 // strip control chars (keep \n in notes), normalise whitespace
 function cleanText(value,max,label,opts){
  const o=opts||{};
  if(value==null)value='';
  if(typeof value==='number'&&Number.isFinite(value))value=String(value);
  if(typeof value!=='string')throw new InputError(label+' must be text.',o.field);
  let t=value.replace(/\r\n?/g,'\n');
  t=o.multiline?t.replace(/[\u0000-\u0009\u000b-\u001f\u007f\u2028\u2029]/g,' ').replace(/\n{3,}/g,'\n\n'):t.replace(/[\u0000-\u001f\u007f\u2028\u2029]/g,' ').replace(/ {2,}/g,' ');
  t=t.trim();
  if(o.required&&!t)throw new InputError(label+' is required.',o.field);
  if(t.length>max)throw new InputError(label+' is too long (max '+max+' characters).',o.field);
  return t;
 }

 function emptyState(){return {app:'GiftTally by OAKX',format:FORMAT,version:1,budgetCents:null,sample:false,seq:0,people:[],gifts:[],costs:[]};}
 function nextId(state,prefix){state.seq=(state.seq||0)+1;return prefix+state.seq.toString(36);}
 function findPerson(state,id){const p=state.people.find(x=>x.id===id);if(!p)throw new InputError('That person no longer exists.');return p;}

 function personFields(input){
  const i=input||{};
  const group=GROUPS.includes(i.group)?i.group:(i.group==null||i.group===''?'family':null);
  if(!group)throw new InputError('Choose a group: '+GROUPS.map(g=>GROUP_LABELS[g]).join(', ')+'.','group');
  return {
   name:cleanText(i.name,LIMITS.name,'Name',{required:true,field:'name'}),
   group,
   budgetCents:'budgetCents' in i?checkCents(i.budgetCents,'Person budget',LIMITS.budgetCents,true):parseMoney(i.budget,'Person budget',{max:LIMITS.budgetCents,field:'budget'}),
   notes:cleanText(i.notes,LIMITS.notes,'Notes',{multiline:true,field:'notes'})
  };
 }
 function giftFields(input){
  const i=input||{};
  const status=i.status==null||i.status===''?'idea':String(i.status);
  if(!STATUSES.includes(status))throw new InputError('Status must be one of: '+STATUSES.map(s=>STATUS_LABELS[s]).join(', ')+'.','status');
  return {
   title:cleanText(i.title,LIMITS.title,'Gift',{required:true,field:'title'}),
   priceCents:'priceCents' in i?checkCents(i.priceCents,'Price',LIMITS.priceCents,true):parseMoney(i.price,'Price',{field:'price'}),
   store:cleanText(i.store,LIMITS.store,'Store',{field:'store'}),
   status,
   tracking:cleanText(i.tracking,LIMITS.tracking,'Tracking number',{field:'tracking'}),
   notes:cleanText(i.notes,LIMITS.notes,'Notes',{multiline:true,field:'notes'})
  };
 }
 function costFields(input){
  const i=input||{};
  const category=i.category==null||i.category===''?'other':String(i.category);
  if(!COST_CATEGORIES.includes(category))throw new InputError('Choose a cost category.','category');
  const amountCents='amountCents' in i?checkCents(i.amountCents,'Amount',LIMITS.priceCents,false):parseMoney(i.amount,'Amount',{required:true,field:'amount'});
  return {category,label:cleanText(i.label,LIMITS.label,'Description',{field:'label'})||COST_LABELS[category],amountCents};
 }

 function setBudget(state,value){
  state.budgetCents=typeof value==='number'&&Number.isInteger(value)?checkCents(value,'Budget',LIMITS.budgetCents,true):parseMoney(value,'Total budget',{max:LIMITS.budgetCents,field:'total-budget'});
  return state.budgetCents;
 }
 function addPerson(state,input,opts){
  const max=Math.min((opts&&opts.maxPeople)||LIMITS.people,LIMITS.people);
  if(state.people.length>=max)throw new InputError(max<LIMITS.people?'The free preview is limited to '+max+' people.':'GiftTally supports up to '+max+' people per plan.');
  const p=Object.assign({id:nextId(state,'p')},personFields(input));
  state.people.push(p);return p;
 }
 function updatePerson(state,id,input){const p=findPerson(state,id);Object.assign(p,personFields(input));return p;}
 function removePerson(state,id){
  findPerson(state,id);
  state.people=state.people.filter(p=>p.id!==id);
  const before=state.gifts.length;state.gifts=state.gifts.filter(g=>g.personId!==id);
  return before-state.gifts.length;
 }
 function addGift(state,personId,input){
  findPerson(state,personId);
  if(state.gifts.length>=LIMITS.gifts)throw new InputError('GiftTally supports up to '+LIMITS.gifts+' gifts per plan.');
  const g=Object.assign({id:nextId(state,'g'),personId},giftFields(input));
  state.gifts.push(g);return g;
 }
 function findGift(state,id){const g=state.gifts.find(x=>x.id===id);if(!g)throw new InputError('That gift no longer exists.');return g;}
 function updateGift(state,id,input){
  const g=findGift(state,id);
  const pid=input&&input.personId!=null?input.personId:g.personId;findPerson(state,pid);
  Object.assign(g,giftFields(input),{personId:pid});return g;
 }
 function setGiftStatus(state,id,status){
  const g=findGift(state,id);
  if(!STATUSES.includes(status))throw new InputError('Unknown status.');
  g.status=status;return g;
 }
 function removeGift(state,id){findGift(state,id);state.gifts=state.gifts.filter(g=>g.id!==id);}
 function addCost(state,input){
  if(state.costs.length>=LIMITS.costs)throw new InputError('GiftTally supports up to '+LIMITS.costs+' other cost lines.');
  const c=Object.assign({id:nextId(state,'c')},costFields(input));state.costs.push(c);return c;
 }
 function updateCost(state,id,input){const c=state.costs.find(x=>x.id===id);if(!c)throw new InputError('That cost no longer exists.');Object.assign(c,costFields(input));return c;}
 function removeCost(state,id){const n=state.costs.length;state.costs=state.costs.filter(c=>c.id!==id);if(state.costs.length===n)throw new InputError('That cost no longer exists.');}

 const isSpent=g=>g.status!=='idea';
 const COLLATOR=new Intl.Collator('en',{sensitivity:'base',numeric:true});
 const cmp=(a,b)=>COLLATOR.compare(String(a),String(b));

 /** Totals, per-person rollups, warnings. O(people + gifts + costs). */
 function summarize(state){
  const byPerson=new Map();
  for(const p of state.people)byPerson.set(p.id,{person:p,spentCents:0,plannedCents:0,giftCount:0,ideaCount:0,doneCount:0,unpricedSpent:0,unpricedIdeas:0});
  const statusCounts={idea:0,bought:0,wrapped:0,shipped:0,delivered:0};
  let giftSpent=0,planned=0,unpricedSpent=0;
  for(const g of state.gifts){
   const r=byPerson.get(g.personId);if(!r)continue;
   statusCounts[g.status]++;r.giftCount++;
   if(isSpent(g)){r.doneCount++;if(g.priceCents==null){r.unpricedSpent++;unpricedSpent++;}else{r.spentCents+=g.priceCents;giftSpent+=g.priceCents;}}
   else{r.ideaCount++;if(g.priceCents==null)r.unpricedIdeas++;else{r.plannedCents+=g.priceCents;planned+=g.priceCents;}}
  }
  let costs=0;const costByCat={};for(const c of state.costs){costs+=c.amountCents;costByCat[c.category]=(costByCat[c.category]||0)+c.amountCents;}
  const people=[];let allocated=0,overCount=0;
  for(const r of byPerson.values()){
   const b=r.person.budgetCents;if(b!=null)allocated+=b;
   r.budgetCents=b;r.remainingCents=b==null?null:b-r.spentCents;
   r.projectedCents=r.spentCents+r.plannedCents;
   r.over=b!=null&&r.spentCents>b;r.projectedOver=b!=null&&!r.over&&r.projectedCents>b;
   r.needsGift=r.doneCount===0;
   r.ratio=b==null?null:(b===0?(r.spentCents>0?Infinity:0):r.spentCents/b);
   if(r.over)overCount++;
   people.push(r);
  }
  const spent=giftSpent+costs, budget=state.budgetCents;
  const needs=people.filter(r=>r.needsGift).sort((a,b)=>cmp(a.person.name,b.person.name));
  const warnings=[];
  if(budget!=null&&spent>budget)warnings.push({level:'bad',code:'over',text:'You are '+formatMoney(spent-budget)+' over your total budget.'});
  else if(budget!=null&&spent+planned>budget)warnings.push({level:'warn',code:'projected',text:'If you buy every priced idea, you\u2019ll be '+formatMoney(spent+planned-budget)+' over budget.'});
  if(budget!=null&&allocated+costs>budget)warnings.push({level:'warn',code:'allocated',text:'Per-person budgets ('+formatMoney(allocated)+') plus other costs ('+formatMoney(costs)+') add up to more than your total budget.'});
  if(overCount)warnings.push({level:'bad',code:'people-over',text:overCount+(overCount===1?' person is':' people are')+' over their gift budget.'});
  if(unpricedSpent)warnings.push({level:'info',code:'unpriced',text:unpricedSpent+(unpricedSpent===1?' bought gift has':' bought gifts have')+' no price yet, so totals may be low.'});
  if(budget==null&&(state.people.length||state.costs.length))warnings.push({level:'info',code:'no-budget',text:'Set a total holiday budget to see what\u2019s left.'});
  return {
   budgetCents:budget, giftSpentCents:giftSpent, costsCents:costs, spentCents:spent, plannedCents:planned,
   projectedCents:spent+planned, remainingCents:budget==null?null:budget-spent,
   ratio:budget==null?null:(budget===0?(spent>0?Infinity:0):spent/budget),
   allocatedCents:allocated, costByCategory:costByCat, statusCounts,
   peopleCount:state.people.length, giftCount:state.gifts.length, people, needsGift:needs, overCount, unpricedSpent, warnings
  };
 }

 /** Ideas still to buy, grouped by store (A–Z, “No store yet” last), then person, then gift. */
 function shoppingList(state){
  const names=new Map(state.people.map(p=>[p.id,p]));
  const groups=new Map();
  for(const g of state.gifts){
   if(g.status!=='idea')continue;const p=names.get(g.personId);if(!p)continue;
   const key=g.store?g.store.toLocaleLowerCase('en'):'';
   if(!groups.has(key))groups.set(key,{store:g.store||'',items:[],totalCents:0,unpriced:0});
   const grp=groups.get(key);grp.items.push({gift:g,person:p});
   if(g.priceCents==null)grp.unpriced++;else grp.totalCents+=g.priceCents;
  }
  const list=[...groups.values()];
  for(const grp of list)grp.items.sort((a,b)=>cmp(a.person.name,b.person.name)||cmp(a.gift.title,b.gift.title)||(a.gift.id<b.gift.id?-1:1));
  list.sort((a,b)=>(a.store===''?1:0)-(b.store===''?1:0)||cmp(a.store,b.store));
  return list;
 }

 function csvCell(s){
  let t=String(s??'');
  const plainNumber=/^-?\d+(\.\d+)?$/.test(t);
  if(!plainNumber&&(/^[=+\-@\t\r|%]/.test(t)||/^\s+[=+\-@]/.test(t)))t="'"+t;
  if(/[",\r\n]/.test(t))t='"'+t.replace(/"/g,'""')+'"';
  return t;
 }
 function csvRow(cells){return cells.map(csvCell).join(',');}

 function toCSV(state){
  const s=summarize(state);const names=new Map(state.people.map(p=>[p.id,p]));
  const L=[];
  L.push(csvRow(['GiftTally by OAKX — holiday gift summary']));
  L.push(csvRow(['Total budget',moneyPlain(s.budgetCents)]));
  L.push(csvRow(['Gifts bought',moneyPlain(s.giftSpentCents)]));
  L.push(csvRow(['Other holiday costs',moneyPlain(s.costsCents)]));
  L.push(csvRow(['Total spent',moneyPlain(s.spentCents)]));
  L.push(csvRow(['Remaining',moneyPlain(s.remainingCents)]));
  L.push(csvRow(['Still planned (priced ideas)',moneyPlain(s.plannedCents)]));
  L.push('');
  L.push(csvRow(['Person','Group','Gift','Store','Status','Price (USD)','Tracking','Notes']));
  const sorted=state.gifts.filter(g=>names.has(g.personId)).slice().sort((a,b)=>cmp(names.get(a.personId).name,names.get(b.personId).name)||STATUSES.indexOf(a.status)-STATUSES.indexOf(b.status)||cmp(a.title,b.title));
  for(const g of sorted){const p=names.get(g.personId);L.push(csvRow([p.name,GROUP_LABELS[p.group],g.title,g.store,STATUS_LABELS[g.status],moneyPlain(g.priceCents),g.tracking,g.notes]));}
  L.push('');
  L.push(csvRow(['Person','Group','Budget (USD)','Spent (USD)','Planned ideas (USD)','Remaining (USD)','Status']));
  for(const r of s.people.slice().sort((a,b)=>cmp(a.person.name,b.person.name)))L.push(csvRow([r.person.name,GROUP_LABELS[r.person.group],moneyPlain(r.budgetCents),moneyPlain(r.spentCents),moneyPlain(r.plannedCents),moneyPlain(r.remainingCents),r.over?'Over budget':r.needsGift?'Needs a gift':'On track']));
  L.push('');
  L.push(csvRow(['Other cost','Category','Amount (USD)']));
  for(const c of state.costs)L.push(csvRow([c.label,COST_LABELS[c.category],moneyPlain(c.amountCents)]));
  return '\uFEFF'+L.join('\r\n')+'\r\n';
 }

 // Report stylesheet is whitelisted by hash in the report's CSP (no 'unsafe-inline', no scripts).
 const REPORT_CSS='body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;color:#1f2a27;background:#faf9f6;margin:0;line-height:1.5}main{max-width:960px;margin:auto;padding:32px 24px}header{display:flex;justify-content:space-between;align-items:flex-end;gap:16px;border-bottom:2px solid #0f241f;padding-bottom:14px;margin-bottom:22px}.brand{font-weight:800;font-size:1.3rem;color:#0f241f;letter-spacing:-.02em}.brand small{display:block;font-weight:600;font-size:.75rem;color:#8a6220;letter-spacing:.12em;text-transform:uppercase}.meta{font-size:.8rem;color:#64748b;text-align:right}.tag{display:inline-block;font-size:.7rem;font-weight:700;letter-spacing:.08em;background:#f5ebd8;color:#8a6220;border-radius:4px;padding:3px 7px}h1{font-size:1.6rem;color:#0f241f;margin:0 0 6px}h2{font-size:1.1rem;color:#0f241f;margin:28px 0 10px}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}.stat{background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:12px 14px}.stat span{display:block;font-size:.75rem;color:#64748b;font-weight:600}.stat strong{font-size:1.25rem;color:#0f241f}.stat.bad strong,.bad{color:#b91c1c}.good{color:#15803d}table{width:100%;border-collapse:collapse;background:#fff;border:1px solid #e5e7eb;font-size:.85rem}th{text-align:left;background:#f3f1eb;color:#475569;font-size:.72rem;text-transform:uppercase;letter-spacing:.05em;padding:8px 10px}td{padding:8px 10px;border-top:1px solid #eeece6;vertical-align:top}td.num,th.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}.person{font-weight:700;color:#0f241f}.warn{background:#fbeaea;border:1px solid #f3c4c4;color:#7f1d1d;border-radius:8px;padding:10px 12px;margin:6px 0;font-size:.85rem}.warn.warn-info,.warn.warn-warn{background:#f5ebd8;border-color:#ebdcbf;color:#6b4a14}ul.needs{columns:2;padding-left:18px}footer{margin-top:30px;font-size:.75rem;color:#64748b}@media print{body{background:#fff}main{padding:0}.stat,table{break-inside:avoid}tr{break-inside:avoid}}@media(max-width:640px){.stats{grid-template-columns:1fr 1fr}ul.needs{columns:1}}';
 const REPORT_CSS_HASH='sha256-joeUY605TSbVcMI5TruGbNAcjTa3Mz/Z3MourrCrVrY=';

 function summaryHTML(state,meta){
  const m=meta||{};const s=summarize(state);const names=new Map(state.people.map(p=>[p.id,p]));
  const e=escape;const money=c=>e(formatMoney(c));
  const stat=(label,val,cls)=>'<div class="stat'+(cls?' '+cls:'')+'"><span>'+e(label)+'</span><strong>'+val+'</strong></div>';
  let h='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'+
   '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \''+REPORT_CSS_HASH+'\'; base-uri \'none\'; form-action \'none\'">'+
   '<title>GiftTally by OAKX — Holiday gift summary</title><style>'+REPORT_CSS+'</style></head><body><main>'+
   '<header><div class="brand"><small>OAKX</small>GiftTally</div><div class="meta">'+(state.sample?'<span class="tag">SAMPLE DATA</span><br>':'')+(m.generated?e(m.generated):'')+'</div></header>'+
   '<h1>Holiday gift summary</h1>'+
   '<div class="stats">'+stat('Total budget',money(s.budgetCents))+stat('Spent so far',money(s.spentCents),s.remainingCents!=null&&s.remainingCents<0?'bad':'')+stat('Remaining',money(s.remainingCents),s.remainingCents!=null&&s.remainingCents<0?'bad':'')+stat('Still planned',money(s.plannedCents))+'</div>';
  for(const w of s.warnings)h+='<div class="warn warn-'+e(w.level)+'">'+e(w.text)+'</div>';
  h+='<h2>People</h2><table><thead><tr><th>Person</th><th>Group</th><th class="num">Budget</th><th class="num">Spent</th><th class="num">Planned</th><th class="num">Remaining</th><th>Status</th></tr></thead><tbody>';
  for(const r of s.people.slice().sort((a,b)=>cmp(a.person.name,b.person.name)))h+='<tr><td class="person">'+e(r.person.name)+'</td><td>'+e(GROUP_LABELS[r.person.group])+'</td><td class="num">'+money(r.budgetCents)+'</td><td class="num">'+money(r.spentCents)+'</td><td class="num">'+money(r.plannedCents)+'</td><td class="num'+(r.remainingCents!=null&&r.remainingCents<0?' bad':'')+'">'+money(r.remainingCents)+'</td><td>'+e(r.over?'Over budget':r.needsGift?'Needs a gift':'On track')+'</td></tr>';
  if(!s.people.length)h+='<tr><td colspan="7">No people yet.</td></tr>';
  h+='</tbody></table>';
  if(s.needsGift.length){h+='<h2>Still needs a gift ('+s.needsGift.length+')</h2><ul class="needs">'+s.needsGift.map(r=>'<li>'+e(r.person.name)+'</li>').join('')+'</ul>';}
  h+='<h2>Gifts</h2><table><thead><tr><th>Person</th><th>Gift</th><th>Store</th><th>Status</th><th class="num">Price</th><th>Tracking / notes</th></tr></thead><tbody>';
  const gifts=state.gifts.filter(g=>names.has(g.personId)).slice().sort((a,b)=>cmp(names.get(a.personId).name,names.get(b.personId).name)||STATUSES.indexOf(a.status)-STATUSES.indexOf(b.status)||cmp(a.title,b.title));
  for(const g of gifts)h+='<tr><td class="person">'+e(names.get(g.personId).name)+'</td><td>'+e(g.title)+'</td><td>'+e(g.store)+'</td><td>'+e(STATUS_LABELS[g.status])+'</td><td class="num">'+money(g.priceCents)+'</td><td>'+e([g.tracking,g.notes].filter(Boolean).join(' · '))+'</td></tr>';
  if(!gifts.length)h+='<tr><td colspan="6">No gifts yet.</td></tr>';
  h+='</tbody></table><h2>Other holiday costs</h2><table><thead><tr><th>Description</th><th>Category</th><th class="num">Amount</th></tr></thead><tbody>';
  for(const c of state.costs)h+='<tr><td>'+e(c.label)+'</td><td>'+e(COST_LABELS[c.category])+'</td><td class="num">'+money(c.amountCents)+'</td></tr>';
  if(!state.costs.length)h+='<tr><td colspan="3">No other costs yet.</td></tr>';
  h+='</tbody></table><footer>GiftTally by OAKX · Made on your device. Your gift list never leaves your computer.</footer></main></body></html>';
  return h;
 }

 function toBackup(state,exportedAt){
  const out={app:'GiftTally by OAKX',format:FORMAT,version:1,exportedAt:exportedAt||new Date().toISOString(),budgetCents:state.budgetCents,
   people:state.people.map(p=>({id:p.id,name:p.name,group:p.group,budgetCents:p.budgetCents,notes:p.notes})),
   gifts:state.gifts.map(g=>({id:g.id,personId:g.personId,title:g.title,priceCents:g.priceCents,store:g.store,status:g.status,tracking:g.tracking,notes:g.notes})),
   costs:state.costs.map(c=>({id:c.id,category:c.category,label:c.label,amountCents:c.amountCents}))};
  return JSON.stringify(out,null,1);
 }

 const isObj=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
 /** Validate any raw object (backup file or saved data) into a clean state. Throws InputError with a clear message.
  *  IDs are reassigned so nothing from the file is trusted as a key. */
 function normalizeState(raw,opts){
  const o=opts||{};
  if(!isObj(raw))throw new InputError('This file isn\u2019t a GiftTally backup (expected a JSON object).');
  if(raw.format!==FORMAT)throw new InputError('This file isn\u2019t a GiftTally backup (missing the gifttally-backup format tag).');
  if(raw.version!==1)throw new InputError('This backup was made by a newer or unknown version of GiftTally.');
  for(const k of ['people','gifts','costs'])if(raw[k]!=null&&!Array.isArray(raw[k]))throw new InputError('Backup field “'+k+'” must be a list.');
  const people=raw.people||[],gifts=raw.gifts||[],costs=raw.costs||[];
  const maxPeople=Math.min(o.maxPeople||LIMITS.people,LIMITS.people);
  if(people.length>maxPeople)throw new InputError(maxPeople<LIMITS.people?'This backup has '+people.length+' people. The free preview is limited to '+maxPeople+'.':'This backup has '+people.length+' people (max '+LIMITS.people+').');
  if(gifts.length>LIMITS.gifts)throw new InputError('This backup has '+gifts.length+' gifts (max '+LIMITS.gifts+').');
  if(costs.length>LIMITS.costs)throw new InputError('This backup has '+costs.length+' other costs (max '+LIMITS.costs+').');
  const st=emptyState();
  const where=(kind,i,e)=>{throw new InputError(kind+' '+(i+1)+': '+e.message);};
  try{st.budgetCents=checkCents(raw.budgetCents==null?null:raw.budgetCents,'Total budget',LIMITS.budgetCents,true);}catch(e){throw new InputError('Total budget: '+e.message);}
  const idMap=new Map();
  people.forEach((p,i)=>{
   if(!isObj(p))where('Person',i,new Error('must be an object.'));
   let f;try{f=personFields({name:p.name,group:p.group,budgetCents:p.budgetCents==null?null:p.budgetCents,notes:p.notes});}catch(e){where('Person',i,e);}
   const key=p.id==null?null:String(p.id);
   if(key==null||idMap.has(key))where('Person',i,new Error('has a missing or duplicate id.'));
   const id=nextId(st,'p');idMap.set(key,id);st.people.push(Object.assign({id},f));
  });
  gifts.forEach((g,i)=>{
   if(!isObj(g))where('Gift',i,new Error('must be an object.'));
   const pid=idMap.get(g.personId==null?null:String(g.personId));
   if(!pid)where('Gift',i,new Error('belongs to a person who isn\u2019t in this backup.'));
   let f;try{f=giftFields({title:g.title,priceCents:g.priceCents==null?null:g.priceCents,store:g.store,status:g.status,tracking:g.tracking,notes:g.notes});}catch(e){where('Gift',i,e);}
   st.gifts.push(Object.assign({id:nextId(st,'g'),personId:pid},f));
  });
  costs.forEach((c,i)=>{
   if(!isObj(c))where('Other cost',i,new Error('must be an object.'));
   let f;try{f=costFields({category:c.category,label:c.label,amountCents:c.amountCents});}catch(e){where('Other cost',i,e);}
   st.costs.push(Object.assign({id:nextId(st,'c')},f));
  });
  st.sample=!!raw.sample&&!!o.keepSample;
  return st;
 }
 function parseBackup(text,opts){
  if(typeof text!=='string')throw new InputError('Could not read that file.');
  if(text.length>LIMITS.importBytes)throw new InputError('That file is too large to be a GiftTally backup (max 5 MB).');
  let raw;try{raw=JSON.parse(text.replace(/^\uFEFF/,''));}catch(e){throw new InputError('That file isn\u2019t valid JSON. Choose a backup saved from GiftTally (gifttally-backup-….json).');}
  return normalizeState(raw,opts);
 }
 /** Internal storage form (same shape as backup, plus sample flag). */
 function toStorage(state){const o=JSON.parse(toBackup(state,''));o.sample=!!state.sample;return JSON.stringify(o);}
 function fromStorage(text,opts){const raw=JSON.parse(text);return normalizeState(raw,Object.assign({},opts,{keepSample:true}));}

 function sampleState(){
  const s=emptyState();
  setBudget(s,'600');
  const mom=addPerson(s,{name:'Mom',group:'family',budget:'150',notes:'Loves cozy things and family photos.'});
  const jordan=addPerson(s,{name:'Jordan',group:'friends',budget:'60'});
  const alex=addPerson(s,{name:'Alex (Secret Santa)',group:'work',budget:'25',notes:'Office exchange limit is $25.'});
  addGift(s,mom.id,{title:'Cashmere scarf',price:'68.00',store:'Nordstrom',status:'bought'});
  addGift(s,mom.id,{title:'2026 family photo book',price:'34.99',store:'Shutterfly',status:'shipped',tracking:'1Z999AA10123456784',notes:'Should arrive by Dec 12.'});
  addGift(s,mom.id,{title:'Spa day gift card',price:'60',store:'Local spa',status:'idea'});
  addGift(s,jordan.id,{title:'Pickleball paddle set',price:'49.99',store:'Target',status:'idea'});
  addGift(s,jordan.id,{title:'Coffee subscription (3 months)',store:'',status:'idea',notes:'Check prices on Black Friday.'});
  addGift(s,alex.id,{title:'Desk plant with ceramic pot',price:'22.50',store:'Home Depot',status:'wrapped'});
  addCost(s,{category:'wrapping',label:'Wrapping paper, tape & bows',amount:'18.75'});
  addCost(s,{category:'shipping',label:'Shipping gifts to Grandma',amount:'24.10'});
  addCost(s,{category:'cards',label:'Holiday cards (50) + stamps',amount:'32.00'});
  addCost(s,{category:'hosting',label:'Christmas dinner groceries',amount:'140'});
  s.sample=true;
  return s;
 }

 const api={compare:cmp,VERSION,FORMAT,STATUSES,STATUS_LABELS,GROUPS,GROUP_LABELS,COST_CATEGORIES,COST_LABELS,LIMITS,InputError,
  escape,parseMoney,formatMoney,moneyPlain,cleanText,emptyState,sampleState,setBudget,addPerson,updatePerson,removePerson,
  addGift,updateGift,setGiftStatus,removeGift,addCost,updateCost,removeCost,summarize,shoppingList,csvCell,toCSV,summaryHTML,
  REPORT_CSS,REPORT_CSS_HASH,toBackup,normalizeState,parseBackup,toStorage,fromStorage};
 if(typeof module==='object'&&module.exports)module.exports=api;
 root.GiftTally=api;
})(typeof window!=='undefined'?window:globalThis);
