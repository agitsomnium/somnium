(function(){
  'use strict';
  var KEY='somnium-theme';
  var root=document.documentElement;
  var VALID={a:1,b:1};
  function readStored(){
    try{var v=localStorage.getItem(KEY);return (v==='a'||v==='b')?v:null;}catch(e){return null;}
  }
  function writeStored(v){
    try{localStorage.setItem(KEY,v);}catch(e){}
  }
  function resolveInitial(){
    var s=readStored();
    if(s)return s;
    var d=window.somniumDefaultTheme;
    if(d==='a'||d==='b')return d;
    return 'a';
  }
  function apply(theme){
    if(theme!=='a'&&theme!=='b')theme='a';
    root.classList.remove('theme-a','theme-b');
    root.classList.add('theme-'+theme);
    var mode=theme==='a'?'dark':'light';
    root.dataset.colorMode=mode;
    root.style.colorScheme=mode;
    return theme;
  }
  var current=apply(resolveInitial());
  function syncButtons(){
    var group=document.querySelector('[data-theme-switch]');
    if(group)group.classList.remove('hidden');
    var btns=document.querySelectorAll('[data-theme-choice]');
    for(var i=0;i<btns.length;i++){
      var b=btns[i];
      var val=b.getAttribute('data-theme-choice');
      b.setAttribute('aria-pressed',val===current?'true':'false');
    }
  }
  function setTheme(theme,persist){
    current=apply(theme);
    if(persist)writeStored(current);
    syncButtons();
    try{window.dispatchEvent(new CustomEvent('somnium-theme-change',{detail:{theme:current}}));}catch(e){}
  }
  function onClick(e){
    var t=e.target;
    while(t&&t!==document){
      if(t.getAttribute&&t.hasAttribute('data-theme-choice')){
        var v=t.getAttribute('data-theme-choice');
        if(v==='a'||v==='b'){setTheme(v,true);}
        return;
      }
      t=t.parentNode;
    }
  }
  function init(){
    syncButtons();
    var group=document.querySelector('[data-theme-switch]');
    if(group)group.addEventListener('click',onClick);
  }
  if(document.readyState==='loading'){
    document.addEventListener('DOMContentLoaded',init);
  }else{
    init();
  }
  window.addEventListener('storage',function(ev){
    if(ev.key!==KEY)return;
    var nv=ev.newValue;
    if(nv==='a'||nv==='b'){setTheme(nv,false);}
    else{setTheme('a',false);}
  });
})();