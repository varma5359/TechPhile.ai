document.addEventListener("DOMContentLoaded", () => {
    const page = document.body;
    const themeButton = document.getElementById("tp-theme-toggle");
    const layoutButton = document.getElementById("tp-layout-toggle");
    const resetButton = document.getElementById("tp-layout-reset");
    const safeStore = {
        get(key) { try { return localStorage.getItem(key); } catch (error) { return null; } },
        set(key, value) { try { localStorage.setItem(key, value); } catch (error) {} },
        remove(key) { try { localStorage.removeItem(key); } catch (error) {} },
    };

    const setDarkMode = (enabled) => {
        page.classList.toggle("tp-dashboard-dark", enabled);
        if (themeButton) {
            themeButton.textContent = enabled ? "Light mode" : "Dark mode";
            themeButton.setAttribute("aria-pressed", String(enabled));
        }
        safeStore.set("tp_admin_dashboard_dark", enabled ? "1" : "0");
    };
    setDarkMode(safeStore.get("tp_admin_dashboard_dark") === "1");
    themeButton?.addEventListener("click", () => setDarkMode(!page.classList.contains("tp-dashboard-dark")));

    const sortableGroups = [...document.querySelectorAll(".tp-sortable[data-layout-key]")];
    const applySavedOrder = (group) => {
        let ids;
        try { ids = JSON.parse(safeStore.get(`tp_admin_order_${group.dataset.layoutKey}`) || "[]"); } catch (error) { ids = []; }
        ids.forEach((id) => {
            const item = [...group.children].find((child) => child.dataset.layoutId === id);
            if (item) group.appendChild(item);
        });
    };
    sortableGroups.forEach((group) => {
        applySavedOrder(group);
        [...group.children].filter((item) => item.dataset.layoutId).forEach((item) => {
            const grip = document.createElement("span");
            grip.className = "tp-layout-grip";
            grip.textContent = "⋮⋮";
            grip.setAttribute("aria-hidden", "true");
            item.prepend(grip);
            item.draggable = false;
            item.addEventListener("dragstart", (event) => {
                if (!page.classList.contains("tp-dashboard-customizing")) { event.preventDefault(); return; }
                item.classList.add("tp-dragging");
                event.dataTransfer.effectAllowed = "move";
                event.dataTransfer.setData("text/plain", item.dataset.layoutId);
            });
            item.addEventListener("dragend", () => {
                item.classList.remove("tp-dragging");
                group.querySelectorAll(".tp-drop-target").forEach((target) => target.classList.remove("tp-drop-target"));
                safeStore.set(`tp_admin_order_${group.dataset.layoutKey}`, JSON.stringify([...group.children].map((child) => child.dataset.layoutId).filter(Boolean)));
            });
            item.addEventListener("dragover", (event) => {
                if (!page.classList.contains("tp-dashboard-customizing") || item.classList.contains("tp-dragging")) return;
                event.preventDefault();
                item.classList.add("tp-drop-target");
            });
            item.addEventListener("dragleave", () => item.classList.remove("tp-drop-target"));
            item.addEventListener("drop", (event) => {
                event.preventDefault();
                const dragged = group.querySelector(".tp-dragging");
                if (!dragged || dragged === item) return;
                const before = event.clientY < item.getBoundingClientRect().top + item.offsetHeight / 2;
                group.insertBefore(dragged, before ? item : item.nextSibling);
                item.classList.remove("tp-drop-target");
            });
        });
    });
    layoutButton?.addEventListener("click", () => {
        const enabled = !page.classList.contains("tp-dashboard-customizing");
        page.classList.toggle("tp-dashboard-customizing", enabled);
        layoutButton.setAttribute("aria-pressed", String(enabled));
        layoutButton.textContent = enabled ? "Done customizing" : "Customize layout";
        sortableGroups.forEach((group) => group.querySelectorAll(":scope > [data-layout-id]").forEach((item) => { item.draggable = enabled; }));
    });
    resetButton?.addEventListener("click", () => {
        sortableGroups.forEach((group) => safeStore.remove(`tp_admin_order_${group.dataset.layoutKey}`));
        window.location.reload();
    });

    const canvas = document.getElementById("tp-activity-chart");
    const dataNode = document.getElementById("tp-activity-data");

    if (!canvas || !dataNode || typeof Chart === "undefined") return;

    let payload;
    try {
        payload = JSON.parse(dataNode.textContent);
    } catch (error) {
        return;
    }

    const darkMode = document.documentElement.classList.contains("dark") || page.classList.contains("tp-dashboard-dark");
    const styles = getComputedStyle(document.documentElement);
    const tickColor = styles.getPropertyValue(darkMode ? "--color-base-300" : "--color-base-500").trim();
    const gridColor = styles.getPropertyValue(darkMode ? "--color-base-800" : "--color-base-200").trim();
    payload.datasets.forEach((dataset) => {
        dataset.backgroundColor = "rgba(37, 99, 235, 0.10)";
        dataset.borderColor = "rgb(37, 99, 235)";
        dataset.borderWidth = 2.5;
        dataset.fill = true;
        dataset.tension = 0.34;
        dataset.pointRadius = 2.5;
        dataset.pointHoverRadius = 5;
        dataset.pointBackgroundColor = "rgb(37, 99, 235)";
        dataset.pointBorderColor = "#ffffff";
        dataset.pointBorderWidth = 2;
    });

    new Chart(canvas, {
        type: "line",
        data: payload,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? false : { duration: 450 },
            interaction: { intersect: false, mode: "index" },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        title: (items) => payload.full_labels?.[items[0]?.dataIndex] || items[0]?.label || "",
                    },
                },
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { color: tickColor, maxRotation: 0, autoSkip: true, maxTicksLimit: 14 },
                },
                y: {
                    beginAtZero: true,
                    suggestedMax: Math.max(...payload.datasets.flatMap((dataset) => dataset.data), 1),
                    ticks: { color: tickColor, precision: 0, stepSize: 1 },
                    grid: { color: gridColor },
                },
            },
        },
    });
});
