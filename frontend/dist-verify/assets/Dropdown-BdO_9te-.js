import{B as Ie,V as Ke,f as _e,h as ce,r as ze,N as $e,p as fe,b as Oe}from"./Popover-BrJClfDH.js";import{b_ as De,be as Ae,a1 as W,W as de,b$ as Fe,c0 as Te,X as je,Y as q,r as j,d as K,y as l,H as ae,aP as X,Z as B,J as P,a9 as k,I as O,ah as he,az as le,V as ve,G as Z,c1 as Be,_ as be,p as m,T as Me,ag as G,c2 as me,a5 as E,F as Le,c3 as Ee,c4 as He,c5 as Ue,L as Ve,M as ue,ab as $,b2 as We,c6 as qe,a0 as re,a3 as I,av as T}from"./index-D9Ac4DhN.js";import{f as Ge,u as Xe}from"./get-CfFPLqoW.js";import{c as Ze}from"./create-ref-setter-C4J8sofl.js";function Je(e={},n){const d=Ae({ctrl:!1,command:!1,win:!1,shift:!1,tab:!1}),{keydown:r,keyup:t}=e,o=a=>{switch(a.key){case"Control":d.ctrl=!0;break;case"Meta":d.command=!0,d.win=!0;break;case"Shift":d.shift=!0;break;case"Tab":d.tab=!0;break}r!==void 0&&Object.keys(r).forEach(w=>{if(w!==a.key)return;const v=r[w];if(typeof v=="function")v(a);else{const{stop:g=!1,prevent:x=!1}=v;g&&a.stopPropagation(),x&&a.preventDefault(),v.handler(a)}})},s=a=>{switch(a.key){case"Control":d.ctrl=!1;break;case"Meta":d.command=!1,d.win=!1;break;case"Shift":d.shift=!1;break;case"Tab":d.tab=!1;break}t!==void 0&&Object.keys(t).forEach(w=>{if(w!==a.key)return;const v=t[w];if(typeof v=="function")v(a);else{const{stop:g=!1,prevent:x=!1}=v;g&&a.stopPropagation(),x&&a.preventDefault(),v.handler(a)}})},u=()=>{(n===void 0||n.value)&&(W("keydown",document,o),W("keyup",document,s)),n!==void 0&&de(n,a=>{a?(W("keydown",document,o),W("keyup",document,s)):(q("keydown",document,o),q("keyup",document,s))})};return Fe()?(Te(u),je(()=>{(n===void 0||n.value)&&(q("keydown",document,o),q("keyup",document,s))})):u(),De(d)}function Ye(e,n,d){const r=j(e.value);let t=null;return de(e,o=>{t!==null&&window.clearTimeout(t),o===!0?d&&!d.value?r.value=!0:t=window.setTimeout(()=>{r.value=!0},n):r.value=!1}),r}const Qe=K({name:"ChevronRight",render(){return l("svg",{viewBox:"0 0 16 16",fill:"none",xmlns:"http://www.w3.org/2000/svg"},l("path",{d:"M5.64645 3.14645C5.45118 3.34171 5.45118 3.65829 5.64645 3.85355L9.79289 8L5.64645 12.1464C5.45118 12.3417 5.45118 12.6583 5.64645 12.8536C5.84171 13.0488 6.15829 13.0488 6.35355 12.8536L10.8536 8.35355C11.0488 8.15829 11.0488 7.84171 10.8536 7.64645L6.35355 3.14645C6.15829 2.95118 5.84171 2.95118 5.64645 3.14645Z",fill:"currentColor"}))}}),se=ae("n-dropdown-menu"),J=ae("n-dropdown"),pe=ae("n-dropdown-option"),we=K({name:"DropdownDivider",props:{clsPrefix:{type:String,required:!0}},render(){return l("div",{class:`${this.clsPrefix}-dropdown-divider`})}}),eo=K({name:"DropdownGroupHeader",props:{clsPrefix:{type:String,required:!0},tmNode:{type:Object,required:!0}},setup(){const{showIconRef:e,hasSubmenuRef:n}=B(se),{renderLabelRef:d,labelFieldRef:r,nodePropsRef:t,renderOptionRef:o}=B(J);return{labelField:r,showIcon:e,hasSubmenu:n,renderLabel:d,nodeProps:t,renderOption:o}},render(){var e;const{clsPrefix:n,hasSubmenu:d,showIcon:r,nodeProps:t,renderLabel:o,renderOption:s}=this,{rawNode:u}=this.tmNode,a=l("div",Object.assign({class:`${n}-dropdown-option`},t==null?void 0:t(u)),l("div",{class:`${n}-dropdown-option-body ${n}-dropdown-option-body--group`},l("div",{"data-dropdown-option":!0,class:[`${n}-dropdown-option-body__prefix`,r&&`${n}-dropdown-option-body__prefix--show-icon`]},X(u.icon)),l("div",{class:`${n}-dropdown-option-body__label`,"data-dropdown-option":!0},o?o(u):X((e=u.title)!==null&&e!==void 0?e:u[this.labelField])),l("div",{class:[`${n}-dropdown-option-body__suffix`,d&&`${n}-dropdown-option-body__suffix--has-submenu`],"data-dropdown-option":!0})));return s?s({node:a,option:u}):a}}),oo=P("icon",`
 height: 1em;
 width: 1em;
 line-height: 1em;
 text-align: center;
 display: inline-block;
 position: relative;
 fill: currentColor;
`,[k("color-transition",{transition:"color .3s var(--n-bezier)"}),k("depth",{color:"var(--n-color)"},[O("svg",{opacity:"var(--n-opacity)",transition:"opacity .3s var(--n-bezier)"})]),O("svg",{height:"1em",width:"1em"})]),no=Object.assign(Object.assign({},Z.props),{depth:[String,Number],size:[Number,String],color:String,component:[Object,Function]}),to=K({_n_icon__:!0,name:"Icon",inheritAttrs:!1,props:no,setup(e){const{mergedClsPrefixRef:n,inlineThemeDisabled:d}=ve(e),r=Z("Icon","-icon",oo,Be,e,n),t=m(()=>{const{depth:s}=e,{common:{cubicBezierEaseInOut:u},self:a}=r.value;if(s!==void 0){const{color:w,[`opacity${s}Depth`]:v}=a;return{"--n-bezier":u,"--n-color":w,"--n-opacity":v}}return{"--n-bezier":u,"--n-color":"","--n-opacity":""}}),o=d?be("icon",m(()=>`${e.depth||"d"}`),t,e):void 0;return{mergedClsPrefix:n,mergedStyle:m(()=>{const{size:s,color:u}=e;return{fontSize:Ge(s),color:u}}),cssVars:d?void 0:t,themeClass:o==null?void 0:o.themeClass,onRender:o==null?void 0:o.onRender}},render(){var e;const{$parent:n,depth:d,mergedClsPrefix:r,component:t,onRender:o,themeClass:s}=this;return!((e=n==null?void 0:n.$options)===null||e===void 0)&&e._n_icon__&&he("icon","don't wrap `n-icon` inside `n-icon`"),o==null||o(),l("i",le(this.$attrs,{role:"img",class:[`${r}-icon`,s,{[`${r}-icon--depth`]:d,[`${r}-icon--color-transition`]:d!==void 0}],style:[this.cssVars,this.mergedStyle]}),t?l(t):this.$slots)}});function ie(e,n){return e.type==="submenu"||e.type===void 0&&e[n]!==void 0}function ro(e){return e.type==="group"}function ye(e){return e.type==="divider"}function io(e){return e.type==="render"}const ge=K({name:"DropdownOption",props:{clsPrefix:{type:String,required:!0},tmNode:{type:Object,required:!0},parentKey:{type:[String,Number],default:null},placement:{type:String,default:"right-start"},props:Object,scrollable:Boolean},setup(e){const n=B(J),{hoverKeyRef:d,keyboardKeyRef:r,lastToggledSubmenuKeyRef:t,pendingKeyPathRef:o,activeKeyPathRef:s,animatedRef:u,mergedShowRef:a,renderLabelRef:w,renderIconRef:v,labelFieldRef:g,childrenFieldRef:x,renderOptionRef:N,nodePropsRef:R,menuPropsRef:D}=n,S=B(pe,null),_=B(se),z=B(me),U=m(()=>e.tmNode.rawNode),H=m(()=>{const{value:i}=x;return ie(e.tmNode.rawNode,i)}),Y=m(()=>{const{disabled:i}=e.tmNode;return i}),Q=m(()=>{if(!H.value)return!1;const{key:i,disabled:f}=e.tmNode;if(f)return!1;const{value:y}=d,{value:A}=r,{value:te}=t,{value:F}=o;return y!==null?F.includes(i):A!==null?F.includes(i)&&F[F.length-1]!==i:te!==null?F.includes(i):!1}),ee=m(()=>r.value===null&&!u.value),oe=Ye(Q,300,ee),ne=m(()=>!!(S!=null&&S.enteringSubmenuRef.value)),M=j(!1);E(pe,{enteringSubmenuRef:M});function L(){M.value=!0}function V(){M.value=!1}function C(){const{parentKey:i,tmNode:f}=e;f.disabled||a.value&&(t.value=i,r.value=null,d.value=f.key)}function c(){const{tmNode:i}=e;i.disabled||a.value&&d.value!==i.key&&C()}function p(i){if(e.tmNode.disabled||!a.value)return;const{relatedTarget:f}=i;f&&!ce({target:f},"dropdownOption")&&!ce({target:f},"scrollbarRail")&&(d.value=null)}function h(){const{value:i}=H,{tmNode:f}=e;a.value&&!i&&!f.disabled&&(n.doSelect(f.key,f.rawNode),n.doUpdateShow(!1))}return{labelField:g,renderLabel:w,renderIcon:v,siblingHasIcon:_.showIconRef,siblingHasSubmenu:_.hasSubmenuRef,menuProps:D,popoverBody:z,animated:u,mergedShowSubmenu:m(()=>oe.value&&!ne.value),rawNode:U,hasSubmenu:H,pending:G(()=>{const{value:i}=o,{key:f}=e.tmNode;return i.includes(f)}),childActive:G(()=>{const{value:i}=s,{key:f}=e.tmNode,y=i.findIndex(A=>f===A);return y===-1?!1:y<i.length-1}),active:G(()=>{const{value:i}=s,{key:f}=e.tmNode,y=i.findIndex(A=>f===A);return y===-1?!1:y===i.length-1}),mergedDisabled:Y,renderOption:N,nodeProps:R,handleClick:h,handleMouseMove:c,handleMouseEnter:C,handleMouseLeave:p,handleSubmenuBeforeEnter:L,handleSubmenuAfterEnter:V}},render(){var e,n;const{animated:d,rawNode:r,mergedShowSubmenu:t,clsPrefix:o,siblingHasIcon:s,siblingHasSubmenu:u,renderLabel:a,renderIcon:w,renderOption:v,nodeProps:g,props:x,scrollable:N}=this;let R=null;if(t){const z=(e=this.menuProps)===null||e===void 0?void 0:e.call(this,r,r.children);R=l(xe,Object.assign({},z,{clsPrefix:o,scrollable:this.scrollable,tmNodes:this.tmNode.children,parentKey:this.tmNode.key}))}const D={class:[`${o}-dropdown-option-body`,this.pending&&`${o}-dropdown-option-body--pending`,this.active&&`${o}-dropdown-option-body--active`,this.childActive&&`${o}-dropdown-option-body--child-active`,this.mergedDisabled&&`${o}-dropdown-option-body--disabled`],onMousemove:this.handleMouseMove,onMouseenter:this.handleMouseEnter,onMouseleave:this.handleMouseLeave,onClick:this.handleClick},S=g==null?void 0:g(r),_=l("div",Object.assign({class:[`${o}-dropdown-option`,S==null?void 0:S.class],"data-dropdown-option":!0},S),l("div",le(D,x),[l("div",{class:[`${o}-dropdown-option-body__prefix`,s&&`${o}-dropdown-option-body__prefix--show-icon`]},[w?w(r):X(r.icon)]),l("div",{"data-dropdown-option":!0,class:`${o}-dropdown-option-body__label`},a?a(r):X((n=r[this.labelField])!==null&&n!==void 0?n:r.title)),l("div",{"data-dropdown-option":!0,class:[`${o}-dropdown-option-body__suffix`,u&&`${o}-dropdown-option-body__suffix--has-submenu`]},this.hasSubmenu?l(to,null,{default:()=>l(Qe,null)}):null)]),this.hasSubmenu?l(Ie,null,{default:()=>[l(Ke,null,{default:()=>l("div",{class:`${o}-dropdown-offset-container`},l(_e,{show:this.mergedShowSubmenu,placement:this.placement,to:N&&this.popoverBody||void 0,teleportDisabled:!N},{default:()=>l("div",{class:`${o}-dropdown-menu-wrapper`},d?l(Me,{onBeforeEnter:this.handleSubmenuBeforeEnter,onAfterEnter:this.handleSubmenuAfterEnter,name:"fade-in-scale-up-transition",appear:!0},{default:()=>R}):R)}))})]}):null);return v?v({node:_,option:r}):_}}),ao=K({name:"NDropdownGroup",props:{clsPrefix:{type:String,required:!0},tmNode:{type:Object,required:!0},parentKey:{type:[String,Number],default:null}},render(){const{tmNode:e,parentKey:n,clsPrefix:d}=this,{children:r}=e;return l(Le,null,l(eo,{clsPrefix:d,tmNode:e,key:e.key}),r==null?void 0:r.map(t=>{const{rawNode:o}=t;return o.show===!1?null:ye(o)?l(we,{clsPrefix:d,key:t.key}):t.isGroup?(he("dropdown","`group` node is not allowed to be put in `group` node."),null):l(ge,{clsPrefix:d,tmNode:t,parentKey:n,key:t.key})}))}}),lo=K({name:"DropdownRenderOption",props:{tmNode:{type:Object,required:!0}},render(){const{rawNode:{render:e,props:n}}=this.tmNode;return l("div",n,[e==null?void 0:e()])}}),xe=K({name:"DropdownMenu",props:{scrollable:Boolean,showArrow:Boolean,arrowStyle:[String,Object],clsPrefix:{type:String,required:!0},tmNodes:{type:Array,default:()=>[]},parentKey:{type:[String,Number],default:null}},setup(e){const{renderIconRef:n,childrenFieldRef:d}=B(J);E(se,{showIconRef:m(()=>{const t=n.value;return e.tmNodes.some(o=>{var s;if(o.isGroup)return(s=o.children)===null||s===void 0?void 0:s.some(({rawNode:a})=>t?t(a):a.icon);const{rawNode:u}=o;return t?t(u):u.icon})}),hasSubmenuRef:m(()=>{const{value:t}=d;return e.tmNodes.some(o=>{var s;if(o.isGroup)return(s=o.children)===null||s===void 0?void 0:s.some(({rawNode:a})=>ie(a,t));const{rawNode:u}=o;return ie(u,t)})})});const r=j(null);return E(He,null),E(Ue,null),E(me,r),{bodyRef:r}},render(){const{parentKey:e,clsPrefix:n,scrollable:d}=this,r=this.tmNodes.map(t=>{const{rawNode:o}=t;return o.show===!1?null:io(o)?l(lo,{tmNode:t,key:t.key}):ye(o)?l(we,{clsPrefix:n,key:t.key}):ro(o)?l(ao,{clsPrefix:n,tmNode:t,parentKey:e,key:t.key}):l(ge,{clsPrefix:n,tmNode:t,parentKey:e,key:t.key,props:o.props,scrollable:d})});return l("div",{class:[`${n}-dropdown-menu`,d&&`${n}-dropdown-menu--scrollable`],ref:"bodyRef"},d?l(Ee,{contentClass:`${n}-dropdown-menu__content`},{default:()=>r}):r,this.showArrow?ze({clsPrefix:n,arrowStyle:this.arrowStyle,arrowClass:void 0,arrowWrapperClass:void 0,arrowWrapperStyle:void 0}):null)}}),so=P("dropdown-menu",`
 transform-origin: var(--v-transform-origin);
 background-color: var(--n-color);
 border-radius: var(--n-border-radius);
 box-shadow: var(--n-box-shadow);
 position: relative;
 transition:
 background-color .3s var(--n-bezier),
 box-shadow .3s var(--n-bezier);
`,[Ve(),P("dropdown-option",`
 position: relative;
 `,[O("a",`
 text-decoration: none;
 color: inherit;
 outline: none;
 `,[O("&::before",`
 content: "";
 position: absolute;
 left: 0;
 right: 0;
 top: 0;
 bottom: 0;
 `)]),P("dropdown-option-body",`
 display: flex;
 cursor: pointer;
 position: relative;
 height: var(--n-option-height);
 line-height: var(--n-option-height);
 font-size: var(--n-font-size);
 color: var(--n-option-text-color);
 transition: color .3s var(--n-bezier);
 `,[O("&::before",`
 content: "";
 position: absolute;
 top: 0;
 bottom: 0;
 left: 4px;
 right: 4px;
 transition: background-color .3s var(--n-bezier);
 border-radius: var(--n-border-radius);
 `),ue("disabled",[k("pending",`
 color: var(--n-option-text-color-hover);
 `,[$("prefix, suffix",`
 color: var(--n-option-text-color-hover);
 `),O("&::before","background-color: var(--n-option-color-hover);")]),k("active",`
 color: var(--n-option-text-color-active);
 `,[$("prefix, suffix",`
 color: var(--n-option-text-color-active);
 `),O("&::before","background-color: var(--n-option-color-active);")]),k("child-active",`
 color: var(--n-option-text-color-child-active);
 `,[$("prefix, suffix",`
 color: var(--n-option-text-color-child-active);
 `)])]),k("disabled",`
 cursor: not-allowed;
 opacity: var(--n-option-opacity-disabled);
 `),k("group",`
 font-size: calc(var(--n-font-size) - 1px);
 color: var(--n-group-header-text-color);
 `,[$("prefix",`
 width: calc(var(--n-option-prefix-width) / 2);
 `,[k("show-icon",`
 width: calc(var(--n-option-icon-prefix-width) / 2);
 `)])]),$("prefix",`
 width: var(--n-option-prefix-width);
 display: flex;
 justify-content: center;
 align-items: center;
 color: var(--n-prefix-color);
 transition: color .3s var(--n-bezier);
 z-index: 1;
 `,[k("show-icon",`
 width: var(--n-option-icon-prefix-width);
 `),P("icon",`
 font-size: var(--n-option-icon-size);
 `)]),$("label",`
 white-space: nowrap;
 flex: 1;
 z-index: 1;
 `),$("suffix",`
 box-sizing: border-box;
 flex-grow: 0;
 flex-shrink: 0;
 display: flex;
 justify-content: flex-end;
 align-items: center;
 min-width: var(--n-option-suffix-width);
 padding: 0 8px;
 transition: color .3s var(--n-bezier);
 color: var(--n-suffix-color);
 z-index: 1;
 `,[k("has-submenu",`
 width: var(--n-option-icon-suffix-width);
 `),P("icon",`
 font-size: var(--n-option-icon-size);
 `)]),P("dropdown-menu","pointer-events: all;")]),P("dropdown-offset-container",`
 pointer-events: none;
 position: absolute;
 left: 0;
 right: 0;
 top: -4px;
 bottom: -4px;
 `)]),P("dropdown-divider",`
 transition: background-color .3s var(--n-bezier);
 background-color: var(--n-divider-color);
 height: 1px;
 margin: 4px 0;
 `),P("dropdown-menu-wrapper",`
 transform-origin: var(--v-transform-origin);
 width: fit-content;
 `),O(">",[P("scrollbar",`
 height: inherit;
 max-height: inherit;
 `)]),ue("scrollable",`
 padding: var(--n-padding);
 `),k("scrollable",[$("content",`
 padding: var(--n-padding);
 `)])]),co={animated:{type:Boolean,default:!0},keyboard:{type:Boolean,default:!0},size:String,inverted:Boolean,placement:{type:String,default:"bottom"},onSelect:[Function,Array],options:{type:Array,default:()=>[]},menuProps:Function,showArrow:Boolean,renderLabel:Function,renderIcon:Function,renderOption:Function,nodeProps:Function,labelField:{type:String,default:"label"},keyField:{type:String,default:"key"},childrenField:{type:String,default:"children"},value:[String,Number]},uo=Object.keys(fe),po=Object.assign(Object.assign(Object.assign({},fe),co),Z.props),mo=K({name:"Dropdown",inheritAttrs:!1,props:po,setup(e){const n=j(!1),d=Xe(I(e,"show"),n),r=m(()=>{const{keyField:c,childrenField:p}=e;return Oe(e.options,{getKey(h){return h[c]},getDisabled(h){return h.disabled===!0},getIgnored(h){return h.type==="divider"||h.type==="render"},getChildren(h){return h[p]}})}),t=m(()=>r.value.treeNodes),o=j(null),s=j(null),u=j(null),a=m(()=>{var c,p,h;return(h=(p=(c=o.value)!==null&&c!==void 0?c:s.value)!==null&&p!==void 0?p:u.value)!==null&&h!==void 0?h:null}),w=m(()=>r.value.getPath(a.value).keyPath),v=m(()=>r.value.getPath(e.value).keyPath),g=G(()=>e.keyboard&&d.value);Je({keydown:{ArrowUp:{prevent:!0,handler:ee},ArrowRight:{prevent:!0,handler:Q},ArrowDown:{prevent:!0,handler:oe},ArrowLeft:{prevent:!0,handler:Y},Enter:{prevent:!0,handler:ne},Escape:H}},g);const{mergedClsPrefixRef:x,inlineThemeDisabled:N,mergedComponentPropsRef:R}=ve(e),D=m(()=>{var c,p;return e.size||((p=(c=R==null?void 0:R.value)===null||c===void 0?void 0:c.Dropdown)===null||p===void 0?void 0:p.size)||"medium"}),S=Z("Dropdown","-dropdown",so,qe,e,x);E(J,{labelFieldRef:I(e,"labelField"),childrenFieldRef:I(e,"childrenField"),renderLabelRef:I(e,"renderLabel"),renderIconRef:I(e,"renderIcon"),hoverKeyRef:o,keyboardKeyRef:s,lastToggledSubmenuKeyRef:u,pendingKeyPathRef:w,activeKeyPathRef:v,animatedRef:I(e,"animated"),mergedShowRef:d,nodePropsRef:I(e,"nodeProps"),renderOptionRef:I(e,"renderOption"),menuPropsRef:I(e,"menuProps"),doSelect:_,doUpdateShow:z}),de(d,c=>{!e.animated&&!c&&U()});function _(c,p){const{onSelect:h}=e;h&&re(h,c,p)}function z(c){const{"onUpdate:show":p,onUpdateShow:h}=e;p&&re(p,c),h&&re(h,c),n.value=c}function U(){o.value=null,s.value=null,u.value=null}function H(){z(!1)}function Y(){L("left")}function Q(){L("right")}function ee(){L("up")}function oe(){L("down")}function ne(){const c=M();c!=null&&c.isLeaf&&d.value&&(_(c.key,c.rawNode),z(!1))}function M(){var c;const{value:p}=r,{value:h}=a;return!p||h===null?null:(c=p.getNode(h))!==null&&c!==void 0?c:null}function L(c){const{value:p}=a,{value:{getFirstAvailableNode:h}}=r;let i=null;if(p===null){const f=h();f!==null&&(i=f.key)}else{const f=M();if(f){let y;switch(c){case"down":y=f.getNext();break;case"up":y=f.getPrev();break;case"right":y=f.getChild();break;case"left":y=f.getParent();break}y&&(i=y.key)}}i!==null&&(o.value=null,s.value=i)}const V=m(()=>{const{inverted:c}=e,p=D.value,{common:{cubicBezierEaseInOut:h},self:i}=S.value,{padding:f,dividerColor:y,borderRadius:A,optionOpacityDisabled:te,[T("optionIconSuffixWidth",p)]:F,[T("optionSuffixWidth",p)]:Se,[T("optionIconPrefixWidth",p)]:Pe,[T("optionPrefixWidth",p)]:ke,[T("fontSize",p)]:Ne,[T("optionHeight",p)]:Re,[T("optionIconSize",p)]:Ce}=i,b={"--n-bezier":h,"--n-font-size":Ne,"--n-padding":f,"--n-border-radius":A,"--n-option-height":Re,"--n-option-prefix-width":ke,"--n-option-icon-prefix-width":Pe,"--n-option-suffix-width":Se,"--n-option-icon-suffix-width":F,"--n-option-icon-size":Ce,"--n-divider-color":y,"--n-option-opacity-disabled":te};return c?(b["--n-color"]=i.colorInverted,b["--n-option-color-hover"]=i.optionColorHoverInverted,b["--n-option-color-active"]=i.optionColorActiveInverted,b["--n-option-text-color"]=i.optionTextColorInverted,b["--n-option-text-color-hover"]=i.optionTextColorHoverInverted,b["--n-option-text-color-active"]=i.optionTextColorActiveInverted,b["--n-option-text-color-child-active"]=i.optionTextColorChildActiveInverted,b["--n-prefix-color"]=i.prefixColorInverted,b["--n-suffix-color"]=i.suffixColorInverted,b["--n-group-header-text-color"]=i.groupHeaderTextColorInverted):(b["--n-color"]=i.color,b["--n-option-color-hover"]=i.optionColorHover,b["--n-option-color-active"]=i.optionColorActive,b["--n-option-text-color"]=i.optionTextColor,b["--n-option-text-color-hover"]=i.optionTextColorHover,b["--n-option-text-color-active"]=i.optionTextColorActive,b["--n-option-text-color-child-active"]=i.optionTextColorChildActive,b["--n-prefix-color"]=i.prefixColor,b["--n-suffix-color"]=i.suffixColor,b["--n-group-header-text-color"]=i.groupHeaderTextColor),b}),C=N?be("dropdown",m(()=>`${D.value[0]}${e.inverted?"i":""}`),V,e):void 0;return{mergedClsPrefix:x,mergedTheme:S,mergedSize:D,tmNodes:t,mergedShow:d,handleAfterLeave:()=>{e.animated&&U()},doUpdateShow:z,cssVars:N?void 0:V,themeClass:C==null?void 0:C.themeClass,onRender:C==null?void 0:C.onRender}},render(){const e=(r,t,o,s,u)=>{var a;const{mergedClsPrefix:w,menuProps:v}=this;(a=this.onRender)===null||a===void 0||a.call(this);const g=(v==null?void 0:v(void 0,this.tmNodes.map(N=>N.rawNode)))||{},x={ref:Ze(t),class:[r,`${w}-dropdown`,`${w}-dropdown--${this.mergedSize}-size`,this.themeClass],clsPrefix:w,tmNodes:this.tmNodes,style:[...o,this.cssVars],showArrow:this.showArrow,arrowStyle:this.arrowStyle,scrollable:this.scrollable,onMouseenter:s,onMouseleave:u};return l(xe,le(this.$attrs,x,g))},{mergedTheme:n}=this,d={show:this.mergedShow,theme:n.peers.Popover,themeOverrides:n.peerOverrides.Popover,internalOnAfterLeave:this.handleAfterLeave,internalRenderBody:e,onUpdateShow:this.doUpdateShow,"onUpdate:show":void 0};return l($e,Object.assign({},We(this.$props,uo),d),{trigger:()=>{var r,t;return(t=(r=this.$slots).default)===null||t===void 0?void 0:t.call(r)}})}});export{Qe as C,mo as N};
