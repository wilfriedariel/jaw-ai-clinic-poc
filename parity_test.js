// usage: node parity_test.js  -> exit 0 only if the page's scoring equals the Python pipeline on every row
const fs=require("fs"),vm=require("vm");
const html=fs.readFileSync(__dirname+"/demo.html","utf8");
const js=html.match(/<script>([\s\S]*)<\/script>/)[1];
const el=()=>new Proxy(function(){},{get:(t,k)=>k==="classList"?{toggle(){},add(){},remove(){}}:k==="value"?"":el(),set:()=>true,apply:()=>el()});
const ctx={setTimeout,performance,window:{scrollTo(){}},document:el(),URL:{createObjectURL(){}},Blob:function(){},alert:m=>{throw new Error("alert:"+m)},navigator:{},console};
vm.createContext(ctx);
vm.runInContext(js+";this.__t={DATA,scoreContact,chanceOf,loadCSV,getALL:()=>ALL,getDEMO:()=>DEMO,intentOf,answerFor,qaQueue,isOpenLead,kbAnswer,trendBuckets,waLink,parseNotes,KB_SAMPLE};",ctx);
const T=ctx.__t,MAP={Hot:"High",Warm:"Medium",Cold:"Low"};let bad=0,n=0;
for(const c of T.DATA.contacts){const {score,reasons}=T.scoreContact(c);n++;
 if(score!==c.score||T.chanceOf(score)!==MAP[c.tier]||JSON.stringify(reasons)!==JSON.stringify(c.why)){if(bad++<5)console.log("MISMATCH",c.id,score,c.score,reasons,c.why);}}
console.log(`parity rows=${n} mismatches=${bad}`);
let QFAIL=0;
// quick answers: classification table, partition of the waiting list, and drafts that never state a price/time/number
const want={"Hi, how much is facial?":"price","Hi, do you have a slot this week for facial?":"slot","Hi, I'm interested in facial. Can I know more?":"info","Ok thanks, let me think about it":"nudge","Is there a weekend slot?":"slot","Do you have any promotions?":"promo","What is the downtime like?":"downtime","Hi, how much is facial? And do you have a slot this week?":"price","asdf":"other"};
let qbad=0;for(const [t,i] of Object.entries(want)){if(T.intentOf(t)!==i){qbad++;console.log("INTENT MISMATCH",t,T.intentOf(t),"want",i);}}
const all=T.qaQueue(T.getALL()), openWaiting=T.getALL().filter(r=>T.isOpenLead(r)&&r.lastWho==="them").length;
const part=all.ready.length+all.person.length;
const numeric=all.ready.filter(x=>/\d|S\$|\$/.test(x.draft)).length, emptyReady=all.ready.filter(x=>!x.draft).length, personWithDraft=all.person.filter(x=>x.draft).length;
console.log(`quick answers waiting=${openWaiting} ready=${all.ready.length} person=${all.person.length} numericDrafts=${numeric} intentMismatch=${qbad}`);
if(qbad||part!==openWaiting||numeric||emptyReady||personWithDraft||!all.ready.length||!all.person.length)QFAIL=1;
// helpdesk: fixed questions must hit the intended note; off-topic must return null (fail safe)
const kbWant={"How do I cancel an appointment?":"Changing or cancelling an appointment","Can I pay with PayNow?":"Payment methods","When do my package sessions expire?":"Package validity and expiry","What should I do after pigmentation laser?":"Pigmentation laser aftercare","what is the best crypto to buy":null,"asdf qwer":null,"Are you open on Sunday?":"Opening hours and location","Is injectables done by a doctor?":"Injectables"};
let kbad=0;for(const [q,t] of Object.entries(kbWant)){const a=T.kbAnswer(q);const got=a?a.title:null;if(got!==t){kbad++;console.log("KB MISMATCH",q,got,"want",t);}}
const pn=T.parseNotes("Refunds\nWe do not give refunds on used sessions.\n\nOne long paragraph with no heading that goes on and on about parking being free for patients.");
if(pn.length!==2||pn[0].title!=="Refunds"||!/^One long paragraph/.test(pn[1].title))kbad++;
const own=T.kbAnswer("is parking free?",pn); if(!own||!/parking/.test(own.text))kbad++;
// trends: buckets must partition the leads exactly (day window 30, week window 8 weeks, months cover all)
const leadsN=T.getALL().filter(r=>r.kind==="lead"&&r.days_since_enquiry!=null).length, td=new Date(2026,9,21);
let tbad=0;for(const [m,w] of [["day",30],["week",56],["month",1e9]]){const B=T.trendBuckets(T.getALL(),m,td);const inWin=T.getALL().filter(r=>r.kind==="lead"&&r.days_since_enquiry!=null&&r.days_since_enquiry<w).length;const sum=B.reduce((a,b)=>a+b.received,0),bk=B.reduce((a,b)=>a+b.booked+b.notBooked,0);
 if(sum!==inWin||bk!==sum||B.some(b=>b.booked+b.notBooked!==b.received||b.waiting>b.notBooked)){tbad++;console.log("TREND MISMATCH",m,sum,inWin);}}
// whatsapp: masked -> blank chat with text; full SG number gets +65; international kept
const wl=[[{phone:"+65 9••• 1234"},"hi there","https://wa.me/?text=hi%20there"],[{phone:"9123 4567"},"","https://wa.me/6591234567"],[{phone:"+65 8123 4567"},"x y","https://wa.me/6581234567?text=x%20y"],[{phone:""},"","https://wa.me/"]];
let wbad=0;for(const [r,t,e] of wl){if(T.waLink(r,t)!==e){wbad++;console.log("WA MISMATCH",T.waLink(r,t),e);}}
const fp=T.kbAnswer("Can I take a photo of Dr Cheak?");console.log("KNOWN false positive (reported, not gated):",fp?fp.title:null);
console.log(`helpdesk mismatches=${kbad} trends mismatches=${tbad} whatsapp mismatches=${wbad}`);
if(kbad||tbad||wbad)QFAIL=1;
T.loadCSV("id,kind,consent,treatment,source,asked_price,asked_slots,msgs,days_since_contact,reply_latency_h,days_since_enquiry\nA1,lead,true,Facial,Referral,true,true,8,1,0.5,3\nA2,lead,false,Facial,Meta ad,false,false,1,40,30,50\n");
const cur=T.getALL();console.log("upload demo=",T.getDEMO(),cur.map(r=>r.id+":"+r.score+":"+r.chance).join(" "));
if(QFAIL||bad||T.getDEMO()||cur[0].chance!=="High"||cur[1].chance!=="Low")process.exit(1);
