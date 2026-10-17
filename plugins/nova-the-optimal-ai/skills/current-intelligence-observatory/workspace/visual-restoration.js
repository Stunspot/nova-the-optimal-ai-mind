"use strict";
(()=>{
  const key="current-intelligence-observatory.environment.v1";
  const select=document.getElementById("appearance");
  const allowed=new Set(["night","paper","light"]);
  let saved="night";
  try{const value=localStorage.getItem(key);if(allowed.has(value))saved=value;}catch(_){/* Preference storage can be unavailable; default remains usable. */}
  document.body.dataset.skin=saved;select.value=saved;
  select.addEventListener("change",()=>{
    const value=allowed.has(select.value)?select.value:"night";
    document.body.dataset.skin=value;
    try{localStorage.setItem(key,value);}catch(_){/* Appearance remains applied for this session. */}
  });
})();
