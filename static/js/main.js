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
      <div class="timestamp" id="timestamp-${ip}">${timestamp.toLocaleString()}</div>
    `;
    users[ip] = { ip, timestamp, el };
    usersContainer.appendChild(el);
    setTimeout(() => el.classList.remove("new"), 600);
  } else {
    user.timestamp = timestamp;
    document.getElementById(`timestamp-${ip}`).textContent =
      timestamp.toLocaleString();
  }
}

function updateColors() {
  const now = new Date();
  const userList = Object.values(users);

  userList.sort((a, b) => now - a.timestamp - (now - b.timestamp));

  for (const user of userList) {
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
    usersContainer.appendChild(user.el);
  }

  requestAnimationFrame(updateColors);
}

requestAnimationFrame(updateColors);

// Подключение к Socket.IO серверу
const socket = io("http://localhost:3000");

socket.on("user_activity", (data) => {
  if (data.ip && data.timestamp) {
    createOrUpdateUser(data.ip, data.timestamp);
  }
});
