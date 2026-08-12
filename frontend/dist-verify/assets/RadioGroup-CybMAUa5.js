import{Z as ee,V as G,ak as $,r as k,ag as U,a0 as B,H as oe,a3 as T,J as V,ab as g,a9 as x,I as _,M as E,d as te,aR as re,y as A,G as j,aj as ne,_ as ae,p as D,bD as ie,av as P,a5 as de}from"./index-D9Ac4DhN.js";import{u as H}from"./get-CfFPLqoW.js";import{g as se}from"./Space-n_UDLqns.js";function he(e,o){if(!e)return;const t=document.createElement("a");t.href=e,o!==void 0&&(t.download=o),document.body.appendChild(t),t.click(),document.body.removeChild(t)}const ge={name:String,value:{type:[String,Number,Boolean],default:"on"},checked:{type:Boolean,default:void 0},defaultChecked:Boolean,disabled:{type:Boolean,default:void 0},label:String,size:String,onUpdateChecked:[Function,Array],"onUpdate:checked":[Function,Array],checkedValue:{type:Boolean,default:void 0}},N=oe("n-radio-group");function pe(e){const o=ee(N,null),{mergedClsPrefixRef:t,mergedComponentPropsRef:d}=G(e),i=$(e,{mergedSize(r){var n,a;const{size:v}=e;if(v!==void 0)return v;if(o){const{mergedSizeRef:{value:F}}=o;if(F!==void 0)return F}if(r)return r.mergedSize.value;const I=(a=(n=d==null?void 0:d.value)===null||n===void 0?void 0:n.Radio)===null||a===void 0?void 0:a.size;return I||"medium"},mergedDisabled(r){return!!(e.disabled||o!=null&&o.disabledRef.value||r!=null&&r.disabled.value)}}),{mergedSizeRef:f,mergedDisabledRef:s}=i,l=k(null),u=k(null),h=k(e.defaultChecked),p=T(e,"checked"),m=H(p,h),c=U(()=>o?o.valueRef.value===e.value:m.value),R=U(()=>{const{name:r}=e;if(r!==void 0)return r;if(o)return o.nameRef.value}),b=k(!1);function y(){if(o){const{doUpdateValue:r}=o,{value:n}=e;B(r,n)}else{const{onUpdateChecked:r,"onUpdate:checked":n}=e,{nTriggerFormInput:a,nTriggerFormChange:v}=i;r&&B(r,!0),n&&B(n,!0),a(),v(),h.value=!0}}function z(){s.value||c.value||y()}function S(){z(),l.value&&(l.value.checked=c.value)}function w(){b.value=!1}function C(){b.value=!0}return{mergedClsPrefix:o?o.mergedClsPrefixRef:t,inputRef:l,labelRef:u,mergedName:R,mergedDisabled:s,renderSafeChecked:c,focus:b,mergedSize:f,handleRadioInputChange:S,handleRadioInputBlur:w,handleRadioInputFocus:C}}const le=V("radio-group",`
 display: inline-block;
 font-size: var(--n-font-size);
`,[g("splitor",`
 display: inline-block;
 vertical-align: bottom;
 width: 1px;
 transition:
 background-color .3s var(--n-bezier),
 opacity .3s var(--n-bezier);
 background: var(--n-button-border-color);
 `,[x("checked",{backgroundColor:"var(--n-button-border-color-active)"}),x("disabled",{opacity:"var(--n-opacity-disabled)"})]),x("button-group",`
 white-space: nowrap;
 height: var(--n-height);
 line-height: var(--n-height);
 `,[V("radio-button",{height:"var(--n-height)",lineHeight:"var(--n-height)"}),g("splitor",{height:"var(--n-height)"})]),V("radio-button",`
 vertical-align: bottom;
 outline: none;
 position: relative;
 user-select: none;
 -webkit-user-select: none;
 display: inline-block;
 box-sizing: border-box;
 padding-left: 14px;
 padding-right: 14px;
 white-space: nowrap;
 transition:
 background-color .3s var(--n-bezier),
 opacity .3s var(--n-bezier),
 border-color .3s var(--n-bezier),
 color .3s var(--n-bezier);
 background: var(--n-button-color);
 color: var(--n-button-text-color);
 border-top: 1px solid var(--n-button-border-color);
 border-bottom: 1px solid var(--n-button-border-color);
 `,[V("radio-input",`
 pointer-events: none;
 position: absolute;
 border: 0;
 border-radius: inherit;
 left: 0;
 right: 0;
 top: 0;
 bottom: 0;
 opacity: 0;
 z-index: 1;
 `),g("state-border",`
 z-index: 1;
 pointer-events: none;
 position: absolute;
 box-shadow: var(--n-button-box-shadow);
 transition: box-shadow .3s var(--n-bezier);
 left: -1px;
 bottom: -1px;
 right: -1px;
 top: -1px;
 `),_("&:first-child",`
 border-top-left-radius: var(--n-button-border-radius);
 border-bottom-left-radius: var(--n-button-border-radius);
 border-left: 1px solid var(--n-button-border-color);
 `,[g("state-border",`
 border-top-left-radius: var(--n-button-border-radius);
 border-bottom-left-radius: var(--n-button-border-radius);
 `)]),_("&:last-child",`
 border-top-right-radius: var(--n-button-border-radius);
 border-bottom-right-radius: var(--n-button-border-radius);
 border-right: 1px solid var(--n-button-border-color);
 `,[g("state-border",`
 border-top-right-radius: var(--n-button-border-radius);
 border-bottom-right-radius: var(--n-button-border-radius);
 `)]),E("disabled",`
 cursor: pointer;
 `,[_("&:hover",[g("state-border",`
 transition: box-shadow .3s var(--n-bezier);
 box-shadow: var(--n-button-box-shadow-hover);
 `),E("checked",{color:"var(--n-button-text-color-hover)"})]),x("focus",[_("&:not(:active)",[g("state-border",{boxShadow:"var(--n-button-box-shadow-focus)"})])])]),x("checked",`
 background: var(--n-button-color-active);
 color: var(--n-button-text-color-active);
 border-color: var(--n-button-border-color-active);
 `),x("disabled",`
 cursor: not-allowed;
 opacity: var(--n-opacity-disabled);
 `)])]);function ue(e,o,t){var d;const i=[];let f=!1;for(let s=0;s<e.length;++s){const l=e[s],u=(d=l.type)===null||d===void 0?void 0:d.name;u==="RadioButton"&&(f=!0);const h=l.props;if(u!=="RadioButton"){i.push(l);continue}if(s===0)i.push(l);else{const p=i[i.length-1].props,m=o===p.value,c=p.disabled,R=o===h.value,b=h.disabled,y=(m?2:0)+(c?0:1),z=(R?2:0)+(b?0:1),S={[`${t}-radio-group__splitor--disabled`]:c,[`${t}-radio-group__splitor--checked`]:m},w={[`${t}-radio-group__splitor--disabled`]:b,[`${t}-radio-group__splitor--checked`]:R},C=y<z?w:S;i.push(A("div",{class:[`${t}-radio-group__splitor`,C]}),l)}}return{children:i,isButtonGroup:f}}const ce=Object.assign(Object.assign({},j.props),{name:String,value:[String,Number,Boolean],defaultValue:{type:[String,Number,Boolean],default:null},size:String,disabled:{type:Boolean,default:void 0},"onUpdate:value":[Function,Array],onUpdateValue:[Function,Array]}),me=te({name:"RadioGroup",props:ce,setup(e){const o=k(null),{mergedSizeRef:t,mergedDisabledRef:d,nTriggerFormChange:i,nTriggerFormInput:f,nTriggerFormBlur:s,nTriggerFormFocus:l}=$(e),{mergedClsPrefixRef:u,inlineThemeDisabled:h,mergedRtlRef:p}=G(e),m=j("Radio","-radio-group",le,ie,e,u),c=k(e.defaultValue),R=T(e,"value"),b=H(R,c);function y(n){const{onUpdateValue:a,"onUpdate:value":v}=e;a&&B(a,n),v&&B(v,n),c.value=n,i(),f()}function z(n){const{value:a}=o;a&&(a.contains(n.relatedTarget)||l())}function S(n){const{value:a}=o;a&&(a.contains(n.relatedTarget)||s())}de(N,{mergedClsPrefixRef:u,nameRef:T(e,"name"),valueRef:b,disabledRef:d,mergedSizeRef:t,doUpdateValue:y});const w=ne("Radio",p,u),C=D(()=>{const{value:n}=t,{common:{cubicBezierEaseInOut:a},self:{buttonBorderColor:v,buttonBorderColorActive:I,buttonBorderRadius:F,buttonBoxShadow:M,buttonBoxShadowFocus:K,buttonBoxShadowHover:O,buttonColor:J,buttonColorActive:L,buttonTextColor:Z,buttonTextColorActive:q,buttonTextColorHover:Q,opacityDisabled:W,[P("buttonHeight",n)]:X,[P("fontSize",n)]:Y}}=m.value;return{"--n-font-size":Y,"--n-bezier":a,"--n-button-border-color":v,"--n-button-border-color-active":I,"--n-button-border-radius":F,"--n-button-box-shadow":M,"--n-button-box-shadow-focus":K,"--n-button-box-shadow-hover":O,"--n-button-color":J,"--n-button-color-active":L,"--n-button-text-color":Z,"--n-button-text-color-hover":Q,"--n-button-text-color-active":q,"--n-height":X,"--n-opacity-disabled":W}}),r=h?ae("radio-group",D(()=>t.value[0]),C,e):void 0;return{selfElRef:o,rtlEnabled:w,mergedClsPrefix:u,mergedValue:b,handleFocusout:S,handleFocusin:z,cssVars:h?void 0:C,themeClass:r==null?void 0:r.themeClass,onRender:r==null?void 0:r.onRender}},render(){var e;const{mergedValue:o,mergedClsPrefix:t,handleFocusin:d,handleFocusout:i}=this,{children:f,isButtonGroup:s}=ue(re(se(this)),o,t);return(e=this.onRender)===null||e===void 0||e.call(this),A("div",{onFocusin:d,onFocusout:i,ref:"selfElRef",class:[`${t}-radio-group`,this.rtlEnabled&&`${t}-radio-group--rtl`,this.themeClass,s&&`${t}-radio-group--button-group`],style:this.cssVars},f)}});export{me as N,he as d,ge as r,pe as s};
