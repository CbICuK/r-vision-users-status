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
        el.style.transform = `translate(${deltaX}px, ${deltaY}px)`;
        el.style.transition = "transform 0s";
        el.style.position = "relative";
        el.style.zIndex = "1000";
      }
  
      requestAnimationFrame(()=>{
        el.style.transform = "";
        el.style.transition = "transform 0.8s ease";

        el.addEventListener("transitionend", function handler(e) {
          if (e.propertyName === "transform") {
            el.style.zIndex = "";
            el.removeEventListener("transitionend", handler);
          }
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
    animateOiiaElements(movedOiiaElements);
  });
}
