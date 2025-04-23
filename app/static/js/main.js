// Allgemeine JavaScript-Funktionen für die gesamte Anwendung
document.addEventListener('DOMContentLoaded', function() {
    // Aktiviere Bootstrap-Tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});