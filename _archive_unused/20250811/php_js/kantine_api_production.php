<?php
/**
 * Kantinenplan API-Integration für WordPress
 * Vollständig kompatibel mit der alten kantine.php
 * Lädt Daten von der Scandy-API statt CSV-Datei
 * 
 * PRODUKTIONSVERSION
 */

// ========================================
// KONFIGURATION - HIER ANPASSEN!
// ========================================

// Scandy-Server URL (IHRE SERVER-IP EINTRAGEN!)
$scandy_api_url = 'https://localhost:5000/api/canteen/current_week';  // HTTPS VERWENDEN!

// Optional: API-Schlüssel für Sicherheit (falls konfiguriert)
$api_key = ''; // Leer lassen, falls kein API-Key gesetzt

// Cache-Dauer in Sekunden (5 Minuten = 300)
$cache_duration = 300;

// Cache-Datei (im gleichen Verzeichnis)
$cache_file = __DIR__ . '/canteen_cache.json';

// ========================================
// FUNKTIONEN
// ========================================

/**
 * Holt Daten von der Scandy-API
 */
function get_canteen_data_from_api($api_url, $api_key = null) {
    $url = $api_url;
    if ($api_key) {
        $url .= (strpos($url, '?') !== false ? '&' : '?') . 'api_key=' . urlencode($api_key);
    }
    
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 10);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, true);  // SSL-VERIFIKATION AKTIVIEREN!
    curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, 2);     // HOST-VERIFIKATION AKTIVIEREN!
    curl_setopt($ch, CURLOPT_USERAGENT, 'WordPress-Canteen-API/1.0');
    
    $response = curl_exec($ch);
    $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    
    if ($http_code === 200 && $response) {
        $data = json_decode($response, true);
        if ($data && isset($data['success']) && $data['success']) {
            return $data;
        }
    }
    
    return false;
}

/**
 * Lädt gecachte Daten oder holt neue von der API
 */
function get_canteen_data($api_url, $api_key, $cache_file, $cache_duration) {
    // Prüfe Cache
    if (file_exists($cache_file)) {
        $cache_data = json_decode(file_get_contents($cache_file), true);
        if ($cache_data && isset($cache_data['timestamp'])) {
            $age = time() - $cache_data['timestamp'];
            if ($age < $cache_duration) {
                return $cache_data['data'];
            }
        }
    }
    
    // Hole neue Daten von der API
    $api_data = get_canteen_data_from_api($api_url, $api_key);
    if ($api_data) {
        // Speichere in Cache
        $cache_data = [
            'timestamp' => time(),
            'data' => $api_data
        ];
        file_put_contents($cache_file, json_encode($cache_data));
        return $api_data;
    }
    
    // Fallback: Versuche Cache auch wenn veraltet
    if (file_exists($cache_file)) {
        $cache_data = json_decode(file_get_contents($cache_file), true);
        if ($cache_data && isset($cache_data['data'])) {
            return $cache_data['data'];
        }
    }
    
    return false;
}

/**
 * Konvertiert API-Daten in das alte CSV-Format für Kompatibilität
 */
function convert_api_to_csv_format($api_data) {
    $csvArray = [];
    
    // Header-Zeile (wie in alter CSV)
    $csvArray[] = ['Tag', 'Datum', 'Menü 1', 'Menü 2 (Vegan)', 'Dessert'];
    
    // Daten-Zeilen
    if (isset($api_data['week']) && is_array($api_data['week'])) {
        foreach ($api_data['week'] as $meal) {
            // Extrahiere nur das Datum aus "Montag, 04.08.2025"
            $date_part = '';
            if (isset($meal['date'])) {
                // Suche nach dem Datum nach dem Komma
                if (strpos($meal['date'], ',') !== false) {
                    $parts = explode(',', $meal['date']);
                    if (count($parts) >= 2) {
                        $date_part = trim($parts[1]); // "04.08.2025"
                    }
                } else {
                    $date_part = $meal['date'];
                }
            }
            
            $csvArray[] = [
                $meal['date'],           // Tag, Datum (vollständig)
                $meal['meat_dish'],      // Menü 1
                $meal['vegan_dish'],     // Menü 2 (Vegan)
                $meal['dessert']         // Dessert
            ];
        }
    }
    
    return $csvArray;
}

/**
 * Hauptfunktion - Vollständig kompatibel mit alter kantine.php
 */
