/* GiftTally by OAKX — UI. Builds every node with textContent; never injects user text as HTML. */
(function(){
 'use strict';
 const EDITION={preview:true,maxPeople:3,buyUrl:'https://buy.stripe.com/4gMfZhgdY9hN7df83n3Je02'}; // build step rewrites this line for the free preview
 const E=window.GiftTally,$=id=>document.getElementById(id);
 const STORE_KEY=EDITION.preview?'oakx-gifttally-preview-v1':'oakx-gifttally-v1';
 const PAGE={people:20,shopping:25,summary:100,needs:12};
 const opts=EDITION.preview?{maxPeople:EDITION.maxPeople}:{};
 let state,undoSnapshot=null,toastTimer=null,tab='people';
 let limits={people:PAGE.people,shopping:PAGE.shopping,summary:PAGE.summary};
 let editing={person:null,gift:null,cost:null};
 let storageOK=true,pinned=null; // newly added person shown first without rendering every card

 // ---------- tiny DOM helper ----------
 function h(tag,attrs,...kids){
  const el=document.createElement(tag);
  if(attrs)for(const k in attrs){const v=attrs[k];if(v==null||v===false)continue;
   if(k==='class')el.className=v;else if(k==='text')el.textContent=v;else if(k==='dataset')Object.assign(el.dataset,v);else el.setAttribute(k,v===true?'':String(v));}
  for(const kid of kids.flat()){if(kid==null||kid===false)continue;el.append(kid instanceof Node?kid:document.createTextNode(String(kid)));}
  return el;
 }
 const money=E.formatMoney;
 const pctOf=r=>r==null?'':r===Infinity?'over':Math.round(r*100)+'%';

 // ---------- persistence ----------
 function save(){
  try{localStorage.setItem(STORE_KEY,E.toStorage(state));storageOK=true;setSaveState('Saved on this device','ok');}
  catch(err){storageOK=false;setSaveState('Not saved — use Save backup','bad');}
 }
 function setSaveState(text,cls){const el=$('save-state');el.textContent=text;el.className='save-state '+cls;}
 function load(){
  let raw=null;
  try{raw=localStorage.getItem(STORE_KEY);}catch(e){storageOK=false;}
  if(raw){
   try{return E.fromStorage(raw,opts);}
   catch(err){
    try{localStorage.setItem(STORE_KEY+'-unreadable-'+Date.now(),raw);}catch(e){}
    setTimeout(()=>fail('Your saved plan could not be read, so the sample plan was loaded. A copy of the unreadable data was kept in this browser.'),0);
   }
  }
  return E.sampleState();
 }

 // ---------- feedback ----------
 function toast(text,withUndo){
  $('toast-text').textContent=text;$('toast-undo').hidden=!withUndo;
  $('toast').classList.add('visible');clearTimeout(toastTimer);
  toastTimer=setTimeout(()=>{$('toast').classList.remove('visible');if(withUndo)undoSnapshot=null;},withUndo?8000:4000);
 }
 function fail(text){$('error').textContent=text;$('error').hidden=false;}
 function clearError(){$('error').hidden=true;$('error').textContent='';}
 function snapshot(){undoSnapshot=E.toStorage(state);}
 function commit(message,undoable){clearError();save();render();if(message)toast(message,undoable);}
 function attempt(fn){try{clearError();return fn();}catch(err){if(err instanceof E.InputError){fail(err.message);return undefined;}fail('Something went wrong: '+(err&&err.message||'unknown error'));console.warn(err);return undefined;}}

 // ---------- selects ----------
 function fillSelect(sel,values,labels,first){
  sel.replaceChildren();if(first)sel.append(h('option',{value:''},first));
  for(const v of values)sel.append(h('option',{value:v},labels[v]));
 }

 // ---------- rendering ----------
 function render(){
  const s=E.summarize(state);
  renderDash(s);renderSide(s);
  if(tab==='people')renderPeople(s);else if(tab==='shopping')renderShopping();else if(tab==='costs')renderCosts();else renderSummary(s);
  $('sample-banner').hidden=!state.sample;
  $('load-sample').hidden=state.sample||state.people.length>0||state.costs.length>0;
 }

 function setStat(id,value,note,cls){$('stat-'+id).textContent=value;$('stat-'+id+'-note').textContent=note||'';$('stat-box-'+id).className='stat'+(cls?' '+cls:'');}
 function renderDash(s){
  const b=s.budgetCents;
  if(document.activeElement!==$('total-budget'))$('total-budget').value=b==null?'':E.moneyPlain(b);
  setStat('budget',b==null?'Not set':money(b),b==null?'Add a total above':s.peopleCount+(s.peopleCount===1?' person':' people')+' · '+s.giftCount+(s.giftCount===1?' gift':' gifts'));
  setStat('spent',money(s.spentCents),money(s.giftSpentCents)+' gifts + '+money(s.costsCents)+' other',s.remainingCents!=null&&s.remainingCents<0?'bad':'');
  if(b==null)setStat('remaining','—','Set a budget to track this');
  else setStat('remaining',money(s.remainingCents),s.remainingCents<0?'Over budget':s.remainingCents===0?'Exactly on budget':pctOf(1-s.ratio)+' of budget left',s.remainingCents<0?'bad':s.ratio>=0.9?'warn':'good');
  setStat('planned',money(s.plannedCents),'Priced ideas not bought yet',b!=null&&s.projectedCents>b?'warn':'');
  const bar=$('budget-progress');
  const r=s.ratio==null?0:Math.min(1,s.ratio===Infinity?1:s.ratio);
  bar.value=Math.round(r*1000);
  bar.className='bar'+(s.ratio==null?'':s.ratio>1?' over':s.ratio>=0.9?' near':'');
  $('progress-left').textContent=b==null?'Set a budget to see progress':money(s.spentCents)+' of '+money(b)+' spent';
  $('progress-right').textContent=b==null?'':s.ratio>1?'Over by '+money(-s.remainingCents):pctOf(s.ratio);
  bar.setAttribute('aria-valuetext',$('progress-left').textContent);
  const ul=$('warnings');ul.replaceChildren();
  for(const w of s.warnings)ul.append(h('li',{class:'warning '+w.level},w.text));
 }

 function renderSide(s){
  const ol=$('needs-list');ol.replaceChildren();
  for(const r of s.needsGift.slice(0,PAGE.needs)){
   const btn=h('button',{type:'button',class:'link-button',dataset:{act:'jump',id:r.person.id}},r.person.name);
   ol.append(h('li',null,btn,r.ideaCount?h('small',null,' · '+r.ideaCount+(r.ideaCount===1?' idea':' ideas')):null));
  }
  const n=s.needsGift.length;
  $('needs-note').textContent=!s.peopleCount?'Add people to start your list.':n===0?'Everyone has at least one gift bought. Nice work!':n>PAGE.needs?'+ '+(n-PAGE.needs)+' more. Use “Needs a gift” in the People filter.':n+' of '+s.peopleCount+' still to shop for.';
  const sc=$('status-counts');sc.replaceChildren();
  for(const st of E.STATUSES)sc.append(h('li',null,h('span',{class:'dot dot-'+st,'aria-hidden':'true'}),h('span',null,E.STATUS_LABELS[st]),h('strong',null,String(s.statusCounts[st]))));
  const cc=$('cost-cats');cc.replaceChildren();
  const cats=E.COST_CATEGORIES.filter(c=>s.costByCategory[c]);
  if(!cats.length)cc.append(h('li',{class:'muted'},'No other costs yet.'));
  for(const c of cats)cc.append(h('li',null,h('span',null,E.COST_LABELS[c]),h('strong',null,money(s.costByCategory[c]))));
 }

 function matches(r,q,giftsByPerson){
  if(!q)return true;
  if(r.person.name.toLowerCase().includes(q)||r.person.notes.toLowerCase().includes(q))return true;
  return (giftsByPerson.get(r.person.id)||[]).some(g=>g.title.toLowerCase().includes(q)||g.store.toLowerCase().includes(q)||g.tracking.toLowerCase().includes(q)||g.notes.toLowerCase().includes(q));
 }
 function giftsIndex(){const m=new Map();for(const g of state.gifts){let a=m.get(g.personId);if(!a)m.set(g.personId,a=[]);a.push(g);}return m;}

 function renderPeople(s){
  const list=$('people-list');list.replaceChildren();
  const q=$('people-search').value.trim().toLowerCase(),grp=$('group-filter').value,show=$('show-filter').value;
  const byPerson=giftsIndex();
  const rows=s.people.filter(r=>(!grp||r.person.group===grp)&&(show==='all'||(show==='needs'&&r.needsGift)||(show==='over'&&r.over))&&matches(r,q,byPerson));
  if(!state.people.length){
   list.append(h('div',{class:'empty-state'},h('h3',null,'Who are you shopping for?'),h('p',null,'Add the first person, then their gift ideas. GiftTally keeps the totals.'),h('button',{type:'button',class:'btn btn-primary',dataset:{act:'add-person'}},'+ Add your first person')));
  }else if(!rows.length){
   list.append(h('div',{class:'empty-state small'},h('p',null,'No one matches these filters.')));
  }
  const frag=document.createDocumentFragment();
  let shown=rows.slice(0,limits.people);
  if(pinned&&!shown.some(r=>r.person.id===pinned)){const pr=rows.find(r=>r.person.id===pinned);if(pr)shown=[pr].concat(shown.slice(0,Math.max(0,limits.people-1)));}
  for(const r of shown)frag.append(personCard(r,byPerson.get(r.person.id)||[],r.person.id===pinned));
  list.append(frag);
  $('more-people').hidden=rows.length<=limits.people;
  $('people-count').textContent=state.people.length?(rows.length===state.people.length?'':rows.length+' of '+state.people.length+' people match. ')+'Showing '+shown.length+' of '+rows.length+'.':'';
  $('add-person').disabled=false;
 }

 function personCard(r,gifts,isNew){
  const p=r.person;
  const badges=[h('span',{class:'chip group-'+p.group},E.GROUP_LABELS[p.group])];
  if(r.over)badges.push(h('span',{class:'badge bad'},'Over budget'));
  else if(r.projectedOver)badges.push(h('span',{class:'badge warn'},'Ideas exceed budget'));
  if(r.needsGift)badges.push(h('span',{class:'badge need'},'Needs a gift'));
  const moneyLine=r.budgetCents==null?
   h('p',{class:'person-money'},h('strong',null,money(r.spentCents)),' spent · no budget set'):
   h('p',{class:'person-money'},h('strong',{class:r.over?'bad':''},money(r.spentCents)),' of '+money(r.budgetCents)+' · ',h('span',{class:r.remainingCents<0?'bad':'good'},r.remainingCents<0?money(-r.remainingCents)+' over':money(r.remainingCents)+' left'));
  const card=h('article',{class:'person'+(r.over?' is-over':'')+(isNew?' is-new':''),id:'person-'+p.id,dataset:{id:p.id},'aria-label':p.name},
   h('div',{class:'person-head'},
    h('div',{class:'person-title'},h('h3',null,p.name),h('div',{class:'badges'},badges)),
    h('div',{class:'person-actions'},
     h('button',{type:'button',class:'btn btn-small btn-primary',dataset:{act:'add-gift'}},'+ Gift'),
     h('button',{type:'button',class:'btn btn-small btn-ghost',dataset:{act:'edit-person'},'aria-label':'Edit '+p.name},'Edit'),
     h('button',{type:'button',class:'btn btn-small btn-ghost danger-text',dataset:{act:'delete-person'},'aria-label':'Delete '+p.name},'Delete'))),
   moneyLine);
  if(r.budgetCents!=null){const ratio=r.ratio===Infinity?1:Math.min(1,r.ratio);card.append(h('progress',{class:'bar mini'+(r.over?' over':r.ratio>=0.9?' near':''),max:'1000',value:String(Math.round(ratio*1000)),'aria-label':p.name+' budget used'}));}
  if(r.plannedCents||r.unpricedIdeas)card.append(h('p',{class:'person-planned'},'Ideas: '+money(r.plannedCents)+(r.unpricedIdeas?' + '+r.unpricedIdeas+' unpriced':'')));
  if(p.notes)card.append(h('p',{class:'person-notes'},p.notes));
  if(!gifts.length){card.append(h('p',{class:'empty-gifts'},'No gifts yet — add an idea.'));return card;}
  const ul=h('ul',{class:'gifts'});
  const sorted=gifts.slice().sort((a,b)=>E.STATUSES.indexOf(a.status)-E.STATUSES.indexOf(b.status)||E.compare(a.title,b.title));
  for(const g of sorted){
   const sel=h('select',{class:'status-select st-'+g.status,dataset:{act:'status',gift:g.id},'aria-label':'Status of '+g.title});
   for(const st of E.STATUSES)sel.append(h('option',{value:st,selected:st===g.status},E.STATUS_LABELS[st]));
   const meta=[g.store,g.tracking?'Tracking '+g.tracking:''].filter(Boolean).join(' · ');
   ul.append(h('li',{class:'gift st-'+g.status,dataset:{gift:g.id}},
    h('div',{class:'gift-main'},h('strong',null,g.title),meta?h('span',{class:'gift-meta'},meta):null,g.notes?h('span',{class:'gift-note'},g.notes):null),
    sel,
    h('span',{class:'gift-price'+(g.priceCents==null?' muted':'')},g.priceCents==null?'No price':money(g.priceCents)),
    h('span',{class:'gift-actions'},
     h('button',{type:'button',class:'icon-btn',dataset:{act:'edit-gift',gift:g.id},'aria-label':'Edit '+g.title,title:'Edit'},'Edit'),
     h('button',{type:'button',class:'icon-btn danger-text',dataset:{act:'delete-gift',gift:g.id},'aria-label':'Delete '+g.title,title:'Delete'},'Delete'))));
  }
  card.append(ul);return card;
 }

 function renderShopping(){
  const wrap=$('shopping-list');wrap.replaceChildren();
  const groups=E.shoppingList(state);
  if(!groups.length){wrap.append(h('div',{class:'empty-state small'},h('p',null,state.gifts.length?'Nothing left to buy — every gift is past the idea stage.':'Add gift ideas and they’ll show up here, grouped by store.')));$('more-shopping').hidden=true;return;}
  const frag=document.createDocumentFragment();
  for(const g of groups.slice(0,limits.shopping)){
   const total=money(g.totalCents)+(g.unpriced?' + '+g.unpriced+' unpriced':'');
   const ul=h('ul',{class:'shop-items'});
   for(const it of g.items)ul.append(h('li',null,
    h('label',{class:'shop-check'},h('input',{type:'checkbox',dataset:{act:'bought',gift:it.gift.id}}),h('span',{class:'sr-only'},'Mark '+it.gift.title+' bought')),
    h('div',{class:'shop-text'},h('strong',null,it.gift.title),h('span',null,'for '+it.person.name+(it.gift.notes?' · '+it.gift.notes:''))),
    h('span',{class:'gift-price'+(it.gift.priceCents==null?' muted':'')},it.gift.priceCents==null?'No price':money(it.gift.priceCents))));
   frag.append(h('section',{class:'shop-group'},h('div',{class:'shop-head'},h('h3',null,g.store||'No store yet'),h('span',null,g.items.length+(g.items.length===1?' item · ':' items · ')+total)),ul));
  }
  wrap.append(frag);
  $('more-shopping').hidden=groups.length<=limits.shopping;
 }

 function renderCosts(){
  const body=$('cost-body');body.replaceChildren();
  if(!state.costs.length)body.append(h('tr',null,h('td',{colspan:'4',class:'muted'},'No other costs yet. Add wrapping, shipping, cards, or hosting above.')));
  let total=0;
  for(const c of state.costs){total+=c.amountCents;
   body.append(h('tr',{class:editing.cost===c.id?'editing':''},h('td',null,c.label),h('td',null,E.COST_LABELS[c.category]),h('td',{class:'num'},money(c.amountCents)),
    h('td',{class:'row-actions'},h('button',{type:'button',class:'icon-btn',dataset:{act:'edit-cost',id:c.id},'aria-label':'Edit '+c.label},'Edit'),h('button',{type:'button',class:'icon-btn danger-text',dataset:{act:'delete-cost',id:c.id},'aria-label':'Delete '+c.label},'Delete'))));}
  $('cost-total').textContent=money(total);
 }

 function renderSummary(s){
  const body=$('summary-body');body.replaceChildren();
  const rows=s.people.slice().sort((a,b)=>E.compare(a.person.name,b.person.name));
  if(!rows.length)body.append(h('tr',null,h('td',{colspan:'7',class:'muted'},'No people yet.')));
  const frag=document.createDocumentFragment();
  for(const r of rows.slice(0,limits.summary))frag.append(h('tr',null,h('td',{class:'strong'},r.person.name),h('td',null,E.GROUP_LABELS[r.person.group]),h('td',{class:'num'},money(r.budgetCents)),h('td',{class:'num'},money(r.spentCents)),h('td',{class:'num'},money(r.plannedCents)),h('td',{class:'num'+(r.remainingCents!=null&&r.remainingCents<0?' bad':'')},money(r.remainingCents)),h('td',null,h('span',{class:'badge '+(r.over?'bad':r.needsGift?'need':'ok')},r.over?'Over budget':r.needsGift?'Needs a gift':'On track'))));
  body.append(frag);
  $('more-summary').hidden=rows.length<=limits.summary;
 }

 function renderPrintView(){
  const s=E.summarize(state);const v=$('print-view');v.replaceChildren();
  const names=new Map(state.people.map(p=>[p.id,p]));
  v.append(h('h1',null,'GiftTally · Holiday gift summary'),h('p',null,(state.sample?'Sample data · ':'')+'Printed '+new Date().toLocaleDateString()));
  v.append(h('p',{class:'pv-totals'},'Budget '+money(s.budgetCents)+' · Spent '+money(s.spentCents)+' · Remaining '+money(s.remainingCents)+' · Still planned '+money(s.plannedCents)));
  for(const w of s.warnings)v.append(h('p',{class:'pv-warn'},w.text));
  const t=h('table',null,h('thead',null,h('tr',null,['Person','Gift','Store','Status','Price'].map(x=>h('th',null,x)))));const tb=h('tbody');
  const gifts=state.gifts.filter(g=>names.has(g.personId)).sort((a,b)=>E.compare(names.get(a.personId).name,names.get(b.personId).name)||E.STATUSES.indexOf(a.status)-E.STATUSES.indexOf(b.status));
  for(const g of gifts)tb.append(h('tr',null,h('td',null,names.get(g.personId).name),h('td',null,g.title),h('td',null,g.store),h('td',null,E.STATUS_LABELS[g.status]),h('td',{class:'num'},money(g.priceCents))));
  t.append(tb);v.append(t);
  if(s.needsGift.length)v.append(h('p',null,'Still needs a gift: '+s.needsGift.map(r=>r.person.name).join(', ')));
  if(state.costs.length)v.append(h('p',null,'Other costs: '+state.costs.map(c=>c.label+' '+money(c.amountCents)).join(' · ')));
 }

 // ---------- tabs ----------
 function showTab(name,focus){
  if(name!==tab)clearError();tab=name;
  document.querySelectorAll('[data-tab]').forEach(b=>{const on=b.dataset.tab===name;b.setAttribute('aria-selected',String(on));b.tabIndex=on?0:-1;$('panel-'+b.dataset.tab).hidden=!on;if(on&&focus)b.focus();});
  render();
 }
 document.querySelectorAll('[data-tab]').forEach(b=>{
  b.addEventListener('click',()=>showTab(b.dataset.tab));
  b.addEventListener('keydown',e=>{const order=['people','shopping','costs','summary'];let i=order.indexOf(tab);
   if(e.key==='ArrowRight')i=(i+1)%4;else if(e.key==='ArrowLeft')i=(i+3)%4;else if(e.key==='Home')i=0;else if(e.key==='End')i=3;else return;e.preventDefault();showTab(order[i],true);});
 });

 // ---------- dialogs ----------
 function openDialog(d,focusId){if(typeof d.showModal==='function'){if(!d.open)d.showModal();}else d.setAttribute('open','');setTimeout(()=>$(focusId).focus(),0);}
 function closeDialog(d){if(typeof d.close==='function'&&d.open)d.close();else d.removeAttribute('open');}
 document.querySelectorAll('dialog [data-close]').forEach(b=>b.addEventListener('click',()=>closeDialog(b.closest('dialog'))));
 document.querySelectorAll('dialog').forEach(d=>d.addEventListener('click',e=>{if(e.target===d)closeDialog(d);}));
 function formError(id,msg){$(id).textContent=msg||'';$(id).hidden=!msg;}

 function openPerson(id){
  if(!id&&EDITION.preview&&state.people.length>=EDITION.maxPeople){fail('The free preview is limited to '+EDITION.maxPeople+' people. Get the full GiftTally ($9 one-time) for unlimited people.');$('preview-banner').scrollIntoView({block:'nearest'});return;}
  editing.person=id||null;const p=id?state.people.find(x=>x.id===id):null;
  $('person-title').textContent=p?'Edit '+p.name:'Add person';$('person-submit').textContent=p?'Save changes':'Add person';
  $('person-name').value=p?p.name:'';$('person-group').value=p?p.group:'family';$('person-budget').value=p&&p.budgetCents!=null?E.moneyPlain(p.budgetCents):'';$('person-notes').value=p?p.notes:'';
  formError('person-error');openDialog($('person-dialog'),'person-name');
 }
 $('person-form').addEventListener('submit',e=>{
  e.preventDefault();
  const input={name:$('person-name').value,group:$('person-group').value,budget:$('person-budget').value,notes:$('person-notes').value};
  try{
   let p;
   if(editing.person)p=E.updatePerson(state,editing.person,input);else{p=E.addPerson(state,input,opts);pinned=p.id;}
   closeDialog($('person-dialog'));
   if(!editing.person&&tab!=='people')showTab('people');
   commit(editing.person?'Saved '+p.name+'.':'Added '+p.name+'.');
   if(!editing.person){const card=$('person-'+p.id);if(card)card.scrollIntoView({block:'nearest'});}
  }catch(err){if(!(err instanceof E.InputError))throw err;formError('person-error',err.message);}
 });

 function storeOptions(){const dl=$('store-options');dl.replaceChildren();const seen=new Set();for(const g of state.gifts){const k=g.store.toLowerCase();if(g.store&&!seen.has(k)&&seen.size<200){seen.add(k);dl.append(h('option',{value:g.store}));}}}
 function openGift(personId,giftId){
  const g=giftId?state.gifts.find(x=>x.id===giftId):null;editing.gift=giftId||null;
  const sel=$('gift-person');sel.replaceChildren();
  const pid=g?g.personId:personId;
  // keep the person list manageable on huge plans: the current person first, then others A–Z
  const people=state.people.slice().sort((a,b)=>E.compare(a.name,b.name));
  for(const p of people)sel.append(h('option',{value:p.id,selected:p.id===pid},p.name));
  sel.value=pid;
  $('gift-title').textContent=g?'Edit gift':'Add gift';$('gift-submit').textContent=g?'Save changes':'Add gift';
  $('gift-name').value=g?g.title:'';$('gift-price').value=g&&g.priceCents!=null?E.moneyPlain(g.priceCents):'';$('gift-status').value=g?g.status:'idea';
  $('gift-store').value=g?g.store:'';$('gift-tracking').value=g?g.tracking:'';$('gift-notes').value=g?g.notes:'';
  storeOptions();formError('gift-error');openDialog($('gift-dialog'),'gift-name');
 }
 $('gift-form').addEventListener('submit',e=>{
  e.preventDefault();
  const input={personId:$('gift-person').value,title:$('gift-name').value,price:$('gift-price').value,status:$('gift-status').value,store:$('gift-store').value,tracking:$('gift-tracking').value,notes:$('gift-notes').value};
  try{
   const g=editing.gift?E.updateGift(state,editing.gift,input):E.addGift(state,input.personId,input);
   closeDialog($('gift-dialog'));commit((editing.gift?'Saved ':'Added ')+g.title+'.');
  }catch(err){if(!(err instanceof E.InputError))throw err;formError('gift-error',err.message);}
 });

 // ---------- people list actions (delegated) ----------
 $('people-list').addEventListener('click',e=>{
  const b=e.target.closest('button[data-act]');if(!b)return;
  const act=b.dataset.act;const card=b.closest('.person');const pid=card&&card.dataset.id;
  if(act==='add-person')return openPerson();
  if(act==='add-gift')return openGift(pid);
  if(act==='edit-person')return openPerson(pid);
  if(act==='edit-gift')return openGift(pid,b.dataset.gift);
  if(act==='delete-person'){
   const p=state.people.find(x=>x.id===pid);if(!p)return;
   const n=state.gifts.filter(g=>g.personId===pid).length;
   if(n&&!confirm('Delete '+p.name+' and their '+n+(n===1?' gift':' gifts')+'?'))return;
   snapshot();attempt(()=>{E.removePerson(state,pid);commit('Deleted '+p.name+'.',true);});
  }
  if(act==='delete-gift'){
   const g=state.gifts.find(x=>x.id===b.dataset.gift);if(!g)return;
   snapshot();attempt(()=>{E.removeGift(state,g.id);commit('Deleted '+g.title+'.',true);});
  }
 });
 $('people-list').addEventListener('change',e=>{
  const sel=e.target.closest('select[data-act="status"]');if(!sel)return;
  attempt(()=>{const g=E.setGiftStatus(state,sel.dataset.gift,sel.value);commit(g.title+' marked '+E.STATUS_LABELS[g.status].toLowerCase()+'.');});
 });
 $('add-person').addEventListener('click',()=>openPerson());
 $('more-people').addEventListener('click',()=>{limits.people+=PAGE.people;render();});
 let searchTimer;
 $('people-search').addEventListener('input',()=>{clearTimeout(searchTimer);searchTimer=setTimeout(()=>{limits.people=PAGE.people;pinned=null;render();},120);});
 $('group-filter').addEventListener('change',()=>{limits.people=PAGE.people;pinned=null;render();});
 $('show-filter').addEventListener('change',()=>{limits.people=PAGE.people;pinned=null;render();});
 document.querySelector('.side').addEventListener('click',e=>{
  const b=e.target.closest('button[data-act="jump"]');if(!b)return;
  const p=state.people.find(x=>x.id===b.dataset.id);if(!p)return;
  $('people-search').value=p.name;$('group-filter').value='';$('show-filter').value='all';limits.people=PAGE.people;showTab('people');
  const card=$('person-'+p.id);if(card){card.scrollIntoView({block:'start'});card.classList.add('flash');setTimeout(()=>card.classList.remove('flash'),1200);}
 });

 // ---------- shopping list ----------
 $('shopping-list').addEventListener('change',e=>{
  const cb=e.target.closest('input[data-act="bought"]');if(!cb||!cb.checked)return;
  snapshot();attempt(()=>{const g=E.setGiftStatus(state,cb.dataset.gift,'bought');commit(g.title+' marked bought.',true);});
 });
 $('more-shopping').addEventListener('click',()=>{limits.shopping+=PAGE.shopping;render();});

 // ---------- budget ----------
 $('budget-form').addEventListener('submit',e=>{
  e.preventDefault();
  attempt(()=>{const v=E.setBudget(state,$('total-budget').value);$('total-budget').blur();commit(v==null?'Budget cleared.':'Budget set to '+money(v)+'.');});
 });

 // ---------- other costs ----------
 function resetCostForm(){editing.cost=null;$('cost-label').value='';$('cost-amount').value='';$('cost-submit').textContent='Add cost';$('cost-cancel').hidden=true;formError('cost-error');}
 $('cost-form').addEventListener('submit',e=>{
  e.preventDefault();
  const input={category:$('cost-category').value,label:$('cost-label').value,amount:$('cost-amount').value};
  try{const c=editing.cost?E.updateCost(state,editing.cost,input):E.addCost(state,input);const was=editing.cost;resetCostForm();commit((was?'Saved ':'Added ')+c.label+'.');$('cost-label').focus();}
  catch(err){if(!(err instanceof E.InputError))throw err;formError('cost-error',err.message);}
 });
 $('cost-cancel').addEventListener('click',()=>{resetCostForm();render();});
 $('cost-body').addEventListener('click',e=>{
  const b=e.target.closest('button[data-act]');if(!b)return;const c=state.costs.find(x=>x.id===b.dataset.id);if(!c)return;
  if(b.dataset.act==='edit-cost'){editing.cost=c.id;$('cost-category').value=c.category;$('cost-label').value=c.label;$('cost-amount').value=E.moneyPlain(c.amountCents);$('cost-submit').textContent='Save cost';$('cost-cancel').hidden=false;formError('cost-error');render();$('cost-label').focus();}
  if(b.dataset.act==='delete-cost'){snapshot();attempt(()=>{E.removeCost(state,c.id);if(editing.cost===c.id)resetCostForm();commit('Deleted '+c.label+'.',true);});}
 });

 // ---------- export / import ----------
 function stamp(){const d=new Date();return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');}
 function download(text,type,name){
  const url=URL.createObjectURL(new Blob([text],{type}));const a=h('a',{href:url,download:name,class:'sr-only'});
  document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),4000);
 }
 $('export-csv').addEventListener('click',()=>{download(E.toCSV(state),'text/csv;charset=utf-8','gifttally-summary-'+stamp()+'.csv');toast('Spreadsheet downloaded. Opens in Excel, Numbers or Google Sheets.');});
 $('export-html').addEventListener('click',()=>{download(E.summaryHTML(state,{generated:'Generated '+new Date().toLocaleString()}),'text/html;charset=utf-8','gifttally-summary-'+stamp()+'.html');toast('Printable summary downloaded. Open it and use Print or Save as PDF.');});
 $('print').addEventListener('click',()=>{renderPrintView();window.print();});
 window.addEventListener('beforeprint',renderPrintView);
 $('export-json').addEventListener('click',()=>{download(E.toBackup(state),'application/json','gifttally-backup-'+stamp()+'.json');toast('Backup saved. Keep it somewhere safe.');});
 $('import-json').addEventListener('click',()=>$('import-file').click());
 $('import-file').addEventListener('change',e=>{
  const f=e.target.files&&e.target.files[0];e.target.value='';if(!f)return;
  if(f.size>E.LIMITS.importBytes){fail('That file is too large to be a GiftTally backup (max 5 MB).');return;}
  const reader=new FileReader();
  reader.onerror=()=>fail('Could not read that file.');
  reader.onload=()=>attempt(()=>{
   const next=E.parseBackup(String(reader.result),opts);
   if(!confirm('Replace the current plan with this backup ('+next.people.length+' people, '+next.gifts.length+' gifts)?'))return;
   snapshot();state=next;resetView();commit('Backup restored: '+next.people.length+' people, '+next.gifts.length+' gifts.',true);
  });
  reader.readAsText(f);
 });
 function resetView(){pinned=null;limits={people:PAGE.people,shopping:PAGE.shopping,summary:PAGE.summary};editing={person:null,gift:null,cost:null};$('people-search').value='';$('group-filter').value='';$('show-filter').value='all';resetCostForm();}
 $('clear-all').addEventListener('click',()=>{if(!confirm('Clear every person, gift, cost and the budget from this browser?'))return;snapshot();state=E.emptyState();resetView();tab='people';showTab('people');commit('Everything cleared.',true);});
 $('clear-sample').addEventListener('click',()=>{snapshot();state=E.emptyState();resetView();commit('Sample cleared. Start by setting your budget.',true);$('total-budget').focus();});
 $('keep-sample').addEventListener('click',()=>{state.sample=false;commit('Sample kept — edit it into your own plan.');});
 $('load-sample').addEventListener('click',()=>{snapshot();state=E.sampleState();resetView();commit('Sample plan loaded.',true);});
 $('toast-undo').addEventListener('click',()=>{
  if(!undoSnapshot)return;
  try{state=E.fromStorage(undoSnapshot,opts);}catch(err){fail('Could not undo.');return;}
  undoSnapshot=null;$('toast-undo').hidden=true;resetView();save();render();toast('Undone.');
 });
 $('more-summary').addEventListener('click',()=>{limits.summary+=PAGE.summary;render();});

 // ---------- keep tabs in sync if the plan changes in another window ----------
 window.addEventListener('storage',e=>{if(e.key===STORE_KEY&&e.newValue){try{state=E.fromStorage(e.newValue,opts);render();}catch(err){}}});

 // ---------- boot ----------
 fillSelect($('person-group'),E.GROUPS,E.GROUP_LABELS);
 fillSelect($('group-filter'),E.GROUPS,E.GROUP_LABELS,'All groups');
 fillSelect($('gift-status'),E.STATUSES,E.STATUS_LABELS);
 fillSelect($('cost-category'),E.COST_CATEGORIES,E.COST_LABELS);
 if(EDITION.preview){$('preview-banner').hidden=false;$('upgrade-link').href=EDITION.buyUrl;}
 state=load();
 render();
 if(!storageOK)setSaveState('Not saving in this browser — use Save backup','bad');
 else save();
})();
