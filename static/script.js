document.addEventListener("DOMContentLoaded", function() {
    // Efeito nos botões
    const buttons = document.querySelectorAll("button");
    buttons.forEach(btn => {
        btn.addEventListener("click", function() {
            this.style.transform = "scale(0.98)";
            setTimeout(() => {
                this.style.transform = "scale(1)";
            }, 100);
        });
    });

    // Validação de formulários
    const forms = document.querySelectorAll("form");
    forms.forEach(form => {
        form.addEventListener("submit", function(e) {
            const inputs = this.querySelectorAll("input[required], select[required]");
            let isValid = true;
            
            inputs.forEach(input => {
                if (!input.value.trim()) {
                    input.style.borderColor = "#e74c3c";
                    isValid = false;
                } else {
                    input.style.borderColor = "#ddd";
                }
            });
            
            if (!isValid) {
                e.preventDefault();
                alert("Por favor, preencha todos os campos obrigatórios.");
            }
        });
    });

    // Atualizar data mínima para agendamentos
    const dateInput = document.getElementById("data");
    if (dateInput) {
        const today = new Date().toISOString().split('T')[0];
        dateInput.setAttribute("min", today);
    }
});