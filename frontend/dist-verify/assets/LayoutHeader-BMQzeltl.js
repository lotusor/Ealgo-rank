import{C as j,b5 as E,E as w,ax as x,H as p,J as m,a9 as y,d as B,y as v,a$ as H,V as I,G as f,b0 as V,_ as T,p as C,r as S,a5 as N}from"./index-D9Ac4DhN.js";function _(t){const{baseColor:e,textColor2:r,bodyColor:i,cardColor:n,dividerColor:o,actionColor:h,scrollbarColor:d,scrollbarColorHover:l,invertedColor:c}=t;return{textColor:r,textColorInverted:"#FFF",color:i,colorEmbedded:h,headerColor:n,headerColorInverted:c,footerColor:h,footerColorInverted:c,headerBorderColor:o,headerBorderColorInverted:c,footerBorderColor:o,footerBorderColorInverted:c,siderBorderColor:o,siderBorderColorInverted:c,siderColor:n,siderColorInverted:c,siderToggleButtonBorder:`1px solid ${o}`,siderToggleButtonColor:e,siderToggleButtonIconColor:r,siderToggleButtonIconColorInverted:r,siderToggleBarColor:x(i,d),siderToggleBarColorHover:x(i,l),__invertScrollbar:"true"}}const R=j({name:"Layout",common:w,peers:{Scrollbar:E},self:_}),J=p("n-layout-sider"),z={type:String,default:"static"},k=m("layout",`
 color: var(--n-text-color);
 background-color: var(--n-color);
 box-sizing: border-box;
 position: relative;
 z-index: auto;
 flex: auto;
 overflow: hidden;
 transition:
 box-shadow .3s var(--n-bezier),
 background-color .3s var(--n-bezier),
 color .3s var(--n-bezier);
`,[m("layout-scroll-container",`
 overflow-x: hidden;
 box-sizing: border-box;
 height: 100%;
 `),y("absolute-positioned",`
 position: absolute;
 left: 0;
 right: 0;
 top: 0;
 bottom: 0;
 `)]),F={embedded:Boolean,position:z,nativeScrollbar:{type:Boolean,default:!0},scrollbarProps:Object,onScroll:Function,contentClass:String,contentStyle:{type:[String,Object],default:""},hasSider:Boolean,siderPlacement:{type:String,default:"left"}},D=p("n-layout");function $(t){return B({name:t?"LayoutContent":"Layout",props:Object.assign(Object.assign({},f.props),F),setup(e){const r=S(null),i=S(null),{mergedClsPrefixRef:n,inlineThemeDisabled:o}=I(e),h=f("Layout","-layout",k,R,e,n);function d(s,a){if(e.nativeScrollbar){const{value:u}=r;u&&(a===void 0?u.scrollTo(s):u.scrollTo(s,a))}else{const{value:u}=i;u&&u.scrollTo(s,a)}}N(D,e);let l=0,c=0;const L=s=>{var a;const u=s.target;l=u.scrollLeft,c=u.scrollTop,(a=e.onScroll)===null||a===void 0||a.call(e,s)};V(()=>{if(e.nativeScrollbar){const s=r.value;s&&(s.scrollTop=c,s.scrollLeft=l)}});const O={display:"flex",flexWrap:"nowrap",width:"100%",flexDirection:"row"},P={scrollTo:d},g=C(()=>{const{common:{cubicBezierEaseInOut:s},self:a}=h.value;return{"--n-bezier":s,"--n-color":e.embedded?a.colorEmbedded:a.color,"--n-text-color":a.textColor}}),b=o?T("layout",C(()=>e.embedded?"e":""),g,e):void 0;return Object.assign({mergedClsPrefix:n,scrollableElRef:r,scrollbarInstRef:i,hasSiderStyle:O,mergedTheme:h,handleNativeElScroll:L,cssVars:o?void 0:g,themeClass:b==null?void 0:b.themeClass,onRender:b==null?void 0:b.onRender},P)},render(){var e;const{mergedClsPrefix:r,hasSider:i}=this;(e=this.onRender)===null||e===void 0||e.call(this);const n=i?this.hasSiderStyle:void 0,o=[this.themeClass,t&&`${r}-layout-content`,`${r}-layout`,`${r}-layout--${this.position}-positioned`];return v("div",{class:o,style:this.cssVars},this.nativeScrollbar?v("div",{ref:"scrollableElRef",class:[`${r}-layout-scroll-container`,this.contentClass],style:[this.contentStyle,n],onScroll:this.handleNativeElScroll},this.$slots):v(H,Object.assign({},this.scrollbarProps,{onScroll:this.onScroll,ref:"scrollbarInstRef",theme:this.mergedTheme.peers.Scrollbar,themeOverrides:this.mergedTheme.peerOverrides.Scrollbar,contentClass:this.contentClass,contentStyle:[this.contentStyle,n]}),this.$slots))}})}const W=$(!1),X=$(!0),K=m("layout-header",`
 transition:
 color .3s var(--n-bezier),
 background-color .3s var(--n-bezier),
 box-shadow .3s var(--n-bezier),
 border-color .3s var(--n-bezier);
 box-sizing: border-box;
 width: 100%;
 background-color: var(--n-color);
 color: var(--n-text-color);
`,[y("absolute-positioned",`
 position: absolute;
 left: 0;
 right: 0;
 top: 0;
 `),y("bordered",`
 border-bottom: solid 1px var(--n-border-color);
 `)]),M={position:z,inverted:Boolean,bordered:{type:Boolean,default:!1}},Y=B({name:"LayoutHeader",props:Object.assign(Object.assign({},f.props),M),setup(t){const{mergedClsPrefixRef:e,inlineThemeDisabled:r}=I(t),i=f("Layout","-layout-header",K,R,t,e),n=C(()=>{const{common:{cubicBezierEaseInOut:h},self:d}=i.value,l={"--n-bezier":h};return t.inverted?(l["--n-color"]=d.headerColorInverted,l["--n-text-color"]=d.textColorInverted,l["--n-border-color"]=d.headerBorderColorInverted):(l["--n-color"]=d.headerColor,l["--n-text-color"]=d.textColor,l["--n-border-color"]=d.headerBorderColor),l}),o=r?T("layout-header",C(()=>t.inverted?"a":"b"),n,t):void 0;return{mergedClsPrefix:e,cssVars:r?void 0:n,themeClass:o==null?void 0:o.themeClass,onRender:o==null?void 0:o.onRender}},render(){var t;const{mergedClsPrefix:e}=this;return(t=this.onRender)===null||t===void 0||t.call(this),v("div",{class:[`${e}-layout-header`,this.themeClass,this.position&&`${e}-layout-header--${this.position}-positioned`,this.bordered&&`${e}-layout-header--bordered`],style:this.cssVars},this.$slots)}});export{Y as N,X as a,W as b,D as c,J as d,R as l,z as p};
