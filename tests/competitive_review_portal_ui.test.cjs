"use strict";
/* CE-1P actual client JavaScript behavior, offline fake DOM/Blob, NO browser/network.
 * The exact production _JS is dumped by Python to an ephemeral CI-only file.
 * This is a mechanical JS behavior test, not independent source review.
 */
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const clientPath = process.env.CE1P_CLIENT_JS;
if (!clientPath || !fs.existsSync(clientPath)) {
  throw Error("CE-1P production JavaScript was not supplied for executable testing");
}
const js = fs.readFileSync(clientPath, "utf8");

function input(value="") {
  return {
    value, listeners: Object.create(null),
    addEventListener(name, callback) { this.listeners[name] = callback; },
  };
}
function card(fields) {
  const children = Object.fromEntries(
    Object.entries(fields).map(([key,value]) => [key,input(value)])
  );
  return {
    fields: children,
    querySelector(key) {
      if (!Object.hasOwn(children,key)) throw Error("unknown control " + key);
      return children[key];
    }
  };
}
function room() {
  return {
    room_manifest_sha256:"a".repeat(64),
    dossier_sha256:"b".repeat(64),
    handoff_sha256:"c".repeat(64),
    issuer_inventory_head_sha256:"d".repeat(64),
    page_tasks:[
      {file:"notice-page-001.png",png_sha256:"e".repeat(64)},
      {file:"attachment-page-001.png",png_sha256:"f".repeat(64)}
    ],
    claim_tasks:[
      {claim_id:"claim-with-original",source_ids_considered:["issuer"],
       counter_source_ids_considered:["counter"],
       issuer_citation_refs:[{source_id:"issuer",document_id:"notice",
                             page_number:1,png_sha256:"e".repeat(64)}]},
      {claim_id:"claim-no-original",source_ids_considered:["buyer"],
       counter_source_ids_considered:[],issuer_citation_refs:[]}
    ],
    publication_authorized:false
  };
}
function make() {
  const ctx = room();
  const pages = ctx.page_tasks.map(() => card({
    ".page-finding":"", ".page-notes":""
  }));
  const claims = ctx.claim_tasks.map(() => card({
    ".claim-disposition":"", ".claim-reasoning":""
  }));
  let failed = false;
  const elements = {
    "review-context":{textContent:JSON.stringify(ctx)},
    "save-draft":input(),
    "load-draft":input(),
    "review-form":input(),
    "review-summary":input(),
    "progress":{textContent:"Review controls loading…"},
    "status":{textContent:"",classList:{
      toggle(key,value){ if(key==="error")failed=!!value; }
    }}
  };
  let lastBlob=null;
  const downloads=[];
  const sandbox = {
    document:{
      getElementById(id) {
        if (!Object.hasOwn(elements,id))throw Error("unknown DOM id "+id);
        return elements[id];
      },
      querySelectorAll(selector) {
        if (selector===".page-card")return pages;
        if (selector===".claim-card")return claims;
        throw Error("unsupported DOM selector "+selector);
      },
      createElement(tag) {
        assert.equal(tag,"a");
        return {
          href:"", download:"",hidden:false,
          click() {
            assert.ok(lastBlob);
            downloads.push({
              filename:this.download,
              content:JSON.parse(lastBlob.bytes)
            });
          },
          remove(){}
        };
      },
      body:{append(){}}
    },
    Blob:class MockBlob {
      constructor(parts,options) {
        assert.equal(options.type,"application/json");
        this.bytes=parts.join("");
      }
    },
    URL:{
      createObjectURL(blob){lastBlob=blob;return "blob:private-review-only";},
      revokeObjectURL(url){assert.equal(url,"blob:private-review-only");}
    },
    setTimeout(callback){callback();}
  };
  vm.runInNewContext(js,sandbox,{timeout:1500});
  return {
    ctx,pages,claims,elements,downloads,
    failed:()=>failed,
    submit(){elements["review-form"].listeners.submit({preventDefault(){}});},
    save(){elements["save-draft"].listeners.click();},
    async load(data) {
      const target={files:[{size:JSON.stringify(data).length,text:async()=>JSON.stringify(data)}],value:"draft.json"};
      await elements["load-draft"].listeners.change({target});
    },
    change(){elements["review-form"].listeners.input();},
  };
}
function complete(h) {
  for (const page of h.pages) {
    page.fields[".page-finding"].value="legible_reported";
    page.fields[".page-notes"].value="Synthetic description of page pixels and limits: ".repeat(2);
  }
  for (const [i,claim] of h.claims.entries()) {
    claim.fields[".claim-disposition"].value =
      i===0 ? "packet_excerpt_located" : "unverified";
    claim.fields[".claim-reasoning"].value =
      "This is only a synthetic assertion; no original issuer or external factual truth was established. ".repeat(2);
  }
  h.elements["review-summary"].value =
    "Fictional reviewers in unit tests cannot authenticate the issuer, establish real independence, or authorize external publication.";
  h.change();
}

