<?php
/*
Plugin Name:    WP Geo XML-RPC Methods
Plugin URI:     http://github.com/dkukral/cms_utility/
Description:    XML Methods to get/set WP-Geo Options
Version:        0.1
Author:         Don Kukral
Author URI:     http://github.com/dkukral/
 */


function check_xmlrpc($username, $password) {
    
	if ( !get_option( 'enable_xmlrpc' ) ) {
		return new IXR_Error( 405, sprintf( __( 'XML-RPC services are disabled on this blog.  An admin user can enable them at %s'),  
		    admin_url('options-writing.php') ) );
    }

	$user = wp_authenticate($username, $password);
	if (is_wp_error($user)) {
        return new IXR_Error(403, __('Bad login/pass combination.'));
	}
	
	return true;
}

add_filter( 'xmlrpc_methods', 'wp_geo_xmlrpc_methods' );
function wp_geo_xmlrpc_methods( $methods ) {
    $methods['wpgeo.getCoords'] = 'get_coords';
    $methods['wpgeo.setCoords'] = 'set_coords';

    return $methods;
}

function get_coords( $args ) {
    global $wpdb;
    $wpdb->escape($args);
        
	$post_ID     = (int) $args[0];
	$username  = $args[1];
	$password   = $args[2];

    $error = check_xmlrpc($username, $password);
    if (is_a($error, 'IXR_Error')) { return $error; }

    if (!get_post($post_ID)) { return new IXR_Error(404, 'Post does not exist'); }

    $_wp_geo_latitude = get_post_meta($post_ID, '_wp_geo_latitude', true);
    $_wp_geo_longitude = get_post_meta($post_ID, '_wp_geo_longitude', true);
    return Array($_wp_geo_latitude, $_wp_geo_longitude);
}

function set_coords( $args ) {
    global $wpdb;
    $wpdb->escape($args);
        
	$post_ID     = (int) $args[0];
	$username  = $args[1];
	$password   = $args[2];
	$coords = $args[3];
	
    $error = check_xmlrpc($username, $password);
    if (is_a($error, 'IXR_Error')) { return $error; }

    if (!$post = get_post($post_ID)) { return new IXR_Error(404, 'Post does not exist'); }
    
    $_wp_geo_latitude = $coords['_wp_geo_latitude'];
    $_wp_geo_longitude = $coords['_wp_geo_longitude'];
    
    update_post_meta($post_ID, '_wp_geo_latitude', $_wp_geo_latitude);
    update_post_meta($post_ID, '_wp_geo_longitude', $_wp_geo_longitude);
    return Array($_wp_geo_latitude, $_wp_geo_longitude);
}
?>
