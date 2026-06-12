document.getElementById("password-addon") &&
  document
    .getElementById("password-addon")
    .addEventListener("click", function () {
      var e = document.getElementById("password-input");
      "password" === e.type ? (e.type = "text") : (e.type = "password");

      var e = document.getElementById("usePassword");
      "password" === e.type ? (e.type = "text") : (e.type = "password");
    });
