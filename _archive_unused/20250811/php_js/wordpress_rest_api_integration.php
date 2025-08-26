<?php
/**
 * WordPress REST API Integration für Kantinenplan
 * Moderne Alternative zur custom PHP-Datei
 */

// Verhindere direkten Zugriff
if (!defined('ABSPATH')) {
    exit;
}

/**
 * Kantinenplan REST API Endpoint
 */
class Canteen_Plan_REST_API {
    
    public function __construct() {
        add_action('rest_api_init', array($this, 'register_routes'));
        add_action('wp_enqueue_scripts', array($this, 'enqueue_scripts'));
    }
    
    /**
     * Registriert REST API Routes
     */
    public function register_routes() {
        register_rest_route('canteen-plan/v1', '/current-week', array(
            'methods' => 'GET',
            'callback' => array($this, 'get_current_week'),
            'permission_callback' => '__return_true'
        ));
        
        register_rest_route('canteen-plan/v1', '/status', array(
            'methods' => 'GET',
            'callback' => array($this, 'get_status'),
            'permission_callback' => '__return_true'
        ));
    }
    
    /**
     * Holt aktuelle Woche von Scandy API
     */
    public function get_current_week($request) {
        $api_url = get_option('canteen_plan_api_url', 'http://your-scandy-server.com');
        $cache_duration = get_option('canteen_plan_cache_duration', 300);
        
        // Prüfe Cache
        $cache_key = 'canteen_plan_current_week';
        $cached_data = get_transient($cache_key);
        
        if ($cached_data !== false) {
            return new WP_REST_Response($cached_data, 200);
        }
        
        // Hole Daten von Scandy API
        $response = wp_remote_get($api_url . '/api/canteen/current_week', array(
            'timeout' => 10,
            'user-agent' => 'WordPress-Canteen-Plan/1.0'
        ));
        
        if (is_wp_error($response)) {
            return new WP_Error('api_error', 'Fehler beim Laden der Daten', array('status' => 500));
        }
        
        $body = wp_remote_retrieve_body($response);
        $data = json_decode($body, true);
        
        if (!$data || !isset($data['success']) || !$data['success']) {
            return new WP_Error('api_error', 'Ungültige API-Antwort', array('status' => 500));
        }
        
        // Cache speichern
        set_transient($cache_key, $data, $cache_duration);
        
        return new WP_REST_Response($data, 200);
    }
    
    /**
     * Gibt API-Status zurück
     */
    public function get_status($request) {
        $api_url = get_option('canteen_plan_api_url', 'http://your-scandy-server.com');
        
        $response = wp_remote_get($api_url . '/api/canteen/status', array(
            'timeout' => 5,
            'user-agent' => 'WordPress-Canteen-Plan/1.0'
        ));
        
        if (is_wp_error($response)) {
            return new WP_REST_Response(array(
                'success' => false,
                'error' => 'Verbindung fehlgeschlagen'
            ), 500);
        }
        
        $body = wp_remote_retrieve_body($response);
        $data = json_decode($body, true);
        
        return new WP_REST_Response($data ?: array('success' => false), 200);
    }
    
    /**
     * Lädt JavaScript und CSS
     */
    public function enqueue_scripts() {
        wp_enqueue_script(
            'canteen-plan-api',
            plugin_dir_url(__FILE__) . 'js/canteen-plan-api.js',
            array(),
            '1.0.0',
            true
        );
        
        wp_localize_script('canteen-plan-api', 'canteenPlanApi', array(
            'restUrl' => rest_url('canteen-plan/v1/'),
            'nonce' => wp_create_nonce('wp_rest')
        ));
        
        wp_enqueue_style(
            'canteen-plan-styles',
            plugin_dir_url(__FILE__) . 'css/canteen-plan.css',
            array(),
            '1.0.0'
        );
    }
}

// Initialisiere REST API
new Canteen_Plan_REST_API();

