import{I as g,J as p,K as w,a9 as y,d as b,y as c,aC as T,T as N,V as R,G as C,_ as V,p as m,a8 as $,aD as B,r as v,aE as I,aF as j,av as O,u as P,m as E,c as A,a as f,w as _,b as h,N as D,e as W,f as K,l as L,t as M,o as q}from"./index-D9Ac4DhN.js";import{u as H}from"./use-compitable-WOsnsMpP.js";import{N as F}from"./Space-n_UDLqns.js";import{_ as G}from"./_plugin-vue_export-helper-DlAUqK2U.js";const J=g([g("@keyframes spin-rotate",`
 from {
 transform: rotate(0);
 }
 to {
 transform: rotate(360deg);
 }
 `),p("spin-container",`
 position: relative;
 `,[p("spin-body",`
 position: absolute;
 top: 50%;
 left: 50%;
 transform: translateX(-50%) translateY(-50%);
 `,[w()])]),p("spin-body",`
 display: inline-flex;
 align-items: center;
 justify-content: center;
 flex-direction: column;
 `),p("spin",`
 display: inline-flex;
 height: var(--n-size);
 width: var(--n-size);
 font-size: var(--n-size);
 color: var(--n-color);
 `,[y("rotate",`
 animation: spin-rotate 2s linear infinite;
 `)]),p("spin-description",`
 display: inline-block;
 font-size: var(--n-font-size);
 color: var(--n-text-color);
 transition: color .3s var(--n-bezier);
 margin-top: 8px;
 `),p("spin-content",`
 opacity: 1;
 transition: opacity .3s var(--n-bezier);
 pointer-events: all;
 `,[y("spinning",`
 user-select: none;
 -webkit-user-select: none;
 pointer-events: none;
 opacity: var(--n-opacity-spinning);
 `)])]),U={small:20,medium:18,large:16},X=Object.assign(Object.assign(Object.assign({},C.props),{contentClass:String,contentStyle:[Object,String],description:String,size:{type:[String,Number],default:"medium"},show:{type:Boolean,default:!0},rotate:{type:Boolean,default:!0},spinning:{type:Boolean,validator:()=>!0,default:void 0},delay:Number}),I),Y=b({name:"Spin",props:X,slots:Object,setup(n){const{mergedClsPrefixRef:l,inlineThemeDisabled:t}=R(n),e=C("Spin","-spin",J,B,n,l),o=m(()=>{const{size:s}=n,{common:{cubicBezierEaseInOut:r},self:u}=e.value,{opacitySpinning:k,color:S,textColor:z}=u,x=typeof s=="number"?j(s):u[O("size",s)];return{"--n-bezier":r,"--n-opacity-spinning":k,"--n-size":x,"--n-color":S,"--n-text-color":z}}),a=t?V("spin",m(()=>{const{size:s}=n;return typeof s=="number"?String(s):s[0]}),o,n):void 0,d=H(n,["spinning","show"]),i=v(!1);return $(s=>{let r;if(d.value){const{delay:u}=n;if(u){r=window.setTimeout(()=>{i.value=!0},u),s(()=>{clearTimeout(r)});return}}i.value=d.value}),{mergedClsPrefix:l,active:i,mergedStrokeWidth:m(()=>{const{strokeWidth:s}=n;if(s!==void 0)return s;const{size:r}=n;return U[typeof r=="number"?"medium":r]}),cssVars:t?void 0:o,themeClass:a==null?void 0:a.themeClass,onRender:a==null?void 0:a.onRender}},render(){var n,l;const{$slots:t,mergedClsPrefix:e,description:o}=this,a=t.icon&&this.rotate,d=(o||t.description)&&c("div",{class:`${e}-spin-description`},o||((n=t.description)===null||n===void 0?void 0:n.call(t))),i=t.icon?c("div",{class:[`${e}-spin-body`,this.themeClass]},c("div",{class:[`${e}-spin`,a&&`${e}-spin--rotate`],style:t.default?"":this.cssVars},t.icon()),d):c("div",{class:[`${e}-spin-body`,this.themeClass]},c(T,{clsPrefix:e,style:t.default?"":this.cssVars,stroke:this.stroke,"stroke-width":this.mergedStrokeWidth,radius:this.radius,scale:this.scale,class:`${e}-spin`}),d);return(l=this.onRender)===null||l===void 0||l.call(this),t.default?c("div",{class:[`${e}-spin-container`,this.themeClass],style:this.cssVars},c("div",{class:[`${e}-spin-content`,this.active&&`${e}-spin-content--spinning`,this.contentClass],style:this.contentStyle},t),c(N,{name:"fade-in-transition"},{default:()=>this.active?i:null})):i}}),Q={class:"auth-wrap"},Z={style:{"font-size":"13px",opacity:"0.7"}},ee=b({__name:"AuthCallbackView",setup(n){const l=W(),t=K(),e=P(),o=v(!0),a=v("正在处理登录回调…");function d(){e.isProfileComplete?t.replace(e.isAdmin?{name:"dashboard"}:{name:"rankings"}):t.replace({name:"register-complete"})}return E(async()=>{const i=l.query;if(i.mock){const u={id:-1,username:i.username||"dev_passport_user",email:"",real_name:"",student_no:"",role:"normal",role_display:"普通用户",school:null,school_bound_at:null,platform_accounts:[],is_super_admin:!1,is_school_admin:!1,date_joined:""};e.token="mock",e.setUser(u),o.value=!1,t.replace({name:"register-complete"});return}const s=i.access,r=i.refresh;if(!s||!r){o.value=!1,a.value="回调参数缺失，请重新登录",setTimeout(()=>t.replace({name:"register"}),1200);return}localStorage.setItem("access_token",s),localStorage.setItem("refresh_token",r),e.token=s;try{await e.loadMe()}catch{e.logout(),o.value=!1,a.value="登录态校验失败，请重新登录",setTimeout(()=>t.replace({name:"login"}),1200);return}o.value=!1,d()}),(i,s)=>(q(),A("div",Q,[f(h(D),{style:{width:"360px"}},{default:_(()=>[f(h(F),{vertical:"",align:"center",size:12},{default:_(()=>[f(h(Y),{show:o.value},null,8,["show"]),L("span",Z,M(a.value),1)]),_:1})]),_:1})]))}}),ie=G(ee,[["__scopeId","data-v-974bf927"]]);export{ie as default};
