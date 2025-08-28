<?php
/**
 * WordPress Shortcode für Kantinenplan-Integration
 * Ersetzt die custom PHP-Datei durch einen sauberen Shortcode
 */

// Verhindere direkten Zugriff
if (!defined('ABSPATH')) {
    exit;
}

/**
 * Kantinenplan Shortcode
 * Verwendung: [canteen_plan]
 */
function canteen_plan_shortcode($atts) {
    // Shortcode-Attribute
    $atts = shortcode_atts(array(
        'api_url' => 'http://your-scandy-server.com', // HIER IHRE SERVER-URL EINTRAGEN
        'cache_duration' => 300, // 5 Minuten
        'show_header' => 'true',
        'show_footer' => 'true',
        'auto_refresh' => 'true'
    ), $atts);

    // Eindeutige ID für diesen Shortcode
    $unique_id = 'canteen-plan-' . uniqid();
    
    // CSS für die Anzeige
    $css = '
    <style>
    .canteen-plan-container {
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
    </style>';

    // JavaScript für die API-Integration
    $js = "
    <script>
    (function() {
        const apiUrl = '" . esc_js($atts['api_url']) . "';
        const cacheDuration = " . intval($atts['cache_duration']) * 1000 . ";
        const containerId = '" . esc_js($unique_id) . "';
        const autoRefresh = " . ($atts['auto_refresh'] === 'true' ? 'true' : 'false') . ";
        
        let cache = null;
        let cacheTime = 0;
        
        async function fetchCanteenData() {
            try {
                // Prüfe Cache
                if (cache && (Date.now() - cacheTime) < cacheDuration) {
                    return cache;
                }
                
                const response = await fetch(apiUrl + '/api/canteen/current_week');
                if (!response.ok) {
                    throw new Error('HTTP ' + response.status + ': ' + response.statusText);
                }
                
                const data = await response.json();
                
                if (!data.success) {
                    throw new Error(data.error || 'API-Fehler');
                }
                
                // Cache speichern
                cache = data;
                cacheTime = Date.now();
                
                return data;
            } catch (error) {
                console.error('Fehler beim Laden des Kantinenplans:', error);
                return null;
            }
        }
        
        function renderCanteenTable(data) {
            const container = document.getElementById(containerId);
            if (!container) {
                console.error('Container nicht gefunden:', containerId);
                return;
            }
            
            if (!data || !data.week || data.week.length === 0) {
                container.innerHTML = `
                    <div class='canteen-error'>
                        <p>Keine Kantinenplan-Daten verfügbar.</p>
                        <button onclick='reloadCanteenPlan()'>Erneut versuchen</button>
                    </div>
                `;
                return;
            }
            
            const today = new Date();
            const todayString = today.toLocaleDateString('de-DE');
            
            let tableHtml = '';
            
            " . ($atts['show_header'] === 'true' ? "
            tableHtml += `
                <div class='canteen-plan-container'>
                    <h3>Kantinenplan - Aktuelle Woche</h3>
            `;
            " : "") . "
            
            tableHtml += `
                <table class='canteen-table'>
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
                    <tr class='\${rowClass}'>
                        <td>\${meal.weekday}</td>
                        <td>\${meal.date}</td>
                        <td>\${meal.meat_dish || '-'}</td>
                        <td>\${meal.vegan_dish || '-'}</td>
                        <td>\${meal.dessert || '-'}</td>
                    </tr>
                `;
            });
            
            tableHtml += `
                    </tbody>
                </table>
            `;
            
            " . ($atts['show_footer'] === 'true' ? "
            tableHtml += `
                <div class='canteen-footer'>
                    <small>Letzte Aktualisierung: \${new Date().toLocaleString('de-DE')}</small>
                    <button onclick='reloadCanteenPlan()' class='refresh-btn'>Aktualisieren</button>
                </div>
            `;
            " : "") . "
            
            " . ($atts['show_header'] === 'true' ? "
            tableHtml += '</div>';
            " : "") . "
            
            container.innerHTML = tableHtml;
        }
        
        async function loadCanteenPlan() {
            const data = await fetchCanteenData();
            renderCanteenTable(data);
        }
        
        function reloadCanteenPlan() {
            cache = null;
            cacheTime = 0;
            loadCanteenPlan();
        }
        
        // Globale Funktion für Reload-Button
        window.reloadCanteenPlan = reloadCanteenPlan;
        
        // Initial laden
        loadCanteenPlan();
        
        // Automatische Aktualisierung
        if (autoRefresh) {
            setInterval(loadCanteenPlan, cacheDuration);
        }
    })();
    </script>";

    // HTML-Container
    $html = '<div id="' . esc_attr($unique_id) . '" class="canteen-plan-container">';
    $html .= '<div class="canteen-loading">Lade Kantinenplan...</div>';
    $html .= '</div>';

    return $css . $js . $html;
}

