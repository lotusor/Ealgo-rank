import{I as b,J as c,a9 as R,ab as v,b6 as ee,b7 as te,d as P,y as l,V as J,aj as A,G as T,_ as F,b8 as re,p as G,H as ie,a5 as ae,a3 as ne,Z as le,a6 as oe,b9 as se,F as N,u as de,m as ce,g,w as a,b as i,ba as ue,bb as ve,bc as he,r as S,a as n,N as w,c as B,aH as D,k as p,o as u,t as C}from"./index-D9Ac4DhN.js";import{u as fe}from"./use-message-DAaYSu_t.js";import{N as E}from"./Space-n_UDLqns.js";import{a as k,N as H}from"./Grid-CrNEPBM7.js";import{N as I}from"./Statistic-sHfTwyoq.js";import{N as $}from"./text-CPo-BLrE.js";import{N as M}from"./Tag-BGB5zlRo.js";import"./use-compitable-WOsnsMpP.js";const me=b([c("list",`
 --n-merged-border-color: var(--n-border-color);
 --n-merged-color: var(--n-color);
 --n-merged-color-hover: var(--n-color-hover);
 margin: 0;
 font-size: var(--n-font-size);
 transition:
 background-color .3s var(--n-bezier),
 color .3s var(--n-bezier),
 border-color .3s var(--n-bezier);
 padding: 0;
 list-style-type: none;
 color: var(--n-text-color);
 background-color: var(--n-merged-color);
 `,[R("show-divider",[c("list-item",[b("&:not(:last-child)",[v("divider",`
 background-color: var(--n-merged-border-color);
 `)])])]),R("clickable",[c("list-item",`
 cursor: pointer;
 `)]),R("bordered",`
 border: 1px solid var(--n-merged-border-color);
 border-radius: var(--n-border-radius);
 `),R("hoverable",[c("list-item",`
 border-radius: var(--n-border-radius);
 `,[b("&:hover",`
 background-color: var(--n-merged-color-hover);
 `,[v("divider",`
 background-color: transparent;
 `)])])]),R("bordered, hoverable",[c("list-item",`
 padding: 12px 20px;
 `),v("header, footer",`
 padding: 12px 20px;
 `)]),v("header, footer",`
 padding: 12px 0;
 box-sizing: border-box;
 transition: border-color .3s var(--n-bezier);
 `,[b("&:not(:last-child)",`
 border-bottom: 1px solid var(--n-merged-border-color);
 `)]),c("list-item",`
 position: relative;
 padding: 12px 0; 
 box-sizing: border-box;
 display: flex;
 flex-wrap: nowrap;
 align-items: center;
 transition:
 background-color .3s var(--n-bezier),
 border-color .3s var(--n-bezier);
 `,[v("prefix",`
 margin-right: 20px;
 flex: 0;
 `),v("suffix",`
 margin-left: 20px;
 flex: 0;
 `),v("main",`
 flex: 1;
 `),v("divider",`
 height: 1px;
 position: absolute;
 bottom: 0;
 left: 0;
 right: 0;
 background-color: transparent;
 transition: background-color .3s var(--n-bezier);
 pointer-events: none;
 `)])]),ee(c("list",`
 --n-merged-color-hover: var(--n-color-hover-modal);
 --n-merged-color: var(--n-color-modal);
 --n-merged-border-color: var(--n-border-color-modal);
 `)),te(c("list",`
 --n-merged-color-hover: var(--n-color-hover-popover);
 --n-merged-color: var(--n-color-popover);
 --n-merged-border-color: var(--n-border-color-popover);
 `))]),ge=Object.assign(Object.assign({},T.props),{size:{type:String,default:"medium"},bordered:Boolean,clickable:Boolean,hoverable:Boolean,showDivider:{type:Boolean,default:!0}}),K=ie("n-list"),O=P({name:"List",props:ge,slots:Object,setup(t){const{mergedClsPrefixRef:e,inlineThemeDisabled:o,mergedRtlRef:h}=J(t),x=A("List",h,e),_=T("List","-list",me,re,t,e);ae(K,{showDividerRef:ne(t,"showDivider"),mergedClsPrefixRef:e});const y=G(()=>{const{common:{cubicBezierEaseInOut:s},self:{fontSize:d,textColor:r,color:m,colorModal:z,colorPopover:j,borderColor:W,borderColorModal:Z,borderColorPopover:q,borderRadius:Q,colorHover:U,colorHoverModal:X,colorHoverPopover:Y}}=_.value;return{"--n-font-size":d,"--n-bezier":s,"--n-text-color":r,"--n-color":m,"--n-border-radius":Q,"--n-border-color":W,"--n-border-color-modal":Z,"--n-border-color-popover":q,"--n-color-modal":z,"--n-color-popover":j,"--n-color-hover":U,"--n-color-hover-modal":X,"--n-color-hover-popover":Y}}),f=o?F("list",void 0,y,t):void 0;return{mergedClsPrefix:e,rtlEnabled:x,cssVars:o?void 0:y,themeClass:f==null?void 0:f.themeClass,onRender:f==null?void 0:f.onRender}},render(){var t;const{$slots:e,mergedClsPrefix:o,onRender:h}=this;return h==null||h(),l("ul",{class:[`${o}-list`,this.rtlEnabled&&`${o}-list--rtl`,this.bordered&&`${o}-list--bordered`,this.showDivider&&`${o}-list--show-divider`,this.hoverable&&`${o}-list--hoverable`,this.clickable&&`${o}-list--clickable`,this.themeClass],style:this.cssVars},e.header?l("div",{class:`${o}-list__header`},e.header()):null,(t=e.default)===null||t===void 0?void 0:t.call(e),e.footer?l("div",{class:`${o}-list__footer`},e.footer()):null)}}),L=P({name:"ListItem",slots:Object,setup(){const t=le(K,null);return t||oe("list-item","`n-list-item` must be placed in `n-list`."),{showDivider:t.showDividerRef,mergedClsPrefix:t.mergedClsPrefixRef}},render(){const{$slots:t,mergedClsPrefix:e}=this;return l("li",{class:`${e}-list-item`},t.prefix?l("div",{class:`${e}-list-item__prefix`},t.prefix()):null,t.default?l("div",{class:`${e}-list-item__main`},t):null,t.suffix?l("div",{class:`${e}-list-item__suffix`},t.suffix()):null,this.showDivider&&l("div",{class:`${e}-list-item__divider`}))}}),pe=c("thing",`
 display: flex;
 transition: color .3s var(--n-bezier);
 font-size: var(--n-font-size);
 color: var(--n-text-color);
`,[c("thing-avatar",`
 margin-right: 12px;
 margin-top: 2px;
 `),c("thing-avatar-header-wrapper",`
 display: flex;
 flex-wrap: nowrap;
 `,[c("thing-header-wrapper",`
 flex: 1;
 `)]),c("thing-main",`
 flex-grow: 1;
 `,[c("thing-header",`
 display: flex;
 margin-bottom: 4px;
 justify-content: space-between;
 align-items: center;
 `,[v("title",`
 font-size: 16px;
 font-weight: var(--n-title-font-weight);
 transition: color .3s var(--n-bezier);
 color: var(--n-title-text-color);
 `)]),v("description",[b("&:not(:last-child)",`
 margin-bottom: 4px;
 `)]),v("content",[b("&:not(:first-child)",`
 margin-top: 12px;
 `)]),v("footer",[b("&:not(:first-child)",`
 margin-top: 12px;
 `)]),v("action",[b("&:not(:first-child)",`
 margin-top: 12px;
 `)])])]),be=Object.assign(Object.assign({},T.props),{title:String,titleExtra:String,description:String,descriptionClass:String,descriptionStyle:[String,Object],content:String,contentClass:String,contentStyle:[String,Object],contentIndented:Boolean}),V=P({name:"Thing",props:be,slots:Object,setup(t,{slots:e}){const{mergedClsPrefixRef:o,inlineThemeDisabled:h,mergedRtlRef:x}=J(t),_=T("Thing","-thing",pe,se,t,o),y=A("Thing",x,o),f=G(()=>{const{self:{titleTextColor:d,textColor:r,titleFontWeight:m,fontSize:z},common:{cubicBezierEaseInOut:j}}=_.value;return{"--n-bezier":j,"--n-font-size":z,"--n-text-color":r,"--n-title-font-weight":m,"--n-title-text-color":d}}),s=h?F("thing",void 0,f,t):void 0;return()=>{var d;const{value:r}=o,m=y?y.value:!1;return(d=s==null?void 0:s.onRender)===null||d===void 0||d.call(s),l("div",{class:[`${r}-thing`,s==null?void 0:s.themeClass,m&&`${r}-thing--rtl`],style:h?void 0:f.value},e.avatar&&t.contentIndented?l("div",{class:`${r}-thing-avatar`},e.avatar()):null,l("div",{class:`${r}-thing-main`},!t.contentIndented&&(e.header||t.title||e["header-extra"]||t.titleExtra||e.avatar)?l("div",{class:`${r}-thing-avatar-header-wrapper`},e.avatar?l("div",{class:`${r}-thing-avatar`},e.avatar()):null,e.header||t.title||e["header-extra"]||t.titleExtra?l("div",{class:`${r}-thing-header-wrapper`},l("div",{class:`${r}-thing-header`},e.header||t.title?l("div",{class:`${r}-thing-header__title`},e.header?e.header():t.title):null,e["header-extra"]||t.titleExtra?l("div",{class:`${r}-thing-header__extra`},e["header-extra"]?e["header-extra"]():t.titleExtra):null),e.description||t.description?l("div",{class:[`${r}-thing-main__description`,t.descriptionClass],style:t.descriptionStyle},e.description?e.description():t.description):null):null):l(N,null,e.header||t.title||e["header-extra"]||t.titleExtra?l("div",{class:`${r}-thing-header`},e.header||t.title?l("div",{class:`${r}-thing-header__title`},e.header?e.header():t.title):null,e["header-extra"]||t.titleExtra?l("div",{class:`${r}-thing-header__extra`},e["header-extra"]?e["header-extra"]():t.titleExtra):null):null,e.description||t.description?l("div",{class:[`${r}-thing-main__description`,t.descriptionClass],style:t.descriptionStyle},e.description?e.description():t.description):null),e.default||t.content?l("div",{class:[`${r}-thing-main__content`,t.contentClass],style:t.contentStyle},e.default?e.default():t.content):null,e.footer?l("div",{class:`${r}-thing-main__footer`},e.footer()):null,e.action?l("div",{class:`${r}-thing-main__action`},e.action()):null))}}}),Re=P({__name:"DashboardView",setup(t){de();const e=fe(),o=S({applications:0,crawlJobs:0,participations:0}),h=S([]),x=S([]),_=S([]);async function y(){var s,d;try{const[r,m,z]=await Promise.all([ue({page_size:5}),ve({page_size:5}),he({page_size:5,is_excluded:"false"})]);o.value={applications:r.count,crawlJobs:m.count,participations:z.count},h.value=r.results,x.value=m.results,_.value=z.results}catch(r){e.error(((d=(s=r==null?void 0:r.response)==null?void 0:s.data)==null?void 0:d.detail)||"加载失败")}}ce(y);function f(s){return s==="approved"?"success":s==="rejected"||s==="cancelled"?"error":"warning"}return(s,d)=>(u(),g(i(E),{vertical:"",size:16},{default:a(()=>[n(i(H),{cols:3,"x-gap":16,responsive:"screen","item-responsive":""},{default:a(()=>[n(i(k),{span:"3 m:1"},{default:a(()=>[n(i(w),null,{default:a(()=>[n(i(I),{label:"管理员申请",value:o.value.applications},null,8,["value"])]),_:1})]),_:1}),n(i(k),{span:"3 m:1"},{default:a(()=>[n(i(w),null,{default:a(()=>[n(i(I),{label:"爬取任务",value:o.value.crawlJobs},null,8,["value"])]),_:1})]),_:1}),n(i(k),{span:"3 m:1"},{default:a(()=>[n(i(w),null,{default:a(()=>[n(i(I),{label:"参赛记录",value:o.value.participations},null,8,["value"])]),_:1})]),_:1})]),_:1}),n(i(H),{cols:3,"x-gap":16,responsive:"screen","item-responsive":""},{default:a(()=>[n(i(k),{span:"3 m:1"},{default:a(()=>[n(i(w),{title:"最新申请",segmented:{content:!0}},{default:a(()=>[h.value.length?(u(),g(i(O),{key:0},{default:a(()=>[(u(!0),B(N,null,D(h.value,r=>(u(),g(i(L),{key:r.id},{default:a(()=>{var m;return[n(i(V),{title:((m=r.school)==null?void 0:m.name)||"未知学校"},{description:a(()=>[n(i(E),{size:6},{default:a(()=>[n(i(M),{size:"small",type:f(r.status)},{default:a(()=>[p(C(r.status_display),1)]),_:2},1032,["type"]),n(i($),{depth:"3"},{default:a(()=>[p(C(r.applicant.username),1)]),_:2},1024)]),_:2},1024)]),_:2},1032,["title"])]}),_:2},1024))),128))]),_:1})):(u(),g(i($),{key:1,depth:"3"},{default:a(()=>[...d[0]||(d[0]=[p("暂无数据",-1)])]),_:1}))]),_:1})]),_:1}),n(i(k),{span:"3 m:1"},{default:a(()=>[n(i(w),{title:"最近爬取",segmented:{content:!0}},{default:a(()=>[x.value.length?(u(),g(i(O),{key:0},{default:a(()=>[(u(!0),B(N,null,D(x.value,r=>(u(),g(i(L),{key:r.id},{default:a(()=>[n(i(V),{title:`${r.platform_display} #${r.id}`},{description:a(()=>[n(i(E),{size:6},{default:a(()=>[n(i(M),{size:"small",type:f(r.status)},{default:a(()=>[p(C(r.status_display),1)]),_:2},1032,["type"]),n(i($),{depth:"3"},{default:a(()=>[p("入库 "+C(r.participation_count),1)]),_:2},1024)]),_:2},1024)]),_:2},1032,["title"])]),_:2},1024))),128))]),_:1})):(u(),g(i($),{key:1,depth:"3"},{default:a(()=>[...d[1]||(d[1]=[p("暂无数据",-1)])]),_:1}))]),_:1})]),_:1}),n(i(k),{span:"3 m:1"},{default:a(()=>[n(i(w),{title:"最近参赛记录",segmented:{content:!0}},{default:a(()=>[_.value.length?(u(),g(i(O),{key:0},{default:a(()=>[(u(!0),B(N,null,D(_.value,r=>(u(),g(i(L),{key:r.id},{default:a(()=>[n(i(V),{title:r.contest_name},{description:a(()=>[n(i(E),{size:6},{default:a(()=>[n(i($),{depth:"3"},{default:a(()=>[p(C(r.user_username||r.handle),1)]),_:2},1024),n(i($),{depth:"3"},{default:a(()=>[p("#"+C(r.rank),1)]),_:2},1024)]),_:2},1024)]),_:2},1032,["title"])]),_:2},1024))),128))]),_:1})):(u(),g(i($),{key:1,depth:"3"},{default:a(()=>[...d[2]||(d[2]=[p("暂无数据",-1)])]),_:1}))]),_:1})]),_:1})]),_:1})]),_:1}))}});export{Re as default};
