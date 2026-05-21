
      // Page initialization
      document.addEventListener("DOMContentLoaded", function () {
        const username = localStorage.getItem("username");
        document.getElementById("userName").textContent = username || "User";
        loadHistory();
        updateDailyStats();
      });

      // Tab switching
      function switchTab(tabName) {
        document.querySelectorAll(".tab-content").forEach((tab) => tab.classList.remove("active"));
        document.querySelectorAll(".nav-btn").forEach((btn) => btn.classList.remove("active"));
        document.getElementById(tabName + "-tab").classList.add("active");
        event.target.classList.add("active");
      }

      // Search Food
      async function searchFood() {
        const foodName = document.getElementById("foodSearch").value.trim();
        if (!foodName) {
          alert("Please enter a food name");
          return;
        }

        const resultsDiv = document.getElementById("searchResults");
        resultsDiv.innerHTML = '<div class="loader-container"><div class="spinner"></div><p style="color: var(--text-secondary);">Searching database...</p></div>';

        try {
          const response = await fetch("/manual", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            // Pass grams: 100 to trigger the backend's USDA API lookup fallback
            body: JSON.stringify({ food: foodName, grams: 100 })
          });
          
          if (!response.ok) {
            showSearchResults(getDummyFoodData(foodName)); // fallback if USDA API fails
          } else {
            const data = await response.json();
            if (data.success && data.nutrition) {
              const mappedData = {
                name: data.food,
                calories: data.nutrition.calories,
                protein: data.nutrition.protein !== "Unknown" ? data.nutrition.protein + "g" : "0g",
                carbs: data.nutrition.carbohydrates !== "Unknown" ? data.nutrition.carbohydrates + "g" : "0g",
                fat: data.nutrition.fat !== "Unknown" ? data.nutrition.fat + "g" : "0g",
                serving: "100g"
              };
              showSearchResults([mappedData]);
            } else {
              showSearchResults(getDummyFoodData(foodName));
            }
          }
        } catch (error) {
          showSearchResults(getDummyFoodData(foodName));
        }
      }

      function getDummyFoodData(foodName) {
        const foods = {
          apple: { name: "Apple", calories: 95, serving: "1 medium (182g)", protein: "0.5g", carbs: "25g", fat: "0.3g" },
          banana: { name: "Banana", calories: 105, serving: "1 medium (118g)", protein: "1.3g", carbs: "27g", fat: "0.4g" },
          pizza: { name: "Pizza", calories: 285, serving: "1 slice (107g)", protein: "12g", carbs: "36g", fat: "10g" },
          burger: { name: "Burger", calories: 354, serving: "1 burger (110g)", protein: "20g", carbs: "29g", fat: "17g" },
          rice: { name: "Rice", calories: 206, serving: "1 cup cooked (158g)", protein: "4.3g", carbs: "45g", fat: "0.4g" },
        };
        return [
          foods[foodName.toLowerCase()] || { name: foodName, calories: 150, serving: "100g", protein: "5g", carbs: "20g", fat: "5g" },
        ];
      }

      function showSearchResults(results) {
        const resultsDiv = document.getElementById("searchResults");
        if (!results || results.length === 0) {
          resultsDiv.innerHTML = '<p style="text-align: center; color: var(--error-color); padding: 20px;">No results found</p>';
          return;
        }

        const qty = parseFloat(document.getElementById("foodQuantity").value) || 1;
        const selectedUnit = getEffectiveUnit("foodUnit", "foodUnitCustom");
        const unit = selectedUnit.toLowerCase();

        let html = "";
        results.forEach((food) => {
          const baseCalories = Number(food.calories) || 0;
          let totalCalories = baseCalories;

          if (unit === "grams" || unit === "g" || unit === "ml") {
            const match = String(food.serving || "").match(/(\d+(?:\.\d+)?)\s*g/i);
            const servingGrams = match ? parseFloat(match[1]) : 100;
            totalCalories = (baseCalories / servingGrams) * qty;
          } else {
            totalCalories = baseCalories * qty;
          }

          totalCalories = Number(totalCalories.toFixed(2));

          html += `
            <div class="result-card">
                <div class="result-food-name">${food.name || "Unknown Food"}</div>
                <div class="nutrition-grid">
                    <div class="nutrition-item">
                        <div class="nutrition-label">Calories</div>
                        <div class="nutrition-value" style="color: #fca5a5;">${food.calories || 0}</div>
                    </div>
                    <div class="nutrition-item">
                        <div class="nutrition-label">Protein</div>
                        <div class="nutrition-value" style="color: #6ee7b7;">${food.protein || "N/A"}</div>
                    </div>
                    <div class="nutrition-item">
                        <div class="nutrition-label">Carbs</div>
                        <div class="nutrition-value" style="color: #93c5fd;">${food.carbs || "N/A"}</div>
                    </div>
                    <div class="nutrition-item">
                        <div class="nutrition-label">Fat</div>
                        <div class="nutrition-value" style="color: #c4b5fd;">${food.fat || "N/A"}</div>
                    </div>
                </div>
                <div style="margin-top: 24px; padding: 16px; background: rgba(168, 85, 247, 0.1); border-left: 4px solid var(--primary-color); border-radius: 8px;">
                  <span style="color: var(--text-secondary); font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">Calculation For:</span><br/>
                  <strong style="font-size: 18px; margin-top: 4px; display: inline-block;">${qty} ${selectedUnit}</strong> 
                  <span style="float: right; font-size: 20px; color: #fff; font-weight: 700;">${totalCalories} kcal</span>
                </div>
                <button onclick="addToHistory('${food.name}', ${totalCalories}, '${qty} ${selectedUnit}')" class="btn-primary" style="margin-top: 24px; width: 100%;">
                    Add to History
                </button>
            </div>
          `;
        });
        resultsDiv.innerHTML = html;
      }

      function getEffectiveUnit(selectId, customInputId) {
        const selected = document.getElementById(selectId).value;
        if (selected === "custom") {
          return document.getElementById(customInputId).value.trim() || "custom";
        }
        return selected;
      }

      function toggleCustomUnit(selectId, customWrapperId) {
        const selected = document.getElementById(selectId).value;
        const wrapper = document.getElementById(customWrapperId);
        wrapper.style.display = selected === "custom" ? "block" : "none";
      }

      // Image Upload
      function handleImageUpload(event) {
        const file = event.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = function (e) {
          document.getElementById("previewArea").innerHTML = `<img src="${e.target.result}" alt="Preview" style="max-width: 100%; border-radius: 16px; margin-top: 24px; box-shadow: var(--glass-shadow);">`;
          document.getElementById("predictBtn").style.display = "flex";
        };
        reader.readAsDataURL(file);
      }

      async function predictFood() {
        const fileInput = document.getElementById("foodImage");
        if (!fileInput.files[0]) {
          alert("Please select an image");
          return;
        }

        const formData = new FormData();
        formData.append("image", fileInput.files[0]);

        const resultsDiv = document.getElementById("predictionResults");
        resultsDiv.innerHTML = '<div class="loader-container"><div class="spinner"></div><p style="color: var(--text-secondary);">AI is analyzing image...</p></div>';

        try {
          const response = await fetch("/predict", { method: "POST", body: formData });
          if (response.ok) {
            const data = await response.json();
            showPredictionResults(data);
          } else {
            // Demo fallback
            resultsDiv.innerHTML = `
              <div class="result-card">
                  <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px;">
                    <div class="result-food-name" style="margin-bottom: 0;">Pizza (Demo)</div>
                    <span class="badge badge-purple">95% Match</span>
                  </div>
                  
                  <div class="nutrition-grid">
                      <div class="nutrition-item">
                          <div class="nutrition-label">Calories</div>
                          <div class="nutrition-value" style="color: #fca5a5;">285</div>
                      </div>
                      <div class="nutrition-item">
                          <div class="nutrition-label">Protein</div>
                          <div class="nutrition-value" style="color: #6ee7b7;">12g</div>
                      </div>
                      <div class="nutrition-item">
                          <div class="nutrition-label">Carbs</div>
                          <div class="nutrition-value" style="color: #93c5fd;">36g</div>
                      </div>
                      <div class="nutrition-item">
                          <div class="nutrition-label">Fat</div>
                          <div class="nutrition-value" style="color: #c4b5fd;">10g</div>
                      </div>
                  </div>
                  <button onclick="addToHistory('Pizza', 285, '1 slice')" class="btn-primary" style="margin-top: 24px; width: 100%;">
                      Add to History
                  </button>
              </div>
            `;
          }
        } catch (error) {
          resultsDiv.innerHTML = '<p style="text-align: center; color: var(--error-color); padding: 20px;">Error predicting food classification</p>';
        }
      }

      function showPredictionResults(data) {
        const confPercent = Math.round((data.confidence || 0.5) * 100);
        const foodName = data.final_food || data.food || (data.prediction && data.prediction.food) || "Detected Food";
        const nutrition = data.calories_data || (data.prediction && data.prediction.nutrition) || {};
        const calories = nutrition.calories || 0;
        const protein = nutrition.protein || "N/A";
        const carbs = nutrition.carbohydrates || nutrition.carbs || "N/A";
        const fat = nutrition.fat || "N/A";
        const serving = nutrition.serving_size || nutrition.serving || "100g";

        const resultsDiv = document.getElementById("predictionResults");
        const html = `
          <div class="result-card">
              <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px;">
                  <div class="result-food-name" style="margin-bottom: 0;">${foodName}</div>
                  <span class="badge badge-purple">${confPercent}% Confidence</span>
              </div>
              
              <!-- Confidence Progress Bar -->
              <div style="margin-bottom: 24px;">
                  <div style="display: flex; justify-content: space-between; font-size: 12px; color: var(--text-secondary); margin-bottom: 6px;">
                      <span>AI Model Match</span>
                      <span>${confPercent}%</span>
                  </div>
                  <div class="progress-container" style="height: 6px;">
                      <div class="progress-bar-fill" style="width: ${confPercent}%; background: var(--primary-gradient);"></div>
                  </div>
              </div>

              <div class="nutrition-grid">
                  <div class="nutrition-item">
                      <div class="nutrition-label">Calories</div>
                      <div class="nutrition-value" style="color: #fca5a5;">${calories}</div>
                  </div>
                  <div class="nutrition-item">
                      <div class="nutrition-label">Protein</div>
                      <div class="nutrition-value" style="color: #6ee7b7;">${protein}</div>
                  </div>
                  <div class="nutrition-item">
                      <div class="nutrition-label">Carbs</div>
                      <div class="nutrition-value" style="color: #93c5fd;">${carbs}</div>
                  </div>
                  <div class="nutrition-item">
                      <div class="nutrition-label">Fat</div>
                      <div class="nutrition-value" style="color: #c4b5fd;">${fat}</div>
                  </div>
              </div>
              <p style="margin-top: 24px; font-size: 13px; color: var(--text-secondary); background: rgba(0,0,0,0.2); padding: 12px; border-radius: 8px;">
                  Standard Serving: ${serving}
              </p>
              <button onclick="addToHistory('${foodName}', ${calories}, '${serving}')" class="btn-primary" style="margin-top: 24px; width: 100%;">
                  Add to History
              </button>
          </div>
        `;
        resultsDiv.innerHTML = html;
      }

      // Manual Food Entry
      async function addManualFood() {
        const name = document.getElementById("manualFoodName").value.trim();
        const quantity = parseFloat(document.getElementById("manualQuantity").value);
        const selectedUnit = getEffectiveUnit("manualUnit", "manualUnitCustom");
        const caloriesPerUnit = parseFloat(document.getElementById("manualCalories").value);
        const serving = document.getElementById("manualServing").value.trim();

        if (!name || Number.isNaN(quantity) || Number.isNaN(caloriesPerUnit) || !serving) {
          alert("Please fill in all required fields");
          return;
        }

        const totalCalories = Number((quantity * caloriesPerUnit).toFixed(2));

        try {
          await fetch("/manual", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ food: name, calories_per_unit: caloriesPerUnit, unit: selectedUnit, quantity }),
          });
        } catch (error) {
          console.log("Manual entry saved locally");
        }

        const formattedServing = `${quantity} ${selectedUnit}`;
        addToHistory(name, totalCalories, formattedServing);

        // Reset
        document.getElementById("manualFoodName").value = "";
        document.getElementById("manualQuantity").value = "1";
        document.getElementById("manualCalories").value = "";
        alert("Food added to history successfully!");
      }

      // History Management & Daily Stats
      function addToHistory(name, calories, serving) {
        let history = JSON.parse(localStorage.getItem("foodHistory") || "[]");
        // Ensure calories is a strictly valid number before saving
        let safeCals = Number(calories);
        if (Number.isNaN(safeCals)) safeCals = 0;
        
        history.unshift({
          id: Date.now(),
          name,
          calories: safeCals,
          serving,
          date: new Date().toLocaleString(),
          dayStr: new Date().toDateString() // For daily tracking
        });
        history = history.slice(0, 50);
        localStorage.setItem("foodHistory", JSON.stringify(history));
        loadHistory();
        updateDailyStats();
      }

      function updateDailyStats() {
        const history = JSON.parse(localStorage.getItem("foodHistory") || "[]");
        const todayStr = new Date().toDateString();
        
        let dailyTotal = 0;
        history.forEach(item => {
            if (item.dayStr === todayStr) {
                const itemCals = Number(item.calories);
                if (!Number.isNaN(itemCals)) {
                  dailyTotal += itemCals;
                }
            }
        });

        dailyTotal = Math.round(dailyTotal);
        document.getElementById("dailyCaloriesStat").textContent = dailyTotal;
        
        // Update bar (assuming 2000 goal)
        let pct = (dailyTotal / 2000) * 100;
        if (pct > 100) pct = 100;
        if (Number.isNaN(pct)) pct = 0;
        document.getElementById("dailyProgressBar").style.width = pct + "%";
      }

      function loadHistory() {
        const history = JSON.parse(localStorage.getItem("foodHistory") || "[]");
        const container = document.getElementById("historyContainer");

        if (history.length === 0) {
          container.innerHTML = '<p style="text-align: center; color: var(--text-secondary); padding: 40px 20px;">Your tracking history is empty.</p>';
          return;
        }

        let html = \`
          <table class="data-table">
              <thead>
                  <tr>
                      <th>Food Name</th>
                      <th>Kcal</th>
                      <th>Serving</th>
                      <th>Logged At</th>
                      <th>Action</th>
                  </tr>
              </thead>
              <tbody>
        \`;

        history.forEach((item) => {
          html += \`
              <tr>
                  <td style="font-weight: 500; color: #fff; text-transform: capitalize;">\${item.name}</td>
                  <td style="color: #fca5a5; font-weight: 600;">\${item.calories}</td>
                  <td>\${item.serving}</td>
                  <td style="font-size: 13px; color: var(--text-secondary);">\${item.date}</td>
                  <td><button onclick="deleteHistoryItem(\${item.id})" class="btn-danger">Delete</button></td>
              </tr>
          \`;
        });

        html += \`</tbody></table>\`;
        container.innerHTML = html;
      }

      function deleteHistoryItem(id) {
        let history = JSON.parse(localStorage.getItem("foodHistory") || "[]");
        history = history.filter((item) => item.id !== id);
        localStorage.setItem("foodHistory", JSON.stringify(history));
        loadHistory();
        updateDailyStats();
      }
    