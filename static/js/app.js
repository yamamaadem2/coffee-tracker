const orderForm = document.getElementById("order-form");
const streakForm = document.getElementById("streak-form");
const formMessage = document.getElementById("form-message");
const streakMessage = document.getElementById("streak-message");
const streakResult = document.getElementById("streak-result");
const ordersBody = document.getElementById("orders-body");
const popularList = document.getElementById("popular-list");
const customersList = document.getElementById("customers-list");
const customerSuggestions = document.getElementById("customer-suggestions");
const streakCustomerInput = document.getElementById("streak-customer");
const refreshOrdersBtn = document.getElementById("refresh-orders");
const refreshPopularBtn = document.getElementById("refresh-popular");
const refreshCustomersBtn = document.getElementById("refresh-customers");

function setMessage(element, text, type = "") {
  element.textContent = text;
  element.className = `message${type ? ` message--${type}` : ""}`;
}

function formatDate(dateStr) {
  return new Date(`${dateStr}T00:00:00`).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function formatErrorDetail(detail) {
  if (typeof detail === "string") {
    return detail;
  }
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg ?? String(item)).join("; ");
  }
  return "Request failed.";
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });

  if (!response.ok) {
    let detail = "Something went wrong.";
    try {
      const body = await response.json();
      detail = formatErrorDetail(body.detail ?? detail);
    } catch {
      // ignore parse errors
    }
    const error = new Error(detail);
    error.status = response.status;
    throw error;
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

function updateCustomerSuggestions(customers) {
  customerSuggestions.innerHTML = customers
    .map((customer) => `<option value="${escapeHtml(customer.name)}"></option>`)
    .join("");
}

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function renderOrders(orders) {
  if (orders.length === 0) {
    ordersBody.innerHTML =
      '<tr><td colspan="3" class="orders-table__empty">No orders yet.</td></tr>';
    return;
  }

  ordersBody.innerHTML = orders
    .map(
      (order) => `
        <tr>
          <td>${escapeHtml(order.customer_name)}</td>
          <td>${escapeHtml(order.drink)}</td>
          <td>${formatDate(order.order_date)}</td>
        </tr>
      `
    )
    .join("");
}

function renderPopularDrinks(drinks) {
  if (drinks.length === 0) {
    popularList.innerHTML =
      '<li class="popular-list__empty">No orders yet — log one to get started.</li>';
    return;
  }

  popularList.innerHTML = drinks
    .map(
      (item, index) => `
        <li class="popular-list__item">
          <span class="popular-list__rank">${index + 1}</span>
          <span class="popular-list__name">${escapeHtml(item.drink)}</span>
          <span class="popular-list__count">${item.order_count} order${item.order_count === 1 ? "" : "s"}</span>
        </li>
      `
    )
    .join("");
}

function renderCustomers(customers) {
  if (customers.length === 0) {
    customersList.innerHTML =
      '<li class="customers-list__empty">No customers yet — log an order to add one.</li>';
    return;
  }

  customersList.innerHTML = customers
    .map(
      (customer) => `
        <li class="customers-list__item">
          <span class="customers-list__name">${escapeHtml(customer.name)}</span>
          <button
            type="button"
            class="btn btn--ghost btn--small customers-list__action"
            data-customer="${escapeHtml(customer.name)}"
          >
            View streak
          </button>
          <span class="customers-list__meta">
            ${customer.order_count} order${customer.order_count === 1 ? "" : "s"} ·
            current streak ${customer.current_streak} ·
            best ${customer.longest_streak}
          </span>
        </li>
      `
    )
    .join("");
}

function renderStreak(data) {
  streakResult.innerHTML = `
    <div class="stat">
      <span class="stat__value">${data.current_streak}</span>
      <span class="stat__label">Current streak</span>
    </div>
    <div class="stat">
      <span class="stat__value">${data.longest_streak}</span>
      <span class="stat__label">Longest streak</span>
    </div>
    <div class="stat">
      <span class="stat__value">${data.total_orders}</span>
      <span class="stat__label">Total orders</span>
    </div>
  `;
  streakResult.classList.remove("hidden");
}

async function loadOrders() {
  const orders = await api("/orders");
  renderOrders(orders);
  return orders;
}

async function loadCustomers() {
  const customers = await api("/customers");
  renderCustomers(customers);
  updateCustomerSuggestions(customers);
  return customers;
}

async function loadPopularDrinks() {
  const drinks = await api("/drinks/popular?top=5");
  renderPopularDrinks(drinks);
}

async function refreshAll() {
  await Promise.all([loadOrders(), loadCustomers(), loadPopularDrinks()]);
}

async function showCustomerStreak(customerName) {
  setMessage(streakMessage, "");
  streakResult.classList.add("hidden");
  streakCustomerInput.value = customerName;

  try {
    const streak = await api(`/customers/${encodeURIComponent(customerName)}/streak`);
    renderStreak(streak);
    setMessage(streakMessage, `Streak for ${streak.customer_name}`, "success");
  } catch (error) {
    if (error.status === 404) {
      setMessage(streakMessage, "Customer not found. Log an order first.", "error");
    } else {
      setMessage(streakMessage, error.message, "error");
    }
  }
}

orderForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  setMessage(formMessage, "");

  const formData = new FormData(orderForm);
  const payload = {
    customer_name: formData.get("customer_name").trim(),
    drink: formData.get("drink").trim(),
  };

  const orderDate = formData.get("order_date");
  if (orderDate) {
    payload.order_date = orderDate;
  }

  try {
    await api("/orders", {
      method: "POST",
      body: JSON.stringify(payload),
    });

    orderForm.reset();
    setMessage(formMessage, "Order logged successfully.", "success");
    await refreshAll();
  } catch (error) {
    setMessage(formMessage, error.message, "error");
  }
});

streakForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const customerName = new FormData(streakForm).get("customer_name").trim();
  await showCustomerStreak(customerName);
});

customersList.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-customer]");
  if (!button) {
    return;
  }
  await showCustomerStreak(button.dataset.customer);
});

refreshOrdersBtn.addEventListener("click", () => {
  loadOrders().catch((error) => setMessage(formMessage, error.message, "error"));
});

refreshPopularBtn.addEventListener("click", () => {
  loadPopularDrinks().catch((error) => setMessage(formMessage, error.message, "error"));
});

refreshCustomersBtn.addEventListener("click", () => {
  loadCustomers().catch((error) => setMessage(formMessage, error.message, "error"));
});

refreshAll().catch((error) => {
  ordersBody.innerHTML =
    `<tr><td colspan="3" class="orders-table__empty">${escapeHtml(error.message)}</td></tr>`;
  customersList.innerHTML =
    `<li class="customers-list__empty">${escapeHtml(error.message)}</li>`;
});
