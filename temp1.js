
      // Load data on page load
      document.addEventListener("DOMContentLoaded", function () {
        loadStats();
        loadUsers();
        loadFoods();
        loadTrackerHistory();
        loadActivityLogs();
      });

      // Tab switching
      function switchTab(btn, tabName) {
        document.querySelectorAll(".tab-content").forEach((tab) => tab.classList.remove("active"));
        document.querySelectorAll(".nav-btn").forEach((b) => b.classList.remove("active"));
        document.getElementById(tabName + "-tab").classList.add("active");
        btn.classList.add("active");
        if (tabName === 'tracker') loadTrackerHistory();
        if (tabName === 'logs' || tabName === 'analytics' || tabName === 'overview') {
            loadActivityLogs();
            loadStats();
        }
      }

      // Load Statistics
      async function loadStats() {
        try {
          const response = await fetch("/admin/stats");
          if (response.ok) {
            const data = await response.json();
            document.getElementById("totalUsers").textContent = data.totalUsers || 0;
            document.getElementById("totalFoods").textContent = data.totalFoods || 0;
            document.getElementById("regularUsers").textContent = data.regularUsers || 0;
            
            // New metrics
            const elActive = document.getElementById("activeToday");
            if (elActive) elActive.textContent = data.activeToday || 0;
            const elSearches = document.getElementById("totalSearches");
            if (elSearches) elSearches.textContent = data.totalSearches || 0;
            const elMostSearched = document.getElementById("mostSearched");
            if (elMostSearched) elMostSearched.textContent = data.mostSearched || "-";
          } else {
            loadStatsFromLocal();
          }
        } catch (err) {
          loadStatsFromLocal();
        }
      }

      function loadStatsFromLocal() {
        try {
          const users = JSON.parse(localStorage.getItem("allUsers") || "[]");
          const foods = JSON.parse(localStorage.getItem("allFoods") || "[]");
          const admins = users.filter((u) => u.role === "admin").length;
          const regularUsers = users.filter((u) => u.role === "user").length;
          document.getElementById("totalUsers").textContent = users.length;
          document.getElementById("totalFoods").textContent = foods.length;
          document.getElementById("regularUsers").textContent = regularUsers;
        } catch (err) { console.error(err); }
      }

      // Load Users
      async function loadUsers() {
        try {
          const response = await fetch("/admin/users");
          if (response.ok) {
            const data = await response.json();
            displayUsers(data.users || []);
            localStorage.setItem("allUsers", JSON.stringify(data.users || []));
          } else {
            loadUsersFromLocal();
          }
        } catch (err) {
          loadUsersFromLocal();
        }
      }

      function loadUsersFromLocal() {
        const users = JSON.parse(localStorage.getItem("allUsers") || "[]");
        displayUsers(users);
      }

      function displayUsers(users) {
        const tbody = document.getElementById("usersTableBody");
        if (!users || users.length === 0) {
          tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-secondary);">No users found</td></tr>';
          return;
        }

        let html = "";
        users.forEach((user) => {
          const role = user.role || "user";
          const isCurrentUser = user.id == localStorage.getItem("user_id");
          html += `
            <tr>
              <td>#${user.id}</td>
              <td>${user.username || "N/A"}</td>
              <td>${user.email || "N/A"}</td>
              <td><span class="role-badge ${role}">${role}</span></td>
              <td>${user.joined || "N/A"}</td>
              <td>
                  ${!isCurrentUser ? '<button onclick="deleteUser(' + user.id + ')" class="btn-danger">Delete</button>' : '<span style="color: var(--text-secondary);">Current</span>'}
              </td>
            </tr>
          `;
        });
        tbody.innerHTML = html;
      }

      function filterUsers() {
        const input = document.getElementById("userSearch").value.toLowerCase();
        const rows = document.querySelectorAll("#usersTableBody tr");
        rows.forEach((row) => {
          const text = row.textContent.toLowerCase();
          row.style.display = text.includes(input) ? "" : "none";
        });
      }

      async function deleteUser(userId) {
        if (!confirm("Are you sure you want to delete this user?")) return;
        try {
          const response = await fetch('/admin/delete_user/' + userId, { method: "POST" });
          if (response.ok) {
            alert("User deleted successfully");
            loadUsers();
            loadStats();
          } else alert("Failed to delete user");
        } catch (err) { alert("Error deleting user"); }
      }

      // Load Foods
      async function loadFoods() {
        try {
          const response = await fetch("/admin/get_foods");
          if (response.ok) {
            const data = await response.json();
            displayFoods(data.foods || []);
            localStorage.setItem("allFoods", JSON.stringify(data.foods || []));
          } else loadFoodsFromLocal();
        } catch (err) { loadFoodsFromLocal(); }
      }

      function loadFoodsFromLocal() {
        const foods = JSON.parse(localStorage.getItem("allFoods") || "[]");
        displayFoods(foods);
      }

      function displayFoods(foods) {
        const tbody = document.getElementById("foodsTableBody");
        if (!foods || foods.length === 0) {
          tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; color: var(--text-secondary);">No foods found</td></tr>';
          return;
        }

        let html = "";
        foods.forEach((food) => {
          html += `
            <tr>
              <td>#${food.id || "-"}</td>
              <td style="text-transform: capitalize;">${food.name || "N/A"}</td>
              <td style="color: #fca5a5; font-weight: 500;">${food.calories || 0}</td>
              <td style="color: #6ee7b7;">${food.protein || 0}g</td>
              <td style="color: #93c5fd;">${food.carbs || 0}g</td>
              <td style="color: #c4b5fd;">${food.fat || 0}g</td>
              <td>${food.serving || "N/A"}</td>
              <td><button onclick="deleteFood(${food.id})" class="btn-danger">Delete</button></td>
            </tr>
          `;
        });
        tbody.innerHTML = html;
      }

      function filterFoods() {
        const input = document.getElementById("foodSearch").value.toLowerCase();
        const rows = document.querySelectorAll("#foodsTableBody tr");
        rows.forEach((row) => {
          const text = row.textContent.toLowerCase();
          row.style.display = text.includes(input) ? "" : "none";
        });
      }

      async function addFood() {
        const name = document.getElementById("foodName").value.trim();
        const calories = document.getElementById("foodCalories").value;
        const protein = document.getElementById("foodProtein").value || 0;
        const carbs = document.getElementById("foodCarbs").value || 0;
        const fat = document.getElementById("foodFat").value || 0;
        const serving = document.getElementById("foodServing").value.trim();

        if (!name || !calories || !serving) {
          alert("Please fill in required fields: Name, Calories, Serving Size");
          return;
        }

        const payload = { name, calories, protein, carbs, fat, serving };

        try {
          const response = await fetch("/admin/add_food", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          });
          if (response.ok) {
            alert("Food added successfully");
            document.getElementById("foodName").value = "";
            document.getElementById("foodCalories").value = "";
            document.getElementById("foodProtein").value = "";
            document.getElementById("foodCarbs").value = "";
            document.getElementById("foodFat").value = "";
            document.getElementById("foodServing").value = "";
            loadFoods();
            loadStats();
          } else alert("Failed to add food");
        } catch (err) { alert("Error adding food"); }
      }

      async function deleteFood(id) {
        if (!confirm("Are you sure you want to delete this food item?")) return;
        try {
          const response = await fetch('/admin/delete_food/' + id, { method: "POST" });
          if (response.ok) {
            alert("Food deleted");
            loadFoods();
            loadStats();
          } else alert("Failed to delete food");
        } catch (err) { alert("Error deleting food"); }
      }

      function toggleCustomUnit(selectId, wrapperId) {
        const val = document.getElementById(selectId).value;
        document.getElementById(wrapperId).style.display = (val === 'custom') ? 'block' : 'none';
        updateAdminTotalCalories();
      }

      function updateAdminTotalCalories() {
        const qty = parseFloat(document.getElementById("trackerQuantity").value) || 0;
        const cal = parseFloat(document.getElementById("trackerCaloriesPerUnit").value) || 0;
        document.getElementById("trackerTotalCalories").textContent = (qty * cal).toFixed(2) + " kcal";
      }

      document.getElementById("trackerQuantity").addEventListener("input", updateAdminTotalCalories);
      document.getElementById("trackerCaloriesPerUnit").addEventListener("input", updateAdminTotalCalories);

      function addAdminManualFood() {
        const name = document.getElementById("trackerFoodName").value.trim();
        const calPerUnit = parseFloat(document.getElementById("trackerCaloriesPerUnit").value);
        const qty = parseFloat(document.getElementById("trackerQuantity").value);
        const unitSelect = document.getElementById("trackerUnit").value;
        const customUnit = document.getElementById("trackerUnitCustom").value.trim();
        const finalUnit = unitSelect === 'custom' ? (customUnit || 'units') : unitSelect;

        if (!name || isNaN(calPerUnit) || isNaN(qty)) {
          alert("Please fill in required fields correctly.");
          return;
        }

        const totalCal = (calPerUnit * qty).toFixed(2);
        const newEntry = {
          id: Date.now(),
          name: name,
          total: totalCal,
          desc: `${qty} ${finalUnit} @ ${calPerUnit} kcal/each`,
          date: new Date().toLocaleString()
        };

        const history = JSON.parse(localStorage.getItem("adminTrackerHistory") || "[]");
        history.unshift(newEntry);
        localStorage.setItem("adminTrackerHistory", JSON.stringify(history.slice(0, 100)));
        
        document.getElementById("trackerFoodName").value = "";
        document.getElementById("trackerCaloriesPerUnit").value = "";
        document.getElementById("trackerQuantity").value = "1";
        updateAdminTotalCalories();
        
        loadTrackerHistory();
        alert("Added to Tracker History.");
      }

      function loadTrackerHistory() {
        const history = JSON.parse(localStorage.getItem("adminTrackerHistory") || "[]");
        const container = document.getElementById("trackerHistoryContainer");
        
        if (history.length === 0) {
          container.innerHTML = '<p style="color: var(--text-secondary);">No tracker history yet.</p>';
          return;
        }

        let html = `
          <div class="data-table-wrapper">
            <table class="data-table">
              <thead><tr><th>Food</th><th>Details</th><th>Total Kcal</th><th>Date</th><th>Action</th></tr></thead>
              <tbody>
        `;
        history.forEach(item => {
          html += `
            <tr>
              <td style="font-weight: 500; text-transform: capitalize;">${item.name}</td>
              <td style="color: var(--text-secondary);">${item.desc}</td>
              <td style="color: #fca5a5; font-weight: 600;">${item.total}</td>
              <td style="font-size: 13px;">${item.date}</td>
              <td><button class="btn-danger" onclick="deleteTrackerHistoryItem(${item.id})">Delete</button></td>
            </tr>
          `;
        });
        html += `</tbody></table></div>`;
        container.innerHTML = html;
      }

      function deleteTrackerHistoryItem(id) {
        let history = JSON.parse(localStorage.getItem("adminTrackerHistory") || "[]");
        history = history.filter(item => item.id !== id);
        localStorage.setItem("adminTrackerHistory", JSON.stringify(history));
        loadTrackerHistory();
      }

      // --- Activity Logs & Analytics ---
      let activityLogs = [];

      async function loadActivityLogs() {
        try {
          const response = await fetch("/admin/activity_logs");
          if (response.ok) {
            const data = await response.json();
            activityLogs = data.logs || [];
            renderActivityLogs();
            drawCharts(activityLogs);
          }
        } catch(err) { console.error("Error loading logs", err); }
      }

      function renderActivityLogs() {
        const filter = (document.getElementById("logFilter")?.value || "").toLowerCase();
        const tbody = document.getElementById("logsTableBody");
        if (!tbody) return;
        
        let html = '';
        const filtered = activityLogs.filter(log => 
          (log.user_email || "").toLowerCase().includes(filter) || 
          (log.action_type || "").toLowerCase().includes(filter)
        );

        if (filtered.length === 0) {
          tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-secondary)">No logs found</td></tr>';
          return;
        }

        filtered.forEach(log => {
          let dateStr = log.timestamp ? new Date(log.timestamp).toLocaleString() : '-';
          html += `
            <tr>
              <td>${dateStr}</td>
              <td style="color:#a5b4fc">${log.user_email || '-'}</td>
              <td><span class="role-badge ${log.action_type === 'search' ? 'user' : 'admin'}">${log.action_type}</span></td>
              <td>${log.food_name || '-'}</td>
              <td style="color:#fca5a5">${log.calories || 0} kcal</td>
              <td>${log.quantity || '-'}</td>
            </tr>
          `;
        });
        tbody.innerHTML = html;
      }

      let chartInstances = {};
      
      function drawCharts(logs) {
        if (!window.Chart) return;

        // Action pie chart
        const actionsCount = logs.reduce((acc, log) => {
          acc[log.action_type] = (acc[log.action_type] || 0) + 1;
          return acc;
        }, {});

        if(chartInstances.pie) chartInstances.pie.destroy();
        const ctxPie = document.getElementById('actionPieChart');
        if (ctxPie) {
          chartInstances.pie = new Chart(ctxPie, {
            type: 'doughnut',
            data: {
              labels: Object.keys(actionsCount),
              datasets: [{
                data: Object.values(actionsCount),
                backgroundColor: ['#a855f7', '#3b82f6', '#10b981', '#f59e0b']
              }]
            },
            options: { plugins: { legend: { position: 'bottom', labels: { color: '#fff' } } } }
          });
        }

        // Top 5 foods
        const foodCount = logs.filter(l => l.food_name).reduce((acc, log) => {
          acc[log.food_name] = (acc[log.food_name] || 0) + 1;
          return acc;
        }, {});
        const topFoods = Object.entries(foodCount).sort((a,b) => b[1] - a[1]).slice(0, 5);

        if(chartInstances.bar) chartInstances.bar.destroy();
        const ctxBar = document.getElementById('topFoodsBarChart');
        if (ctxBar) {
          chartInstances.bar = new Chart(ctxBar, {
            type: 'bar',
            data: {
              labels: topFoods.map(f => f[0]),
              datasets: [{
                label: 'Interactions',
                data: topFoods.map(f => f[1]),
                backgroundColor: 'rgba(59, 130, 246, 0.8)'
              }]
            },
            options: { scales: { y: { beginAtZero: true, ticks: { color: '#fff', stepSize: 1 } }, x: { ticks: { color: '#fff' } } }, plugins: { legend: { display: false } } }
          });
        }
        
        // Activity line chart
        const dayCounts = {};
        for(let i=6; i>=0; i--) {
            let d = new Date(); d.setDate(d.getDate() - i);
            dayCounts[d.toLocaleDateString()] = 0;
        }
        logs.forEach(l => {
            if(!l.timestamp) return;
            let dString = new Date(l.timestamp).toLocaleDateString();
            if (dayCounts[dString] !== undefined) dayCounts[dString]++;
        });

        if(chartInstances.line) chartInstances.line.destroy();
        const ctxLine = document.getElementById('activityLineChart');
        if (ctxLine) {
          chartInstances.line = new Chart(ctxLine, {
            type: 'line',
            data: {
              labels: Object.keys(dayCounts),
              datasets: [{
                label: 'Actions per Day',
                data: Object.values(dayCounts),
                borderColor: '#10b981',
                tension: 0.3,
                fill: true,
                backgroundColor: 'rgba(16, 185, 129, 0.1)'
              }]
            },
            options: { scales: { y: { beginAtZero: true, ticks: { color: '#fff', stepSize: 1 } }, x: { ticks: { color: '#fff' } } }, plugins: { legend: { display: false } } }
          });
        }
      }

    