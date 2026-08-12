import{E as io,cE as ho,ay as r,J as go,a9 as u,ab as m,M as I,I as z,d as bo,A as V,y as x,aA as Co,V as vo,G as D,aj as uo,_ as po,p as F,r as fo,a0 as ko,av as h,aB as mo,cF as A,a5 as xo,a3 as yo,H as Po}from"./index-D9Ac4DhN.js";let S=[];const K=new WeakMap;function Io(){S.forEach(e=>e(...K.get(e))),S=[]}function Eo(e,...i){K.set(e,i),!S.includes(e)&&S.push(e)===1&&requestAnimationFrame(Io)}function zo(e){const{textColor2:i,primaryColorHover:l,primaryColorPressed:p,primaryColor:c,infoColor:d,successColor:n,warningColor:s,errorColor:t,baseColor:f,borderColor:k,opacityDisabled:b,tagColor:B,closeIconColor:y,closeIconColorHover:v,closeIconColorPressed:o,borderRadiusSmall:a,fontSizeMini:C,fontSizeTiny:g,fontSizeSmall:H,fontSizeMedium:$,heightMini:R,heightTiny:M,heightSmall:E,heightMedium:T,closeColorHover:_,closeColorPressed:O,buttonColor2Hover:W,buttonColor2Pressed:j,fontWeightStrong:w}=e;return Object.assign(Object.assign({},ho),{closeBorderRadius:a,heightTiny:R,heightSmall:M,heightMedium:E,heightLarge:T,borderRadius:a,opacityDisabled:b,fontSizeTiny:C,fontSizeSmall:g,fontSizeMedium:H,fontSizeLarge:$,fontWeightStrong:w,textColorCheckable:i,textColorHoverCheckable:i,textColorPressedCheckable:i,textColorChecked:f,colorCheckable:"#0000",colorHoverCheckable:W,colorPressedCheckable:j,colorChecked:c,colorCheckedHover:l,colorCheckedPressed:p,border:`1px solid ${k}`,textColor:i,color:B,colorBordered:"rgb(250, 250, 252)",closeIconColor:y,closeIconColorHover:v,closeIconColorPressed:o,closeColorHover:_,closeColorPressed:O,borderPrimary:`1px solid ${r(c,{alpha:.3})}`,textColorPrimary:c,colorPrimary:r(c,{alpha:.12}),colorBorderedPrimary:r(c,{alpha:.1}),closeIconColorPrimary:c,closeIconColorHoverPrimary:c,closeIconColorPressedPrimary:c,closeColorHoverPrimary:r(c,{alpha:.12}),closeColorPressedPrimary:r(c,{alpha:.18}),borderInfo:`1px solid ${r(d,{alpha:.3})}`,textColorInfo:d,colorInfo:r(d,{alpha:.12}),colorBorderedInfo:r(d,{alpha:.1}),closeIconColorInfo:d,closeIconColorHoverInfo:d,closeIconColorPressedInfo:d,closeColorHoverInfo:r(d,{alpha:.12}),closeColorPressedInfo:r(d,{alpha:.18}),borderSuccess:`1px solid ${r(n,{alpha:.3})}`,textColorSuccess:n,colorSuccess:r(n,{alpha:.12}),colorBorderedSuccess:r(n,{alpha:.1}),closeIconColorSuccess:n,closeIconColorHoverSuccess:n,closeIconColorPressedSuccess:n,closeColorHoverSuccess:r(n,{alpha:.12}),closeColorPressedSuccess:r(n,{alpha:.18}),borderWarning:`1px solid ${r(s,{alpha:.35})}`,textColorWarning:s,colorWarning:r(s,{alpha:.15}),colorBorderedWarning:r(s,{alpha:.12}),closeIconColorWarning:s,closeIconColorHoverWarning:s,closeIconColorPressedWarning:s,closeColorHoverWarning:r(s,{alpha:.12}),closeColorPressedWarning:r(s,{alpha:.18}),borderError:`1px solid ${r(t,{alpha:.23})}`,textColorError:t,colorError:r(t,{alpha:.1}),colorBorderedError:r(t,{alpha:.08}),closeIconColorError:t,closeIconColorHoverError:t,closeIconColorPressedError:t,closeColorHoverError:r(t,{alpha:.12}),closeColorPressedError:r(t,{alpha:.18})})}const So={common:io,self:zo},Bo={color:Object,type:{type:String,default:"default"},round:Boolean,size:String,closable:Boolean,disabled:{type:Boolean,default:void 0}},Ho=go("tag",`
 --n-close-margin: var(--n-close-margin-top) var(--n-close-margin-right) var(--n-close-margin-bottom) var(--n-close-margin-left);
 white-space: nowrap;
 position: relative;
 box-sizing: border-box;
 cursor: default;
 display: inline-flex;
 align-items: center;
 flex-wrap: nowrap;
 padding: var(--n-padding);
 border-radius: var(--n-border-radius);
 color: var(--n-text-color);
 background-color: var(--n-color);
 transition: 
 border-color .3s var(--n-bezier),
 background-color .3s var(--n-bezier),
 color .3s var(--n-bezier),
 box-shadow .3s var(--n-bezier),
 opacity .3s var(--n-bezier);
 line-height: 1;
 height: var(--n-height);
 font-size: var(--n-font-size);
`,[u("strong",`
 font-weight: var(--n-font-weight-strong);
 `),m("border",`
 pointer-events: none;
 position: absolute;
 left: 0;
 right: 0;
 top: 0;
 bottom: 0;
 border-radius: inherit;
 border: var(--n-border);
 transition: border-color .3s var(--n-bezier);
 `),m("icon",`
 display: flex;
 margin: 0 4px 0 0;
 color: var(--n-text-color);
 transition: color .3s var(--n-bezier);
 font-size: var(--n-avatar-size-override);
 `),m("avatar",`
 display: flex;
 margin: 0 6px 0 0;
 `),m("close",`
 margin: var(--n-close-margin);
 transition:
 background-color .3s var(--n-bezier),
 color .3s var(--n-bezier);
 `),u("round",`
 padding: 0 calc(var(--n-height) / 3);
 border-radius: calc(var(--n-height) / 2);
 `,[m("icon",`
 margin: 0 4px 0 calc((var(--n-height) - 8px) / -2);
 `),m("avatar",`
 margin: 0 6px 0 calc((var(--n-height) - 8px) / -2);
 `),u("closable",`
 padding: 0 calc(var(--n-height) / 4) 0 calc(var(--n-height) / 3);
 `)]),u("icon, avatar",[u("round",`
 padding: 0 calc(var(--n-height) / 3) 0 calc(var(--n-height) / 2);
 `)]),u("disabled",`
 cursor: not-allowed !important;
 opacity: var(--n-opacity-disabled);
 `),u("checkable",`
 cursor: pointer;
 box-shadow: none;
 color: var(--n-text-color-checkable);
 background-color: var(--n-color-checkable);
 `,[I("disabled",[z("&:hover","background-color: var(--n-color-hover-checkable);",[I("checked","color: var(--n-text-color-hover-checkable);")]),z("&:active","background-color: var(--n-color-pressed-checkable);",[I("checked","color: var(--n-text-color-pressed-checkable);")])]),u("checked",`
 color: var(--n-text-color-checked);
 background-color: var(--n-color-checked);
 `,[I("disabled",[z("&:hover","background-color: var(--n-color-checked-hover);"),z("&:active","background-color: var(--n-color-checked-pressed);")])])])]),$o=Object.assign(Object.assign(Object.assign({},D.props),Bo),{bordered:{type:Boolean,default:void 0},checked:Boolean,checkable:Boolean,strong:Boolean,triggerClickOnClose:Boolean,onClose:[Array,Function],onMouseenter:Function,onMouseleave:Function,"onUpdate:checked":Function,onUpdateChecked:Function,internalCloseFocusable:{type:Boolean,default:!0},internalCloseIsButtonTag:{type:Boolean,default:!0},onCheckedChange:Function}),Ro=Po("n-tag"),To=bo({name:"Tag",props:$o,slots:Object,setup(e){const i=fo(null),{mergedBorderedRef:l,mergedClsPrefixRef:p,inlineThemeDisabled:c,mergedRtlRef:d,mergedComponentPropsRef:n}=vo(e),s=F(()=>{var o,a;return e.size||((a=(o=n==null?void 0:n.value)===null||o===void 0?void 0:o.Tag)===null||a===void 0?void 0:a.size)||"medium"}),t=D("Tag","-tag",Ho,So,e,p);xo(Ro,{roundRef:yo(e,"round")});function f(){if(!e.disabled&&e.checkable){const{checked:o,onCheckedChange:a,onUpdateChecked:C,"onUpdate:checked":g}=e;C&&C(!o),g&&g(!o),a&&a(!o)}}function k(o){if(e.triggerClickOnClose||o.stopPropagation(),!e.disabled){const{onClose:a}=e;a&&ko(a,o)}}const b={setTextContent(o){const{value:a}=i;a&&(a.textContent=o)}},B=uo("Tag",d,p),y=F(()=>{const{type:o,color:{color:a,textColor:C}={}}=e,g=s.value,{common:{cubicBezierEaseInOut:H},self:{padding:$,closeMargin:R,borderRadius:M,opacityDisabled:E,textColorCheckable:T,textColorHoverCheckable:_,textColorPressedCheckable:O,textColorChecked:W,colorCheckable:j,colorHoverCheckable:w,colorPressedCheckable:L,colorChecked:q,colorCheckedHover:G,colorCheckedPressed:J,closeBorderRadius:Q,fontWeightStrong:X,[h("colorBordered",o)]:Y,[h("closeSize",g)]:Z,[h("closeIconSize",g)]:oo,[h("fontSize",g)]:eo,[h("height",g)]:N,[h("color",o)]:ro,[h("textColor",o)]:lo,[h("border",o)]:ao,[h("closeIconColor",o)]:U,[h("closeIconColorHover",o)]:co,[h("closeIconColorPressed",o)]:no,[h("closeColorHover",o)]:so,[h("closeColorPressed",o)]:to}}=t.value,P=mo(R);return{"--n-font-weight-strong":X,"--n-avatar-size-override":`calc(${N} - 8px)`,"--n-bezier":H,"--n-border-radius":M,"--n-border":ao,"--n-close-icon-size":oo,"--n-close-color-pressed":to,"--n-close-color-hover":so,"--n-close-border-radius":Q,"--n-close-icon-color":U,"--n-close-icon-color-hover":co,"--n-close-icon-color-pressed":no,"--n-close-icon-color-disabled":U,"--n-close-margin-top":P.top,"--n-close-margin-right":P.right,"--n-close-margin-bottom":P.bottom,"--n-close-margin-left":P.left,"--n-close-size":Z,"--n-color":a||(l.value?Y:ro),"--n-color-checkable":j,"--n-color-checked":q,"--n-color-checked-hover":G,"--n-color-checked-pressed":J,"--n-color-hover-checkable":w,"--n-color-pressed-checkable":L,"--n-font-size":eo,"--n-height":N,"--n-opacity-disabled":E,"--n-padding":$,"--n-text-color":C||lo,"--n-text-color-checkable":T,"--n-text-color-checked":W,"--n-text-color-hover-checkable":_,"--n-text-color-pressed-checkable":O}}),v=c?po("tag",F(()=>{let o="";const{type:a,color:{color:C,textColor:g}={}}=e;return o+=a[0],o+=s.value[0],C&&(o+=`a${A(C)}`),g&&(o+=`b${A(g)}`),l.value&&(o+="c"),o}),y,e):void 0;return Object.assign(Object.assign({},b),{rtlEnabled:B,mergedClsPrefix:p,contentRef:i,mergedBordered:l,handleClick:f,handleCloseClick:k,cssVars:c?void 0:y,themeClass:v==null?void 0:v.themeClass,onRender:v==null?void 0:v.onRender})},render(){var e,i;const{mergedClsPrefix:l,rtlEnabled:p,closable:c,color:{borderColor:d}={},round:n,onRender:s,$slots:t}=this;s==null||s();const f=V(t.avatar,b=>b&&x("div",{class:`${l}-tag__avatar`},b)),k=V(t.icon,b=>b&&x("div",{class:`${l}-tag__icon`},b));return x("div",{class:[`${l}-tag`,this.themeClass,{[`${l}-tag--rtl`]:p,[`${l}-tag--strong`]:this.strong,[`${l}-tag--disabled`]:this.disabled,[`${l}-tag--checkable`]:this.checkable,[`${l}-tag--checked`]:this.checkable&&this.checked,[`${l}-tag--round`]:n,[`${l}-tag--avatar`]:f,[`${l}-tag--icon`]:k,[`${l}-tag--closable`]:c}],style:this.cssVars,onClick:this.handleClick,onMouseenter:this.onMouseenter,onMouseleave:this.onMouseleave},k||f,x("span",{class:`${l}-tag__content`,ref:"contentRef"},(i=(e=this.$slots).default)===null||i===void 0?void 0:i.call(e)),!this.checkable&&c?x(Co,{clsPrefix:l,class:`${l}-tag__close`,disabled:this.disabled,onClick:this.handleCloseClick,focusable:this.internalCloseFocusable,round:n,isButtonTag:this.internalCloseIsButtonTag,absolute:!0}):null,!this.checkable&&this.mergedBordered?x("div",{class:`${l}-tag__border`,style:{borderColor:d}}):null)}});export{To as N,Eo as b};
