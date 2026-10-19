(function () {
    const body = document.body;
    const root = document.documentElement;
    const preference = body.dataset.theme || 'light';
    const systemTheme = window.matchMedia('(prefers-color-scheme: dark)');

    function applyTheme() {
        root.dataset.activeTheme = preference === 'system'
            ? (systemTheme.matches ? 'dark' : 'light')
            : preference;
    }

    applyTheme();
    if (preference === 'system') {
        if (systemTheme.addEventListener) {
            systemTheme.addEventListener('change', applyTheme);
        } else if (systemTheme.addListener) {
            systemTheme.addListener(applyTheme);
        }
    }
}());