function display_canteen_table($api_url, $api_key, $cache_file, $cache_duration) {
    // Hole Daten von API
    $api_data = get_canteen_data($api_url, $api_key, $cache_file, $cache_duration);
    
    if (!$api_data) {
        echo '<div class="alert alert-warning">';
        echo '<strong>Hinweis:</strong> Kantinenplan-Daten konnten nicht geladen werden.';
        echo '<br><small>Bitte prüfen Sie die API-Verbindung oder versuchen Sie es später erneut.</small>';
        echo '</div>';
        return;
    }
    
    // Konvertiere zu CSV-Format für Kompatibilität
    $csvArray = convert_api_to_csv_format($api_data);
    
    // Ab hier identisch mit alter kantine.php
    $datum = array();
    $menu1 = array();
    $menu2 = array();
    $dessert = array();

    // Starte bei 1 (A2, B2, etc) um die Header-Zeile zu ignorieren
    for($i = 1; $i < count($csvArray); ++$i) {
        if(!(empty($csvArray[$i][0]))) {
            array_push($datum, $csvArray[$i][0]);
        }
        if(!(empty($csvArray[$i][1]))) {
            array_push($menu1, $csvArray[$i][1]);
        }
        if(!(empty($csvArray[$i][2]))) {
            array_push($menu2, $csvArray[$i][2]);
        }
        if(!(empty($csvArray[$i][3]))) {
            array_push($dessert, $csvArray[$i][3]);
        }
    }

    $heute1 = date("d.m.Y");
    $heute2 = date("j.n.Y");
    $heute3 = date("j.m.Y");
    $index;
    
    // Finde Index wo das heutige Datum im Array $datum[] ist
    for($i = 0; $i < count($datum); ++$i) {
        // Extrahiere nur das Datum aus "Montag, 04.08.2025"
        $current_date = $datum[$i];
        if (strpos($current_date, ',') !== false) {
            $parts = explode(',', $current_date);
            if (count($parts) >= 2) {
                $current_date = trim($parts[1]); // "04.08.2025"
            }
        }
        
        if ($heute1 == $current_date or $heute2 == substr($current_date, 0, -5) or $heute2 == substr($current_date, 0, -4) or $heute3 == substr($current_date, 0, -5) or $heute3 == substr($current_date, 0, -4)) {
            $index = $i;
            break;
        }
    }

    if ($index === NULL){
        echo '<div class="alert alert-info">';
        echo '<strong>Hinweis:</strong> Keine Daten für heute gefunden.';
        echo '<br><small>Datum: ' . $heute1 . '</small>';
        echo '</div>';
        return;
    }

    // Finde heraus welcher Index Montag ist relativ zu heute
    $remainder;
    if ($index > 0){
        $remainder = ($index % 5);
    }
    if ($remainder > 0) {
        $index = $index - $remainder;
    }

    $endofweek = $index + 5;
    $today = $index + $remainder;

    // Drucke die Tabelle
    echo '<table class="table table-striped">';
    echo '<thead><tr>';
    echo '<th>Tag, Datum</th>';
    echo '<th>Menü 1</th>';
    echo '<th>Menü 2 (Vegan)</th>';
    echo '<th>Dessert</th>';
    echo '</tr></thead>';
    echo '<tbody>';
    
    for($index; $index < $endofweek; ++$index) {
        if ($index == $today) {
            echo '<tr class="table-primary">';
        } else {
            echo '<tr>';
        }
        echo '<td>' . htmlspecialchars($datum[$index] ?? '') . '</td>';
        echo '<td>' . htmlspecialchars($menu1[$index] ?? '') . '</td>';
        echo '<td>' . htmlspecialchars($menu2[$index] ?? '') . '</td>';
        echo '<td>' . htmlspecialchars($dessert[$index] ?? '') . '</td>';
        echo '</tr>';
    }
    echo '</tbody></table>';
    
    // Zeige Cache-Info
    if (isset($api_data['generated_at'])) {
        echo '<div class="text-muted small mt-2">';
        echo 'Aktualisiert: ' . date('d.m.Y H:i', strtotime($api_data['generated_at']));
        echo '</div>';
    }
}

// ========================================
// AUSFÜHRUNG
// ========================================

// Führe die Anzeige aus
display_canteen_table($scandy_api_url, $api_key, $cache_file, $cache_duration);

?> 