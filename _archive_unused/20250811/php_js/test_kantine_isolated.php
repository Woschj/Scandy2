<?php
// Isolierte Test-Version der kantine.php
// Testet die API-Verbindung und Datenverarbeitung

// Konfiguration
$scandy_api_url = 'https://localhost:5000';  // Lokale Scandy API - HTTPS VERWENDEN!
$api_key = '';  // Optional
$cache_duration = 300; // 5 Minuten
$cache_file = '/tmp/kantine_cache.json';

echo "<h1>Kantinenplan Test</h1>";
echo "<p>API URL: $scandy_api_url</p>";

// Funktion zum Abrufen der API-Daten
function fetch_canteen_data($api_url) {
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $api_url . '/api/canteen/current_week');
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 10);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, true);  // SSL-VERIFIKATION AKTIVIEREN!
    curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, 2);     // HOST-VERIFIKATION AKTIVIEREN!
    
    $response = curl_exec($ch);
    $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $error = curl_error($ch);
    curl_close($ch);
    
    echo "<p>HTTP Code: $http_code</p>";
    if ($error) {
        echo "<p>cURL Error: $error</p>";
        return false;
    }
    
    if ($http_code !== 200) {
        echo "<p>HTTP Error: $http_code</p>";
        return false;
    }
    
    $data = json_decode($response, true);
    if (!$data) {
        echo "<p>JSON Parse Error</p>";
        echo "<pre>Response: $response</pre>";
        return false;
    }
    
    return $data;
}

// API-Daten abrufen
echo "<h2>API-Test</h2>";
$api_data = fetch_canteen_data($scandy_api_url);

if ($api_data) {
    echo "<p>✅ API-Verbindung erfolgreich!</p>";
    echo "<pre>API Response: " . json_encode($api_data, JSON_PRETTY_PRINT) . "</pre>";
    
    // Daten in CSV-Format konvertieren (wie die alte kantine.php)
    echo "<h2>CSV-Konvertierung</h2>";
    
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
    
    echo "<p>Konvertierte Daten:</p>";
    echo "<p>Datum: " . implode(', ', $datum) . "</p>";
    echo "<p>Menu1: " . implode(', ', $menu1) . "</p>";
    echo "<p>Menu2: " . implode(', ', $menu2) . "</p>";
    echo "<p>Dessert: " . implode(', ', $dessert) . "</p>";
    
    // Datum-Vergleich testen
    echo "<h2>Datum-Vergleich Test</h2>";
    $heute1 = date("d.m.Y");
    $heute2 = date("j.n.Y");
    $heute3 = date("j.m.Y");
    
    echo "<p>Heute (d.m.Y): $heute1</p>";
    echo "<p>Heute (j.n.Y): $heute2</p>";
    echo "<p>Heute (j.m.Y): $heute3</p>";
    
    $index = null;
    for($i = 0; $i < count($datum); ++$i) {
        $datum_clean = substr($datum[$i], -10); // Extrahiere "DD.MM.YYYY" aus "Montag, DD.MM.YYYY"
        echo "<p>Vergleiche: '$heute1' mit '$datum_clean'</p>";
        
        if ($heute1 == $datum_clean || $heute2 == $datum_clean || $heute3 == $datum_clean) {
            $index = $i;
            echo "<p>✅ Match gefunden bei Index $i</p>";
            break;
        }
    }
    
    if ($index === null) {
        echo "<p>❌ Kein Match für heute gefunden!</p>";
        echo "<p>Verfügbare Daten: " . implode(', ', $datum) . "</p>";
    }
    
} else {
    echo "<p>❌ API-Verbindung fehlgeschlagen!</p>";
}

echo "<h2>PHP-Info</h2>";
echo "<p>PHP Version: " . phpversion() . "</p>";
echo "<p>cURL verfügbar: " . (function_exists('curl_init') ? 'Ja' : 'Nein') . "</p>";
echo "<p>JSON verfügbar: " . (function_exists('json_decode') ? 'Ja' : 'Nein') . "</p>";
?> 