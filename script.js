
/* ============================================================
   DUKAANIQ — RETAIL INTELLIGENCE
   Frontend Controller
   ============================================================ */

"use strict";


/* ============================================================
   CONFIG
   ============================================================ */

const API_BASE = window.location.protocol === "file:" ? "http://127.0.0.1:8000" : "";

let currentData = null;
let currentPage = "dashboard";

let revenueChartInstance = null;
let countryChartInstance = null;
let trendChartInstance = null;


/* ============================================================
   DOM HELPERS
   ============================================================ */

function $(id) {
    return document.getElementById(id);
}

function formatNumber(value) {
    const number = Number(value || 0);

    return new Intl.NumberFormat("en-US", {
        maximumFractionDigits: 2
    }).format(number);
}

function formatMoney(value) {
    const number = Number(value || 0);

    return new Intl.NumberFormat("en-US", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(number);
}

function escapeHTML(value) {
    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}


/* ============================================================
   API
   ============================================================ */

async function api(endpoint, options = {}) {

    let response;

    try {
        response = await fetch(
            API_BASE + endpoint,
            {
                ...options,
                cache: "no-store"
            }
        );
    } catch (networkError) {
        console.error("DukaanIQ API connection failed:", networkError);
        throw new Error(
            "Cannot reach the DukaanIQ backend. Start FastAPI at http://127.0.0.1:8000 and try again."
        );
    }

    let data = null;

    try {
        data = await response.json();
    } catch {
        data = {};
    }

    if (!response.ok) {

        const message =
            data.detail ||
            data.message ||
            `Request failed: ${response.status}`;

        throw new Error(message);
    }

    return data;
}


/* ============================================================
   TOAST
   ============================================================ */

function showToast(message) {

    const toast = $("toast");
    const toastMessage = $("toastMessage");

    if (!toast || !toastMessage) {
        return;
    }

    toastMessage.textContent = message;

    toast.classList.add("show");

    setTimeout(() => {
        toast.classList.remove("show");
    }, 3000);
}


/* ============================================================
   NAVIGATION
   ============================================================ */

function showPage(pageId) {

    const pages = document.querySelectorAll(".page");
    const navItems = document.querySelectorAll(".nav-item");

    pages.forEach(page => {
        page.classList.toggle(
            "active",
            page.id === pageId
        );
    });

    navItems.forEach(item => {
        item.classList.toggle(
            "active",
            item.dataset.page === pageId
        );
    });

    currentPage = pageId;

    const pageNames = {
        dashboard: "Dashboard",
        products: "Products",
        inventory: "Demand",
        analytics: "Analytics",
        ai: "AI Analyst",
        reports: "Reports"
    };

    if ($("currentPage")) {
        $("currentPage").textContent =
            pageNames[pageId] || "Dashboard";
    }

    const sidebar = $("sidebar");

    if (sidebar) {
        sidebar.classList.remove("open");
    }

    if (pageId === "products") {
        loadProducts();
    }

    if (pageId === "inventory") {
        loadDemand();
    }

    if (pageId === "analytics") {
        loadAnalytics();
    }
}


/* ============================================================
   NAV EVENTS
   ============================================================ */

function setupNavigation() {

    document.querySelectorAll(".nav-item").forEach(item => {

        item.addEventListener("click", () => {

            const page = item.dataset.page;

            if (page) {
                showPage(page);
            }
        });
    });

    document.querySelectorAll("[data-page]").forEach(button => {

        if (
            button.classList.contains("nav-item")
        ) {
            return;
        }

        button.addEventListener("click", () => {

            const page = button.dataset.page;

            if (page) {
                showPage(page);
            }
        });
    });

    const mobileMenu = $("mobileMenu");

    if (mobileMenu) {

        mobileMenu.addEventListener(
            "click",
            () => {

                const sidebar = $("sidebar");

                if (sidebar) {
                    sidebar.classList.toggle("open");
                }
            }
        );
    }
}


/* ============================================================
   UPLOAD MODAL
   ============================================================ */

function openUploadModal() {

    const modal = $("uploadModal");

    if (modal) {
        modal.classList.add("active");
    }
}

function closeUploadModal() {

    const modal = $("uploadModal");

    if (modal) {
        modal.classList.remove("active");
    }
}

function setupUploadModal() {

    const closeModal = $("closeModal");
    const csvInput = $("csvInput");
    const processCSV = $("processCSV");
    const fileText = $("fileText");

    if ($("uploadButton")) {
        $("uploadButton").addEventListener(
            "click",
            openUploadModal
        );
    }

    if ($("dashboardUpload")) {
        $("dashboardUpload").addEventListener(
            "click",
            openUploadModal
        );
    }

    if ($("dashboardImportBtn")) {
        $("dashboardImportBtn").addEventListener(
            "click",
            openUploadModal
        );
    }

    if (closeModal) {
        closeModal.addEventListener(
            "click",
            closeUploadModal
        );
    }

    if (csvInput) {

        csvInput.addEventListener(
            "change",
            () => {

                const file = csvInput.files[0];

                if (!file) {

                    if (fileText) {
                        fileText.textContent =
                            "Choose a CSV file";
                    }

                    if (processCSV) {
                        processCSV.disabled = true;
                    }

                    return;
                }

                if (fileText) {
                    fileText.textContent =
                        file.name;
                }

                if (processCSV) {
                    processCSV.disabled = false;
                }
            }
        );
    }

    if (processCSV) {

        processCSV.addEventListener(
            "click",
            uploadCSV
        );
    }

    const modal = $("uploadModal");

    if (modal) {

        modal.addEventListener(
            "click",
            event => {

                if (event.target === modal) {
                    closeUploadModal();
                }
            }
        );
    }
}


/* ============================================================
   CSV UPLOAD
   ============================================================ */

async function uploadCSV() {

    const csvInput = $("csvInput");
    const processCSV = $("processCSV");

    if (!csvInput || !csvInput.files.length) {

        showToast(
            "Please select a CSV file first."
        );

        return;
    }

    const file = csvInput.files[0];

    if (!file.name.toLowerCase().endsWith(".csv")) {

        showToast(
            "Please select a valid CSV file."
        );

        return;
    }

    const formData = new FormData();

    formData.append(
        "file",
        file
    );

    try {

        if (processCSV) {
            processCSV.disabled = true;
            processCSV.textContent = "Processing...";
        }

        showToast(
            "Uploading dataset..."
        );

        const uploadResult = await api(
            "/upload",
            {
                method: "POST",
                body: formData
            }
        );

        console.log(
            "UPLOAD RESULT:",
            uploadResult
        );

        if (!uploadResult.success) {
            throw new Error(
                uploadResult.message ||
                "Upload failed."
            );
        }

        /*
         * IMPORTANT:
         * Do NOT use uploadResult.summary as the dashboard.
         * Fetch the fresh dashboard from backend.
         */

        await refreshDashboard();

        const activeDataset = await api(`/dataset?_=${Date.now()}`);
        console.log("ACTIVE DATASET AFTER UPLOAD:", activeDataset);
        if (!activeDataset.is_user_upload || activeDataset.filename !== uploadResult.filename) {
            throw new Error("Upload succeeded, but the backend did not switch to the uploaded CSV.");
        }

        closeUploadModal();

        showPage("dashboard");

        showToast(
            `CSV loaded successfully — ${formatNumber(
                uploadResult.rows
            )} rows`
        );

    } catch (error) {

        console.error(
            "UPLOAD ERROR:",
            error
        );

        showToast(
            error.message ||
            "Could not upload CSV."
        );

    } finally {

        if (processCSV) {
            processCSV.disabled = false;
            processCSV.textContent = "Process CSV";
        }
    }
}


/* ============================================================
   REFRESH DASHBOARD
   ============================================================ */

async function refreshDashboard() {

    const data = await api(
        `/dashboard?_=${Date.now()}`
    );

    console.log(
        "DASHBOARD RESULT:",
        data
    );

    if (!data.loaded) {

        currentData = null;

        renderEmptyDashboard();

        updateDatasetStatus(null);

        return;
    }

    currentData = data;

    renderDashboard(data);

    updateDatasetStatus(data);

    const banner = $("activeDatasetText");
    if (banner) {
        const filename = data.dataset_filename || "active dataset";
        banner.textContent = data.is_user_upload
            ? `ACTIVE UPLOAD: ${filename} — dashboard and reports are calculated from this CSV.`
            : `DEMO DATASET: ${filename} — upload a CSV to replace it with your own data.`;
    }
}


/* ============================================================
   DATASET STATUS
   ============================================================ */

function updateDatasetStatus(data) {

    const datasetStatus = $("datasetStatus");
    const sidebarStatusText = $("sidebarStatusText");

    if (!data || !data.loaded) {

        if (datasetStatus) {
            datasetStatus.textContent =
                "No dataset";
        }

        if (sidebarStatusText) {
            sidebarStatusText.textContent =
                "No dataset loaded";
        }

        return;
    }

    const rows =
        data.dataset_info?.rows ??
        0;

    const products =
        data.products_count ??
        data.dataset_info?.products ??
        0;

    if (datasetStatus) {
        datasetStatus.textContent =
            `${formatNumber(rows)} rows`;
    }

    if (sidebarStatusText) {
        sidebarStatusText.textContent =
            `${formatNumber(rows)} rows • ${formatNumber(products)} products`;
    }
}


/* ============================================================
   EMPTY DASHBOARD
   ============================================================ */

function renderEmptyDashboard() {

    if ($("kpiRevenue")) {
        $("kpiRevenue").textContent = "—";
    }

    if ($("kpiProfit")) {
        $("kpiProfit").textContent = "—";
    }

    if ($("kpiProducts")) {
        $("kpiProducts").textContent = "—";
    }

    if ($("kpiAlerts")) {
        $("kpiAlerts").textContent = "—";
    }

    if ($("topProductsList")) {
        $("topProductsList").innerHTML =
            "<p>Import a CSV to load products.</p>";
    }

    if ($("categoryList")) {
        $("categoryList").innerHTML =
            "<p>Import a CSV to load country sales.</p>";
    }

    if ($("alertsList")) {
        $("alertsList").innerHTML =
            "<p>Import a CSV to load sales insights.</p>";
    }
}


/* ============================================================
   DASHBOARD
   ============================================================ */

function renderDashboard(data) {

    const kpis = data.kpis || {};

    const revenue =
        kpis.revenue ??
        data.revenue ??
        0;

    const orders =
        kpis.orders ??
        data.orders ??
        0;

    const products =
        data.products_count ??
        data.dataset_info?.products ??
        0;

    const customers =
        kpis.customers ??
        data.customers ??
        0;

    /*
     * HTML currently labels:
     * kpiRevenue = Revenue
     * kpiProfit = Orders
     * kpiProducts = Products
     * kpiAlerts = Customers
     */

    if ($("kpiRevenue")) {
        $("kpiRevenue").textContent =
            formatMoney(revenue);
    }

    if ($("kpiProfit")) {
        $("kpiProfit").textContent =
            formatNumber(orders);
    }

    if ($("kpiProducts")) {
        $("kpiProducts").textContent =
            formatNumber(products);
    }

    if ($("kpiAlerts")) {
        $("kpiAlerts").textContent =
            formatNumber(customers);
    }

    renderRevenueChart(
        data.sales_trend || []
    );

    renderCountryChart(
        data.countries || []
    );

    renderTopProducts(
        data.top_products || []
    );

    renderCountryList(
        data.countries || []
    );

    renderAlerts(
        data
    );

    renderAIInsight(
        data
    );
}


/* ============================================================
   REVENUE CHART
   ============================================================ */

function renderRevenueChart(trend) {

    const canvas = $("revenueChart");

    if (!canvas || typeof Chart === "undefined") {
        return;
    }

    const labels = trend.map(
        item => item.date
    );

    const values = trend.map(
        item => Number(item.revenue || 0)
    );

    if (revenueChartInstance) {
        revenueChartInstance.destroy();
    }

    revenueChartInstance = new Chart(
        canvas,
        {
            type: "line",

            data: {
                labels,

                datasets: [
                    {
                        label: "Revenue",
                        data: values,
                        tension: 0.3,
                        fill: true
                    }
                ]
            },

            options: {
                responsive: true,

                maintainAspectRatio: false,

                plugins: {
                    legend: {
                        display: false
                    }
                },

                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        }
    );
}


/* ============================================================
   COUNTRY CHART
   ============================================================ */

function renderCountryChart(countries) {

    const canvas = $("categoryChart");

    if (!canvas || typeof Chart === "undefined") {
        return;
    }

    const topCountries =
        countries.slice(0, 7);

    const labels = topCountries.map(
        item => item.country
    );

    const values = topCountries.map(
        item => Number(item.revenue || 0)
    );

    if (countryChartInstance) {
        countryChartInstance.destroy();
    }

    countryChartInstance = new Chart(
        canvas,
        {
            type: "doughnut",

            data: {
                labels,

                datasets: [
                    {
                        data: values
                    }
                ]
            },

            options: {
                responsive: true,

                maintainAspectRatio: false,

                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        }
    );

    const total =
        values.reduce(
            (sum, value) => sum + value,
            0
        );

    if ($("donutTotal")) {

        $("donutTotal").textContent =
            formatMoney(total);
    }
}


/* ============================================================
   COUNTRY LIST
   ============================================================ */

function renderCountryList(countries) {

    const container = $("categoryList");

    if (!container) {
        return;
    }

    if (!countries.length) {

        container.innerHTML =
            "<p>No country sales data available.</p>";

        return;
    }

    container.innerHTML =
        countries
            .slice(0, 7)
            .map((country, index) => {

                return `
                    <div class="category-item">
                        <div>
                            <strong>
                                ${escapeHTML(country.country)}
                            </strong>
                        </div>

                        <div>
                            ${formatMoney(country.revenue)}
                        </div>
                    </div>
                `;
            })
            .join("");
}


/* ============================================================
   TOP PRODUCTS
   ============================================================ */

function renderTopProducts(products) {

    const container = $("topProductsList");

    if (!container) {
        return;
    }

    if (!products.length) {

        container.innerHTML =
            "<p>No product data available.</p>";

        return;
    }

    container.innerHTML =
        products
            .slice(0, 10)
            .map(product => {

                return `
                    <div class="product-item">

                        <div>
                            <strong>
                                ${escapeHTML(
                                    product.product
                                )}
                            </strong>

                            <small>
                                ${escapeHTML(
                                    product.stock_code
                                )}
                            </small>
                        </div>

                        <div>
                            <strong>
                                ${formatMoney(
                                    product.revenue
                                )}
                            </strong>

                            <small>
                                ${formatNumber(
                                    product.units_sold
                                )} units
                            </small>
                        </div>

                    </div>
                `;
            })
            .join("");
}


/* ============================================================
   DASHBOARD ALERTS / INSIGHTS
   ============================================================ */

function renderAlerts(data) {

    const container = $("alertsList");

    if (!container) {
        return;
    }

    const products =
        data.top_products || [];

    if (!products.length) {

        container.innerHTML =
            "<p>No sales alerts available.</p>";

        return;
    }

    const top = products[0];

    container.innerHTML = `
        <div class="alert-item">

            <strong>
                Highest revenue product
            </strong>

            <span>
                ${escapeHTML(top.product)}
                generated
                ${formatMoney(top.revenue)}
                in revenue.
            </span>

        </div>

        <div class="alert-item">

            <strong>
                Dataset limitation
            </strong>

            <span>
                Stock levels and profit cannot be
                calculated from this CSV.
            </span>

        </div>
    `;
}


/* ============================================================
   AI INSIGHT
   ============================================================ */

function renderAIInsight(data) {

    const title = $("aiInsightTitle");
    const text = $("aiInsightText");

    if (!title || !text) {
        return;
    }

    const products =
        data.top_products || [];

    if (!products.length) {

        title.textContent =
            "Import your sales data";

        text.textContent =
            "Upload a CSV to generate business insights.";

        return;
    }

    const top = products[0];

    title.textContent =
        "Top Revenue Product";

    text.textContent =
        `${top.product} generated ${formatMoney(
            top.revenue
        )} in revenue with ${formatNumber(
            top.units_sold
        )} units sold.`;
}


/* ============================================================
   PRODUCTS PAGE
   ============================================================ */

async function loadProducts() {

    const table = $("productTable");
    const count = $("productsCount");

    if (!table) {
        return;
    }

    try {

        const query =
            $("productSearch")?.value.trim() || "";

        const endpoint = query
            ? `/products/search?q=${encodeURIComponent(
                query
              )}&limit=100`
            : "/products?limit=100";

        const data = await api(
            endpoint
        );

        console.log(
            "PRODUCTS RESULT:",
            data
        );

        const products =
            data.products || [];

        if (count) {
            count.textContent =
                `${formatNumber(
                    data.total ?? products.length
                )} products`;
        }

        renderProductsTable(
            products
        );

    } catch (error) {

        console.error(
            "PRODUCTS ERROR:",
            error
        );

        renderProductsError(
            error.message
        );
    }
}


/* ============================================================
   PRODUCTS TABLE
   ============================================================ */

function renderProductsTable(products) {

    const table = $("productTable");

    if (!table) {
        return;
    }

    if (!products.length) {

        table.innerHTML = `
            <tr>
                <td colspan="7">
                    No products found.
                </td>
            </tr>
        `;

        return;
    }

    table.innerHTML =
        products
            .map(product => {

                return `
                    <tr>

                        <td>
                            ${escapeHTML(
                                product.product
                            )}
                        </td>

                        <td>
                            ${escapeHTML(
                                product.stock_code
                            )}
                        </td>

                        <td>
                            ${formatNumber(
                                product.units_sold
                            )}
                        </td>

                        <td>
                            ${formatMoney(
                                product.average_price
                            )}
                        </td>

                        <td>
                            ${formatMoney(
                                product.revenue
                            )}
                        </td>

                        <td>
                            N/A
                        </td>

                        <td>
                            Sales data
                        </td>

                    </tr>
                `;
            })
            .join("");
}


function renderProductsError(message) {

    const table = $("productTable");

    if (!table) {
        return;
    }

    table.innerHTML = `
        <tr>
            <td colspan="7">
                Could not load products:
                ${escapeHTML(message)}
            </td>
        </tr>
    `;
}


/* ============================================================
   PRODUCT SEARCH
   ============================================================ */

function setupProductSearch() {

    const search = $("productSearch");

    if (!search) {
        return;
    }

    let timer = null;

    search.addEventListener(
        "input",
        () => {

            clearTimeout(timer);

            timer = setTimeout(
                loadProducts,
                300
            );
        }
    );
}


/* ============================================================
   DEMAND PAGE
   ============================================================ */

async function loadDemand() {

    try {

        const data = await api(
            "/demand?limit=100"
        );

        console.log(
            "DEMAND RESULT:",
            data
        );

        renderDemand(
            data.products || []
        );

    } catch (error) {

        console.error(
            "DEMAND ERROR:",
            error
        );

        if ($("stockList")) {
            $("stockList").innerHTML =
                `<p>${escapeHTML(
                    error.message
                )}</p>`;
        }
    }
}


function renderDemand(products) {

    const list = $("stockList");
    const queue = $("restockQueue");

    if (list) {

        if (!products.length) {

            list.innerHTML =
                "<p>No demand data available.</p>";

        } else {

            list.innerHTML =
                products
                    .slice(0, 10)
                    .map(product => {

                        return `
                            <div class="stock-item">

                                <strong>
                                    ${escapeHTML(
                                        product.product
                                    )}
                                </strong>

                                <span>
                                    ${formatNumber(
                                        product.units_sold
                                    )} units sold
                                </span>

                            </div>
                        `;
                    })
                    .join("");
        }
    }

    if (queue) {

        queue.innerHTML = `
            <p>
                Actual restocking cannot be determined
                because this dataset has no stock-on-hand
                column.
            </p>
        `;
    }
}


/* ============================================================
   ANALYTICS PAGE
   ============================================================ */

async function loadAnalytics() {

    try {

        const data = await api(
            "/analytics"
        );

        console.log(
            "ANALYTICS RESULT:",
            data
        );

        renderAnalytics(
            data
        );

    } catch (error) {

        console.error(
            "ANALYTICS ERROR:",
            error
        );

        showToast(
            error.message
        );
    }
}


function renderAnalytics(data) {

    const trend =
        data.daily_sales || [];

    renderTrendChart(
        trend
    );

    const healthStats =
        $("healthStats");

    if (healthStats) {

        healthStats.innerHTML = `
            <div>
                <strong>
                    ${formatNumber(
                        trend.length
                    )}
                </strong>
                <span>Sales Days</span>
            </div>

            <div>
                <strong>
                    ${formatNumber(
                        data.customers?.length || 0
                    )}
                </strong>
                <span>Customer Records</span>
            </div>
        `;
    }
}


/* ============================================================
   TREND CHART
   ============================================================ */

function renderTrendChart(trend) {

    const canvas = $("trendChart");

    if (!canvas || typeof Chart === "undefined") {
        return;
    }

    const labels = trend.map(
        item => item.date
    );

    const values = trend.map(
        item => Number(item.revenue || 0)
    );

    if (trendChartInstance) {
        trendChartInstance.destroy();
    }

    trendChartInstance = new Chart(
        canvas,
        {
            type: "line",

            data: {
                labels,

                datasets: [
                    {
                        label: "Daily Revenue",
                        data: values,
                        tension: 0.3
                    }
                ]
            },

            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        }
    );
}


/* ============================================================
   AI ANALYST
   ============================================================ */

function setupAI() {

    const form = $("chatForm");
    const input = $("chatInput");
    const messages = $("chatMessages");

    if (form && input) {

        form.addEventListener(
            "submit",
            async event => {

                event.preventDefault();

                const question =
                    input.value.trim();

                if (!question) {
                    return;
                }

                addChatMessage(
                    "user",
                    question
                );

                input.value = "";

                addChatMessage(
                    "assistant",
                    "Analyzing your sales data..."
                );

                try {

                    const data = await api(
                        "/ask-ai",
                        {
                            method: "POST",

                            headers: {
                                "Content-Type":
                                    "application/json"
                            },

                            body: JSON.stringify({
                                question
                            })
                        }
                    );

                    removeLastAssistantMessage();

                    addChatMessage(
                        "assistant",
                        data.answer ||
                        "No answer returned.",
                        data
                    );

                } catch (error) {

                    removeLastAssistantMessage();

                    addChatMessage(
                        "assistant",
                        `Sorry, I couldn't analyze that: ${error.message}`
                    );
                }
            }
        );
    }

    document.querySelectorAll(
        ".suggestion"
    ).forEach(button => {

        button.addEventListener(
            "click",
            () => {

                const question =
                    button.textContent.trim();

                if (input) {

                    input.value =
                        question;

                    input.focus();
                }
            }
        );
    });
}


/* ============================================================
   CHAT MESSAGE
   ============================================================ */

function formatAIValue(value) {
    if (value === null || value === undefined) return "N/A";
    if (typeof value === "number") {
        return Number.isInteger(value) ? value.toLocaleString() : value.toLocaleString(undefined, {maximumFractionDigits: 2});
    }
    return String(value);
}


function addChatMessage(
    role,
    text,
    metadata = null
) {

    const messages = $("chatMessages");

    if (!messages) {
        return;
    }

    const message = document.createElement(
        "div"
    );

    message.className =
        `chat-message ${role}`;

    const tools = metadata?.tools_used || [];
    const limitations = metadata?.limitations || [];
    const structured = metadata?.structured_response || null;

    const toolHTML = tools.length
        ? `<div class="ai-tool-trace"><span>Tools used</span>${tools.map(t => `<b>${escapeHTML(t.replace("get_", "").replaceAll("_", " "))}</b>`).join("")}</div>`
        : "";

    const limitationHTML = limitations.length
        ? `<div class="ai-limitations"><strong>Data limitation:</strong> ${escapeHTML(limitations[0])}</div>`
        : "";

    let structuredHTML = "";
    if (structured) {
        const evidence = structured.evidence || [];
        const knowledge = structured.knowledge_used || [];
        const evidenceHTML = evidence.length
            ? `<div class="ai-evidence">${evidence.map(e => `<div class="ai-evidence-item"><span class="ai-evidence-label">${escapeHTML(String(e.label))}</span><span class="ai-evidence-value">${escapeHTML(formatAIValue(e.value))}</span></div>`).join("")}</div>`
            : `<div class="ai-limitations">No directly relevant numeric evidence was returned by the analytics tools.</div>`;
        const knowledgeHTML = knowledge.length
            ? `<div class="ai-knowledge"><div class="ai-card-title">Retail knowledge used</div>${knowledge.map(k => `<div class="ai-knowledge-item"><b>${escapeHTML(k.title)}</b><span>${escapeHTML(k.topic || "retail")}</span></div>`).join("")}</div>`
            : "";
        structuredHTML = `<div class="ai-structured-card"><div class="ai-card-title">Evidence from analytics</div>${evidenceHTML}<div class="ai-card-title">Recommendation</div><div class="ai-recommendation">${escapeHTML(structured.recommendation || "")}</div>${knowledgeHTML}</div>`;
    }

    message.innerHTML = `
        <div>
            ${escapeHTML(text).replace(/\n/g, "<br>")}
            ${toolHTML}
            ${structuredHTML}
            ${limitationHTML}
        </div>
    `;

    messages.appendChild(
        message
    );

    messages.scrollTop =
        messages.scrollHeight;
}


function removeLastAssistantMessage() {

    const messages = $("chatMessages");

    if (!messages) {
        return;
    }

    const children =
        messages.children;

    for (
        let i = children.length - 1;
        i >= 0;
        i--
    ) {

        if (
            children[i].classList.contains(
                "assistant"
            )
        ) {

            children[i].remove();

            return;
        }
    }
}


/* ============================================================
   REPORTS
   ============================================================ */

function setupReports() {

    const salesReportBtn =
        $("salesReportBtn");

    if (salesReportBtn) {

        salesReportBtn.addEventListener(
            "click",
            async () => {

                try {

                    const data = await api(
                        "/reports/sales"
                    );

                    downloadJSON(
                        data,
                        "dukaaniq-sales-report.json"
                    );

                    showToast(
                        "Sales report generated."
                    );

                } catch (error) {

                    showToast(
                        error.message
                    );
                }
            }
        );
    }
}


function downloadJSON(
    data,
    filename
) {

    const blob = new Blob(
        [
            JSON.stringify(
                data,
                null,
                2
            )
        ],
        {
            type: "application/json"
        }
    );

    const url =
        URL.createObjectURL(blob);

    const link =
        document.createElement("a");

    link.href = url;
    link.download = filename;

    document.body.appendChild(link);

    link.click();

    link.remove();

    URL.revokeObjectURL(url);
}


/* ============================================================
   INITIALIZATION
   ============================================================ */

async function initialize() {

    console.log(
        "DukaanIQ initializing..."
    );

    setupNavigation();

    setupUploadModal();

    setupProductSearch();

    setupAI();

    setupReports();

    try {

        await refreshDashboard();

    } catch (error) {

        console.error(
            "INITIALIZATION ERROR:",
            error
        );

        renderEmptyDashboard();

        showToast(
            "Backend is not connected."
        );
    }

    showPage("dashboard");
}


document.addEventListener(
    "DOMContentLoaded",
    initialize
);