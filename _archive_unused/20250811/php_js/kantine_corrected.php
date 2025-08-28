<?php
// Korrigierte kantine.php für WordPress
// Ersetzt die alte CSV-basierte Version

// Fehlerbehandlung für WordPress
error_reporting(E_ALL);
ini_set('display_errors', 1);

// Konfiguration - HIER MÜSSEN SIE DIE IP-ADRESSE IHRES SCANDY-SERVERS EINTRAGEN
$scandy_api_url = 'https://195.37.23.143:5000';  // ÄNDERN SIE DIESE IP-ADRESSE! HTTPS VERWENDEN!
$api_key = '';  // Optional
$cache_duration = 300; // 5 Minuten
$cache_file = '/tmp/kantine_cache.json';

// Funktion zum Abrufen der API-Daten
function fetch_canteen_data($api_url) {
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $api_url . '/api/canteen/current_week');
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 10);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, true);  // SSL-VERIFIKATION AKTIVIEREN!
    curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, 2);     // HOST-VERIFIKATION AKTIVIEREN!
    curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 5);
    curl_setopt($ch, CURLOPT_USERAGENT, 'WordPress-Kantinenplan/1.0');
    
    $response = curl_exec($ch);
    $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $error = curl_error($ch);
    curl_close($ch);
    
    if ($error) {
        error_log("Kantinenplan cURL Error: $error");
        return false;
    }
    
    if ($http_code !== 200) {
        error_log("Kantinenplan HTTP Error: $http_code");
        return false;
    }
    
    $data = json_decode($response, true);
    if (!$data) {
        error_log("Kantinenplan JSON Parse Error");
        return false;
    }
    
    return $data;
}

// Cache-Funktion
function get_cached_data($cache_file, $cache_duration) {
    if (file_exists($cache_file)) {
        $cache_time = filemtime($cache_file);
        if (time() - $cache_time < $cache_duration) {
            $cached_data = file_get_contents($cache_file);
            return json_decode($cached_data, true);
        }
    }
    return false;
}

function save_cache_data($cache_file, $data) {
    try {
        file_put_contents($cache_file, json_encode($data));
        return true;
    } catch (Exception $e) {
        error_log("Kantinenplan Cache Error: " . $e->getMessage());
        return false;
    }
}

// Hauptlogik mit Fehlerbehandlung
try {
    // API-Daten abrufen (mit Cache)
    $api_data = get_cached_data($cache_file, $cache_duration);
    
    if (!$api_data) {
        $api_data = fetch_canteen_data($scandy_api_url);
        if ($api_data) {
            save_cache_data($cache_file, $api_data);
        }
    }
    
    if (!$api_data) {
        echo "<div style='color: red; padding: 10px; border: 1px solid red;'>Kantinenplan-Daten konnten nicht geladen werden. Bitte versuchen Sie es später erneut.</div>";
        return;
    }
    
    // Daten in CSV-Format konvertieren (kompatibel mit alter kantine.php)
    $csvArray = [];
    $datum = array();
    $menu1 = array();
    $menu2 = array();
    $dessert = array();
    
    if (isset($api_data['week']) && is_array($api_data['week'])) {
        foreach ($api_data['week'] as $meal) {
            $datum[] = $meal['date'];
            $menu1[] = $meal['meat_dish'] ?? '';
            $menu2[] = $meal['vegan_dish'] ?? '';
            $dessert[] = $meal['dessert'] ?? '';
        }
    }
    
    if (empty($datum)) {
        echo "<div style='color: orange; padding: 10px; border: 1px solid orange;'>Keine Kantinenplan-Daten verfügbar.</div>";
        return;
    }
    
    // Datum-Vergleich (wie in alter kantine.php)
    $heute1 = date("d.m.Y");
    $heute2 = date("j.n.Y");
    $heute3 = date("j.m.Y");
    
    $index = null;
    for($i = 0; $i < count($datum); ++$i) {
        $datum_clean = substr($datum[$i], -10); // Extrahiere "DD.MM.YYYY" aus "Montag, DD.MM.YYYY"
        
        if ($heute1 == $datum_clean || $heute2 == $datum_clean || $heute3 == $datum_clean) {
            $index = $i;
            break;
        }
    }
    
    if ($index === null) {
        echo "<div style='color: orange; padding: 10px; border: 1px solid orange;'>Datum $heute1 nicht in den Kantinenplan-Daten gefunden!</div>";
        return;
    }
    
    // Wochentag-Berechnung (wie in alter kantine.php)
    $remainder = 0;
    if ($index > 0) {
        $remainder = ($index % 5);
    }
    if ($remainder > 0) {
        $index = $index - $remainder;
    }
    
    $endofweek = $index + 5;
    $today = $index + $remainder;
    
    // HTML-Tabelle ausgeben (wie in alter kantine.php)
    echo("<table style='width: 100%; border-collapse: collapse; margin: 10px 0;'> 
    <tr style='background-color: #f0f0f0;'> 
    <th style='border: 1px solid #ddd; padding: 8px; text-align: left;'>Tag, Datum</th> 
    <th style='border: 1px solid #ddd; padding: 8px; text-align: left;'>Menü 1</th> 
    <th style='border: 1px solid #ddd; padding: 8px; text-align: left;'>Menü 2 (Vegan)</th>
    <th style='border: 1px solid #ddd; padding: 8px; text-align: left;'>Dessert</th>
    </tr>");
    
    for($index; $index < $endofweek; ++$index) {
        $dessert_display = isset($dessert[$index]) ? $dessert[$index] : '';
        
        if ($index == $today) {
            echo("<tr style='background-color: #fff3cd;'> 
    <td style='border: 1px solid #ddd; padding: 8px;'>" . htmlspecialchars($datum[$index]) . "</td> 
    <td style='border: 1px solid #ddd; padding: 8px;'>" . htmlspecialchars($menu1[$index]) . "</td> 
    <td style='border: 1px solid #ddd; padding: 8px;'>" . htmlspecialchars($menu2[$index]) . "</td>
    <td style='border: 1px solid #ddd; padding: 8px;'>" . htmlspecialchars($dessert_display) . "</td>
    </tr> ");
        } else {
            echo("<tr class='optionallyhidden' style='background-color: #f8f9fa;'> 
    <td style='border: 1px solid #ddd; padding: 8px;'>" . htmlspecialchars($datum[$index]) . "</td> 
    <td style='border: 1px solid #ddd; padding: 8px;'>" . htmlspecialchars($menu1[$index]) . "</td> 
    <td style='border: 1px solid #ddd; padding: 8px;'>" . htmlspecialchars($menu2[$index]) . "</td>
    <td style='border: 1px solid #ddd; padding: 8px;'>" . htmlspecialchars($dessert_display) . "</td>
    </tr> ");
        }
    }
    
    echo("</table>");
    
} catch (Exception $e) {
    error_log("Kantinenplan Exception: " . $e->getMessage());
    echo "<div style='color: red; padding: 10px; border: 1px solid red;'>Fehler beim Laden des Kantinenplans: " . htmlspecialchars($e->getMessage()) . "</div>";
}
?> 