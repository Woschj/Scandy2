/**
 * Moderne WordPress-Kantinenplan-Integration
 * Ersetzt die PHP-Datei durch JavaScript-API-Calls
 */

class CanteenPlanIntegration {
    constructor(config) {
        this.apiUrl = config.apiUrl || 'http://your-scandy-server.com';
        this.cacheDuration = config.cacheDuration || 300000; // 5 Minuten
        this.containerId = config.containerId || 'canteen-plan';
        this.cache = null;
        this.cacheTime = 0;
    }

    /**
     * Lädt Kantinenplan-Daten von der Scandy-API
     */
    async fetchCanteenData() {
        try {
            // Prüfe Cache
            if (this.cache && (Date.now() - this.cacheTime) < this.cacheDuration) {
                return this.cache;
            }

            const response = await fetch(`${this.apiUrl}/api/canteen/current_week`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.error || 'API-Fehler');
            }

            // Cache speichern
            this.cache = data;
            this.cacheTime = Date.now();

            return data;
        } catch (error) {
            console.error('Fehler beim Laden des Kantinenplans:', error);
            return null;
        }
    }

    /**
     * Rendert die Kantinenplan-Tabelle
     */
    renderCanteenTable(data) {
        const container = document.getElementById(this.containerId);
        if (!container) {
            console.error('Container nicht gefunden:', this.containerId);
            return;
        }

        if (!data || !data.week || data.week.length === 0) {
            container.innerHTML = `
                <div class="canteen-error">
                    <p>Keine Kantinenplan-Daten verfügbar.</p>
                    <button onclick="canteenPlan.reload()">Erneut versuchen</button>
                </div>
            `;
            return;
        }

        const today = new Date();
        const todayString = today.toLocaleDateString('de-DE');

        let tableHtml = `
            <div class="canteen-plan">
                <h3>Kantinenplan - Aktuelle Woche</h3>
                <table class="canteen-table">
                    <thead>
                        <tr>
                            <th>Tag</th>
                            <th>Datum</th>
                            <th>Menü 1 (Fleisch)</th>
                            <th>Menü 2 (Vegan)</th>
                            <th>Dessert</th>
                        </tr>
                    </thead>
                    <tbody>
        `;

        data.week.forEach((meal, index) => {
            const isToday = meal.date.includes(todayString);
            const rowClass = isToday ? 'today' : '';
            
            tableHtml += `
                <tr class="${rowClass}">
                    <td>${meal.weekday}</td>
                    <td>${meal.date}</td>
                    <td>${meal.meat_dish || '-'}</td>
                    <td>${meal.vegan_dish || '-'}</td>
                    <td>${meal.dessert || '-'}</td>
                </tr>
            `;
        });

        tableHtml += `
                    </tbody>
                </table>
                <div class="canteen-footer">
                    <small>Letzte Aktualisierung: ${new Date().toLocaleString('de-DE')}</small>
                    <button onclick="canteenPlan.reload()" class="refresh-btn">Aktualisieren</button>
                </div>
            </div>
        `;

        container.innerHTML = tableHtml;
    }

    /**
     * Lädt und rendert den Kantinenplan
     */
    async load() {
        const data = await this.fetchCanteenData();
        this.renderCanteenTable(data);
    }

    /**
     * Erzwingt Neuladen (Cache umgehen)
     */
    async reload() {
        this.cache = null;
        this.cacheTime = 0;
        await this.load();
    }

    /**
     * Automatische Aktualisierung
     */
    startAutoRefresh(interval = 300000) { // 5 Minuten
        setInterval(() => {
            this.load();
        }, interval);
    }
}

// CSS für die Kantinenplan-Anzeige
const canteenStyles = `
<style>
.canteen-plan {
    font-family: Arial, sans-serif;
    max-width: 100%;
    margin: 20px 0;
}

.canteen-table {
    width: 100%;
    border-collapse: collapse;
    margin: 10px 0;
    background: white;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.canteen-table th,
.canteen-table td {
    padding: 12px;
    text-align: left;
    border-bottom: 1px solid #ddd;
}

.canteen-table th {
    background-color: #f5f5f5;
    font-weight: bold;
    color: #333;
}

.canteen-table tr:hover {
    background-color: #f9f9f9;
}

.canteen-table tr.today {
    background-color: #e8f5e8;
    font-weight: bold;
}

.canteen-table tr.today td {
    border-left: 4px solid #4CAF50;
}

.canteen-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 10px;
    padding: 10px;
    background: #f9f9f9;
    border-radius: 4px;
}

.refresh-btn {
    background: #4CAF50;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
}

.refresh-btn:hover {
    background: #45a049;
}

.canteen-error {
    padding: 20px;
    background: #ffebee;
    border: 1px solid #f44336;
    border-radius: 4px;
    color: #c62828;
    text-align: center;
}

.canteen-loading {
    text-align: center;
    padding: 20px;
    color: #666;
}
</style>
`;

// Automatische Initialisierung
document.addEventListener('DOMContentLoaded', function() {
    // Styles einfügen
    document.head.insertAdjacentHTML('beforeend', canteenStyles);
    
    // Kantinenplan initialisieren
    window.canteenPlan = new CanteenPlanIntegration({
        apiUrl: 'http://your-scandy-server.com', // HIER IHRE SERVER-URL EINTRAGEN
        containerId: 'canteen-plan',
        cacheDuration: 300000 // 5 Minuten
    });
    
    // Kantinenplan laden
    canteenPlan.load();
    
    // Automatische Aktualisierung starten
    canteenPlan.startAutoRefresh();
});
</script> 