// Shortcode registrieren
add_shortcode('canteen_plan', 'canteen_plan_shortcode');

/**
 * Admin-Menü für Kantinenplan-Einstellungen
 */
function canteen_plan_admin_menu() {
    add_options_page(
        'Kantinenplan Einstellungen',
        'Kantinenplan',
        'manage_options',
        'canteen-plan-settings',
        'canteen_plan_settings_page'
    );
}
add_action('admin_menu', 'canteen_plan_admin_menu');

/**
 * Einstellungsseite
 */
function canteen_plan_settings_page() {
    if (isset($_POST['submit'])) {
        update_option('canteen_plan_api_url', sanitize_text_field($_POST['api_url']));
        update_option('canteen_plan_cache_duration', intval($_POST['cache_duration']));
        echo '<div class="notice notice-success"><p>Einstellungen gespeichert!</p></div>';
    }
    
    $api_url = get_option('canteen_plan_api_url', 'http://your-scandy-server.com');
    $cache_duration = get_option('canteen_plan_cache_duration', 300);
    
    ?>
    <div class="wrap">
        <h1>Kantinenplan Einstellungen</h1>
        <form method="post">
            <table class="form-table">
                <tr>
                    <th scope="row">Scandy API URL</th>
                    <td>
                        <input type="url" name="api_url" value="<?php echo esc_attr($api_url); ?>" class="regular-text" />
                        <p class="description">URL Ihres Scandy-Servers (z.B. http://localhost:5000)</p>
                    </td>
                </tr>
                <tr>
                    <th scope="row">Cache-Dauer (Sekunden)</th>
                    <td>
                        <input type="number" name="cache_duration" value="<?php echo esc_attr($cache_duration); ?>" min="60" max="3600" />
                        <p class="description">Wie lange sollen Daten gecacht werden? (60-3600 Sekunden)</p>
                    </td>
                </tr>
            </table>
            <?php submit_button(); ?>
        </form>
        
        <h2>Verwendung</h2>
        <p>Fügen Sie den Shortcode <code>[canteen_plan]</code> in Ihre Seiten oder Beiträge ein.</p>
        
        <h3>Erweiterte Optionen:</h3>
        <ul>
            <li><code>[canteen_plan api_url="http://localhost:5000"]</code> - Benutzerdefinierte API-URL</li>
            <li><code>[canteen_plan cache_duration="600"]</code> - 10 Minuten Cache</li>
            <li><code>[canteen_plan show_header="false"]</code> - Header ausblenden</li>
            <li><code>[canteen_plan show_footer="false"]</code> - Footer ausblenden</li>
            <li><code>[canteen_plan auto_refresh="false"]</code> - Automatische Aktualisierung deaktivieren</li>
        </ul>
    </div>
    <?php
}

/**
 * Plugin-Aktivierung
 */
function canteen_plan_activate() {
    add_option('canteen_plan_api_url', 'http://your-scandy-server.com');
    add_option('canteen_plan_cache_duration', 300);
}
register_activation_hook(__FILE__, 'canteen_plan_activate');
?> 