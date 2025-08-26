<?php

// Konfiguration - HIER MÜSSEN SIE DIE IP-ADRESSE IHRES SCANDY-SERVERS EINTRAGEN
$scandy_api_url = 'https://10.42.2.107';  // ÄNDERN SIE DIESE IP-ADRESSE! HTTPS VERWENDEN!

// Funktion zum Abrufen der API-Daten (ersetzt CSV-Lesung)
function fetch_api_data($api_url) {
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $api_url . '/api/canteen/current_week');
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 10);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, true);  // SSL-VERIFIKATION AKTIVIEREN!
    curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, 2);     // HOST-VERIFIKATION AKTIVIEREN!
    curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 5);
    
    $response = curl_exec($ch);
    $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $error = curl_error($ch);
    curl_close($ch);
    
    if ($error || $http_code !== 200) {
        return false;
    }
    
    $data = json_decode($response, true);
    if (!$data || !isset($data['week'])) {
        return false;
    }
    
    return $data['week'];
}

// API-Daten abrufen (ersetzt CSV-Lesung)
$api_data = fetch_api_data($scandy_api_url);

if (!$api_data) {
    echo "Kantinenplan-Daten konnten nicht geladen werden.";
    exit;
}

// Daten in das gleiche Format wie die alte CSV-Struktur konvertieren
$csvArray = [];
$csvArray[] = ['Datum', 'Menü1', 'Menü2', 'Dessert']; // Header (wird ignoriert)

foreach ($api_data as $meal) {
    $csvArray[] = [
        $meal['date'],
        $meal['meat_dish'] ?? '',
        $meal['vegan_dish'] ?? '',
        $meal['dessert'] ?? ''
    ];
}

// Ab hier ist der Code IDENTISCH zur alten kantine.php
$datum = array();
$menu1 = array();
$menu2 = array();
$dessert = array();

//start at 1 (A2, B2, etc) to ignore the Header Row
for($i = 1; $i < count($csvArray); ++$i) {
    if(!(empty($csvArray[$i][0])))// !== NULL)// && $csvArray[$i][0] !== NULL)
    {
        array_push($datum, $csvArray[$i][0]);
    }
    if(!(empty($csvArray[$i][1] ?? '')))// && $csvArray[$i][1] !== NULL)
    {
        //echo $csvArray[$i][1];
        array_push($menu1, $csvArray[$i][1] ?? '');
    }
    if(!(empty($csvArray[$i][2] ?? '')))// && $csvArray[$i][2] !== NULL)
    {
        array_push($menu2, $csvArray[$i][2] ?? '');
    }

    if(!(empty($csvArray[$i][3] ?? '')))// && $csvArray[$i][3] !== NULL)
    {
        array_push($dessert, $csvArray[$i][3] ?? '');
    }
}

$heute1 = date("d.m.Y");
$heute2 = date("j.n.Y");
$heute3 = date("j.m.Y");
//$heute1 = "6.2.2024";
//$heute2 = "6.2.2024";
//$heute3 = "6.02.2024";
$index;
//echo substr($datum[$i],-9)."<br />";
//find index where today's date is within array $datum[]
for($i = 0; $i < count($datum); ++$i) {
    if ($heute1 == substr($datum[$i],-10) or $heute2 == substr($datum[$i],-8) or $heute2 == substr($datum[$i],-9) or $heute3 == substr($datum[$i],-8) or $heute3 == substr($datum[$i],-9)) {
        $index = $i;
        break;
    }
    //      else {
    //              echo substr($datum[$i],-8)."<br />";
    //      }
}

if ($index === NULL){
    echo "Datum $heute1 und Datum $heute2 nicht in der CSV datei gefunden!";
    print_r($datum);
    exit;
}

//echo $index."<br />";
//find out what index Monday is relative to today so we can set the index value to monday and print the entire week
$remainder;
if ($index > 0){
    $remainder = ($index % 5);
}
if ($remainder > 0) {
    $index = $index - $remainder;
}

//echo $remainder."<br />";

//echo $index."<br />";

//print_r($datum);
$endofweek = $index + 5;
$today = $index + $remainder;
//print_r($menu1[$index]);

////print the table
echo("<table> <tr> <th>Tag, Datum</th> <th>Menü   1</th> <th>Menü   2 (Vegan)</th></tr>");
for($index; $index < $endofweek; ++$index) {
    if ($index == $today) {
        echo("<tr> <td>$datum[$index]</td> <td>$menu1[$index]</td> <td>$menu2[$index]</td></tr> ");
    }
    else {
        echo("<tr class='optionallyhidden'> <td>$datum[$index]</td> <td>$menu1[$index]</td> <td>$menu2[$index]</td></tr> ");
    }
}
echo( "</table>");

?> 