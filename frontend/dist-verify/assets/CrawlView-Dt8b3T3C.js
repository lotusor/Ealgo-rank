import{Z as K,p as _,bs as Z,E as Q,I as x,J as X,a9 as P,ab as Y,d as W,y as S,V as ee,m as U,W as T,G as O,_ as te,r as $,a3 as E,u as oe,g as N,w as y,b as m,bb as ne,a as v,B as L,k as B,h as le,N as V,be as ae,bt as re,bu as se,aJ as ie,o as z}from"./index-D9Ac4DhN.js";import{u as ue}from"./use-message-DAaYSu_t.js";import{N as I}from"./Space-n_UDLqns.js";import{N as ce}from"./Select-B9dtBnGm.js";import{N as M}from"./InputNumber-D-fg4_sV.js";import{N as de}from"./text-CPo-BLrE.js";import{N as me}from"./DataTable-BJGzejVx.js";import{N as he}from"./Tag-BGB5zlRo.js";import"./Popover-BrJClfDH.js";import"./get-CfFPLqoW.js";import"./use-compitable-WOsnsMpP.js";import"./Suffix-BKWUYBGL.js";import"./index-B7F8ta0J.js";import"./Input-DqFpdO4S.js";import"./Add-6-1lXh7l.js";import"./RadioGroup-CybMAUa5.js";import"./Tooltip-DHktrkPd.js";import"./Dropdown-BdO_9te-.js";import"./create-ref-setter-C4J8sofl.js";import"./Pagination-ZoR3xdu9.js";function fe(t,e){const a=K(Z,null);return _(()=>t.hljs||(a==null?void 0:a.mergedHljsRef.value))}function pe(t){const{textColor2:e,fontSize:a,fontWeightStrong:f,textColor3:p}=t;return{textColor:e,fontSize:a,fontWeightStrong:f,"mono-3":"#a0a1a7","hue-1":"#0184bb","hue-2":"#4078f2","hue-3":"#a626a4","hue-4":"#50a14f","hue-5":"#e45649","hue-5-2":"#c91243","hue-6":"#986801","hue-6-2":"#c18401",lineNumberTextColor:p}}const ge={common:Q,self:pe},ve=x([X("code",`
 font-size: var(--n-font-size);
 font-family: var(--n-font-family);
 `,[P("show-line-numbers",`
 display: flex;
 `),Y("line-numbers",`
 user-select: none;
 padding-right: 12px;
 text-align: right;
 transition: color .3s var(--n-bezier);
 color: var(--n-line-number-text-color);
 `),P("word-wrap",[x("pre",`
 white-space: pre-wrap;
 word-break: break-all;
 `)]),x("pre",`
 margin: 0;
 line-height: inherit;
 font-size: inherit;
 font-family: inherit;
 `),x("[class^=hljs]",`
 color: var(--n-text-color);
 transition: 
 color .3s var(--n-bezier),
 background-color .3s var(--n-bezier);
 `)]),({props:t})=>{const e=`${t.bPrefix}code`;return[`${e} .hljs-comment,
 ${e} .hljs-quote {
 color: var(--n-mono-3);
 font-style: italic;
 }`,`${e} .hljs-doctag,
 ${e} .hljs-keyword,
 ${e} .hljs-formula {
 color: var(--n-hue-3);
 }`,`${e} .hljs-section,
 ${e} .hljs-name,
 ${e} .hljs-selector-tag,
 ${e} .hljs-deletion,
 ${e} .hljs-subst {
 color: var(--n-hue-5);
 }`,`${e} .hljs-literal {
 color: var(--n-hue-1);
 }`,`${e} .hljs-string,
 ${e} .hljs-regexp,
 ${e} .hljs-addition,
 ${e} .hljs-attribute,
 ${e} .hljs-meta-string {
 color: var(--n-hue-4);
 }`,`${e} .hljs-built_in,
 ${e} .hljs-class .hljs-title {
 color: var(--n-hue-6-2);
 }`,`${e} .hljs-attr,
 ${e} .hljs-variable,
 ${e} .hljs-template-variable,
 ${e} .hljs-type,
 ${e} .hljs-selector-class,
 ${e} .hljs-selector-attr,
 ${e} .hljs-selector-pseudo,
 ${e} .hljs-number {
 color: var(--n-hue-6);
 }`,`${e} .hljs-symbol,
 ${e} .hljs-bullet,
 ${e} .hljs-link,
 ${e} .hljs-meta,
 ${e} .hljs-selector-id,
 ${e} .hljs-title {
 color: var(--n-hue-2);
 }`,`${e} .hljs-emphasis {
 font-style: italic;
 }`,`${e} .hljs-strong {
 font-weight: var(--n-font-weight-strong);
 }`,`${e} .hljs-link {
 text-decoration: underline;
 }`]}]),be=Object.assign(Object.assign({},O.props),{language:String,code:{type:String,default:""},trim:{type:Boolean,default:!0},hljs:Object,uri:Boolean,inline:Boolean,wordWrap:Boolean,showLineNumbers:Boolean,internalFontSize:Number,internalNoHighlight:Boolean}),we=W({name:"Code",props:be,setup(t,{slots:e}){const{internalNoHighlight:a}=t,{mergedClsPrefixRef:f,inlineThemeDisabled:p}=ee(),g=$(null),j=a?{value:void 0}:fe(t),R=(l,u,r)=>{const{value:c}=j;return!c||!(l&&c.getLanguage(l))?null:c.highlight(r?u.trim():u,{language:l}).value},i=_(()=>t.inline||t.wordWrap?!1:t.showLineNumbers),b=()=>{if(e.default)return;const{value:l}=g;if(!l)return;const{language:u}=t,r=t.uri?window.decodeURIComponent(t.code):t.code;if(u){const h=R(u,r,t.trim);if(h!==null){if(t.inline)l.innerHTML=h;else{const o=l.querySelector(".__code__");o&&l.removeChild(o);const n=document.createElement("pre");n.className="__code__",n.innerHTML=h,l.appendChild(n)}return}}if(t.inline){l.textContent=r;return}const c=l.querySelector(".__code__");if(c)c.textContent=r;else{const h=document.createElement("pre");h.className="__code__",h.textContent=r,l.innerHTML="",l.appendChild(h)}};U(b),T(E(t,"language"),b),T(E(t,"code"),b),a||T(j,b);const C=O("Code","-code",ve,ge,t,f),k=_(()=>{const{common:{cubicBezierEaseInOut:l,fontFamilyMono:u},self:{textColor:r,fontSize:c,fontWeightStrong:h,lineNumberTextColor:o,"mono-3":n,"hue-1":s,"hue-2":d,"hue-3":F,"hue-4":q,"hue-5":A,"hue-5-2":D,"hue-6":J,"hue-6-2":G}}=C.value,{internalFontSize:H}=t;return{"--n-font-size":H?`${H}px`:c,"--n-font-family":u,"--n-font-weight-strong":h,"--n-bezier":l,"--n-text-color":r,"--n-mono-3":n,"--n-hue-1":s,"--n-hue-2":d,"--n-hue-3":F,"--n-hue-4":q,"--n-hue-5":A,"--n-hue-5-2":D,"--n-hue-6":J,"--n-hue-6-2":G,"--n-line-number-text-color":o}}),w=p?te("code",_(()=>`${t.internalFontSize||"a"}`),k,t):void 0;return{mergedClsPrefix:f,codeRef:g,mergedShowLineNumbers:i,lineNumbers:_(()=>{let l=1;const u=[];let r=!1;for(const c of t.code)c===`
`?(r=!0,u.push(l++)):r=!1;return r||u.push(l++),u.join(`
`)}),cssVars:p?void 0:k,themeClass:w==null?void 0:w.themeClass,onRender:w==null?void 0:w.onRender}},render(){var t,e;const{mergedClsPrefix:a,wordWrap:f,mergedShowLineNumbers:p,onRender:g}=this;return g==null||g(),S("code",{class:[`${a}-code`,this.themeClass,f&&`${a}-code--word-wrap`,p&&`${a}-code--show-line-numbers`],style:this.cssVars,ref:"codeRef"},p?S("pre",{class:`${a}-code__line-numbers`},this.lineNumbers):null,(e=(t=this.$slots).default)===null||e===void 0?void 0:e.call(t))}}),We=W({__name:"CrawlView",setup(t){const e=oe(),a=ue(),f=$(!1),p=$([]),g=$(0),j=$(1),R=[{label:"Codeforces",value:"codeforces"},{label:"AtCoder",value:"atcoder"},{label:"牛客",value:"nowcoder"}],i=ae({platform:"codeforces",count:20,months_back:2}),b=$(!1);async function C(){f.value=!0;try{const o=await ne({page:j.value,page_size:20});p.value=o.results,g.value=o.count}finally{f.value=!1}}async function k(){var o,n;b.value=!0;try{const s={platform:i.platform};i.platform==="nowcoder"?s.months_back=i.months_back:s.count=i.count,await re(s),a.success("已派发爬取任务（worker 启动后自动执行）"),await C()}catch(s){a.error(((n=(o=s==null?void 0:s.response)==null?void 0:o.data)==null?void 0:n.detail)||"触发失败")}finally{b.value=!1}}async function w(){var o,n;try{await se(),a.success("已触发全量重算（worker 异步执行）")}catch(s){a.error(((n=(o=s==null?void 0:s.response)==null?void 0:o.data)==null?void 0:n.detail)||"重算触发失败（需超级管理员）")}}function l(o){return o==="success"?"success":o==="failed"||o==="partial"?"error":o==="running"?"info":"warning"}const u=[{title:"ID",key:"id",width:70},{title:"平台",key:"platform_display"},{title:"状态",key:"status",render:o=>S(he,{size:"small",type:l(o.status)},{default:()=>o.status_display})},{title:"入库记录",key:"participation_count",width:90},{title:"排除作弊",key:"cheater_count",width:90},{title:"触发人",key:"triggered_by_name"},{title:"创建时间",key:"created_at",width:170},{title:"日志",key:"log",render:o=>S(L,{size:"small",onClick:()=>h(o)},{default:()=>"查看"})}],r=$(!1),c=$("");function h(o){c.value=o.log||o.error_message||"（无日志）",r.value=!0}return U(C),(o,n)=>{const s=ie("n-modal");return z(),N(m(I),{vertical:"",size:16},{default:y(()=>[v(m(V),{title:"触发爬取"},{default:y(()=>[v(m(I),{align:"end"},{default:y(()=>[v(m(ce),{value:i.platform,"onUpdate:value":n[0]||(n[0]=d=>i.platform=d),options:R,style:{width:"160px"}},null,8,["value"]),i.platform!=="nowcoder"?(z(),N(m(M),{key:0,value:i.count,"onUpdate:value":n[1]||(n[1]=d=>i.count=d),min:1,max:200,placeholder:"抓取场数",style:{width:"140px"}},null,8,["value"])):(z(),N(m(M),{key:1,value:i.months_back,"onUpdate:value":n[2]||(n[2]=d=>i.months_back=d),min:1,max:12,placeholder:"最近 N 个月",style:{width:"140px"}},null,8,["value"])),v(m(L),{type:"primary",loading:b.value,onClick:k},{default:y(()=>[...n[4]||(n[4]=[B(" 触发爬取 ",-1)])]),_:1},8,["loading"]),m(e).isSuperAdmin?(z(),N(m(L),{key:2,onClick:w},{default:y(()=>[...n[5]||(n[5]=[B(" 触发全量重算 ",-1)])]),_:1})):le("",!0)]),_:1}),v(m(de),{depth:"3",style:{display:"block","margin-top":"8px"}},{default:y(()=>[...n[6]||(n[6]=[B(" 爬取任务由 Celery worker 消费（队列 crawl / crawl_slow）。未启动 worker 时任务会进入队列，启动后自动执行。 重算由超级管理员触发，依赖参与记录入库后生效。 ",-1)])]),_:1})]),_:1}),v(m(V),{title:"爬取任务"},{default:y(()=>[v(m(me),{columns:u,data:p.value,loading:f.value,pagination:{page:j.value,pageSize:20,itemCount:g.value,onUpdatePage:d=>{j.value=d,C()}},"row-key":d=>d.id},null,8,["data","loading","pagination","row-key"])]),_:1}),v(s,{show:r.value,"onUpdate:show":n[3]||(n[3]=d=>r.value=d),title:"执行日志",preset:"card",style:{width:"640px"}},{default:y(()=>[v(m(we),{code:c.value,"word-wrap":""},null,8,["code"])]),_:1},8,["show"])]),_:1})}}});export{We as default};