test("client initializes with all pages and claims unanswered", () => {
  const h=make();
  assert.match(h.elements.progress.textContent,/0\/2 pages/);
  assert.match(h.elements.progress.textContent,/0\/2 claims/);
  assert.equal(h.downloads.length,0);
  assert.equal(h.failed(),false);
});

test("incomplete page or claim controls block completed unsigned export", () => {
  const h=make();
  h.submit();
  assert.equal(h.downloads.length,0);
  assert.equal(h.failed(),true);
  assert.match(h.elements.status.textContent,/Page 1 needs/);
  complete(h);
  h.claims[1].fields[".claim-reasoning"].value="Too short";
  h.submit();
  assert.equal(h.downloads.length,0);
  assert.match(h.elements.status.textContent,/Claim claim-no-original needs/);
});

test("complete manual findings export all exact references but never approval", () => {
  const h=make();
  complete(h);
  assert.match(h.elements.progress.textContent,/2\/2 pages/);
  assert.match(h.elements.progress.textContent,/2\/2 claims/);
  h.submit();
  assert.equal(h.downloads.length,1);
  assert.equal(h.failed(),false);
  const {filename,content} = h.downloads[0];
  assert.match(filename,/UNSIGNED/);
  assert.equal(content.schema_version,"CE1P_UNSIGNED_OBSERVATIONS_V1");
  assert.equal(content.room_manifest_sha256,h.ctx.room_manifest_sha256);
  assert.equal(content.dossier_sha256,h.ctx.dossier_sha256);
  assert.equal(content.handoff_sha256,h.ctx.handoff_sha256);
  assert.equal(content.issuer_inventory_head_sha256,h.ctx.issuer_inventory_head_sha256);
  assert.equal(content.page_observations.length,2);
  assert.equal(content.claim_assessments.length,2);
  assert.equal(content.claim_assessments[0].issuer_citation_refs[0].document_id,"notice");
  assert.deepEqual(Array.from(content.claim_assessments[0].counter_source_ids_considered),["counter"]);
  assert.equal(content.claim_assessments[1].disposition,"unverified");
  assert.ok(content.page_observations.every(p=>p.observed_at.endsWith("Z")));
  assert.ok(content.claim_assessments.every(c=>c.assessed_at.endsWith("Z")));
  assert.equal(content.requires_separate_root_governed_review_signing,true);
  assert.equal(content.independent_critic_approved,false);
  assert.equal(content.publication_authorized,false);
  assert.ok(!Object.hasOwn(content,"signature"));
});

test("room-bound draft saves partial notes and restores without approving", async () => {
  const h=make();
  h.pages[0].fields[".page-finding"].value="unassessable";
  h.pages[0].fields[".page-notes"].value="The synthetic page requires another original to confirm contents.";
  h.claims[0].fields[".claim-disposition"].value="contradiction_reported";
  h.claims[0].fields[".claim-reasoning"].value="Contradictory test metadata; no actual independent reviewer exists.";
  h.elements["review-summary"].value="Unfinished test review with unresolved original-source questions.";
  h.save();
  assert.equal(h.downloads.length,1);
  const draft=h.downloads[0].content;
  assert.equal(draft.schema_version,"CE1P_LOCAL_DRAFT_V1");
  assert.equal(draft.room_manifest_sha256,h.ctx.room_manifest_sha256);
  assert.equal(draft.publication_authorized,false);
  assert.equal(draft.pages[1].visual_finding,null);
  h.pages[0].fields[".page-finding"].value="";
  h.claims[0].fields[".claim-disposition"].value="";
  await h.load(draft);
  assert.equal(h.failed(),false);
  assert.equal(h.pages[0].fields[".page-finding"].value,"unassessable");
  assert.equal(h.claims[0].fields[".claim-disposition"].value,"contradiction_reported");
});

test("draft bound to another room fails without overwriting existing controls", async () => {
  const h=make();
  h.pages[0].fields[".page-notes"].value="Original reviewer note must remain intact.";
  h.save();
  const bad=JSON.parse(JSON.stringify(h.downloads[0].content));
  bad.room_manifest_sha256="0".repeat(64);
  bad.pages[0].visual_notes="Attacker's notes to overwrite independent observations";
  await h.load(bad);
  assert.equal(h.failed(),true);
  assert.equal(h.pages[0].fields[".page-notes"].value,"Original reviewer note must remain intact.");
  assert.match(h.elements.status.textContent,/does not belong/);
});

test("missing original PDF pages cannot be declared excerpt-located", () => {
  const h=make();
  complete(h);
  h.claims[1].fields[".claim-disposition"].value="packet_excerpt_located";
  h.submit();
  assert.equal(h.downloads.length,0);
  assert.equal(h.failed(),true);
  assert.match(h.elements.status.textContent,/no original issuer page/);
});
