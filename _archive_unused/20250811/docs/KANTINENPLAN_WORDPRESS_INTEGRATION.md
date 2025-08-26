# Kantinenplan WordPress-Integration

## Übersicht

Diese Anleitung beschreibt, wie Sie den Kantinenplan von Scandy in WordPress einbinden können. Die Integration ersetzt die alte CSV-basierte Lösung durch eine moderne API-basierte Lösung.

## Voraussetzungen

- WordPress-Installation
- Scandy-System läuft auf `http://192.168.178.56:5000`
- PHP mit cURL-Unterstützung
- Schreibrechte im WordPress-Theme-Verzeichnis

## Installation

### 1. Datei herunterladen

Laden Sie die `kantine_wordpress.php` Datei herunter und kopieren Sie sie in Ihr WordPress-Theme:

```bash
# Kopieren Sie die Datei in Ihr Theme-Verzeichnis
cp kantine_wordpress.php /path/to/wordpress/wp-content/themes/your-theme/includes/kantine.php
```

### 2. Berechtigungen setzen

```bash
# Setzen Sie die richtigen Berechtigungen
chown www-data:www-data /path/to/wordpress/wp-content/themes/your-theme/includes/kantine.php
chmod 644 /path/to/wordpress/wp-content/themes/your-theme/includes/kantine.php
```

## Einbindung in WordPress

### Option 1: Als Shortcode einbinden

Fügen Sie folgenden Code in die `functions.php` Ihres Themes ein:

```php
// Kantinenplan Shortcode
add_shortcode('kantinenplan', function() {
    ob_start();
    include_once get_template_directory() . '/includes/kantine.php';
    return ob_get_clean();
});
```

**Verwendung:** `[kantinenplan]` in WordPress-Seiten oder Posts

### Option 2: Als Template-Teil einbinden

Fügen Sie folgenden Code in Ihre Template-Datei ein (z.B. `page-kantine.php`):

```php
<?php include_once get_template_directory() . '/includes/kantine.php'; ?>
```

### Option 3: Als Widget einbinden

Erstellen Sie ein WordPress-Widget:

```php
class Kantinenplan_Widget extends WP_Widget {
    public function __construct() {
        parent::__construct(
            'kantinenplan_widget',
            'Kantinenplan Widget',
            array('description' => 'Zeigt den aktuellen Kantinenplan an')
        );
    }

    public function widget($args, $instance) {
        echo $args['before_widget'];
        echo $args['before_title'] . 'Kantinenplan' . $args['after_title'];
        include_once get_template_directory() . '/includes/kantine.php';
        echo $args['after_widget'];
    }
}

// Widget registrieren
add_action('widgets_init', function() {
    register_widget('Kantinenplan_Widget');
});
```

## Konfiguration

### API-URL anpassen

Falls Ihre Scandy-Installation auf einem anderen Server läuft, passen Sie die URL in der `kantine_wordpress.php` an:

```php
// Konfiguration
$scandy_api_url = 'http://ihre-scandy-server.com:5000/api/canteen/current_week';
```

### Cache-Einstellungen

Die Datei verwendet ein 5-Minuten-Cache für bessere Performance. Sie können dies anpassen:

```php
$cache_duration = 300; // 5 Minuten Cache
```

## Funktionalität

### Automatische Datenverarbeitung

- **API-Abfrage:** Lädt Daten von der Scandy-API
- **Caching:** Speichert Daten für 5 Minuten
- **Fehlerbehandlung:** Zeigt Fallback-Nachricht bei Problemen
- **Datums-Logik:** Zeigt die aktuelle Woche an

### HTML-Ausgabe

Die Datei erzeugt eine HTML-Tabelle im gleichen Format wie die alte CSV-Lösung:

```html
<table>
  <tr>
    <th>Tag, Datum</th>
    <th>Menü   1</th>
    <th>Menü   2 (Vegan)</th>
  </tr>
  <tr>
    <td>Montag, 04.08.2025</td>
    <td>Schnitzel mit Pommes</td>
    <td>Veganes Curry</td>
  </tr>
  <!-- ... weitere Zeilen -->
</table>
```

### CSS-Klassen

Die Tabelle verwendet die gleichen CSS-Klassen wie die alte Lösung:

- `optionallyhidden` - Für nicht-heutige Tage
- Standard-Tabellen-Styling

## Troubleshooting

### Häufige Probleme

#### 1. "Fehler beim Laden der Kantinenplan-Daten!"

**Ursache:** API nicht erreichbar oder Scandy nicht gestartet

**Lösung:**
- Prüfen Sie, ob Scandy läuft: `http://192.168.178.56:5000`
- Prüfen Sie die API-URL in der PHP-Datei
- Prüfen Sie die Netzwerkverbindung

#### 2. "Datum nicht in der API gefunden!"

**Ursache:** Keine Daten für die aktuelle Woche vorhanden

**Lösung:**
- Geben Sie Daten in Scandy ein: `/canteen`
- Prüfen Sie das Datumsformat

#### 3. cURL-Fehler

**Ursache:** PHP cURL-Erweiterung nicht installiert

**Lösung:**
```bash
sudo apt install php-curl
sudo systemctl restart apache2
```

### Debug-Modus

Fügen Sie temporär Debug-Ausgaben hinzu:

```php
// In kantine_wordpress.php vor display_canteen_table()
error_reporting(E_ALL);
ini_set('display_errors', 1);
```

## Performance-Optimierung

### Cache-Verwaltung

Die Datei erstellt automatisch Cache-Dateien. Sie können diese manuell löschen:

```bash
rm /path/to/wordpress/wp-content/themes/your-theme/includes/canteen_cache.json
```

### CDN-Integration

Für bessere Performance können Sie die Tabelle in ein CDN einbinden oder weitere Caching-Mechanismen verwenden.

## Sicherheit

### API-Schutz

Für Produktionsumgebungen sollten Sie:

1. **HTTPS verwenden** statt HTTP
2. **API-Key implementieren** für zusätzliche Sicherheit
3. **Rate-Limiting** auf der Scandy-API aktivieren

### WordPress-Sicherheit

- Die PHP-Datei läuft im WordPress-Kontext
- Alle WordPress-Sicherheitsmaßnahmen gelten
- Keine zusätzlichen Sicherheitsrisiken

## Support

Bei Problemen:

1. Prüfen Sie die WordPress-Fehler-Logs
2. Testen Sie die API direkt: `http://192.168.178.56:5000/api/canteen/current_week`
3. Prüfen Sie die PHP-Fehler-Logs

## Changelog

### Version 1.0
- Erste Version mit API-Integration
- Vollständige Kompatibilität mit alter CSV-Lösung
- Caching für bessere Performance
- Fehlerbehandlung und Fallback-Mechanismen 