/**
 * Kantinenplan Widget
 */
class Canteen_Plan_Widget extends WP_Widget {
    
    public function __construct() {
        parent::__construct(
            'canteen_plan_widget',
            'Kantinenplan Widget',
            array('description' => 'Zeigt den aktuellen Kantinenplan an')
        );
    }
    
    public function widget($args, $instance) {
        echo $args['before_widget'];
        
        if (!empty($instance['title'])) {
            echo $args['before_title'] . apply_filters('widget_title', $instance['title']) . $args['after_title'];
        }
        
        echo '<div id="canteen-plan-widget" class="canteen-plan-widget">';
        echo '<div class="loading">Lade Kantinenplan...</div>';
        echo '</div>';
        
        echo $args['after_widget'];
    }
    
    public function form($instance) {
        $title = !empty($instance['title']) ? $instance['title'] : 'Kantinenplan';
        ?>
        <p>
            <label for="<?php echo $this->get_field_id('title'); ?>">Titel:</label>
            <input class="widefat" id="<?php echo $this->get_field_id('title'); ?>" 
                   name="<?php echo $this->get_field_name('title'); ?>" 
                   type="text" value="<?php echo esc_attr($title); ?>">
        </p>
        <?php
    }
    
    public function update($new_instance, $old_instance) {
        $instance = array();
        $instance['title'] = (!empty($new_instance['title'])) ? strip_tags($new_instance['title']) : '';
        return $instance;
    }
}

// Widget registrieren
function register_canteen_plan_widget() {
    register_widget('Canteen_Plan_Widget');
}
add_action('widgets_init', 'register_canteen_plan_widget');

/**
 * Admin-Menü
 */
function canteen_plan_admin_menu() {
    add_options_page(
        'Kantinenplan API Einstellungen',
        'Kantinenplan API',
        'manage_options',
        'canteen-plan-api-settings',
        'canteen_plan_api_settings_page'
    );
}
add_action('admin_menu', 'canteen_plan_admin_menu');

/**
 * Einstellungsseite
 */
function canteen_plan_api_settings_page() {
    if (isset($_POST['submit'])) {
        update_option('canteen_plan_api_url', sanitize_text_field($_POST['api_url']));
        update_option('canteen_plan_cache_duration', intval($_POST['cache_duration']));
        echo '<div class="notice notice-success"><p>Einstellungen gespeichert!</p></div>';
    }
    
    $api_url = get_option('canteen_plan_api_url', 'http://your-scandy-server.com');
    $cache_duration = get_option('canteen_plan_cache_duration', 300);
    
    ?>
    <div class="wrap">
        <h1>Kantinenplan API Einstellungen</h1>
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
        
        <h2>API-Endpunkte</h2>
        <p>Die folgenden REST API-Endpunkte sind verfügbar:</p>
        <ul>
            <li><code><?php echo rest_url('canteen-plan/v1/current-week'); ?></code> - Aktuelle Woche</li>
            <li><code><?php echo rest_url('canteen-plan/v1/status'); ?></code> - API-Status</li>
        </ul>
        
        <h2>Widget</h2>
        <p>Fügen Sie das "Kantinenplan Widget" zu Ihren Sidebars hinzu.</p>
        
        <h2>JavaScript Integration</h2>
        <p>Verwenden Sie die globale Variable <code>canteenPlanApi</code> für API-Calls:</p>
        <pre><code>
// Aktuelle Woche laden
fetch(canteenPlanApi.restUrl + 'current-week')
    .then(response => response.json())
    .then(data => console.log(data));
        </code></pre>
    </div>
    <?php
}

/**
 * Plugin-Aktivierung
 */
function canteen_plan_api_activate() {
    add_option('canteen_plan_api_url', 'http://your-scandy-server.com');
    add_option('canteen_plan_cache_duration', 300);
}
register_activation_hook(__FILE__, 'canteen_plan_api_activate');
?> 