// usage: node parity_test.js  -> exit 0 only if the page's scoring equals the Python pipeline on every row
const fs=require("fs"),vm=require("vm");
const html=fs.readFileSync(__dirname+"/demo.html","utf8");
const js=html.match(/<script>([\s\S]*)<\/script>/)[1];
const el=()=>new Proxy(function(){},{get:(t,k)=>k==="classList"?{toggle(){},add(){},remove(){}}:k==="value"?"":el(),set:()=>true,apply:()=>el()});
const ctx={setTimeout,performance,window:{scrollTo(){}},document:el(),URL:{createObjectURL(){}},Blob:function(){},alert:m=>{throw new Error("alert:"+m)},navigator:{},console};
vm.createContext(ctx);
vm.runInContext(js+";this.__t={DATA,scoreContact,chanceOf,loadCSV,getALL:()=>ALL,getDEMO:()=>DEMO};",ctx);
const T=ctx.__t,MAP={Hot:"High",Warm:"Medium",Cold:"Low"};let bad=0,n=0;
for(const c of T.DATA.contacts){const {score,reasons}=T.scoreContact(c);n++;
 if(score!==c.score||T.chanceOf(score)!==MAP[c.tier]||JSON.stringify(reasons)!==JSON.stringify(c.why)){if(bad++<5)console.log("MISMATCH",c.id,score,c.score,reasons,c.why);}}
console.log(`parity rows=${n} mismatches=${bad}`);
T.loadCSV("id,kind,consent,treatment,source,asked_price,asked_slots,msgs,days_since_contact,reply_latency_h,days_since_enquiry\nA1,lead,true,Facial,Referral,true,true,8,1,0.5,3\nA2,lead,false,Facial,Meta ad,false,false,1,40,30,50\n");
const cur=T.getALL();console.log("upload demo=",T.getDEMO(),cur.map(r=>r.id+":"+r.score+":"+r.chance).join(" "));
if(bad||T.getDEMO()||cur[0].chance!=="High"||cur[1].chance!=="Low")process.exit(1);
