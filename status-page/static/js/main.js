const protocol = location.protocol === "https:" ? "wss" : "ws";
const ws = new WebSocket(`${protocol}://${location.hostname}/online/ws`);

const users = {};
const usersContainer = document.getElementById("users");

const GREEN = [0, 200, 0];
const ORANGE = [255, 165, 0];
const GRAY = [128, 128, 128];
const PHASE1 = 3600;
const PHASE2 = 86400;

function lerpColor(c1, c2, t) {
  const r = Math.round(c1[0] + (c2[0] - c1[0]) * t);
  const g = Math.round(c1[1] + (c2[1] - c1[1]) * t);
  const b = Math.round(c1[2] + (c2[2] - c1[2]) * t);
  return `rgb(${r},${g},${b})`;
}

function createOrUpdateUser(ip, timestampStr) {
  const timestamp = new Date(timestampStr);
  let user = users[ip];

  if (!user) {
    const el = document.createElement("div");
    el.className = "user new";
    el.innerHTML = `
      <div class="status" id="status-${ip}"></div>
      <div class="ip">${ip}</div>
      <div class="oiia-wrapper"><div class="oiia"></div></div>
      <div class="timestamp" id="timestamp-${ip}">${timestamp.toLocaleString()}</div>
    `;
    users[ip] = { ip, timestamp, el };
    usersContainer.appendChild(el);
    setTimeout(() => el.classList.remove("new"), 600);
  } else {
    if (+user.timestamp !== +timestamp) {
      user.timestamp = timestamp;
      const tsEl = document.getElementById(`timestamp-${ip}`);
      if (tsEl) {
        tsEl.textContent = timestamp.toLocaleString();
      }
    }
  }
}

function updateColors() {
  const now = new Date();
  const userList = Object.values(users);

  const firstRects = new Map();
  for (const user of userList) {
    firstRects.set(user.el, user.el.getBoundingClientRect());
  }

  userList.sort((a,b) => b.timestamp -a.timestamp);

  for(const user of userList) {
    usersContainer.appendChild(user.el);
  }

  requestAnimationFrame(()=>{
    const movedElements = [];
    const movedOiiaElements = [];
    for (const user of userList) {
      const el = user.el;
      const firstRect = firstRects.get(el);
      const lastRect = el.getBoundingClientRect();
  
      const deltaX = firstRect.left - lastRect.left;
      const deltaY = firstRect.top - lastRect.top;
      
      if (deltaX !==0 || deltaY !==0) {
        const oiiaEl = el.querySelector(".oiia-wrapper .oiia");
        if (oiiaEl) {
          oiiaEl.style.backgroundPositionY = `0px`;
          movedElements.push(oiiaEl);
        }
        if (deltaY > 0) {
          movedOiiaElements.push(oiiaEl);
        }
        
        el.style.position = "relative";
        el.style.zIndex = "1000";
        el.style.transform = `translate(${deltaX}px, ${deltaY}px)`;
        el.style.transition = "transform 0s";
      }

      requestAnimationFrame(()=>{
        el.style.transform = "";
        el.style.transition = "transform 0.8s ease";

        el.addEventListener("transitionend", function handler(e) {
          if (e.propertyName === "transform") {
            el.style.zIndex = "";
            el.removeEventListener("transitionend", handler);
          }
          el.style.position = "";
        });
      });
  
      const ageSec = (now - user.timestamp) / 1000;
      const statusEl = user.el.querySelector(".status");
  
      let color;
      if (ageSec <= PHASE1) {
        const t = ageSec / PHASE1;
        color = lerpColor(GREEN, ORANGE, t);
      } else if (ageSec <= PHASE2) {
        const t = (ageSec - PHASE1) / (PHASE2 - PHASE1);
        color = lerpColor(ORANGE, GRAY, t);
      } else {
        color = "rgb(128,128,128)";
      }
  
      statusEl.style.backgroundColor = color;
    }
    animateOiiaElements(movedElements);
  });
}

function animateOiiaElements(elements) {
  for (const el of elements) {
    if (!el) return;

    const frameHeight = 200;
    const totalFrames = 60;
    const fps = 120;
    const duration = 1000*(totalFrames) / fps;
    let currentFrame = 0;
    const step = () => {

      if (currentFrame >=totalFrames) {
        el.style.backgroundPositionY = `0px`
        return;
      }
      el.style.backgroundPositionY = `-${currentFrame*frameHeight}px`
      currentFrame++;
      setTimeout(step, 1000/fps);
    }
    step();

  }
}

document.addEventListener("DOMContentLoaded", function () {
  const toggle = document.getElementById("oiia-toggle");

  function updateOiiaVisibility() {
    const show = toggle.checked;
    document.querySelectorAll(".oiia").forEach(el => {
      el.classList.toggle("hidden", !show);
    });
  }

  toggle.addEventListener("change", updateOiiaVisibility);

  const observer = new MutationObserver(() => updateOiiaVisibility());
  observer.observe(document.getElementById("users"), { childList: true, subtree: true });

  updateOiiaVisibility();
});

setInterval(updateColors, 1000);

ws.onmessage = (event) => {
  let data = JSON.parse(event.data);
  if (data.ip && data.timestamp) {
    createOrUpdateUser(data.ip, data.timestamp);
  }
}

