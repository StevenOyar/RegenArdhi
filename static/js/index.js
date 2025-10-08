// Floating Get Started Button Visibility
document.addEventListener("DOMContentLoaded", () => {
  const floatingBtn = document.querySelector(".floating-btn");

  if (!floatingBtn) return;

  window.addEventListener("scroll", () => {
    const scrollY = window.scrollY;
    const triggerHeight = window.innerHeight / 1.3;

    if (scrollY > triggerHeight) {
      floatingBtn.classList.add("visible");
    } else {
      floatingBtn.classList.remove("visible");
    }
  });
});
