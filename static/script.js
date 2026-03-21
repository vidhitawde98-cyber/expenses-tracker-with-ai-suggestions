document.addEventListener("DOMContentLoaded", function () {

    // ===== DARK MODE =====
    const darkModeToggle = document.getElementById("darkModeToggle");
    const body = document.body;

    if (localStorage.getItem("darkMode") === "enabled") {
        body.classList.add("dark-mode");
        if (darkModeToggle) darkModeToggle.innerText = "☀️ Light Mode";
    } else {
        if (darkModeToggle) darkModeToggle.innerText = "🌙 Dark Mode";
    }

    if (darkModeToggle) {
        darkModeToggle.addEventListener("click", function () {
            body.classList.toggle("dark-mode");
            if (body.classList.contains("dark-mode")) {
                localStorage.setItem("darkMode", "enabled");
                darkModeToggle.innerText = "☀️ Light Mode";
            } else {
                localStorage.setItem("darkMode", "disabled");
                darkModeToggle.innerText = "🌙 Dark Mode";
            }
        });
    }

    // ===== AUTO-DISMISS FLASH MESSAGES =====
    setTimeout(function () {
        const flashMessages = document.querySelectorAll('.alert-dismissible');
        flashMessages.forEach(function (alert) {
            try {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            } catch (e) {}
        });
    }, 5000);

    // ===== EYE ICON FOR ALL PASSWORD FIELDS =====
    const passwordFields = document.querySelectorAll('input[type="password"]');

    passwordFields.forEach(function (input) {
        // Create wrapper
        const wrapper = document.createElement('div');
        wrapper.style.cssText = 'position: relative; display: block;';

        // Insert wrapper before input
        input.parentNode.insertBefore(wrapper, input);
        wrapper.appendChild(input);

        // Create eye button
        const eyeBtn = document.createElement('button');
        eyeBtn.type = 'button';
        eyeBtn.innerHTML = '👁️';
        input.style.paddingRight = '44px';
        eyeBtn.style.cssText = `
            position: absolute;
            right: 10px;
            top: 0;
            bottom: 0;
            height: 100%;
            background: none;
            border: none;
            cursor: pointer;
            font-size: 18px;
            padding: 0 4px;
            line-height: 1;
            z-index: 10;
            display: flex;
            align-items: center;
            justify-content: center;
         `;
        
        wrapper.appendChild(eyeBtn);

        // Toggle on click
        eyeBtn.addEventListener('click', function () {
            if (input.type === 'password') {
                input.type = 'text';
                eyeBtn.innerHTML = '🙈';
            } else {
                input.type = 'password';
                eyeBtn.innerHTML = '👁️';
            }
        });
    });

});