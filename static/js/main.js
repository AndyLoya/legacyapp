/* Global JS - e.g. auto-hide flash messages */
document.addEventListener("DOMContentLoaded", function () {
  var flashes = document.querySelectorAll(".flash");
  flashes.forEach(function (el) {
    setTimeout(function () {
      el.style.opacity = "0";
      el.style.transition = "opacity 0.3s";
      setTimeout(function () {
        el.remove();
      }, 300);
    }, 4000);
  });
});
