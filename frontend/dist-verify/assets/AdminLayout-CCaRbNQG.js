import{d as B,y as s,J as c,a9 as I,ab as l,I as z,O as Pe,a$ as qe,r as K,b0 as Ye,V as Ae,G as ee,_ as Te,p as f,Z as D,a0 as M,a3 as oe,a5 as X,H as ve,M as W,aa as We,aP as q,b1 as me,ag as ce,F as Xe,b2 as re,ad as Je,aS as Ze,a8 as xe,a4 as Qe,az as eo,b3 as oo,u as to,g as Ce,w as _,b as P,a as O,l as ye,k as U,t as ne,h as ro,B as ie,b4 as no,f as io,aI as lo,aJ as ao,e as co,o as ze}from"./index-D9Ac4DhN.js";import{p as so,l as uo,c as vo,d as ke,b as we,N as mo,a as ho}from"./LayoutHeader-BMQzeltl.js";import{N as po}from"./Tooltip-DHktrkPd.js";import{C as go,N as fo}from"./Dropdown-BdO_9te-.js";import{f as le,u as se}from"./get-CfFPLqoW.js";import{V as bo}from"./index-B7F8ta0J.js";import{u as xo}from"./use-compitable-WOsnsMpP.js";import{b as ae}from"./Popover-BrJClfDH.js";import{u as Co}from"./use-message-DAaYSu_t.js";import{N as Ie}from"./Space-n_UDLqns.js";import{N as Se}from"./text-CPo-BLrE.js";import{N as yo}from"./Tag-BGB5zlRo.js";import"./create-ref-setter-C4J8sofl.js";const zo=B({name:"ChevronDownFilled",render(){return s("svg",{viewBox:"0 0 16 16",fill:"none",xmlns:"http://www.w3.org/2000/svg"},s("path",{d:"M3.20041 5.73966C3.48226 5.43613 3.95681 5.41856 4.26034 5.70041L8 9.22652L11.7397 5.70041C12.0432 5.41856 12.5177 5.43613 12.7996 5.73966C13.0815 6.0432 13.0639 6.51775 12.7603 6.7996L8.51034 10.7996C8.22258 11.0668 7.77743 11.0668 7.48967 10.7996L3.23966 6.7996C2.93613 6.51775 2.91856 6.0432 3.20041 5.73966Z",fill:"currentColor"}))}}),wo=c("layout-sider",`
 flex-shrink: 0;
 box-sizing: border-box;
 position: relative;
 z-index: 1;
 color: var(--n-text-color);
 transition:
 color .3s var(--n-bezier),
 border-color .3s var(--n-bezier),
 min-width .3s var(--n-bezier),
 max-width .3s var(--n-bezier),
 transform .3s var(--n-bezier),
 background-color .3s var(--n-bezier);
 background-color: var(--n-color);
 display: flex;
 justify-content: flex-end;
`,[I("bordered",[l("border",`
 content: "";
 position: absolute;
 top: 0;
 bottom: 0;
 width: 1px;
 background-color: var(--n-border-color);
 transition: background-color .3s var(--n-bezier);
 `)]),l("left-placement",[I("bordered",[l("border",`
 right: 0;
 `)])]),I("right-placement",`
 justify-content: flex-start;
 `,[I("bordered",[l("border",`
 left: 0;
 `)]),I("collapsed",[c("layout-toggle-button",[c("base-icon",`
 transform: rotate(180deg);
 `)]),c("layout-toggle-bar",[z("&:hover",[l("top",{transform:"rotate(-12deg) scale(1.15) translateY(-2px)"}),l("bottom",{transform:"rotate(12deg) scale(1.15) translateY(2px)"})])])]),c("layout-toggle-button",`
 left: 0;
 transform: translateX(-50%) translateY(-50%);
 `,[c("base-icon",`
 transform: rotate(0);
 `)]),c("layout-toggle-bar",`
 left: -28px;
 transform: rotate(180deg);
 `,[z("&:hover",[l("top",{transform:"rotate(12deg) scale(1.15) translateY(-2px)"}),l("bottom",{transform:"rotate(-12deg) scale(1.15) translateY(2px)"})])])]),I("collapsed",[c("layout-toggle-bar",[z("&:hover",[l("top",{transform:"rotate(-12deg) scale(1.15) translateY(-2px)"}),l("bottom",{transform:"rotate(12deg) scale(1.15) translateY(2px)"})])]),c("layout-toggle-button",[c("base-icon",`
 transform: rotate(0);
 `)])]),c("layout-toggle-button",`
 transition:
 color .3s var(--n-bezier),
 right .3s var(--n-bezier),
 left .3s var(--n-bezier),
 border-color .3s var(--n-bezier),
 background-color .3s var(--n-bezier);
 cursor: pointer;
 width: 24px;
 height: 24px;
 position: absolute;
 top: 50%;
 right: 0;
 border-radius: 50%;
 display: flex;
 align-items: center;
 justify-content: center;
 font-size: 18px;
 color: var(--n-toggle-button-icon-color);
 border: var(--n-toggle-button-border);
 background-color: var(--n-toggle-button-color);
 box-shadow: 0 2px 4px 0px rgba(0, 0, 0, .06);
 transform: translateX(50%) translateY(-50%);
 z-index: 1;
 `,[c("base-icon",`
 transition: transform .3s var(--n-bezier);
 transform: rotate(180deg);
 `)]),c("layout-toggle-bar",`
 cursor: pointer;
 height: 72px;
 width: 32px;
 position: absolute;
 top: calc(50% - 36px);
 right: -28px;
 `,[l("top, bottom",`
 position: absolute;
 width: 4px;
 border-radius: 2px;
 height: 38px;
 left: 14px;
 transition: 
 background-color .3s var(--n-bezier),
 transform .3s var(--n-bezier);
 `),l("bottom",`
 position: absolute;
 top: 34px;
 `),z("&:hover",[l("top",{transform:"rotate(12deg) scale(1.15) translateY(-2px)"}),l("bottom",{transform:"rotate(-12deg) scale(1.15) translateY(2px)"})]),l("top, bottom",{backgroundColor:"var(--n-toggle-bar-color)"}),z("&:hover",[l("top, bottom",{backgroundColor:"var(--n-toggle-bar-color-hover)"})])]),l("border",`
 position: absolute;
 top: 0;
 right: 0;
 bottom: 0;
 width: 1px;
 transition: background-color .3s var(--n-bezier);
 `),c("layout-sider-scroll-container",`
 flex-grow: 1;
 flex-shrink: 0;
 box-sizing: border-box;
 height: 100%;
 opacity: 0;
 transition: opacity .3s var(--n-bezier);
 max-width: 100%;
 `),I("show-content",[c("layout-sider-scroll-container",{opacity:1})]),I("absolute-positioned",`
 position: absolute;
 left: 0;
 top: 0;
 bottom: 0;
 `)]),Io=B({props:{clsPrefix:{type:String,required:!0},onClick:Function},render(){const{clsPrefix:e}=this;return s("div",{onClick:this.onClick,class:`${e}-layout-toggle-bar`},s("div",{class:`${e}-layout-toggle-bar__top`}),s("div",{class:`${e}-layout-toggle-bar__bottom`}))}}),So=B({name:"LayoutToggleButton",props:{clsPrefix:{type:String,required:!0},onClick:Function},render(){const{clsPrefix:e}=this;return s("div",{class:`${e}-layout-toggle-button`,onClick:this.onClick},s(Pe,{clsPrefix:e},{default:()=>s(go,null)}))}}),Ro={position:so,bordered:Boolean,collapsedWidth:{type:Number,default:48},width:{type:[Number,String],default:272},contentClass:String,contentStyle:{type:[String,Object],default:""},collapseMode:{type:String,default:"transform"},collapsed:{type:Boolean,default:void 0},defaultCollapsed:Boolean,showCollapsedContent:{type:Boolean,default:!0},showTrigger:{type:[Boolean,String],default:!1},nativeScrollbar:{type:Boolean,default:!0},inverted:Boolean,scrollbarProps:Object,triggerClass:String,triggerStyle:[String,Object],collapsedTriggerClass:String,collapsedTriggerStyle:[String,Object],"onUpdate:collapsed":[Function,Array],onUpdateCollapsed:[Function,Array],onAfterEnter:Function,onAfterLeave:Function,onExpand:[Function,Array],onCollapse:[Function,Array],onScroll:Function},No=B({name:"LayoutSider",props:Object.assign(Object.assign({},ee.props),Ro),setup(e){const n=D(vo),r=K(null),i=K(null),u=K(e.defaultCollapsed),d=se(oe(e,"collapsed"),u),p=f(()=>le(d.value?e.collapsedWidth:e.width)),x=f(()=>e.collapseMode!=="transform"?{}:{minWidth:le(e.width)}),h=f(()=>n?n.siderPlacement:"left");function w(N,C){if(e.nativeScrollbar){const{value:y}=r;y&&(C===void 0?y.scrollTo(N):y.scrollTo(N,C))}else{const{value:y}=i;y&&y.scrollTo(N,C)}}function A(){const{"onUpdate:collapsed":N,onUpdateCollapsed:C,onExpand:y,onCollapse:V}=e,{value:L}=d;C&&M(C,!L),N&&M(N,!L),u.value=!L,L?y&&M(y):V&&M(V)}let g=0,v=0;const R=N=>{var C;const y=N.target;g=y.scrollLeft,v=y.scrollTop,(C=e.onScroll)===null||C===void 0||C.call(e,N)};Ye(()=>{if(e.nativeScrollbar){const N=r.value;N&&(N.scrollTop=v,N.scrollLeft=g)}}),X(ke,{collapsedRef:d,collapseModeRef:oe(e,"collapseMode")});const{mergedClsPrefixRef:k,inlineThemeDisabled:T}=Ae(e),E=ee("Layout","-layout-sider",wo,uo,e,k);function $(N){var C,y;N.propertyName==="max-width"&&(d.value?(C=e.onAfterLeave)===null||C===void 0||C.call(e):(y=e.onAfterEnter)===null||y===void 0||y.call(e))}const Y={scrollTo:w},j=f(()=>{const{common:{cubicBezierEaseInOut:N},self:C}=E.value,{siderToggleButtonColor:y,siderToggleButtonBorder:V,siderToggleBarColor:L,siderToggleBarColorHover:te}=C,H={"--n-bezier":N,"--n-toggle-button-color":y,"--n-toggle-button-border":V,"--n-toggle-bar-color":L,"--n-toggle-bar-color-hover":te};return e.inverted?(H["--n-color"]=C.siderColorInverted,H["--n-text-color"]=C.textColorInverted,H["--n-border-color"]=C.siderBorderColorInverted,H["--n-toggle-button-icon-color"]=C.siderToggleButtonIconColorInverted,H.__invertScrollbar=C.__invertScrollbar):(H["--n-color"]=C.siderColor,H["--n-text-color"]=C.textColor,H["--n-border-color"]=C.siderBorderColor,H["--n-toggle-button-icon-color"]=C.siderToggleButtonIconColor),H}),F=T?Te("layout-sider",f(()=>e.inverted?"a":"b"),j,e):void 0;return Object.assign({scrollableElRef:r,scrollbarInstRef:i,mergedClsPrefix:k,mergedTheme:E,styleMaxWidth:p,mergedCollapsed:d,scrollContainerStyle:x,siderPlacement:h,handleNativeElScroll:R,handleTransitionend:$,handleTriggerClick:A,inlineThemeDisabled:T,cssVars:j,themeClass:F==null?void 0:F.themeClass,onRender:F==null?void 0:F.onRender},Y)},render(){var e;const{mergedClsPrefix:n,mergedCollapsed:r,showTrigger:i}=this;return(e=this.onRender)===null||e===void 0||e.call(this),s("aside",{class:[`${n}-layout-sider`,this.themeClass,`${n}-layout-sider--${this.position}-positioned`,`${n}-layout-sider--${this.siderPlacement}-placement`,this.bordered&&`${n}-layout-sider--bordered`,r&&`${n}-layout-sider--collapsed`,(!r||this.showCollapsedContent)&&`${n}-layout-sider--show-content`],onTransitionend:this.handleTransitionend,style:[this.inlineThemeDisabled?void 0:this.cssVars,{maxWidth:this.styleMaxWidth,width:le(this.width)}]},this.nativeScrollbar?s("div",{class:[`${n}-layout-sider-scroll-container`,this.contentClass],onScroll:this.handleNativeElScroll,style:[this.scrollContainerStyle,{overflow:"auto"},this.contentStyle],ref:"scrollableElRef"},this.$slots):s(qe,Object.assign({},this.scrollbarProps,{onScroll:this.onScroll,ref:"scrollbarInstRef",style:this.scrollContainerStyle,contentStyle:this.contentStyle,contentClass:this.contentClass,theme:this.mergedTheme.peers.Scrollbar,themeOverrides:this.mergedTheme.peerOverrides.Scrollbar,builtinThemeOverrides:this.inverted&&this.cssVars.__invertScrollbar==="true"?{colorHover:"rgba(255, 255, 255, .4)",color:"rgba(255, 255, 255, .3)"}:void 0}),this.$slots),i?i==="bar"?s(Io,{clsPrefix:n,class:r?this.collapsedTriggerClass:this.triggerClass,style:r?this.collapsedTriggerStyle:this.triggerStyle,onClick:this.handleTriggerClick}):s(So,{clsPrefix:n,class:r?this.collapsedTriggerClass:this.triggerClass,style:r?this.collapsedTriggerStyle:this.triggerStyle,onClick:this.handleTriggerClick}):null,this.bordered?s("div",{class:`${n}-layout-sider__border`}):null)}}),J=ve("n-menu"),He=ve("n-submenu"),he=ve("n-menu-item-group"),Re=[z("&::before","background-color: var(--n-item-color-hover);"),l("arrow",`
 color: var(--n-arrow-color-hover);
 `),l("icon",`
 color: var(--n-item-icon-color-hover);
 `),c("menu-item-content-header",`
 color: var(--n-item-text-color-hover);
 `,[z("a",`
 color: var(--n-item-text-color-hover);
 `),l("extra",`
 color: var(--n-item-text-color-hover);
 `)])],Ne=[l("icon",`
 color: var(--n-item-icon-color-hover-horizontal);
 `),c("menu-item-content-header",`
 color: var(--n-item-text-color-hover-horizontal);
 `,[z("a",`
 color: var(--n-item-text-color-hover-horizontal);
 `),l("extra",`
 color: var(--n-item-text-color-hover-horizontal);
 `)])],Po=z([c("menu",`
 background-color: var(--n-color);
 color: var(--n-item-text-color);
 overflow: hidden;
 transition: background-color .3s var(--n-bezier);
 box-sizing: border-box;
 font-size: var(--n-font-size);
 padding-bottom: 6px;
 `,[I("horizontal",`
 max-width: 100%;
 width: 100%;
 display: flex;
 overflow: hidden;
 padding-bottom: 0;
 `,[c("submenu","margin: 0;"),c("menu-item","margin: 0;"),c("menu-item-content",`
 padding: 0 20px;
 border-bottom: 2px solid #0000;
 `,[z("&::before","display: none;"),I("selected","border-bottom: 2px solid var(--n-border-color-horizontal)")]),c("menu-item-content",[I("selected",[l("icon","color: var(--n-item-icon-color-active-horizontal);"),c("menu-item-content-header",`
 color: var(--n-item-text-color-active-horizontal);
 `,[z("a","color: var(--n-item-text-color-active-horizontal);"),l("extra","color: var(--n-item-text-color-active-horizontal);")])]),I("child-active",`
 border-bottom: 2px solid var(--n-border-color-horizontal);
 `,[c("menu-item-content-header",`
 color: var(--n-item-text-color-child-active-horizontal);
 `,[z("a",`
 color: var(--n-item-text-color-child-active-horizontal);
 `),l("extra",`
 color: var(--n-item-text-color-child-active-horizontal);
 `)]),l("icon",`
 color: var(--n-item-icon-color-child-active-horizontal);
 `)]),W("disabled",[W("selected, child-active",[z("&:focus-within",Ne)]),I("selected",[G(null,[l("icon","color: var(--n-item-icon-color-active-hover-horizontal);"),c("menu-item-content-header",`
 color: var(--n-item-text-color-active-hover-horizontal);
 `,[z("a","color: var(--n-item-text-color-active-hover-horizontal);"),l("extra","color: var(--n-item-text-color-active-hover-horizontal);")])])]),I("child-active",[G(null,[l("icon","color: var(--n-item-icon-color-child-active-hover-horizontal);"),c("menu-item-content-header",`
 color: var(--n-item-text-color-child-active-hover-horizontal);
 `,[z("a","color: var(--n-item-text-color-child-active-hover-horizontal);"),l("extra","color: var(--n-item-text-color-child-active-hover-horizontal);")])])]),G("border-bottom: 2px solid var(--n-border-color-horizontal);",Ne)]),c("menu-item-content-header",[z("a","color: var(--n-item-text-color-horizontal);")])])]),W("responsive",[c("menu-item-content-header",`
 overflow: hidden;
 text-overflow: ellipsis;
 `)]),I("collapsed",[c("menu-item-content",[I("selected",[z("&::before",`
 background-color: var(--n-item-color-active-collapsed) !important;
 `)]),c("menu-item-content-header","opacity: 0;"),l("arrow","opacity: 0;"),l("icon","color: var(--n-item-icon-color-collapsed);")])]),c("menu-item",`
 height: var(--n-item-height);
 margin-top: 6px;
 position: relative;
 `),c("menu-item-content",`
 box-sizing: border-box;
 line-height: 1.75;
 height: 100%;
 display: grid;
 grid-template-areas: "icon content arrow";
 grid-template-columns: auto 1fr auto;
 align-items: center;
 cursor: pointer;
 position: relative;
 padding-right: 18px;
 transition:
 background-color .3s var(--n-bezier),
 padding-left .3s var(--n-bezier),
 border-color .3s var(--n-bezier);
 `,[z("> *","z-index: 1;"),z("&::before",`
 z-index: auto;
 content: "";
 background-color: #0000;
 position: absolute;
 left: 8px;
 right: 8px;
 top: 0;
 bottom: 0;
 pointer-events: none;
 border-radius: var(--n-border-radius);
 transition: background-color .3s var(--n-bezier);
 `),I("disabled",`
 opacity: .45;
 cursor: not-allowed;
 `),I("collapsed",[l("arrow","transform: rotate(0);")]),I("selected",[z("&::before","background-color: var(--n-item-color-active);"),l("arrow","color: var(--n-arrow-color-active);"),l("icon","color: var(--n-item-icon-color-active);"),c("menu-item-content-header",`
 color: var(--n-item-text-color-active);
 `,[z("a","color: var(--n-item-text-color-active);"),l("extra","color: var(--n-item-text-color-active);")])]),I("child-active",[c("menu-item-content-header",`
 color: var(--n-item-text-color-child-active);
 `,[z("a",`
 color: var(--n-item-text-color-child-active);
 `),l("extra",`
 color: var(--n-item-text-color-child-active);
 `)]),l("arrow",`
 color: var(--n-arrow-color-child-active);
 `),l("icon",`
 color: var(--n-item-icon-color-child-active);
 `)]),W("disabled",[W("selected, child-active",[z("&:focus-within",Re)]),I("selected",[G(null,[l("arrow","color: var(--n-arrow-color-active-hover);"),l("icon","color: var(--n-item-icon-color-active-hover);"),c("menu-item-content-header",`
 color: var(--n-item-text-color-active-hover);
 `,[z("a","color: var(--n-item-text-color-active-hover);"),l("extra","color: var(--n-item-text-color-active-hover);")])])]),I("child-active",[G(null,[l("arrow","color: var(--n-arrow-color-child-active-hover);"),l("icon","color: var(--n-item-icon-color-child-active-hover);"),c("menu-item-content-header",`
 color: var(--n-item-text-color-child-active-hover);
 `,[z("a","color: var(--n-item-text-color-child-active-hover);"),l("extra","color: var(--n-item-text-color-child-active-hover);")])])]),I("selected",[G(null,[z("&::before","background-color: var(--n-item-color-active-hover);")])]),G(null,Re)]),l("icon",`
 grid-area: icon;
 color: var(--n-item-icon-color);
 transition:
 color .3s var(--n-bezier),
 font-size .3s var(--n-bezier),
 margin-right .3s var(--n-bezier);
 box-sizing: content-box;
 display: inline-flex;
 align-items: center;
 justify-content: center;
 `),l("arrow",`
 grid-area: arrow;
 font-size: 16px;
 color: var(--n-arrow-color);
 transform: rotate(180deg);
 opacity: 1;
 transition:
 color .3s var(--n-bezier),
 transform 0.2s var(--n-bezier),
 opacity 0.2s var(--n-bezier);
 `),c("menu-item-content-header",`
 grid-area: content;
 transition:
 color .3s var(--n-bezier),
 opacity .3s var(--n-bezier);
 opacity: 1;
 white-space: nowrap;
 color: var(--n-item-text-color);
 `,[z("a",`
 outline: none;
 text-decoration: none;
 transition: color .3s var(--n-bezier);
 color: var(--n-item-text-color);
 `,[z("&::before",`
 content: "";
 position: absolute;
 left: 0;
 right: 0;
 top: 0;
 bottom: 0;
 `)]),l("extra",`
 font-size: .93em;
 color: var(--n-group-text-color);
 transition: color .3s var(--n-bezier);
 `)])]),c("submenu",`
 cursor: pointer;
 position: relative;
 margin-top: 6px;
 `,[c("menu-item-content",`
 height: var(--n-item-height);
 `),c("submenu-children",`
 overflow: hidden;
 padding: 0;
 `,[We({duration:".2s"})])]),c("menu-item-group",[c("menu-item-group-title",`
 margin-top: 6px;
 color: var(--n-group-text-color);
 cursor: default;
 font-size: .93em;
 height: 36px;
 display: flex;
 align-items: center;
 transition:
 padding-left .3s var(--n-bezier),
 color .3s var(--n-bezier);
 `)])]),c("menu-tooltip",[z("a",`
 color: inherit;
 text-decoration: none;
 `)]),c("menu-divider",`
 transition: background-color .3s var(--n-bezier);
 background-color: var(--n-divider-color);
 height: 1px;
 margin: 6px 18px;
 `)]);function G(e,n){return[I("hover",e,n),z("&:hover",e,n)]}const _e=B({name:"MenuOptionContent",props:{collapsed:Boolean,disabled:Boolean,title:[String,Function],icon:Function,extra:[String,Function],showArrow:Boolean,childActive:Boolean,hover:Boolean,paddingLeft:Number,selected:Boolean,maxIconSize:{type:Number,required:!0},activeIconSize:{type:Number,required:!0},iconMarginRight:{type:Number,required:!0},clsPrefix:{type:String,required:!0},onClick:Function,tmNode:{type:Object,required:!0},isEllipsisPlaceholder:Boolean},setup(e){const{props:n}=D(J);return{menuProps:n,style:f(()=>{const{paddingLeft:r}=e;return{paddingLeft:r&&`${r}px`}}),iconStyle:f(()=>{const{maxIconSize:r,activeIconSize:i,iconMarginRight:u}=e;return{width:`${r}px`,height:`${r}px`,fontSize:`${i}px`,marginRight:`${u}px`}})}},render(){const{clsPrefix:e,tmNode:n,menuProps:{renderIcon:r,renderLabel:i,renderExtra:u,expandIcon:d}}=this,p=r?r(n.rawNode):q(this.icon);return s("div",{onClick:x=>{var h;(h=this.onClick)===null||h===void 0||h.call(this,x)},role:"none",class:[`${e}-menu-item-content`,{[`${e}-menu-item-content--selected`]:this.selected,[`${e}-menu-item-content--collapsed`]:this.collapsed,[`${e}-menu-item-content--child-active`]:this.childActive,[`${e}-menu-item-content--disabled`]:this.disabled,[`${e}-menu-item-content--hover`]:this.hover}],style:this.style},p&&s("div",{class:`${e}-menu-item-content__icon`,style:this.iconStyle,role:"none"},[p]),s("div",{class:`${e}-menu-item-content-header`,role:"none"},this.isEllipsisPlaceholder?this.title:i?i(n.rawNode):q(this.title),this.extra||u?s("span",{class:`${e}-menu-item-content-header__extra`}," ",u?u(n.rawNode):q(this.extra)):null),this.showArrow?s(Pe,{ariaHidden:!0,class:`${e}-menu-item-content__arrow`,clsPrefix:e},{default:()=>d?d(n.rawNode):s(zo,null)}):null)}}),Q=8;function pe(e){const n=D(J),{props:r,mergedCollapsedRef:i}=n,u=D(He,null),d=D(he,null),p=f(()=>r.mode==="horizontal"),x=f(()=>p.value?r.dropdownPlacement:"tmNodes"in e?"right-start":"right"),h=f(()=>{var v;return Math.max((v=r.collapsedIconSize)!==null&&v!==void 0?v:r.iconSize,r.iconSize)}),w=f(()=>{var v;return!p.value&&e.root&&i.value&&(v=r.collapsedIconSize)!==null&&v!==void 0?v:r.iconSize}),A=f(()=>{if(p.value)return;const{collapsedWidth:v,indent:R,rootIndent:k}=r,{root:T,isGroup:E}=e,$=k===void 0?R:k;return T?i.value?v/2-h.value/2:$:d&&typeof d.paddingLeftRef.value=="number"?R/2+d.paddingLeftRef.value:u&&typeof u.paddingLeftRef.value=="number"?(E?R/2:R)+u.paddingLeftRef.value:0}),g=f(()=>{const{collapsedWidth:v,indent:R,rootIndent:k}=r,{value:T}=h,{root:E}=e;return p.value||!E||!i.value?Q:(k===void 0?R:k)+T+Q-(v+T)/2});return{dropdownPlacement:x,activeIconSize:w,maxIconSize:h,paddingLeft:A,iconMarginRight:g,NMenu:n,NSubmenu:u,NMenuOptionGroup:d}}const ge={internalKey:{type:[String,Number],required:!0},root:Boolean,isGroup:Boolean,level:{type:Number,required:!0},title:[String,Function],extra:[String,Function]},Ao=B({name:"MenuDivider",setup(){const e=D(J),{mergedClsPrefixRef:n,isHorizontalRef:r}=e;return()=>r.value?null:s("div",{class:`${n.value}-menu-divider`})}}),Oe=Object.assign(Object.assign({},ge),{tmNode:{type:Object,required:!0},disabled:Boolean,icon:Function,onClick:Function}),To=me(Oe),ko=B({name:"MenuOption",props:Oe,setup(e){const n=pe(e),{NSubmenu:r,NMenu:i,NMenuOptionGroup:u}=n,{props:d,mergedClsPrefixRef:p,mergedCollapsedRef:x}=i,h=r?r.mergedDisabledRef:u?u.mergedDisabledRef:{value:!1},w=f(()=>h.value||e.disabled);function A(v){const{onClick:R}=e;R&&R(v)}function g(v){w.value||(i.doSelect(e.internalKey,e.tmNode.rawNode),A(v))}return{mergedClsPrefix:p,dropdownPlacement:n.dropdownPlacement,paddingLeft:n.paddingLeft,iconMarginRight:n.iconMarginRight,maxIconSize:n.maxIconSize,activeIconSize:n.activeIconSize,mergedTheme:i.mergedThemeRef,menuProps:d,dropdownEnabled:ce(()=>e.root&&x.value&&d.mode!=="horizontal"&&!w.value),selected:ce(()=>i.mergedValueRef.value===e.internalKey),mergedDisabled:w,handleClick:g}},render(){const{mergedClsPrefix:e,mergedTheme:n,tmNode:r,menuProps:{renderLabel:i,nodeProps:u}}=this,d=u==null?void 0:u(r.rawNode);return s("div",Object.assign({},d,{role:"menuitem",class:[`${e}-menu-item`,d==null?void 0:d.class]}),s(po,{theme:n.peers.Tooltip,themeOverrides:n.peerOverrides.Tooltip,trigger:"hover",placement:this.dropdownPlacement,disabled:!this.dropdownEnabled||this.title===void 0,internalExtraClass:["menu-tooltip"]},{default:()=>i?i(r.rawNode):q(this.title),trigger:()=>s(_e,{tmNode:r,clsPrefix:e,paddingLeft:this.paddingLeft,iconMarginRight:this.iconMarginRight,maxIconSize:this.maxIconSize,activeIconSize:this.activeIconSize,selected:this.selected,title:this.title,extra:this.extra,disabled:this.mergedDisabled,icon:this.icon,onClick:this.handleClick})}))}}),Ee=Object.assign(Object.assign({},ge),{tmNode:{type:Object,required:!0},tmNodes:{type:Array,required:!0}}),Ho=me(Ee),_o=B({name:"MenuOptionGroup",props:Ee,setup(e){const n=pe(e),{NSubmenu:r}=n,i=f(()=>r!=null&&r.mergedDisabledRef.value?!0:e.tmNode.disabled);X(he,{paddingLeftRef:n.paddingLeft,mergedDisabledRef:i});const{mergedClsPrefixRef:u,props:d}=D(J);return function(){const{value:p}=u,x=n.paddingLeft.value,{nodeProps:h}=d,w=h==null?void 0:h(e.tmNode.rawNode);return s("div",{class:`${p}-menu-item-group`,role:"group"},s("div",Object.assign({},w,{class:[`${p}-menu-item-group-title`,w==null?void 0:w.class],style:[(w==null?void 0:w.style)||"",x!==void 0?`padding-left: ${x}px;`:""]}),q(e.title),e.extra?s(Xe,null," ",q(e.extra)):null),s("div",null,e.tmNodes.map(A=>fe(A,d))))}}});function de(e){return e.type==="divider"||e.type==="render"}function Oo(e){return e.type==="divider"}function fe(e,n){const{rawNode:r}=e,{show:i}=r;if(i===!1)return null;if(de(r))return Oo(r)?s(Ao,Object.assign({key:e.key},r.props)):null;const{labelField:u}=n,{key:d,level:p,isGroup:x}=e,h=Object.assign(Object.assign({},r),{title:r.title||r[u],extra:r.titleExtra||r.extra,key:d,internalKey:d,level:p,root:p===0,isGroup:x});return e.children?e.isGroup?s(_o,re(h,Ho,{tmNode:e,tmNodes:e.children,key:d})):s(ue,re(h,Eo,{key:d,rawNodes:r[n.childrenField],tmNodes:e.children,tmNode:e})):s(ko,re(h,To,{key:d,tmNode:e}))}const Fe=Object.assign(Object.assign({},ge),{rawNodes:{type:Array,default:()=>[]},tmNodes:{type:Array,default:()=>[]},tmNode:{type:Object,required:!0},disabled:Boolean,icon:Function,onClick:Function,domId:String,virtualChildActive:{type:Boolean,default:void 0},isEllipsisPlaceholder:Boolean}),Eo=me(Fe),ue=B({name:"Submenu",props:Fe,setup(e){const n=pe(e),{NMenu:r,NSubmenu:i}=n,{props:u,mergedCollapsedRef:d,mergedThemeRef:p}=r,x=f(()=>{const{disabled:v}=e;return i!=null&&i.mergedDisabledRef.value||u.disabled?!0:v}),h=K(!1);X(He,{paddingLeftRef:n.paddingLeft,mergedDisabledRef:x}),X(he,null);function w(){const{onClick:v}=e;v&&v()}function A(){x.value||(d.value||r.toggleExpand(e.internalKey),w())}function g(v){h.value=v}return{menuProps:u,mergedTheme:p,doSelect:r.doSelect,inverted:r.invertedRef,isHorizontal:r.isHorizontalRef,mergedClsPrefix:r.mergedClsPrefixRef,maxIconSize:n.maxIconSize,activeIconSize:n.activeIconSize,iconMarginRight:n.iconMarginRight,dropdownPlacement:n.dropdownPlacement,dropdownShow:h,paddingLeft:n.paddingLeft,mergedDisabled:x,mergedValue:r.mergedValueRef,childActive:ce(()=>{var v;return(v=e.virtualChildActive)!==null&&v!==void 0?v:r.activePathRef.value.includes(e.internalKey)}),collapsed:f(()=>u.mode==="horizontal"?!1:d.value?!0:!r.mergedExpandedKeysRef.value.includes(e.internalKey)),dropdownEnabled:f(()=>!x.value&&(u.mode==="horizontal"||d.value)),handlePopoverShowChange:g,handleClick:A}},render(){var e;const{mergedClsPrefix:n,menuProps:{renderIcon:r,renderLabel:i}}=this,u=()=>{const{isHorizontal:p,paddingLeft:x,collapsed:h,mergedDisabled:w,maxIconSize:A,activeIconSize:g,title:v,childActive:R,icon:k,handleClick:T,menuProps:{nodeProps:E},dropdownShow:$,iconMarginRight:Y,tmNode:j,mergedClsPrefix:F,isEllipsisPlaceholder:N,extra:C}=this,y=E==null?void 0:E(j.rawNode);return s("div",Object.assign({},y,{class:[`${F}-menu-item`,y==null?void 0:y.class],role:"menuitem"}),s(_e,{tmNode:j,paddingLeft:x,collapsed:h,disabled:w,iconMarginRight:Y,maxIconSize:A,activeIconSize:g,title:v,extra:C,showArrow:!p,childActive:R,clsPrefix:F,icon:k,hover:$,onClick:T,isEllipsisPlaceholder:N}))},d=()=>s(Je,null,{default:()=>{const{tmNodes:p,collapsed:x}=this;return x?null:s("div",{class:`${n}-submenu-children`,role:"menu"},p.map(h=>fe(h,this.menuProps)))}});return this.root?s(fo,Object.assign({size:"large",trigger:"hover"},(e=this.menuProps)===null||e===void 0?void 0:e.dropdownProps,{themeOverrides:this.mergedTheme.peerOverrides.Dropdown,theme:this.mergedTheme.peers.Dropdown,builtinThemeOverrides:{fontSizeLarge:"14px",optionIconSizeLarge:"18px"},value:this.mergedValue,disabled:!this.dropdownEnabled,placement:this.dropdownPlacement,keyField:this.menuProps.keyField,labelField:this.menuProps.labelField,childrenField:this.menuProps.childrenField,onUpdateShow:this.handlePopoverShowChange,options:this.rawNodes,onSelect:this.doSelect,inverted:this.inverted,renderIcon:r,renderLabel:i}),{default:()=>s("div",{class:`${n}-submenu`,role:"menu","aria-expanded":!this.collapsed,id:this.domId},u(),this.isHorizontal?null:d())}):s("div",{class:`${n}-submenu`,role:"menu","aria-expanded":!this.collapsed,id:this.domId},u(),d())}}),Fo=Object.assign(Object.assign({},ee.props),{options:{type:Array,default:()=>[]},collapsed:{type:Boolean,default:void 0},collapsedWidth:{type:Number,default:48},iconSize:{type:Number,default:20},collapsedIconSize:{type:Number,default:24},rootIndent:Number,indent:{type:Number,default:32},labelField:{type:String,default:"label"},keyField:{type:String,default:"key"},childrenField:{type:String,default:"children"},disabledField:{type:String,default:"disabled"},defaultExpandAll:Boolean,defaultExpandedKeys:Array,expandedKeys:Array,value:[String,Number],defaultValue:{type:[String,Number],default:null},mode:{type:String,default:"vertical"},watchProps:{type:Array,default:void 0},disabled:Boolean,show:{type:Boolean,default:!0},inverted:Boolean,"onUpdate:expandedKeys":[Function,Array],onUpdateExpandedKeys:[Function,Array],onUpdateValue:[Function,Array],"onUpdate:value":[Function,Array],expandIcon:Function,renderIcon:Function,renderLabel:Function,renderExtra:Function,dropdownProps:Object,accordion:Boolean,nodeProps:Function,dropdownPlacement:{type:String,default:"bottom"},responsive:Boolean,items:Array,onOpenNamesChange:[Function,Array],onSelect:[Function,Array],onExpandedNamesChange:[Function,Array],expandedNames:Array,defaultExpandedNames:Array}),Mo=B({name:"Menu",inheritAttrs:!1,props:Fo,setup(e){const{mergedClsPrefixRef:n,inlineThemeDisabled:r}=Ae(e),i=ee("Menu","-menu",Po,oo,e,n),u=D(ke,null),d=f(()=>{var a;const{collapsed:b}=e;if(b!==void 0)return b;if(u){const{collapseModeRef:o,collapsedRef:m}=u;if(o.value==="width")return(a=m.value)!==null&&a!==void 0?a:!1}return!1}),p=f(()=>{const{keyField:a,childrenField:b,disabledField:o}=e;return ae(e.items||e.options,{getIgnored(m){return de(m)},getChildren(m){return m[b]},getDisabled(m){return m[o]},getKey(m){var S;return(S=m[a])!==null&&S!==void 0?S:m.name}})}),x=f(()=>new Set(p.value.treeNodes.map(a=>a.key))),{watchProps:h}=e,w=K(null);h!=null&&h.includes("defaultValue")?xe(()=>{w.value=e.defaultValue}):w.value=e.defaultValue;const A=oe(e,"value"),g=se(A,w),v=K([]),R=()=>{v.value=e.defaultExpandAll?p.value.getNonLeafKeys():e.defaultExpandedNames||e.defaultExpandedKeys||p.value.getPath(g.value,{includeSelf:!1}).keyPath};h!=null&&h.includes("defaultExpandedKeys")?xe(R):R();const k=xo(e,["expandedNames","expandedKeys"]),T=se(k,v),E=f(()=>p.value.treeNodes),$=f(()=>p.value.getPath(g.value).keyPath);X(J,{props:e,mergedCollapsedRef:d,mergedThemeRef:i,mergedValueRef:g,mergedExpandedKeysRef:T,activePathRef:$,mergedClsPrefixRef:n,isHorizontalRef:f(()=>e.mode==="horizontal"),invertedRef:oe(e,"inverted"),doSelect:Y,toggleExpand:F});function Y(a,b){const{"onUpdate:value":o,onUpdateValue:m,onSelect:S}=e;m&&M(m,a,b),o&&M(o,a,b),S&&M(S,a,b),w.value=a}function j(a){const{"onUpdate:expandedKeys":b,onUpdateExpandedKeys:o,onExpandedNamesChange:m,onOpenNamesChange:S}=e;b&&M(b,a),o&&M(o,a),m&&M(m,a),S&&M(S,a),v.value=a}function F(a){const b=Array.from(T.value),o=b.findIndex(m=>m===a);if(~o)b.splice(o,1);else{if(e.accordion&&x.value.has(a)){const m=b.findIndex(S=>x.value.has(S));m>-1&&b.splice(m,1)}b.push(a)}j(b)}const N=a=>{const b=p.value.getPath(a??g.value,{includeSelf:!1}).keyPath;if(!b.length)return;const o=Array.from(T.value),m=new Set([...o,...b]);e.accordion&&x.value.forEach(S=>{m.has(S)&&!b.includes(S)&&m.delete(S)}),j(Array.from(m))},C=f(()=>{const{inverted:a}=e,{common:{cubicBezierEaseInOut:b},self:o}=i.value,{borderRadius:m,borderColorHorizontal:S,fontSize:De,itemHeight:Ue,dividerColor:Ge}=o,t={"--n-divider-color":Ge,"--n-bezier":b,"--n-font-size":De,"--n-border-color-horizontal":S,"--n-border-radius":m,"--n-item-height":Ue};return a?(t["--n-group-text-color"]=o.groupTextColorInverted,t["--n-color"]=o.colorInverted,t["--n-item-text-color"]=o.itemTextColorInverted,t["--n-item-text-color-hover"]=o.itemTextColorHoverInverted,t["--n-item-text-color-active"]=o.itemTextColorActiveInverted,t["--n-item-text-color-child-active"]=o.itemTextColorChildActiveInverted,t["--n-item-text-color-child-active-hover"]=o.itemTextColorChildActiveInverted,t["--n-item-text-color-active-hover"]=o.itemTextColorActiveHoverInverted,t["--n-item-icon-color"]=o.itemIconColorInverted,t["--n-item-icon-color-hover"]=o.itemIconColorHoverInverted,t["--n-item-icon-color-active"]=o.itemIconColorActiveInverted,t["--n-item-icon-color-active-hover"]=o.itemIconColorActiveHoverInverted,t["--n-item-icon-color-child-active"]=o.itemIconColorChildActiveInverted,t["--n-item-icon-color-child-active-hover"]=o.itemIconColorChildActiveHoverInverted,t["--n-item-icon-color-collapsed"]=o.itemIconColorCollapsedInverted,t["--n-item-text-color-horizontal"]=o.itemTextColorHorizontalInverted,t["--n-item-text-color-hover-horizontal"]=o.itemTextColorHoverHorizontalInverted,t["--n-item-text-color-active-horizontal"]=o.itemTextColorActiveHorizontalInverted,t["--n-item-text-color-child-active-horizontal"]=o.itemTextColorChildActiveHorizontalInverted,t["--n-item-text-color-child-active-hover-horizontal"]=o.itemTextColorChildActiveHoverHorizontalInverted,t["--n-item-text-color-active-hover-horizontal"]=o.itemTextColorActiveHoverHorizontalInverted,t["--n-item-icon-color-horizontal"]=o.itemIconColorHorizontalInverted,t["--n-item-icon-color-hover-horizontal"]=o.itemIconColorHoverHorizontalInverted,t["--n-item-icon-color-active-horizontal"]=o.itemIconColorActiveHorizontalInverted,t["--n-item-icon-color-active-hover-horizontal"]=o.itemIconColorActiveHoverHorizontalInverted,t["--n-item-icon-color-child-active-horizontal"]=o.itemIconColorChildActiveHorizontalInverted,t["--n-item-icon-color-child-active-hover-horizontal"]=o.itemIconColorChildActiveHoverHorizontalInverted,t["--n-arrow-color"]=o.arrowColorInverted,t["--n-arrow-color-hover"]=o.arrowColorHoverInverted,t["--n-arrow-color-active"]=o.arrowColorActiveInverted,t["--n-arrow-color-active-hover"]=o.arrowColorActiveHoverInverted,t["--n-arrow-color-child-active"]=o.arrowColorChildActiveInverted,t["--n-arrow-color-child-active-hover"]=o.arrowColorChildActiveHoverInverted,t["--n-item-color-hover"]=o.itemColorHoverInverted,t["--n-item-color-active"]=o.itemColorActiveInverted,t["--n-item-color-active-hover"]=o.itemColorActiveHoverInverted,t["--n-item-color-active-collapsed"]=o.itemColorActiveCollapsedInverted):(t["--n-group-text-color"]=o.groupTextColor,t["--n-color"]=o.color,t["--n-item-text-color"]=o.itemTextColor,t["--n-item-text-color-hover"]=o.itemTextColorHover,t["--n-item-text-color-active"]=o.itemTextColorActive,t["--n-item-text-color-child-active"]=o.itemTextColorChildActive,t["--n-item-text-color-child-active-hover"]=o.itemTextColorChildActiveHover,t["--n-item-text-color-active-hover"]=o.itemTextColorActiveHover,t["--n-item-icon-color"]=o.itemIconColor,t["--n-item-icon-color-hover"]=o.itemIconColorHover,t["--n-item-icon-color-active"]=o.itemIconColorActive,t["--n-item-icon-color-active-hover"]=o.itemIconColorActiveHover,t["--n-item-icon-color-child-active"]=o.itemIconColorChildActive,t["--n-item-icon-color-child-active-hover"]=o.itemIconColorChildActiveHover,t["--n-item-icon-color-collapsed"]=o.itemIconColorCollapsed,t["--n-item-text-color-horizontal"]=o.itemTextColorHorizontal,t["--n-item-text-color-hover-horizontal"]=o.itemTextColorHoverHorizontal,t["--n-item-text-color-active-horizontal"]=o.itemTextColorActiveHorizontal,t["--n-item-text-color-child-active-horizontal"]=o.itemTextColorChildActiveHorizontal,t["--n-item-text-color-child-active-hover-horizontal"]=o.itemTextColorChildActiveHoverHorizontal,t["--n-item-text-color-active-hover-horizontal"]=o.itemTextColorActiveHoverHorizontal,t["--n-item-icon-color-horizontal"]=o.itemIconColorHorizontal,t["--n-item-icon-color-hover-horizontal"]=o.itemIconColorHoverHorizontal,t["--n-item-icon-color-active-horizontal"]=o.itemIconColorActiveHorizontal,t["--n-item-icon-color-active-hover-horizontal"]=o.itemIconColorActiveHoverHorizontal,t["--n-item-icon-color-child-active-horizontal"]=o.itemIconColorChildActiveHorizontal,t["--n-item-icon-color-child-active-hover-horizontal"]=o.itemIconColorChildActiveHoverHorizontal,t["--n-arrow-color"]=o.arrowColor,t["--n-arrow-color-hover"]=o.arrowColorHover,t["--n-arrow-color-active"]=o.arrowColorActive,t["--n-arrow-color-active-hover"]=o.arrowColorActiveHover,t["--n-arrow-color-child-active"]=o.arrowColorChildActive,t["--n-arrow-color-child-active-hover"]=o.arrowColorChildActiveHover,t["--n-item-color-hover"]=o.itemColorHover,t["--n-item-color-active"]=o.itemColorActive,t["--n-item-color-active-hover"]=o.itemColorActiveHover,t["--n-item-color-active-collapsed"]=o.itemColorActiveCollapsed),t}),y=r?Te("menu",f(()=>e.inverted?"a":"b"),C,e):void 0,V=Qe(),L=K(null),te=K(null);let H=!0;const be=()=>{var a;H?H=!1:(a=L.value)===null||a===void 0||a.sync({showAllItemsBeforeCalculate:!0})};function Me(){return document.getElementById(V)}const Z=K(-1);function Be(a){Z.value=e.options.length-a}function $e(a){a||(Z.value=-1)}const Le=f(()=>{const a=Z.value;return{children:a===-1?[]:e.options.slice(a)}}),Ke=f(()=>{const{childrenField:a,disabledField:b,keyField:o}=e;return ae([Le.value],{getIgnored(m){return de(m)},getChildren(m){return m[a]},getDisabled(m){return m[b]},getKey(m){var S;return(S=m[o])!==null&&S!==void 0?S:m.name}})}),je=f(()=>ae([{}]).treeNodes[0]);function Ve(){var a;if(Z.value===-1)return s(ue,{root:!0,level:0,key:"__ellpisisGroupPlaceholder__",internalKey:"__ellpisisGroupPlaceholder__",title:"···",tmNode:je.value,domId:V,isEllipsisPlaceholder:!0});const b=Ke.value.treeNodes[0],o=$.value,m=!!(!((a=b.children)===null||a===void 0)&&a.some(S=>o.includes(S.key)));return s(ue,{level:0,root:!0,key:"__ellpisisGroup__",internalKey:"__ellpisisGroup__",title:"···",virtualChildActive:m,tmNode:b,domId:V,rawNodes:b.rawNode.children||[],tmNodes:b.children||[],isEllipsisPlaceholder:!0})}return{mergedClsPrefix:n,controlledExpandedKeys:k,uncontrolledExpanededKeys:v,mergedExpandedKeys:T,uncontrolledValue:w,mergedValue:g,activePath:$,tmNodes:E,mergedTheme:i,mergedCollapsed:d,cssVars:r?void 0:C,themeClass:y==null?void 0:y.themeClass,overflowRef:L,counterRef:te,updateCounter:()=>{},onResize:be,onUpdateOverflow:$e,onUpdateCount:Be,renderCounter:Ve,getCounter:Me,onRender:y==null?void 0:y.onRender,showOption:N,deriveResponsiveState:be}},render(){const{mergedClsPrefix:e,mode:n,themeClass:r,onRender:i}=this;i==null||i();const u=()=>this.tmNodes.map(h=>fe(h,this.$props)),p=n==="horizontal"&&this.responsive,x=()=>s("div",eo(this.$attrs,{role:n==="horizontal"?"menubar":"menu",class:[`${e}-menu`,r,`${e}-menu--${n}`,p&&`${e}-menu--responsive`,this.mergedCollapsed&&`${e}-menu--collapsed`],style:this.cssVars}),p?s(bo,{ref:"overflowRef",onUpdateOverflow:this.onUpdateOverflow,getCounter:this.getCounter,onUpdateCount:this.onUpdateCount,updateCounter:this.updateCounter,style:{width:"100%",display:"flex",overflow:"hidden"}},{default:u,counter:this.renderCounter}):u());return p?s(Ze,{onResize:this.onResize},{default:x}):x()}}),Jo=B({__name:"AdminLayout",setup(e){const n=io(),r=co(),i=to(),u=Co(),d=f(()=>!1),p=f(()=>{const A=[{label:"仪表盘",key:"dashboard",path:"/admin/dashboard"},{label:"申请审批台",key:"applications",path:"/admin/applications"},{label:"爬虫与重算",key:"crawl",path:"/admin/crawl"},{label:"参赛记录管理",key:"participations",path:"/admin/participations"},{label:"成员名单",key:"members",path:"/admin/members"}];return i.isSuperAdmin&&A.splice(1,0,{label:"学校管理",key:"schools",path:"/admin/schools"}),A.map(g=>({label:g.label,key:g.key,onClick:()=>n.push(g.path)}))}),x=f(()=>r.name);function h(){lo(),i.logout(),u.success("已退出登录"),n.push({name:"login"})}const w=f(()=>i.isSuperAdmin?"超级管理员":i.isSchoolAdmin?"学校管理员":"用户");return(A,g)=>{const v=ao("router-view");return ze(),Ce(P(we),{"has-sider":"",style:{height:"100vh"}},{default:_(()=>[O(P(No),{bordered:"","collapsed-width":64,width:220,collapsed:d.value,"show-trigger":""},{default:_(()=>[g[3]||(g[3]=ye("div",{style:{padding:"16px","font-weight":"700","font-size":"16px"}},[U(" E-algo Rank "),ye("div",{style:{"font-size":"12px","font-weight":"400",opacity:"0.6"}}," 管理后台 ")],-1)),O(P(Mo),{options:p.value,value:x.value,"onUpdate:value":g[0]||(g[0]=R=>P(n).push("/admin/"+R))},null,8,["options","value"])]),_:1},8,["collapsed"]),O(P(we),null,{default:_(()=>[O(P(mo),{bordered:"",style:{padding:"0 16px",display:"flex","align-items":"center","justify-content":"space-between",height:"56px"}},{default:_(()=>[O(P(Ie),{align:"center"},{default:_(()=>{var R;return[O(P(Se),{strong:""},{default:_(()=>{var k,T;return[U(ne(((k=P(i).user)==null?void 0:k.real_name)||((T=P(i).user)==null?void 0:T.username)),1)]}),_:1}),O(P(yo),{size:"small",type:P(i).isSuperAdmin?"error":"warning"},{default:_(()=>[U(ne(w.value),1)]),_:1},8,["type"]),(R=P(i).user)!=null&&R.school?(ze(),Ce(P(Se),{key:0,depth:"3"},{default:_(()=>[U(" 所属："+ne(P(i).user.school.name),1)]),_:1})):ro("",!0)]}),_:1}),O(P(Ie),null,{default:_(()=>[O(P(ie),{text:"",onClick:g[1]||(g[1]=()=>P(n).push("/u/rankings"))},{default:_(()=>[...g[4]||(g[4]=[U("← 返回前台",-1)])]),_:1}),O(P(ie),{text:"",onClick:g[2]||(g[2]=()=>A.$emit("toggle-theme"))},{default:_(()=>[...g[5]||(g[5]=[U("🌗 主题",-1)])]),_:1}),O(P(ie),{tertiary:"",size:"small",onClick:h},{default:_(()=>[...g[6]||(g[6]=[U("退出",-1)])]),_:1})]),_:1})]),_:1}),O(P(ho),{"content-style":"padding: 16px"},{default:_(()=>[no(A.$slots,"default"),O(v)]),_:3})]),_:3})]),_:3})}}});export{Jo as default};
